"""CSV export helpers for normalized acquisition output."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

NORMALIZED_COLUMNS = [
    "symbol",
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "market_cap",
    "exchange",
    "currency",
    "source_url",
]


def ensure_column_order(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure exact normalized column order."""
    missing = [col for col in NORMALIZED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing normalized columns: {missing}")
    return df.loc[:, NORMALIZED_COLUMNS]


def write_csv(df: pd.DataFrame, output_path: Path) -> None:
    """Write CSV with exact column order."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered = ensure_column_order(df)
    ordered.to_csv(output_path, index=False)

