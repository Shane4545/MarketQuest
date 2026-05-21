"""Collect one unified reality snapshot from all providers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from marketquest.config import load_config, offline_training_requested
from marketquest.data_sources import alpaca_data_provider, finnhub_provider, yfinance_fallback
from marketquest.data_sources.company_press_provider import fetch_company_press
from marketquest.data_sources.government_provider import fetch_government_feeds
from marketquest.data_sources.market_hours import is_regular_session_open, market_status
from marketquest.data_sources.public_posts_provider import fetch_public_posts_records
from marketquest.data_sources.sec_edgar_provider import fetch_recent_filings
from marketquest.data_sources.fred_provider import fetch_macro
from marketquest.cross_asset.cross_asset_features import enrich_snapshot_cross_asset
from marketquest.data_sources.forex_provider import fetch_cross_asset_quotes
from marketquest.data_sources.rss_news_provider import fetch_headlines
from marketquest.data_sources.base import utc_now_iso
from marketquest.entity_graph.graph_store import GraphStore
from marketquest.events.classifier import process_event_batch
from marketquest.freshness import age_minutes, is_scoring_eligible
from marketquest.reality_engine.snapshot import finalize_snapshot, load_offline_training_snapshot, write_snapshot
from marketquest.scoring.orchestrator import run_all_agents_from_snapshot
from marketquest.game.leaderboard import marks_from_snapshot


def _market_session_label(status: str) -> str:
    return {
        "open": "open",
        "pre": "pre_market",
        "post": "after_hours",
        "closed": "closed",
    }.get(status, status)


def _news_to_raw(n: dict[str, Any], fetched: str) -> dict[str, Any]:
    pub = n.get("published_at") or fetched
    return {
        "source": n.get("source", "rss"),
        "source_url": n.get("url", ""),
        "fetched_at_utc": fetched,
        "published_at_utc": pub,
        "symbols": n.get("symbols") or [],
        "entities": [],
        "raw_title": n.get("headline", ""),
        "summary": n.get("summary") or n.get("headline", ""),
        "confidence": n.get("confidence", 0.5),
        "freshness_minutes": age_minutes(pub),
        "license_note": "headline only, no full article stored",
    }


def _filing_to_raw(f: dict[str, Any], fetched: str) -> dict[str, Any]:
    return {
        "source": "sec_edgar",
        "source_url": f.get("url", ""),
        "fetched_at_utc": fetched,
        "published_at_utc": f.get("filed_at") or fetched,
        "symbols": [f.get("symbol", "")],
        "entities": [],
        "raw_title": f"{f.get('symbol')} filed {f.get('form_type')}",
        "summary": f"SEC filing {f.get('form_type')} for {f.get('symbol')}",
        "form_type": f.get("form_type"),
        "confidence": 0.9,
        "freshness_minutes": age_minutes(f.get("filed_at") or fetched),
        "license_note": "SEC public filing metadata only",
    }


def _merge_quotes(symbols: list[str]) -> tuple[list[dict], dict[str, Any]]:
    provider_status: dict[str, Any] = {}
    by_sym: dict[str, dict] = {}

    for name, mod in [
        ("finnhub", finnhub_provider),
        ("alpaca", alpaca_data_provider),
    ]:
        rows, res = mod.quotes_with_provenance(symbols)
        provider_status[name] = res.status_dict()
        for r in rows:
            sym = r["symbol"]
            prov = r.get("provenance", {})
            if sym not in by_sym or prov.get("freshness") == "LIVE":
                by_sym[sym] = r

    missing = [s for s in symbols if s.upper() not in by_sym]
    if missing:
        rows, res = yfinance_fallback.quotes_with_provenance(missing)
        provider_status["yfinance"] = res.status_dict()
        for r in rows:
            sym = r["symbol"]
            if sym not in by_sym:
                by_sym[sym] = r

    prices = [by_sym[s.upper()] for s in symbols if s.upper() in by_sym]
    return prices, provider_status


def _build_freshness_summary(
    provider_status: dict[str, Any],
    prices: list[dict],
    *,
    scoring_ok: bool,
) -> dict[str, Any]:
    stale_providers = [
        k for k, v in provider_status.items() if v.get("status") in ("STALE", "OFFLINE")
    ]
    quote_freshness = [
        (p.get("provenance") or {}).get("freshness", "OFFLINE") for p in prices
    ]
    label = "live"
    if not prices:
        label = "offline"
    elif "STALE" in quote_freshness:
        label = "stale"
    elif all(f == "OFFLINE" for f in quote_freshness):
        label = "offline"
    elif any(f == "DELAYED" for f in quote_freshness):
        label = "delayed"
    return {
        "label": label,
        "scoring_data_eligible": scoring_ok,
        "stale_providers": stale_providers,
        "quote_count": len(prices),
    }


def collect_snapshot(
    repo: Path,
    *,
    offline_training: bool | None = None,
) -> dict[str, Any]:
    if offline_training_requested(offline_training):
        snap = load_offline_training_snapshot(repo)
        if snap:
            write_snapshot(repo, snap)
            return snap

    cfg = load_config(repo)
    symbols = cfg["symbols"]
    fetched = utc_now_iso()
    session_open = is_regular_session_open()
    mstatus = market_status()
    market_session = _market_session_label(mstatus)

    try:
        from marketquest.data_sources.alpaca_data_provider import try_start_stream

        if try_start_stream(symbols):
            provider_status_pre = {"alpaca_stream": {"status": "LIVE", "fallback": False}}
        else:
            provider_status_pre = {}
    except Exception:
        provider_status_pre = {}

    prices, provider_status = _merge_quotes(symbols)
    provider_status.update(provider_status_pre)

    sec_res = fetch_recent_filings(symbols)
    provider_status["sec_edgar"] = sec_res.status_dict()
    filings = [f.to_dict() for f in sec_res.filings]

    fred_res = fetch_macro()
    provider_status["fred"] = fred_res.status_dict()
    macro = [m.to_dict() for m in fred_res.macro]

    forex_quotes = fetch_cross_asset_quotes(repo)
    live_fx = [q for q in forex_quotes if q.get("status") not in ("OFFLINE", None) and q.get("last") is not None]
    provider_status["forex"] = {
        "status": "LIVE" if live_fx else ("DELAYED" if forex_quotes else "OFFLINE"),
        "ok": bool(live_fx or forex_quotes),
        "count": len(forex_quotes),
        "live_count": len(live_fx),
        "offline_count": len([q for q in forex_quotes if q.get("status") == "OFFLINE"]),
    }
    oil_point = next((m for m in macro if m.get("series_id") == "DCOILWTICO"), None)

    raw_events: list[dict[str, Any]] = []

    rss_res = fetch_headlines(symbols)
    provider_status["rss"] = rss_res.status_dict()
    for n in rss_res.news:
        raw_events.append(_news_to_raw(n.to_dict(), fetched))

    fh_news = finnhub_provider.fetch_company_news(symbols)
    for n in fh_news:
        raw_events.append(_news_to_raw(n if isinstance(n, dict) else n.to_dict(), fetched))
    if fh_news:
        provider_status.setdefault("finnhub", {})["news_count"] = len(fh_news)

    gov_records, gov_res = fetch_government_feeds()
    provider_status["government"] = gov_res.status_dict()
    raw_events.extend(gov_records)

    press_records, press_res = fetch_company_press(cfg.get("press_rss"))
    provider_status["company_press"] = press_res.status_dict()
    raw_events.extend(press_records)

    x_records, x_res = fetch_public_posts_records()
    provider_status["x_api"] = x_res.status_dict()
    raw_events.extend(x_records)

    for f in filings:
        raw_events.append(_filing_to_raw(f, fetched))

    classified = process_event_batch(raw_events, repo, watchlist=symbols)
    graph = GraphStore(repo)
    entity_updates = graph.merge_from_events(classified)

    public_figure_events = [
        e for e in classified if e.get("event_type") == "public_figure_statement"
    ]

    movers = sorted(
        prices,
        key=lambda x: abs(float(x.get("change_pct") or 0)),
        reverse=True,
    )[:5]

    any_stale = any(
        (p.get("provenance") or {}).get("freshness") == "STALE" for p in prices
    )
    scoring_ok = bool(prices) and not any_stale and all(
        is_scoring_eligible(
            (p.get("provenance") or {}).get("freshness", "OFFLINE"),
            market_session_open=session_open,
        )
        for p in prices
    )

    partial: dict[str, Any] = {
        "timestamp_utc": fetched,
        "market_status": mstatus,
        "market_session": market_session,
        "provider_status": provider_status,
        "symbols_checked": symbols,
        "prices": prices,
        "movers": movers,
        "news_events": classified[:50],
        "public_figure_events": public_figure_events[:20],
        "entity_graph_updates": entity_updates,
        "sec_filings": filings,
        "macro_indicators": macro,
        "currencies": forex_quotes,
        "scoring_data_eligible": scoring_ok,
        "offline_training_mode": False,
        "tagline": "Real markets, real events, real scoring, simulated portfolios.",
    }
    partial["freshness"] = _build_freshness_summary(provider_status, prices, scoring_ok=scoring_ok)

    cross_asset = enrich_snapshot_cross_asset(repo, {**partial, "cross_asset": {"forex": forex_quotes, "macro": macro, "oil": oil_point}})
    partial["cross_asset"] = cross_asset
    partial["currencies"] = cross_asset.get("forex", forex_quotes)
    partial["regime"] = cross_asset.get("regime", {})

    if scoring_ok:
        picks_payload = run_all_agents_from_snapshot(repo, partial)
        partial["ai_agent_picks"] = picks_payload.get("picks", [])
        partial["agent_predictions"] = picks_payload.get("picks", [])
    else:
        partial["ai_agent_picks"] = []
        partial["agent_predictions"] = []
        partial["stale_warning"] = (
            "Data stale — not used for current competition scoring."
            if any_stale
            else "Insufficient live data for competition scoring."
        )

    partial["leaderboard_marks"] = marks_from_snapshot(repo, partial)
    partial = finalize_snapshot(partial)
    write_snapshot(repo, partial)
    return partial
