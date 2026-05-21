"""Sector ETF quotes from snapshot."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_sector_symbols(repo: Path) -> dict[str, str]:
    path = repo / "app" / "data" / "marketquest" / "watchlists" / "cross_asset_proxies.json"
    if not path.is_file():
        return {"XLK": "technology", "XLE": "energy", "XLF": "financials"}
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict(data.get("sectors") or {})


def extract_sectors(snapshot: dict[str, Any], repo: Path) -> list[dict[str, Any]]:
    sectors = load_sector_symbols(repo)
    prices = {p["symbol"]: p for p in snapshot.get("prices", []) if p.get("symbol")}
    rows: list[dict[str, Any]] = []
    for sym, label in sectors.items():
        if sym.upper() not in prices:
            continue
        p = prices[sym.upper()]
        rows.append({
            "symbol": sym.upper(),
            "sector": label,
            "last": p.get("last"),
            "change_pct_1d": p.get("change_pct"),
            "status": (p.get("provenance") or {}).get("freshness", "OFFLINE"),
        })
    return sorted(rows, key=lambda x: abs(float(x.get("change_pct_1d") or 0)), reverse=True)
