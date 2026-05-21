"""FX quotes with enriched schema for cross-asset layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from marketquest.cross_asset.currency_watchlist import major_pairs
from marketquest.data_sources.forex_provider import fetch_cross_asset_quotes


def fetch_currencies(repo: Path) -> list[dict[str, Any]]:
    """Return normalized FX quotes for major pairs."""
    quotes = fetch_cross_asset_quotes(repo)
    wanted = set(major_pairs(repo))
    result: list[dict[str, Any]] = []
    for q in quotes:
        pair = str(q.get("pair", "")).upper()
        if pair not in wanted and wanted:
            continue
        result.append(_normalize_quote(q))
    # Include any extra pairs returned (e.g. policy pairs) with labeling
    seen = {r["pair"] for r in result}
    for q in quotes:
        pair = str(q.get("pair", "")).upper()
        if pair not in seen:
            result.append(_normalize_quote(q))
            seen.add(pair)
    return result


def _normalize_quote(q: dict[str, Any]) -> dict[str, Any]:
    prov = q.get("provenance") or {}
    status = str(q.get("status") or prov.get("freshness") or q.get("freshness") or "OFFLINE")
    return {
        "pair": str(q.get("pair", "")).upper(),
        "bid": q.get("bid"),
        "ask": q.get("ask"),
        "mid": q.get("mid") or q.get("last"),
        "last": q.get("last"),
        "change_pct_15m": q.get("change_pct_15m"),
        "change_pct_1h": q.get("change_pct_1h"),
        "change_pct_1d": q.get("change_pct_1d") or q.get("change_pct"),
        "provider": q.get("provider") or prov.get("provider", "unknown"),
        "fetched_at_utc": q.get("fetched_at") or prov.get("fetched_at"),
        "market_timestamp_utc": q.get("market_timestamp_utc"),
        "freshness_minutes": q.get("freshness_minutes", 0),
        "status": status,
        "why_it_matters": q.get("why_it_matters", ""),
        "provenance": prov,
        "errors": q.get("errors") or [],
    }
