"""Run all MarketQuest agents — snapshot-aware."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.agents.benchmarks.equal_weight_baseline import run_equal_weight_baseline
from marketquest.agents.benchmarks.momentum_baseline import run_momentum_baseline
from marketquest.agents.benchmarks.qqq_baseline import run_qqq_baseline
from marketquest.agents.benchmarks.registry import BENCHMARK_IDS
from marketquest.agents.benchmarks.spy_baseline import run_spy_baseline
from marketquest.agents.ensemble import run_ensemble
from marketquest.agents.entity_graph_agent import run_entity_graph_from_snapshot
from marketquest.agents.filing_event import run_filing_event_from_snapshot
from marketquest.agents.human_baseline import run_human_baseline
from marketquest.agents.macro import run_macro_from_snapshot
from marketquest.agents.macro_event import run_macro_event_agent
from marketquest.agents.momentum import run_momentum_agent
from marketquest.agents.news_sentiment import run_news_sentiment_agent
from marketquest.agents.public_figure_agent import run_public_figure_from_snapshot
from marketquest.agents.random_baseline import run_random_baseline
from marketquest.agents.correlation_skeptic_agent import run_correlation_skeptic
from marketquest.agents.cross_asset_agent import run_cross_asset_agent
from marketquest.agents.divergence_agent import run_divergence_agent
from marketquest.agents.fx_agent import run_fx_agent
from marketquest.agents.regime_agent import run_regime_agent
from marketquest.agents.skeptic_agent import run_skeptic
from marketquest.agents._pick import make_pick
from marketquest.config import load_config, offline_training_requested, today_iso
from marketquest.paths import agent_picks_dir, fixtures_dir
from marketquest.scoring.reality_score import score_universe_from_snapshot

AGENT_IDS = BENCHMARK_IDS + [
    "skeptic",
    "correlation_skeptic",
    "human_baseline",
    "public_figure",
    "momentum",
    "fx_agent",
    "cross_asset_agent",
    "regime_agent",
    "divergence_agent",
]


def load_fixture_picks(repo: Path) -> list[dict[str, Any]]:
    path = fixtures_dir(repo) / "agent_picks.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("picks", data if isinstance(data, list) else []))


def _momentum_from_snapshot(snapshot: dict[str, Any], as_of: str) -> dict[str, Any]:
    prices = snapshot.get("prices", [])
    if not prices:
        return run_momentum_agent(snapshot.get("repo") or Path("."), as_of=as_of, mock=True)
    top = max(prices, key=lambda p: abs(float(p.get("change_pct") or 0)))
    sym = top["symbol"]
    chg = float(top.get("change_pct") or 0)
    return make_pick(
        symbol=sym,
        agent_id="momentum",
        as_of=as_of,
        score=abs(chg) / 10,
        predicted_bias="bullish" if chg > 0 else "bearish",
        headline=f"Momentum: {sym} move {top.get('change_pct')}%",
        bullets=[
            f"Change: {top.get('change_pct')}%",
            "Reality-ranked from live snapshot",
        ],
        features={"change_pct": top.get("change_pct"), "gap_pct": top.get("gap_pct")},
        data_mode="live",
        prediction_type="paper_long" if chg > 0 else "watch",
        horizon="15m",
        confidence=min(abs(chg) / 15, 0.8),
        expected_direction="up" if chg > 0 else "down",
        reasons=[f"Intraday momentum {chg:.2f}%"],
        risks=["Momentum can reverse quickly"],
    )


def _news_from_snapshot(snapshot: dict[str, Any], as_of: str) -> dict[str, Any]:
    news = snapshot.get("news_events", [])
    if not news:
        sym = (snapshot.get("symbols_checked") or ["SPY"])[0]
        return make_pick(
            symbol=sym,
            agent_id="news_only",
            as_of=as_of,
            score=0,
            predicted_bias="neutral",
            headline="No news in snapshot",
            bullets=[],
            features={},
            prediction_type="watch",
            horizon="1h",
            confidence=0.1,
        )
    best = news[0]
    tickers = best.get("candidate_tickers") or best.get("symbols") or snapshot.get("symbols_checked") or ["SPY"]
    sym = str(tickers[0]).upper()
    title = str(best.get("title") or best.get("headline", ""))[:120]
    imp = float(best.get("importance_score") or 50) / 100
    return make_pick(
        symbol=sym,
        agent_id="news_only",
        as_of=as_of,
        score=float(best.get("sentiment") or imp),
        predicted_bias="bullish" if float(best.get("sentiment") or 0) > 0 else "neutral",
        headline=title,
        bullets=[
            f"Source: {best.get('source')}",
            f"Event type: {best.get('event_type') or best.get('category')}",
        ],
        features={"sentiment": best.get("sentiment"), "importance": best.get("importance_score")},
        news=[{"title": title, "sentiment": best.get("sentiment"), "source": best.get("source")}],
        data_mode="live",
        prediction_type="watch",
        horizon="1h",
        confidence=min(imp, 0.75),
        reasons=[f"Fresh headline: {title[:80]}"],
        risks=list(best.get("uncertainties") or [])[:2],
        source_event_ids=[str(best.get("event_id", ""))],
    )


def run_all_agents_from_snapshot(
    repo: Path,
    snapshot: dict[str, Any],
) -> dict[str, Any]:
    as_of = (snapshot.get("timestamp_utc") or today_iso())[:10]
    symbols = snapshot.get("symbols_checked") or load_config(repo)["symbols"]
    snapshot = {**snapshot, "repo": repo}

    if not snapshot.get("scoring_data_eligible"):
        return {
            "as_of": as_of,
            "data_mode": "stale",
            "picks": [],
            "reality_scores": score_universe_from_snapshot(snapshot),
            "stale_warning": snapshot.get(
                "stale_warning",
                "Data stale — not used for current competition scoring.",
            ),
        }

    core_picks = [
        _momentum_from_snapshot(snapshot, as_of),
        _news_from_snapshot(snapshot, as_of),
        run_filing_event_from_snapshot(snapshot, as_of=as_of),
        run_macro_from_snapshot(snapshot, as_of=as_of),
        run_public_figure_from_snapshot(snapshot, as_of=as_of),
        run_entity_graph_from_snapshot(snapshot, repo, as_of=as_of),
        run_fx_agent(snapshot, as_of=as_of),
        run_cross_asset_agent(snapshot, as_of=as_of),
        run_regime_agent(snapshot, as_of=as_of),
        run_divergence_agent(snapshot, as_of=as_of),
    ]
    skeptic_pick = run_skeptic(core_picks, snapshot, as_of=as_of)
    corr_skeptic_pick = run_correlation_skeptic(core_picks, snapshot, as_of=as_of)
    ensemble_pick = run_ensemble(core_picks, as_of=as_of, skeptic=skeptic_pick)
    benchmark_picks = [
        run_random_baseline(repo, symbols=symbols, as_of=as_of),
        run_spy_baseline(snapshot, as_of=as_of),
        run_qqq_baseline(snapshot, as_of=as_of),
        run_equal_weight_baseline(snapshot, as_of=as_of),
        run_momentum_baseline(snapshot, as_of=as_of),
    ]
    picks = core_picks + [ensemble_pick] + benchmark_picks
    picks.append(run_human_baseline(repo, symbols=symbols, as_of=as_of))
    picks.append(skeptic_pick)
    picks.append(corr_skeptic_pick)

    for p in picks:
        if p.get("agent_id") == "news":
            p["agent_id"] = "news_only"
        if p.get("agent_id") == "news_sentiment":
            p["agent_id"] = "news_only"

    reality_scores = score_universe_from_snapshot({**snapshot, "ai_agent_picks": picks})
    for p in picks:
        rs = next((r for r in reality_scores if r["symbol"] == p.get("symbol")), None)
        if rs:
            p["reality_score"] = rs["reality_score"]
            p["reality_reasons"] = rs.get("reasons", [])

    return {
        "as_of": as_of,
        "data_mode": "live",
        "picks": picks,
        "reality_scores": reality_scores,
    }


def run_all_agents(
    repo: Path,
    *,
    as_of: str | None = None,
    mock: bool | None = None,
    refresh: bool = False,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    use_training = offline_training_requested(mock)
    cache_path = agent_picks_dir(repo) / f"{as_of}.json"

    if snapshot is not None:
        payload = run_all_agents_from_snapshot(repo, snapshot)
        agent_picks_dir(repo).mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    if not refresh and cache_path.is_file() and not use_training:
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        if cached.get("picks") and len(cached.get("picks", [])) >= 7:
            return cached

    if use_training:
        picks = load_fixture_picks(repo)
        needs_rebuild = (
            refresh
            or len(picks) < 7
            or not any(p.get("prediction_type") for p in picks)
            or not any(p.get("agent_id") == "skeptic" for p in picks)
            or not any(p.get("agent_id") == "fx_agent" for p in picks)
        )
        if needs_rebuild:
            symbols = load_config(repo)["symbols"]
            core = [
                run_momentum_agent(repo, as_of=as_of, mock=True),
                run_news_sentiment_agent(repo, as_of=as_of, mock=True),
                run_macro_event_agent(repo, as_of=as_of, mock=True),
                run_filing_event_from_snapshot({"sec_filings": [], "symbols_checked": symbols}, as_of=as_of),
                run_macro_from_snapshot({"macro_indicators": [], "symbols_checked": symbols}, as_of=as_of),
                run_public_figure_from_snapshot({"news_events": [], "symbols_checked": symbols}, as_of=as_of),
                run_entity_graph_from_snapshot({"entity_graph_updates": [], "symbols_checked": symbols}, repo, as_of=as_of),
            ]
            snap_stub = {
                "prices": [],
                "symbols_checked": symbols,
                "news_events": [],
                "sec_filings": [],
                "macro_indicators": [],
                "cross_asset": {"forex": [], "regime": {"regime": "event_uncertain", "confidence": 0.3, "evidence": []}},
            }
            core.extend([
                run_fx_agent(snap_stub, as_of=as_of),
                run_cross_asset_agent(snap_stub, as_of=as_of),
                run_regime_agent(snap_stub, as_of=as_of),
                run_divergence_agent(snap_stub, as_of=as_of),
            ])
            sk = run_skeptic(core, {"scoring_data_eligible": True, "prices": [], "news_events": []}, as_of=as_of)
            csk = run_correlation_skeptic(core, snap_stub, as_of=as_of)
            core.append(run_ensemble(core, as_of=as_of, skeptic=sk))
            core.append(sk)
            core.append(csk)
            core.append(run_human_baseline(repo, symbols=symbols, as_of=as_of))
            core.append(run_random_baseline(repo, symbols=symbols, as_of=as_of))
            from marketquest.agents.benchmarks.spy_baseline import run_spy_baseline
            from marketquest.agents.benchmarks.qqq_baseline import run_qqq_baseline
            from marketquest.agents.benchmarks.equal_weight_baseline import run_equal_weight_baseline
            from marketquest.agents.benchmarks.momentum_baseline import run_momentum_baseline

            snap_stub = {"prices": [], "symbols_checked": symbols, "news_events": [], "sec_filings": [], "macro_indicators": []}
            core.extend([
                run_spy_baseline(snap_stub, as_of=as_of),
                run_qqq_baseline(snap_stub, as_of=as_of),
                run_equal_weight_baseline(snap_stub, as_of=as_of),
                run_momentum_baseline(snap_stub, as_of=as_of),
            ])
            picks = core
        payload = {"as_of": as_of, "data_mode": "offline_training", "picks": picks}
        agent_picks_dir(repo).mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    from marketquest.reality_engine.collector import collect_snapshot

    snap = collect_snapshot(repo, offline_training=False)
    return run_all_agents_from_snapshot(repo, snap)
