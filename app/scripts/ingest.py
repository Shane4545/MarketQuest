"""Ingest raw universe CSV -> staged Parquet."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from _bootstrap import ensure_phase1_path

ensure_phase1_path()

from phase1.paths import staged_dir  # noqa: E402
from phase1.schema import UNIVERSE_COLUMNS  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest universe CSV into staged Parquet.")
    ap.add_argument("--input", required=True, help="Path to raw universe CSV")
    args = ap.parse_args()

    src = Path(args.input)
    if not src.is_file():
        raise SystemExit(f"Input not found: {src}")

    df = pd.read_csv(src)
    missing = [c for c in UNIVERSE_COLUMNS if c not in df.columns]
    if missing:
        raise SystemExit(f"Missing required columns: {missing}")

    df["date"] = pd.to_datetime(df["date"])
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    out = staged_dir() / "prices.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    print(f"Ingested {len(df)} rows -> {out}")


if __name__ == "__main__":
    main()
