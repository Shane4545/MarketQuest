"""Commodity proxy quotes from snapshot prices."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_commodity_symbols(repo: Path) -> dict[str, str]:
    path = repo / "app" / "data" / "marketquest" / "watchlists" / "cross_asset_proxies.json"
    if not path.is_file():
        return {"USO": "oil_wti", "GLD": "gold", "SLV": "silver", "UNG": "natural_gas"}
    data = json.loads(path.read_text(encoding="utf-8"))
    return dict(data.get("commodities") or {})


def extract_commodities(snapshot: dict[str, Any], repo: Path) -> list[dict[str, Any]]:
    symbols = load_commodity_symbols(repo)
    prices = {p["symbol"]: p for p in snapshot.get("prices", []) if p.get("symbol")}
    macro = snapshot.get("macro_indicators") or []
    oil_macro = next((m for m in macro if m.get("series_id") == "DCOILWTICO"), None)
    rows: list[dict[str, Any]] = []
    for sym, label in symbols.items():
        row = prices.get(sym.upper())
        if row:
            rows.append({
                "symbol": sym.upper(),
                "label": label,
                "last": row.get("last"),
                "change_pct_1d": row.get("change_pct"),
                "provider": (row.get("provenance") or {}).get("provider"),
                "status": (row.get("provenance") or {}).get("freshness", "OFFLINE"),
            })
    if oil_macro and not any(r["symbol"] == "USO" for r in rows):
        rows.append({
            "symbol": "DCOILWTICO",
            "label": "oil_wti_fred",
            "last": oil_macro.get("value"),
            "change_pct_1d": None,
            "provider": "fred",
            "status": "DELAYED",
        })
    return rows
