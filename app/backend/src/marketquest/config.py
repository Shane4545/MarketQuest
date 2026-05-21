"""MarketQuest configuration — no pencil journal coupling."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from phase1.paths import repo_root

TAGLINE = "Wall Street intelligence game — real data, paper scoring, honest learning."

DISCLAIMER = (
    "Paper trading simulation only. Not investment advice. "
    "No real-money order placement. Past paper scores do not predict future results."
)

ALLOWED_WORDING = [
    "beat the random baseline this week",
    "beat SPY this week in paper scoring",
    "lost to the Human Baseline this week",
    "performed poorly during stale-data periods",
]

FORBIDDEN_WORDING = [
    "guaranteed to beat brokers",
    "better than Edward Jones",
    "best stocks ever",
    "always wins",
    "use this with real money",
]

DEFAULT_SYMBOLS = [
    "NVDA",
    "TSLA",
    "AMD",
    "AAPL",
    "MSFT",
    "META",
    "GOOGL",
    "AMZN",
    "SPY",
    "PLTR",
]


def _load_press_rss(root: Path) -> list[dict[str, str]]:
    import json

    wl_path = root / "app" / "data" / "marketquest" / "watchlists" / "default.json"
    if not wl_path.is_file():
        return []
    data = json.loads(wl_path.read_text(encoding="utf-8"))
    return list(data.get("press_rss") or [])


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _load_watchlist_json(root: Path) -> list[str]:
    import json

    wl_path = root / "app" / "data" / "marketquest" / "watchlists" / "default.json"
    if not wl_path.is_file():
        return []
    data = json.loads(wl_path.read_text(encoding="utf-8"))
    symbols: list[str] = []
    for s in data.get("symbols", []):
        symbols.append(str(s).upper())
    for group in (data.get("groups") or {}).values():
        for s in group:
            sym = str(s).upper()
            if sym not in symbols:
                symbols.append(sym)
    return symbols


def load_config(repo: Path | None = None) -> dict[str, Any]:
    root = repo or repo_root()
    cfg_path = root / "config" / "marketquest.yaml"
    pencil_path = root / "config" / "aggressive_pencil.yaml"
    mq = _load_yaml(cfg_path)
    pencil = _load_yaml(pencil_path)

    json_symbols = _load_watchlist_json(root)
    symbols = json_symbols or mq.get("symbols") or DEFAULT_SYMBOLS
    seed_file = root / "config" / "volatile_seed.txt"
    if mq.get("use_volatile_seed") and seed_file.is_file():
        lines = [
            ln.strip().upper()
            for ln in seed_file.read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.startswith("#")
        ]
        if lines:
            symbols = lines[: int(mq.get("max_symbols", 12))]

    composite = mq.get("composite_weights") or pencil.get("composite_weights") or {
        "ml": 0.25,
        "gap": 0.35,
        "rvol": 0.30,
        "sentiment": 0.10,
    }
    news_cfg = mq.get("news") or pencil.get("news") or {
        "lookback_hours": 48,
        "earnings_keywords": ["earnings", "eps", "revenue"],
        "financing_keywords": ["offering", "dilution", "secondary"],
    }

    return {
        "repo": root,
        "symbols": [str(s).upper() for s in symbols[: int(mq.get("max_symbols", 25))]],
        "press_rss": _load_press_rss(root),
        "starting_cash_usd": float(mq.get("starting_cash_usd", 100_000)),
        "long_only": bool(mq.get("long_only", True)),
        "refresh_interval_minutes": int(mq.get("refresh_interval_minutes", 15)),
        "stale_threshold_minutes": int(mq.get("stale_threshold_minutes", 20)),
        "composite_weights": composite,
        "news": news_cfg,
        "catalyst_required": False,
        "cooldown_days": 0,
        "breakaway_gap_exception_pct": float(
            mq.get("breakaway_gap_exception_pct", pencil.get("breakaway_gap_exception_pct", 8.0))
        ),
        "disclaimer": DISCLAIMER,
        "tagline": TAGLINE,
        "offline_training_env": os.environ.get("MARKETQUEST_OFFLINE_TRAINING", "").lower()
        in ("1", "true", "yes"),
    }


def today_iso() -> str:
    return date.today().isoformat()


def offline_training_requested(explicit: bool | None = None) -> bool:
    if explicit is True:
        return True
    if explicit is False:
        return False
    return load_config().get("offline_training_env", False)


def mock_requested(explicit_mock: bool | None = None) -> bool:
    """Legacy alias — maps to offline training mode."""
    return offline_training_requested(explicit_mock)
