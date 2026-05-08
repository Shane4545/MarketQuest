"""Map provider rows into internal normalized OHLCV schema."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from .exporter import NORMALIZED_COLUMNS

REQUIRED_OHLCV = ["open", "high", "low", "close", "volume"]


@dataclass
class MappingResult:
    """Result container for schema mapping."""

    normalized: pd.DataFrame
    rejected_rows: pd.DataFrame
    skipped_symbols: pd.DataFrame


def _source_reference(provider: str) -> str:
    if provider == "fixture":
        return "fixture://openbb_historical_sample"
    if provider == "yfinance":
        return "https://finance.yahoo.com/"
    if provider == "tmx":
        return "https://www.tsx.com/"
    return f"provider://{provider}"


def _coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def map_openbb_rows(
    rows: list[dict[str, Any]],
    requested_symbols: list[str],
    provider: str,
    source_url: str | None = None,
) -> MappingResult:
    """Map raw rows into normalized format with governance side outputs."""
    frame = pd.DataFrame(rows)
    if frame.empty:
        skipped = pd.DataFrame(
            [{"symbol": s, "reason": "no_rows_returned"} for s in requested_symbols]
        )
        empty = pd.DataFrame(columns=NORMALIZED_COLUMNS)
        rejected = pd.DataFrame(columns=["symbol", "reason", "raw_row"])
        return MappingResult(normalized=empty, rejected_rows=rejected, skipped_symbols=skipped)

    rename_map = {"adj_close": "close"}
    frame = frame.rename(columns=rename_map)

    if "symbol" not in frame.columns:
        frame["symbol"] = ""
    if "date" not in frame.columns:
        frame["date"] = pd.NaT

    row_source = source_url or _source_reference(provider)
    if "source_url" not in frame.columns:
        frame["source_url"] = row_source
    frame["source_url"] = frame["source_url"].fillna(row_source)

    for optional in ["market_cap", "exchange", "currency"]:
        if optional not in frame.columns:
            frame[optional] = ""
        frame[optional] = frame[optional].fillna("")

    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    frame = _coerce_numeric(frame, REQUIRED_OHLCV + ["market_cap"])

    bad_mask = frame["symbol"].astype(str).eq("")
    bad_mask |= frame["date"].isna()
    bad_mask |= frame[REQUIRED_OHLCV].isna().any(axis=1)

    rejected = frame[bad_mask].copy()
    if not rejected.empty:
        rejected["reason"] = "missing_required_fields"
        rejected["raw_row"] = rejected.astype(str).to_dict(orient="records")
        rejected = rejected.loc[:, ["symbol", "reason", "raw_row"]]
    else:
        rejected = pd.DataFrame(columns=["symbol", "reason", "raw_row"])

    good = frame[~bad_mask].copy()
    good = good.loc[:, NORMALIZED_COLUMNS]

    found_symbols = set(good["symbol"].astype(str).unique().tolist())
    skipped_symbols = []
    for sym in requested_symbols:
        if sym not in found_symbols:
            skipped_symbols.append({"symbol": sym, "reason": "not_returned_or_rejected"})
    skipped = pd.DataFrame(skipped_symbols, columns=["symbol", "reason"])

    return MappingResult(normalized=good, rejected_rows=rejected, skipped_symbols=skipped)

