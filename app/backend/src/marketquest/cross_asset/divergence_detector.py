"""Detect stock vs expected driver mismatches."""

from __future__ import annotations

from typing import Any

from marketquest.cross_asset.correlation_engine import compute_correlations


def detect_divergences(snapshot: dict[str, Any], *, max_items: int = 10) -> list[dict[str, Any]]:
    correlations = compute_correlations(snapshot)
    changes = {p["symbol"]: float(p.get("change_pct") or 0) for p in snapshot.get("prices", []) if p.get("symbol")}
    for f in (snapshot.get("cross_asset") or {}).get("forex") or []:
        if f.get("pair"):
            changes[str(f["pair"]).upper()] = float(f.get("change_pct_1d") or f.get("change_pct") or 0)

    divergences: list[dict[str, Any]] = []
    for c in correlations:
        sym = c["symbol"]
        driver = c["related_asset"]
        if sym not in changes or driver not in changes:
            continue
        sym_chg, drv_chg = changes[sym], changes[driver]
        if abs(drv_chg) < 0.4:
            continue
        expected = "up" if drv_chg > 0 else "down"
        if sym_chg > 0.15:
            actual = "up"
        elif sym_chg < -0.15:
            actual = "down"
        else:
            actual = "flat"
        if expected == actual:
            continue
        if c.get("direction") == "negative" and expected == "up":
            expected = "down"
        elif c.get("direction") == "negative" and expected == "down":
            expected = "up"

        score = min(abs(drv_chg - sym_chg) / 5.0, 1.0)
        divergences.append({
            "symbol": sym,
            "driver": driver,
            "expected_direction": expected,
            "actual_direction": actual,
            "divergence_score": round(score, 3),
            "possible_interpretations": [
                "Stock-specific event may be stronger than cross-asset driver",
                "Cross-asset effect may appear later",
                "Relationship may not be valid today",
            ],
            "agent_action": "watch",
        })

    return divergences[:max_items]
