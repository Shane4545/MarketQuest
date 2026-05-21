"""OHLCV helpers for MarketQuest agents."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pandas as pd


def fetch_prices_yfinance(symbols: list[str], *, days: int = 30) -> pd.DataFrame:
    """Download recent daily bars via yfinance."""
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return pd.DataFrame()

    end = date.today()
    start = end - timedelta(days=days + 5)
    frames: list[pd.DataFrame] = []
    for sym in symbols:
        try:
            raw = yf.download(
                sym,
                start=start.isoformat(),
                end=end.isoformat(),
                progress=False,
                auto_adjust=True,
            )
            if raw is None or raw.empty:
                continue
            df = raw.reset_index()
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            colmap = {c.lower(): c for c in df.columns}
            date_col = colmap.get("date") or "Date"
            close_col = colmap.get("close") or "Close"
            vol_col = colmap.get("volume") or "Volume"
            out = pd.DataFrame(
                {
                    "symbol": sym.upper(),
                    "date": pd.to_datetime(df[date_col]).dt.date.astype(str),
                    "close": pd.to_numeric(df[close_col], errors="coerce"),
                    "volume": pd.to_numeric(df.get(vol_col, 0), errors="coerce").fillna(0),
                }
            )
            frames.append(out.dropna(subset=["close"]))
        except Exception:
            continue
    if not frames:
        return pd.DataFrame(columns=["symbol", "date", "close", "volume"])
    return pd.concat(frames, ignore_index=True)


def latest_close_by_symbol(prices_df: pd.DataFrame) -> dict[str, float]:
    out: dict[str, float] = {}
    if prices_df.empty:
        return out
    for sym, grp in prices_df.groupby("symbol"):
        row = grp.sort_values("date").iloc[-1]
        out[str(sym).upper()] = float(row["close"])
    return out


def simple_features(prices_df: pd.DataFrame, as_of: date) -> list[dict[str, Any]]:
    """Rule-based features per symbol for V0 when ML pipeline unavailable."""
    rows: list[dict[str, Any]] = []
    if prices_df.empty:
        return rows
    as_of_s = as_of.isoformat()
    for sym, grp in prices_df.groupby("symbol"):
        g = grp.sort_values("date")
        if len(g) < 2:
            continue
        last = g.iloc[-1]
        prev = g.iloc[-2]
        close = float(last["close"])
        prev_close = float(prev["close"])
        gap_pct = ((close - prev_close) / prev_close * 100) if prev_close else 0.0
        vol = float(last.get("volume") or 0)
        avg_vol = float(g["volume"].tail(20).mean() or 1)
        rvol = vol / avg_vol if avg_vol > 0 else 1.0
        rows.append(
            {
                "symbol": str(sym).upper(),
                "as_of": as_of_s,
                "gap_pct": round(gap_pct, 4),
                "rvol": round(rvol, 4),
                "close": close,
                "ml_predicted_return_1d_pct": round(gap_pct * min(rvol, 10) * 0.1, 4),
                "sentiment_mean": 0.0,
            }
        )
    return rows
