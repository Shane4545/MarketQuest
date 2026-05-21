"""Orchestrate cross-asset enrichment for reality snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from marketquest.cross_asset.commodity_provider import extract_commodities
from marketquest.cross_asset.correlation_engine import compute_correlations
from marketquest.cross_asset.currency_provider import fetch_currencies
from marketquest.cross_asset.divergence_detector import detect_divergences
from marketquest.cross_asset.index_provider import extract_indexes
from marketquest.cross_asset.lead_lag_engine import compute_lead_lag
from marketquest.cross_asset.regime_detector import detect_regime
from marketquest.cross_asset.sector_provider import extract_sectors
from marketquest.cross_asset.cross_asset_explainer import build_matrix_rows


def enrich_snapshot_cross_asset(repo: Path, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Build full cross_asset block including regime, correlations, divergences."""
    existing = dict(snapshot.get("cross_asset") or {})
    currencies = fetch_currencies(repo)
    if not currencies and existing.get("forex"):
        currencies = existing["forex"]

    cross: dict[str, Any] = {
        "forex": currencies,
        "macro": existing.get("macro") or snapshot.get("macro_indicators") or [],
        "oil": existing.get("oil"),
        "commodities": extract_commodities(snapshot, repo),
        "indexes": extract_indexes(snapshot, repo),
        "sectors": extract_sectors(snapshot, repo),
    }
    snapshot_with_cross = {**snapshot, "cross_asset": cross, "currencies": currencies}
    cross["correlations"] = compute_correlations(snapshot_with_cross)
    cross["lead_lag"] = compute_lead_lag(snapshot_with_cross)
    cross["divergences"] = detect_divergences(snapshot_with_cross)
    cross["regime"] = detect_regime(snapshot_with_cross)
    cross["matrix"] = build_matrix_rows(snapshot_with_cross, cross["correlations"], cross["regime"])
    cross["currency_count"] = len(currencies)
    cross["currency_errors"] = [c for c in currencies if c.get("status") == "OFFLINE"]
    return cross
