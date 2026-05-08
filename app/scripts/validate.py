"""Validate staged prices Parquet (schema + OHLCV sanity)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from _bootstrap import ensure_phase1_path

ensure_phase1_path()

from phase1.schema import UNIVERSE_COLUMNS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Staged prices Parquet")
    args = ap.parse_args()

    p = Path(args.input)
    if not p.is_file():
        raise SystemExit(f"File not found: {p}")

    df = pd.read_parquet(p)
    missing = [c for c in UNIVERSE_COLUMNS if c not in df.columns]
    if missing:
        print("VALIDATION_FAIL missing columns:", missing, file=sys.stderr)
        raise SystemExit(1)

    bad = df[df["high"] < df["low"]]
    if not bad.empty:
        print("VALIDATION_FAIL high<low rows:", len(bad), file=sys.stderr)
        raise SystemExit(1)

    if (df["volume"] < 0).any():
        print("VALIDATION_FAIL negative volume", file=sys.stderr)
        raise SystemExit(1)

    if df[["open", "high", "low", "close"]].isna().any().any():
        print("VALIDATION_FAIL NaN in OHLC", file=sys.stderr)
        raise SystemExit(1)

    print(f"OK validated {len(df)} rows in {p}")


if __name__ == "__main__":
    main()
