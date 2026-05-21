"""Human-readable cross-asset matrix rows for UI."""

from __future__ import annotations

from typing import Any


def build_matrix_rows(
    snapshot: dict[str, Any],
    correlations: list[dict[str, Any]],
    regime: dict[str, Any],
) -> list[dict[str, Any]]:
    prices = {p["symbol"]: p for p in snapshot.get("prices", []) if p.get("symbol")}
    symbols = [s for s in (snapshot.get("symbols_checked") or []) if s not in ("SPY", "QQQ")][:12]
    corr_by_sym: dict[str, list[dict[str, Any]]] = {}
    for c in correlations:
        corr_by_sym.setdefault(c["symbol"], []).append(c)

    rows: list[dict[str, Any]] = []
    for sym in symbols:
        sym = str(sym).upper()
        if sym not in prices:
            continue
        sym_corrs = corr_by_sym.get(sym, [])
        fx_corr = next((c for c in sym_corrs if "/" in c.get("related_asset", "")), None)
        cmd_corr = next((c for c in sym_corrs if c.get("related_asset") in ("USO", "GLD", "XLE")), None)
        sec_corr = next((c for c in sym_corrs if str(c.get("related_asset", "")).startswith("XL")), None)
        rows.append({
            "symbol": sym,
            "change_pct_1d": prices[sym].get("change_pct"),
            "strongest_currency_correlation": fx_corr,
            "strongest_commodity_correlation": cmd_corr,
            "strongest_sector_correlation": sec_corr,
            "regime_alignment": regime.get("regime"),
            "regime_confidence": regime.get("confidence"),
            "skeptic_warning": "Low sample — correlation is not causation" if sym_corrs else "Insufficient cross-asset data",
        })
    return rows
