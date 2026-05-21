"""Index ETF quotes from snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_index_symbols(repo: Path) -> list[str]:
    path = repo / "app" / "data" / "marketquest" / "watchlists" / "cross_asset_proxies.json"
    if not path.is_file():
        return ["SPY", "QQQ", "IWM", "DIA"]
    data = json.loads(path.read_text(encoding="utf-8"))
    return [str(s).upper() for s in data.get("indexes") or []]


def extract_indexes(snapshot: dict[str, Any], repo: Path) -> list[dict[str, Any]]:
    symbols = load_index_symbols(repo)
    prices = {p["symbol"]: p for p in snapshot.get("prices", []) if p.get("symbol")}
    return [
        {
            "symbol": sym,
            "last": prices[sym].get("last"),
            "change_pct_1d": prices[sym].get("change_pct"),
            "status": (prices[sym].get("provenance") or {}).get("freshness", "OFFLINE"),
        }
        for sym in symbols
        if sym in prices
    ]
