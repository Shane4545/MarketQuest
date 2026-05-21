"""HTTP-facing MarketQuest data loaders — snapshot-first."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from marketquest.config import ALLOWED_WORDING, DISCLAIMER, FORBIDDEN_WORDING, TAGLINE, load_config, offline_training_requested, today_iso
from marketquest.career.careers import get_careers
from marketquest.education.glossary import get_education, get_glossary
from marketquest.education.lesson_cards import get_lessons
from marketquest.education.quiz_engine import get_active_challenge, submit_challenge
from marketquest.research_scout.ai_tool_registry import query_registry
from marketquest.research_scout.weekly_research_report import load_latest_report
from marketquest.cross_asset.cross_asset_features import enrich_snapshot_cross_asset
from marketquest.cross_asset.currency_provider import fetch_currencies
from marketquest.cross_asset.regime_detector import detect_regime
from marketquest.entity_graph.graph_store import GraphStore
from marketquest.game.leaderboard import build_leaderboard_from_picks, load_leaderboard
from marketquest.game.portfolio import load_portfolio_valued, paper_trade
from marketquest.paths import ensure_dirs
from marketquest.reality_engine.collector import collect_snapshot
from marketquest.reality_engine.snapshot import load_latest_snapshot, load_offline_training_snapshot
from marketquest.scoring.orchestrator import AGENT_IDS, run_all_agents, run_all_agents_from_snapshot
from marketquest.scoring.reality_score import score_universe_from_snapshot
from marketquest.learning.outcome_labels import label_horizon_outcomes
from marketquest.data_sources.market_hours import is_regular_session_open, market_status, refresh_interval_seconds


def _resolve_snapshot(
    repo: Path,
    *,
    training: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    if refresh and not offline_training_requested(training):
        return collect_snapshot(repo, offline_training=False)
    if offline_training_requested(training):
        snap = load_offline_training_snapshot(repo)
        if snap:
            return snap
    snap = load_latest_snapshot(repo)
    if snap:
        return snap
    if offline_training_requested(training):
        return load_offline_training_snapshot(repo) or {}
    return collect_snapshot(repo, offline_training=False)


def refresh_reality(repo: Path, *, training: bool | None = None) -> dict[str, Any]:
    if offline_training_requested(training):
        snap = load_offline_training_snapshot(repo)
        if snap:
            from marketquest.reality_engine.snapshot import write_snapshot

            write_snapshot(repo, snap)
            return {"ok": True, "snapshot": snap, "mode": "offline_training"}
        return {"error": "offline training fixtures missing"}
    snap = collect_snapshot(repo, offline_training=False)
    return {"ok": True, "snapshot": snap, "mode": "live"}


def _watchlist_from_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    prices = snap.get("prices", [])
    return {
        "as_of": (snap.get("timestamp_utc") or today_iso())[:10],
        "timestamp_utc": snap.get("timestamp_utc"),
        "data_mode": "offline_training" if snap.get("offline_training_mode") else "live",
        "quotes": [
            {
                "symbol": p.get("symbol"),
                "last": p.get("last"),
                "change_pct": p.get("change_pct"),
                "volume": p.get("volume"),
                "provenance": p.get("provenance"),
                "reality_score": next(
                    (
                        r.get("reality_score")
                        for r in snap.get("reality_scores", [])
                        if r.get("symbol") == p.get("symbol")
                    ),
                    None,
                ),
            }
            for p in prices
        ],
        "symbol_count": len(prices),
        "movers": snap.get("movers", []),
        "scoring_data_eligible": snap.get("scoring_data_eligible"),
        "stale_warning": snap.get("stale_warning"),
    }


def get_watchlist(
    repo: Path,
    *,
    mock: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    snap = _resolve_snapshot(repo, training=mock, refresh=refresh)
    return _watchlist_from_snapshot(snap)


def get_picks(
    repo: Path,
    *,
    as_of: str | None = None,
    mock: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    if offline_training_requested(mock):
        return run_all_agents(repo, as_of=as_of, mock=True, refresh=True)
    snap = _resolve_snapshot(repo, training=mock, refresh=refresh)
    if snap.get("ai_agent_picks") and not refresh:
        return {
            "as_of": as_of or (snap.get("timestamp_utc") or "")[:10],
            "data_mode": "offline_training" if snap.get("offline_training_mode") else "live",
            "picks": snap["ai_agent_picks"],
            "reality_scores": snap.get("reality_scores") or score_universe_from_snapshot(snap),
        }
    return run_all_agents(repo, as_of=as_of, mock=mock, refresh=refresh, snapshot=snap)


def get_portfolio(
    repo: Path,
    user_id: str = "default",
    *,
    mock: bool | None = None,
) -> dict[str, Any]:
    return load_portfolio_valued(repo, user_id, mock=mock)


def get_leaderboard(
    repo: Path,
    *,
    week: str | None = None,
    mock: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    snap = _resolve_snapshot(repo, training=mock, refresh=refresh)
    portfolio = load_portfolio_valued(repo, "default", mock=mock)
    return load_leaderboard(repo, week=week, mock=mock, refresh=refresh, snapshot=snap, portfolio=portfolio)


def get_education_panel(
    repo: Path,
    *,
    mock: bool | None = None,
) -> dict[str, Any]:
    picks_data = get_picks(repo, mock=mock)
    return get_education(picks_data.get("picks", []))


def get_dashboard(
    repo: Path,
    *,
    mock: bool | None = None,
    refresh: bool = False,
    user_id: str = "default",
) -> dict[str, Any]:
    ensure_dirs(repo)
    training = offline_training_requested(mock)
    snap = _resolve_snapshot(repo, training=training, refresh=refresh)

    if not snap.get("ai_agent_picks") and snap.get("scoring_data_eligible"):
        picks_payload = run_all_agents_from_snapshot(repo, snap)
        snap["ai_agent_picks"] = picks_payload.get("picks", [])
        snap["reality_scores"] = picks_payload.get("reality_scores", [])

    if not snap.get("reality_scores") and snap.get("prices"):
        snap["reality_scores"] = score_universe_from_snapshot(snap)

    watchlist = _watchlist_from_snapshot(snap)
    picks_payload = {
        "as_of": (snap.get("timestamp_utc") or today_iso())[:10],
        "data_mode": "offline_training" if snap.get("offline_training_mode") else "live",
        "picks": snap.get("ai_agent_picks", []),
        "reality_scores": snap.get("reality_scores", []),
        "stale_warning": snap.get("stale_warning"),
    }
    portfolio = load_portfolio_valued(repo, user_id, mock=training)
    leaderboard = build_leaderboard_from_picks(
        picks_payload.get("picks", []),
        data_mode=picks_payload.get("data_mode", "live"),
        portfolio=portfolio,
    )

    benchmark_picks = [p for p in picks_payload.get("picks", []) if p.get("player_type") == "benchmark" or "baseline" in str(p.get("agent_id", ""))]
    agent_picks_only = [p for p in picks_payload.get("picks", []) if p.get("player_type") == "agent" or (p.get("agent_id") not in ("skeptic", "human_baseline", "default") and "baseline" not in str(p.get("agent_id", "")) and p.get("agent_id") not in ("momentum", "public_figure"))]

    cross_asset = snap.get("cross_asset") or {
        "forex": [],
        "macro": snap.get("macro_indicators", []),
        "oil": next((m for m in snap.get("macro_indicators", []) if m.get("series_id") == "DCOILWTICO"), None),
    }
    if not cross_asset.get("regime"):
        cross_asset = enrich_snapshot_cross_asset(repo, {**snap, "cross_asset": cross_asset})
    regime = snap.get("regime") or cross_asset.get("regime") or detect_regime({**snap, "cross_asset": cross_asset})
    challenge = get_active_challenge(repo, snap)
    lessons = get_lessons(repo=repo)
    careers = get_careers(repo)
    research = query_registry(repo)
    research_report = load_latest_report(repo)
    horizon_outcomes = label_horizon_outcomes(repo, snap)

    agents_arena = [
        {
            "agent_id": p.get("agent_id"),
            "display_name": _agent_name(p.get("agent_id")),
            "pick_symbol": p.get("symbol"),
            "score": p.get("reality_score") or p.get("score"),
            "predicted_bias": p.get("predicted_bias"),
            "status": "active" if snap.get("scoring_data_eligible") else "stale",
        }
        for p in picks_payload.get("picks", [])
    ]

    return {
        "product": "MarketQuest",
        "version": "2.0.0",
        "tagline": TAGLINE,
        "as_of": today_iso(),
        "timestamp_utc": snap.get("timestamp_utc"),
        "market_status": snap.get("market_status"),
        "data_mode": picks_payload.get("data_mode"),
        "offline_training_mode": bool(snap.get("offline_training_mode")),
        "scoring_data_eligible": snap.get("scoring_data_eligible", False),
        "stale_warning": snap.get("stale_warning"),
        "disclaimer": DISCLAIMER,
        "provider_status": snap.get("provider_status", {}),
        "snapshot_age_minutes": _snapshot_age(snap),
        "watchlist": watchlist,
        "picks": picks_payload,
        "reality_scores": snap.get("reality_scores", []),
        "explanations": [
            {
                "agent_id": p.get("agent_id"),
                "symbol": p.get("symbol"),
                "reality_reasons": p.get("reality_reasons", []),
                **(p.get("explanation") or {}),
            }
            for p in picks_payload.get("picks", [])
        ],
        "news_by_pick": [
            {"agent_id": p.get("agent_id"), "symbol": p.get("symbol"), "articles": p.get("news", [])}
            for p in picks_payload.get("picks", [])
        ],
        "news_events": snap.get("news_events", [])[:20],
        "public_figure_events": snap.get("public_figure_events", [])[:10],
        "entity_graph": get_entity_graph(repo),
        "entity_graph_updates": snap.get("entity_graph_updates", [])[:10],
        "freshness": snap.get("freshness", {}),
        "next_refresh_seconds": get_status(repo, mock=mock).get("next_refresh_seconds"),
        "sec_filings": snap.get("sec_filings", [])[:10],
        "macro_indicators": snap.get("macro_indicators", []),
        "cross_asset": cross_asset,
        "regime": regime,
        "currencies": cross_asset.get("forex") or snap.get("currencies") or [],
        "portfolio": portfolio,
        "leaderboard": leaderboard,
        "benchmark_picks": benchmark_picks,
        "benchmark_comparisons": leaderboard.get("benchmark_comparisons", {}),
        "benchmark_disclosures": leaderboard.get("benchmark_disclosures", []),
        "agents_arena": agents_arena,
        "education": get_education(picks_payload.get("picks", [])),
        "lessons": lessons,
        "active_challenge": challenge,
        "careers": careers,
        "research_registry": research,
        "research_report": research_report,
        "horizon_outcomes": horizon_outcomes,
        "wording": {"allowed": ALLOWED_WORDING, "forbidden": FORBIDDEN_WORDING},
        "ai_disclosure": leaderboard.get("ai_disclosure"),
    }


def _snapshot_age(snap: dict[str, Any]) -> float | None:
    from marketquest.freshness import age_minutes

    ts = snap.get("timestamp_utc")
    if not ts:
        return None
    return round(age_minutes(ts), 2)


def _agent_name(agent_id: str | None) -> str:
    names = {
        "momentum": "Momentum Agent",
        "news": "News Agent",
        "news_only": "News-Only Agent",
        "spy_baseline": "SPY Baseline",
        "qqq_baseline": "QQQ Baseline",
        "equal_weight_baseline": "Equal-Weight Watchlist",
        "momentum_baseline": "Simple Momentum Baseline",
        "filing_event": "Filing/Event Agent",
        "macro": "Macro Agent",
        "macro_event": "Macro Agent",
        "ensemble": "Ensemble Agent",
        "human_baseline": "Human Baseline",
        "random_baseline": "Random Baseline",
        "public_figure": "Public Figure Agent",
        "entity_graph": "Entity Graph Agent",
        "skeptic": "Skeptic Agent",
        "fx_agent": "FX Agent",
        "cross_asset_agent": "Cross-Asset Agent",
        "regime_agent": "Regime Agent",
        "divergence_agent": "Divergence Agent",
        "correlation_skeptic": "Correlation Skeptic Agent",
    }
    return names.get(str(agent_id), str(agent_id or "Agent"))


def get_status(
    repo: Path,
    *,
    mock: bool | None = None,
) -> dict[str, Any]:
    snap = _resolve_snapshot(repo, training=mock, refresh=False)
    interval = refresh_interval_seconds()
    age = _snapshot_age(snap) or 0
    next_refresh_sec = max(0, interval - int(age * 60))
    return {
        "market_session": snap.get("market_session") or snap.get("market_status"),
        "market_status": snap.get("market_status"),
        "timestamp_utc": snap.get("timestamp_utc"),
        "snapshot_id": snap.get("snapshot_id"),
        "snapshot_age_minutes": age,
        "next_refresh_seconds": next_refresh_sec,
        "refresh_interval_seconds": interval,
        "provider_status": snap.get("provider_status", {}),
        "freshness": snap.get("freshness", {}),
        "scoring_data_eligible": snap.get("scoring_data_eligible", False),
        "stale_warning": snap.get("stale_warning"),
        "offline_training_mode": bool(snap.get("offline_training_mode")),
    }


def get_snapshot_latest(
    repo: Path,
    *,
    mock: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    snap = _resolve_snapshot(repo, training=mock, refresh=refresh)
    if not snap:
        return {"error": "no snapshot available"}
    return snap


def get_events(
    repo: Path,
    *,
    mock: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    snap = _resolve_snapshot(repo, training=mock, refresh=refresh)
    return {
        "timestamp_utc": snap.get("timestamp_utc"),
        "events": snap.get("news_events", []),
        "public_figure_events": snap.get("public_figure_events", []),
        "count": len(snap.get("news_events", [])),
    }


def get_currencies(
    repo: Path,
    *,
    mock: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    snap = _resolve_snapshot(repo, training=mock, refresh=refresh)
    if offline_training_requested(mock):
        forex = (snap.get("cross_asset") or {}).get("forex") or snap.get("currencies") or []
    else:
        forex = fetch_currencies(repo) or (snap.get("cross_asset") or {}).get("forex") or []
    live = [q for q in forex if q.get("last") is not None and q.get("status") != "OFFLINE"]
    offline = [q for q in forex if q.get("status") == "OFFLINE" or q.get("last") is None]
    return {
        "timestamp_utc": snap.get("timestamp_utc"),
        "pairs": forex,
        "count": len(forex),
        "live_count": len(live),
        "offline_count": len(offline),
        "provider_note": "Finnhub → FRED → yfinance fallback; OFFLINE pairs labeled explicitly",
    }


def get_cross_asset(
    repo: Path,
    *,
    mock: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    snap = _resolve_snapshot(repo, training=mock, refresh=refresh)
    cross = snap.get("cross_asset")
    if not cross or not cross.get("matrix"):
        cross = enrich_snapshot_cross_asset(repo, snap)
    return {
        "timestamp_utc": snap.get("timestamp_utc"),
        "cross_asset": cross,
        "correlations": cross.get("correlations", []),
        "lead_lag": cross.get("lead_lag", []),
        "divergences": cross.get("divergences", []),
        "matrix": cross.get("matrix", []),
    }


def get_regime(
    repo: Path,
    *,
    mock: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    snap = _resolve_snapshot(repo, training=mock, refresh=refresh)
    regime = snap.get("regime") or (snap.get("cross_asset") or {}).get("regime")
    if not regime:
        cross = snap.get("cross_asset") or enrich_snapshot_cross_asset(repo, snap)
        regime = cross.get("regime") or detect_regime({**snap, "cross_asset": cross})
    return {
        "timestamp_utc": snap.get("timestamp_utc"),
        "regime": regime,
    }


def get_agents_debate(
    repo: Path,
    *,
    symbol: str | None = None,
    mock: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    picks_payload = get_picks(repo, mock=mock, refresh=refresh)
    picks = picks_payload.get("picks", [])
    sym = (symbol or "").upper()
    if sym:
        debate = [p for p in picks if p.get("symbol") == sym]
    else:
        debate = picks
    return {
        "symbol": sym or None,
        "agents": AGENT_IDS,
        "picks": debate,
        "all_picks": picks,
    }


def get_entity_graph(repo: Path) -> dict[str, Any]:
    return GraphStore(repo).export_for_api()


def get_learning_report(repo: Path) -> dict[str, Any]:
    from marketquest.learning.nightly_review import load_latest_report

    return load_latest_report(repo)


def submit_challenge_answer(repo: Path, body: dict[str, Any]) -> dict[str, Any]:
    return submit_challenge(
        repo,
        challenge_id=str(body.get("challenge_id", "")),
        answer=str(body.get("answer", "")),
        player_id=str(body.get("player_id", "default")),
        expected_sectors=body.get("expected_sectors"),
    )


def get_careers_panel(repo: Path) -> dict[str, Any]:
    return get_careers(repo)


def get_research_registry(repo: Path, *, category: str | None = None) -> dict[str, Any]:
    return query_registry(repo, category=category)


def get_research_report_panel(repo: Path) -> dict[str, Any]:
    return load_latest_report(repo)


def get_glossary_panel(repo: Path) -> dict[str, Any]:
    return get_glossary(repo)


def get_lessons_panel(repo: Path, *, context: str | None = None) -> dict[str, Any]:
    return get_lessons(context=context, repo=repo)


def get_challenges_active(repo: Path, *, mock: bool | None = None) -> dict[str, Any]:
    snap = _resolve_snapshot(repo, training=mock, refresh=False)
    return get_active_challenge(repo, snap)


def execute_paper_order(repo: Path, body: dict[str, Any], *, mock: bool | None = None) -> dict[str, Any]:
    """Accept spec paper-order body with notional or qty."""
    side = str(body.get("side", "paper_buy")).lower().replace("paper_", "")
    if side == "short":
        return {"error": "short selling not allowed in V0 (long-only)"}
    trade_body = dict(body)
    trade_body["side"] = "buy" if side in ("buy", "long") else side
    if body.get("notional") and not body.get("qty"):
        snap = _resolve_snapshot(repo, training=mock, refresh=False)
        if not snap.get("scoring_data_eligible") and not offline_training_requested(mock):
            return {"error": "data stale — paper order rejected"}
        prices = {p["symbol"]: float(p.get("last") or 0) for p in snap.get("prices", [])}
        sym = str(body.get("symbol", "")).upper()
        price = prices.get(sym, 0)
        if price <= 0:
            return {"error": f"no price for {sym}"}
        trade_body["qty"] = max(1, int(float(body["notional"]) / price))
    return paper_trade(repo, trade_body, mock=mock)


def execute_paper_trade(repo: Path, body: dict[str, Any], *, mock: bool | None = None) -> dict[str, Any]:
    side = str(body.get("side", "buy")).lower()
    if side == "short":
        return {"error": "short selling not allowed in V0 (long-only)"}
    return paper_trade(repo, body, mock=mock)
