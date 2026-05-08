"""Compute per-symbol features as-of a date -> features parquet."""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from _bootstrap import ensure_phase1_path

ensure_phase1_path()

from phase1.features_module import compute_features_table  # noqa: E402
from phase1.paths import config_dir, features_dir, staged_dir  # noqa: E402


def load_rules_yaml() -> dict:
    p = config_dir() / "pattern_rules.yaml"
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True, help="YYYY-MM-DD")
    ap.add_argument(
        "--staged",
        default=str(staged_dir() / "prices.parquet"),
        help="Input staged parquet",
    )
    args = ap.parse_args()

    as_of = date.fromisoformat(args.as_of)
    staged = Path(args.staged)

    rules = load_rules_yaml()
    rule_cfg = rules.get("momentum_volume_pressure", {})

    df = pd.read_parquet(staged)
    df["date"] = pd.to_datetime(df["date"])

    feat = compute_features_table(df, as_of, rule_cfg)
    out = features_dir() / f"features_{args.as_of}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    feat.to_parquet(out, index=False)
    print(f"Wrote {len(feat)} feature rows -> {out}")


if __name__ == "__main__":
    main()
