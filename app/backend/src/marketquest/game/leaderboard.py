"""Weekly competition leaderboard — humans + AI agents + benchmarks."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from marketquest.agents.benchmarks.registry import COMPARISON_PAIRS, display_name
from marketquest.config import today_iso
from marketquest.game.competition import score_entry
from marketquest.paths import fixtures_dir, leaderboards_dir
from marketquest.scoring.orchestrator import run_all_agents

AGENT_NAMES = {
    "momentum": "Momentum Agent",
    "news": "News Agent",
    "news_only": "News-Only Agent",
    "news_sentiment": "News Agent",
    "filing_event": "Filing Agent",
    "macro": "Macro Agent",
    "macro_event": "Macro Agent",
    "ensemble": "Ensemble Agent",
    "human_baseline": "Human Baseline",
    "random_baseline": "Random Baseline",
    "spy_baseline": "SPY Baseline",
    "qqq_baseline": "QQQ Baseline",
    "equal_weight_baseline": "Equal-Weight Watchlist",
    "momentum_baseline": "Simple Momentum Baseline",
    "entity_graph": "Entity Graph Agent",
    "public_figure": "Public Figure Agent",
    "skeptic": "Skeptic Agent",
    "default": "You (default)",
}


def _iso_week(d: date | None = None) -> str:
    d = d or date.today()
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def _entry_from_pick(p: dict[str, Any], rank: int) -> dict[str, Any]:
    aid = str(p.get("agent_id", ""))
    weekly = float(p.get("reality_score") or p.get("score", 0) or 0) / 10.0
    player_type = p.get("player_type") or (
        "human" if aid in ("default", "human_baseline") else (
            "benchmark" if "baseline" in aid else "agent"
        )
    )
    return {
        "rank": rank,
        "id": aid,
        "display_name": AGENT_NAMES.get(aid, display_name(aid) if aid else aid),
        "type": player_type,
        "weekly_return_pct": round(weekly, 2),
        "max_drawdown_pct": round(abs(min(0, weekly)) * 0.5, 2),
        "hit_rate": round(min(100, 50 + weekly * 5), 1),
        "best_pick": p.get("symbol"),
        "worst_pick": None,
        "explanation_score": round(min(10, len((p.get("explanation") or {}).get("bullets") or []) * 2), 1),
        "last_updated": p.get("as_of") or today_iso(),
        "score_pct": round(weekly, 2),
        "random_beats_ai": aid == "random_baseline",
    }


def _human_portfolio_entry(portfolio: dict[str, Any] | None) -> dict[str, Any] | None:
    if not portfolio:
        return None
    start = float(portfolio.get("starting_value_usd") or portfolio.get("total_value_usd") or 0)
    total = float(portfolio.get("total_value_usd") or start)
    if start <= 0:
        return None
    weekly_return = ((total - start) / start) * 100
    return {
        "rank": 0,
        "id": "default",
        "display_name": "You (Human Player)",
        "type": "human",
        "weekly_return_pct": round(weekly_return, 2),
        "max_drawdown_pct": round(abs(min(0, weekly_return)) * 0.5, 2),
        "hit_rate": 50.0,
        "best_pick": None,
        "worst_pick": None,
        "explanation_score": 0.0,
        "last_updated": portfolio.get("as_of") or today_iso(),
        "score_pct": round(weekly_return, 2),
        "random_beats_ai": False,
    }


def build_benchmark_comparisons(entries: list[dict[str, Any]], week: str) -> dict[str, Any]:
    by_id = {e["id"]: e for e in entries}
    comparisons: dict[str, Any] = {}
    disclosures: list[str] = []

    for a_id, b_id in COMPARISON_PAIRS:
        a = by_id.get(a_id)
        b = by_id.get(b_id)
        if not a or not b:
            continue
        a_score = float(a.get("score_pct") or 0)
        b_score = float(b.get("score_pct") or 0)
        delta = round(a_score - b_score, 2)
        winner = a_id if delta >= 0 else b_id
        key = f"{a_id}_vs_{b_id}"
        comparisons[key] = {
            "winner": winner,
            "delta_pct": abs(delta),
            "period": week,
            "a_id": a_id,
            "b_id": b_id,
            "a_score": a_score,
            "b_score": b_score,
        }
        a_name = AGENT_NAMES.get(a_id, a_id)
        b_name = AGENT_NAMES.get(b_id, b_id)
        if winner == a_id:
            disclosures.append(f"{a_name} beat {b_name} this week in paper scoring (+{abs(delta):.2f}%).")
        else:
            disclosures.append(f"{b_name} beat {a_name} this week in paper scoring (+{abs(delta):.2f}%).")

    random_entry = by_id.get("random_baseline")
    ensemble = by_id.get("ensemble")
    ai_disclosure = None
    if random_entry and ensemble and random_entry.get("rank", 99) < ensemble.get("rank", 99):
        ai_disclosure = "Random baseline is currently ahead of AI agents this week."

    return {"pairs": comparisons, "disclosures": disclosures, "ai_disclosure": ai_disclosure}


def marks_from_snapshot(repo: Path, snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    picks = snapshot.get("ai_agent_picks", [])
    marks = []
    for p in picks:
        marks.append(
            {
                "id": p.get("agent_id"),
                "symbol": p.get("symbol"),
                "score": p.get("reality_score") or p.get("score"),
            }
        )
    return marks


def build_leaderboard_from_picks(
    picks: list[dict],
    *,
    week: str | None = None,
    data_mode: str = "live",
    portfolio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    week = week or _iso_week()
    entries = [_entry_from_pick(p, 0) for p in picks]

    human_entry = _human_portfolio_entry(portfolio)
    if human_entry:
        entries = [e for e in entries if e["id"] not in ("default", "human_baseline")] + [human_entry]

    for e in entries:
        e["_sort"] = score_entry(
            weekly_return_pct=float(e.get("weekly_return_pct") or 0),
            max_drawdown_pct=float(e.get("max_drawdown_pct") or 0),
            hit_rate=float(e.get("hit_rate") or 0),
            explanation_score=float(e.get("explanation_score") or 0),
        )
    entries.sort(key=lambda e: -e["_sort"])
    for i, e in enumerate(entries, 1):
        e["rank"] = i
        del e["_sort"]

    comparisons = build_benchmark_comparisons(entries, week)
    players = [e for e in entries if e["type"] == "human"]
    benchmarks = [e for e in entries if e["type"] == "benchmark"]
    agents = [e for e in entries if e["type"] == "agent"]

    return {
        "week": week,
        "as_of": today_iso(),
        "data_mode": data_mode,
        "entries": entries,
        "players": players,
        "benchmarks": benchmarks,
        "agents": agents,
        "benchmark_comparisons": comparisons["pairs"],
        "benchmark_disclosures": comparisons["disclosures"],
        "ai_disclosure": comparisons["ai_disclosure"],
    }


def load_leaderboard(
    repo: Path,
    *,
    week: str | None = None,
    mock: bool | None = None,
    refresh: bool = False,
    snapshot: dict[str, Any] | None = None,
    portfolio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    week = week or _iso_week()
    path = leaderboards_dir(repo) / f"{week}.json"

    if snapshot and snapshot.get("ai_agent_picks"):
        payload = build_leaderboard_from_picks(
            snapshot["ai_agent_picks"],
            week=week,
            data_mode="offline_training" if snapshot.get("offline_training_mode") else "live",
            portfolio=portfolio,
        )
        leaderboards_dir(repo).mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    if not refresh and path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))

    agents = run_all_agents(repo, mock=mock, refresh=refresh)
    payload = build_leaderboard_from_picks(
        agents.get("picks", []),
        week=week,
        data_mode=agents.get("data_mode", "live"),
        portfolio=portfolio,
    )
    leaderboards_dir(repo).mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
