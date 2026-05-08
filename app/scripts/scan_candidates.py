"""
Scan feature table with configurable rules (no hard-coded symbols).

Reads pattern_rules.yaml; outputs selected and rejected candidate Parquet files.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

import pandas as pd
import yaml

from _bootstrap import ensure_phase1_path

ensure_phase1_path()

from phase1.paths import config_dir, curated_dir, features_dir  # noqa: E402
from phase1.scan_rules import scan_frame  # noqa: E402


def load_rules() -> dict:
    p = config_dir() / "pattern_rules.yaml"
    with open(p, encoding="utf-8") as f:
        return yaml.safe_load(f)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--rule", default="momentum_volume_pressure")
    ap.add_argument(
        "--features",
        default=None,
        help="Features parquet (default: app/data/features/features_<as-of>.parquet)",
    )
    args = ap.parse_args()

    date.fromisoformat(args.as_of)  # validate

    feat_path = Path(
        args.features
        if args.features
        else features_dir() / f"features_{args.as_of}.parquet"
    )
    if not feat_path.is_file():
        raise SystemExit(f"Features not found: {feat_path}")

    features = pd.read_parquet(feat_path)
    rules = load_rules()
    selected, rejected = scan_frame(features, args.rule, rules)

    curated_dir().mkdir(parents=True, exist_ok=True)
    out_sel = curated_dir() / f"candidates_{args.as_of}.parquet"
    out_rej = curated_dir() / f"rejected_candidates_{args.as_of}.parquet"
    selected.to_parquet(out_sel, index=False)
    rejected.to_parquet(out_rej, index=False)
    print(f"Selected {len(selected)} -> {out_sel}")
    print(f"Rejected {len(rejected)} -> {out_rej}")


if __name__ == "__main__":
    main()
