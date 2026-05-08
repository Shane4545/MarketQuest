"""Build random matched control basket from universe (staged prices metadata)."""

from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from _bootstrap import ensure_phase1_path

ensure_phase1_path()

from phase1.paths import baskets_dir, staged_dir  # noqa: E402


def safe_float(x) -> float | None:
    if x == "" or x is None or (isinstance(x, float) and pd.isna(x)):
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def market_cap_bucket(mc: float | None) -> str:
    if mc is None:
        return "unknown"
    if mc < 50_000_000:
        return "micro"
    if mc < 300_000_000:
        return "small"
    if mc < 2_000_000_000:
        return "mid"
    return "large"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--basket-name", required=True)
    ap.add_argument("--method", default="random_matched")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    basket_files = list(baskets_dir().glob(f"{args.basket_name}_*.json"))
    # exclude control files
    basket_files = [p for p in basket_files if "_controls_" not in p.name]
    if not basket_files:
        raise SystemExit(f"No frozen basket json matching {args.basket_name}_*.json")

    basket_path = sorted(basket_files, key=lambda p: p.stat().st_mtime)[-1]
    with open(basket_path, encoding="utf-8") as f:
        basket = json.load(f)

    as_of = basket["as_of"]
    as_of_d = date.fromisoformat(as_of)
    symbols_in = {p["symbol"] for p in basket["positions"]}

    prices = pd.read_parquet(staged_dir() / "prices.parquet")
    prices["date"] = pd.to_datetime(prices["date"]).dt.date
    row_asof = prices[prices["date"] == as_of_d]
    if row_asof.empty:
        raise SystemExit("No staged rows on as-of date for controls")

    rng = random.Random(args.seed)
    all_syms = set(row_asof["symbol"].astype(str))

    controls = []
    for sym in symbols_in:
        sub = row_asof[row_asof["symbol"] == sym].iloc[0]
        mc = safe_float(sub.get("market_cap"))
        bucket = market_cap_bucket(mc)

        def same_bucket(r) -> bool:
            return market_cap_bucket(safe_float(r.get("market_cap"))) == bucket

        pool = row_asof[row_asof.apply(same_bucket, axis=1)]
        pool_syms = [str(s) for s in pool["symbol"].unique() if str(s) not in symbols_in]
        if not pool_syms:
            pool_syms = [str(s) for s in all_syms - symbols_in]
        if not pool_syms:
            raise SystemExit("No control pool available")
        pick = rng.choice(pool_syms)
        controls.append(
            {
                "treatment_symbol": sym,
                "control_symbol": pick,
                "stratum": bucket,
                "method": args.method,
            }
        )

    out = {
        "basket_name": args.basket_name,
        "as_of": as_of,
        "method": args.method,
        "seed": args.seed,
        "pairs": controls,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    outp = baskets_dir() / f"{args.basket_name}_controls_{as_of}.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote control basket -> {outp}")


if __name__ == "__main__":
    main()
