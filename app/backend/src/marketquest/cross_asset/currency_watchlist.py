"""Load FX watchlist from JSON."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_currency_watchlist(repo: Path) -> dict[str, Any]:
    path = repo / "app" / "data" / "marketquest" / "watchlists" / "currencies.json"
    if not path.is_file():
        return {"major_pairs": ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CAD", "AUD/USD", "NZD/USD", "USD/CHF"]}
    return json.loads(path.read_text(encoding="utf-8"))


def all_pairs(repo: Path) -> list[str]:
    wl = load_currency_watchlist(repo)
    seen: set[str] = set()
    pairs: list[str] = []
    for key in ("major_pairs", "trade_policy_pairs", "commodity_sensitive_pairs", "risk_pairs", "custom_pairs"):
        for p in wl.get(key) or []:
            norm = str(p).upper()
            if norm not in seen:
                seen.add(norm)
                pairs.append(norm)
    return pairs


def major_pairs(repo: Path) -> list[str]:
    wl = load_currency_watchlist(repo)
    return [str(p).upper() for p in wl.get("major_pairs") or []]
