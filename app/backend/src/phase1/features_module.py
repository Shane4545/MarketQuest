"""Compute deterministic features per symbol as-of a calendar date."""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd


def _num(series: pd.Series, idx: int, field: str) -> float:
    return float(series.iloc[idx][field])


def compute_row_for_symbol(
    df_sym: pd.DataFrame,
    as_of: date,
    rule_cfg: dict[str, Any],
) -> dict[str, Any]:
    """Return one feature dict for symbol at as_of (last row <= as_of)."""
    sym = str(df_sym["symbol"].iloc[0]) if not df_sym.empty else "UNKNOWN"
    df = df_sym.copy()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df[df["date"] <= as_of].sort_values("date")
    weak_max = float(rule_cfg.get("weak_close_clv_max", 0.35))
    blow_surge = float(rule_cfg.get("blowoff_min_volume_surge", 4.5))
    blow_ret = float(rule_cfg.get("blowoff_min_prior_5d_return_pct", 45))

    out: dict[str, Any] = {
        "symbol": sym,
        "as_of": str(as_of),
        "insufficient_evidence": False,
        "missing_required_ohlcv": False,
    }

    required = ["open", "high", "low", "close", "volume"]
    if df.empty:
        out["insufficient_evidence"] = True
        out["reason"] = "no rows on or before as-of"
        return _nan_fill(out)

    last = df.iloc[-1]
    for c in required:
        if pd.isna(last.get(c)):
            out["missing_required_ohlcv"] = True
            out["insufficient_evidence"] = True

    # Market cap
    mc_raw = last.get("market_cap")
    mc_missing = pd.isna(mc_raw) or (str(mc_raw).strip() == "" or str(mc_raw).strip().lower() == "nan")
    out["market_cap_missing_flag"] = bool(mc_missing)
    if not mc_missing:
        try:
            out["market_cap_value"] = float(mc_raw)
        except (TypeError, ValueError):
            out["market_cap_missing_flag"] = True

    if len(df) < 6:
        out["insufficient_evidence"] = True
        out["prior_5d_return_pct"] = np.nan
        out["volume_surge"] = np.nan
    else:
        c0 = _num(df, -6, "close")
        c1 = _num(df, -1, "close")
        out["prior_5d_return_pct"] = (c1 / c0 - 1.0) * 100.0 if c0 else np.nan
        win = df.iloc[-6:-1]
        v_hist = win["volume"].astype(float)
        v_last = float(last["volume"])
        denom = float(v_hist.mean()) if len(v_hist) and not np.isnan(v_hist.mean()) else np.nan
        out["volume_surge"] = (v_last / denom) if denom and denom > 0 else np.nan

    hi = float(last["high"])
    lo = float(last["low"])
    cl = float(last["close"])
    if hi > lo:
        out["close_location_value"] = (cl - lo) / (hi - lo)
    else:
        out["close_location_value"] = 0.5

    out["close_weak_flag"] = bool(out["close_location_value"] < weak_max)

    pr = out.get("prior_5d_return_pct")
    vs = out.get("volume_surge")
    blowoff = False
    if pr is not None and vs is not None and not (isinstance(pr, float) and np.isnan(pr)):
        try:
            blowoff = float(vs) >= blow_surge and float(pr) >= blow_ret
        except (TypeError, ValueError):
            pass
    out["blowoff_flag"] = blowoff

    return out


def _nan_fill(out: dict[str, Any]) -> dict[str, Any]:
    defaults = {
        "prior_5d_return_pct": np.nan,
        "volume_surge": np.nan,
        "close_location_value": np.nan,
        "close_weak_flag": False,
        "blowoff_flag": False,
        "market_cap_missing_flag": False,
    }
    for k, v in defaults.items():
        out.setdefault(k, v)
    return out


def compute_features_table(df: pd.DataFrame, as_of: date, rule_cfg: dict[str, Any]) -> pd.DataFrame:
    rows = []
    for sym in sorted(df["symbol"].unique()):
        sub = df[df["symbol"] == sym]
        rows.append(compute_row_for_symbol(sub, as_of, rule_cfg))
    return pd.DataFrame(rows)
