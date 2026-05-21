"""Read/write reality snapshots."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from marketquest.paths import snapshot_path_for, snapshots_dir


def finalize_snapshot(payload: dict[str, Any]) -> dict[str, Any]:
    """Add snapshot_id and normalize top-level fields."""
    ts = payload.get("timestamp_utc", "")
    sid = ts.replace(":", "-").replace("+00:00", "Z") if ts else "unknown"
    payload["snapshot_id"] = sid
    if "market_session" not in payload:
        ms = payload.get("market_status", "closed")
        payload["market_session"] = {
            "open": "open",
            "pre": "pre_market",
            "post": "after_hours",
        }.get(ms, "closed")
    return payload


def write_snapshot(repo: Path, payload: dict[str, Any]) -> Path:
    payload = finalize_snapshot(payload)
    ts = payload.get("timestamp_utc", "")
    path = snapshot_path_for(repo, ts)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_latest_snapshot(repo: Path) -> dict[str, Any] | None:
    root = snapshots_dir(repo)
    if not root.is_dir():
        return None
    candidates: list[Path] = []
    for day_dir in sorted(root.iterdir(), reverse=True):
        if not day_dir.is_dir():
            # legacy flat file snapshots/{date}.json
            if day_dir.suffix == ".json":
                candidates.append(day_dir)
            continue
        for f in sorted(day_dir.glob("*.json"), reverse=True):
            candidates.append(f)
    if not candidates:
        # legacy top-level json
        for f in sorted(root.glob("*.json"), reverse=True):
            candidates.append(f)
    if not candidates:
        return None
    return json.loads(candidates[0].read_text(encoding="utf-8"))


def load_offline_training_snapshot(repo: Path) -> dict[str, Any] | None:
    from marketquest.paths import fixtures_dir

    path = fixtures_dir(repo) / "reality_snapshot.json"
    if not path.is_file():
        return _build_training_snapshot_from_fixtures(repo)
    data = json.loads(path.read_text(encoding="utf-8"))
    data["offline_training_mode"] = True
    return data


def _build_training_snapshot_from_fixtures(repo: Path) -> dict[str, Any] | None:
    from marketquest.config import today_iso
    from marketquest.paths import fixtures_dir

    wl = fixtures_dir(repo) / "watchlist.json"
    picks = fixtures_dir(repo) / "agent_picks.json"
    if not wl.is_file():
        return None
    watch = json.loads(wl.read_text(encoding="utf-8"))
    pick_data = json.loads(picks.read_text(encoding="utf-8")) if picks.is_file() else {}
    agent_picks = pick_data.get("picks", [])
    if len(agent_picks) < 7:
        from marketquest.scoring.orchestrator import run_all_agents

        agent_picks = run_all_agents(repo, mock=True, refresh=True).get("picks", [])
    return {
        "timestamp_utc": today_iso() + "T12:00:00+00:00",
        "market_status": "closed",
        "offline_training_mode": True,
        "scoring_data_eligible": False,
        "provider_status": {"fixture": {"status": "OFFLINE", "fallback": True}},
        "symbols_checked": [q["symbol"] for q in watch.get("quotes", [])],
        "prices": [
            {**q, "provenance": {"provider": "fixture", "freshness": "OFFLINE", "fallback": True}}
            for q in watch.get("quotes", [])
        ],
        "movers": [],
        "news_events": [
            {
                "event_id": "fixture-1",
                "title": "Fed officials discuss inflation path — educational signal only",
                "event_type": "macro_rates",
                "source": "fixture_rss",
                "importance_score": 55,
                "candidate_tickers": ["SPY", "XLF"],
                "freshness_minutes": 30
            },
            {
                "event_id": "fixture-2",
                "title": "Energy sector monitors oil supply headlines",
                "event_type": "energy_oil_shock",
                "source": "fixture_rss",
                "importance_score": 48,
                "candidate_tickers": ["XLE", "XOM"],
                "freshness_minutes": 45
            },
            {
                "event_id": "fixture-3",
                "title": "Infrastructure names watch CAD and policy context",
                "event_type": "infrastructure_project",
                "source": "fixture_rss",
                "importance_score": 42,
                "candidate_tickers": ["BAM", "BN"],
                "freshness_minutes": 60
            }
        ],
        "sec_filings": [],
        "macro_indicators": [],
        "cross_asset": {
            "forex": [
                {"pair": "USD/CAD", "last": 1.36, "change_pct_1d": 0.12, "freshness": "OFFLINE", "status": "OFFLINE", "provider": "fixture", "why_it_matters": "CAD tracks oil and trade."},
                {"pair": "EUR/USD", "last": 1.08, "change_pct_1d": -0.05, "freshness": "OFFLINE", "status": "OFFLINE", "provider": "fixture"},
                {"pair": "GBP/USD", "last": 1.27, "change_pct_1d": 0.03, "freshness": "OFFLINE", "status": "OFFLINE", "provider": "fixture"},
                {"pair": "USD/JPY", "last": 148.5, "change_pct_1d": 0.08, "freshness": "OFFLINE", "status": "OFFLINE", "provider": "fixture"},
                {"pair": "AUD/USD", "last": 0.65, "change_pct_1d": -0.1, "freshness": "OFFLINE", "status": "OFFLINE", "provider": "fixture"},
                {"pair": "NZD/USD", "last": 0.60, "change_pct_1d": 0.02, "freshness": "OFFLINE", "status": "OFFLINE", "provider": "fixture"},
                {"pair": "USD/CHF", "last": 0.88, "change_pct_1d": 0.04, "freshness": "OFFLINE", "status": "OFFLINE", "provider": "fixture"},
            ],
            "macro": [{"series_id": "FEDFUNDS", "name": "Fed Funds Rate", "value": 5.25}],
            "oil": {"series_id": "DCOILWTICO", "name": "WTI Crude Oil", "value": 72.5},
            "regime": {"regime": "event_uncertain", "confidence": 0.4, "evidence": ["Offline training fixture"], "likely_sensitive_groups": ["watchlist broad"]},
        },
        "currencies": [
            {"pair": "USD/CAD", "last": 1.36, "status": "OFFLINE", "provider": "fixture"},
            {"pair": "EUR/USD", "last": 1.08, "status": "OFFLINE", "provider": "fixture"},
            {"pair": "GBP/USD", "last": 1.27, "status": "OFFLINE", "provider": "fixture"},
            {"pair": "USD/JPY", "last": 148.5, "status": "OFFLINE", "provider": "fixture"},
            {"pair": "AUD/USD", "last": 0.65, "status": "OFFLINE", "provider": "fixture"},
            {"pair": "NZD/USD", "last": 0.60, "status": "OFFLINE", "provider": "fixture"},
            {"pair": "USD/CHF", "last": 0.88, "status": "OFFLINE", "provider": "fixture"},
        ],
        "regime": {"regime": "event_uncertain", "confidence": 0.4, "evidence": ["Offline training fixture"], "likely_sensitive_groups": ["watchlist broad"]},
        "ai_agent_picks": agent_picks,
        "leaderboard_marks": [],
        "tagline": "OFFLINE TRAINING MODE",
    }
