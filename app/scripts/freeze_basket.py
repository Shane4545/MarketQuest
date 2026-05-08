"""Freeze a paper basket from candidate selection (metadata + allocations)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from _bootstrap import ensure_phase1_path

ensure_phase1_path()

from phase1.paths import baskets_dir, curated_dir  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--as-of", required=True)
    ap.add_argument("--basket-name", required=True)
    ap.add_argument("--amount", type=float, required=True, help="Notional paper amount (currency units)")
    ap.add_argument("--from-candidates", required=True, help="Path to candidates parquet")
    args = ap.parse_args()

    date.fromisoformat(args.as_of)
    cpath = Path(args.from_candidates)
    if not cpath.is_file():
        raise SystemExit(f"Candidates file not found: {cpath}")

    cand = pd.read_parquet(cpath)
    if cand.empty:
        raise SystemExit("No candidates to freeze")

    n = len(cand)
    per = float(args.amount) / n
    positions = []
    for _, row in cand.iterrows():
        positions.append(
            {
                "symbol": str(row["symbol"]),
                "notional_allocation": per,
                "scan_reason": str(row.get("scan_reason", "")),
            }
        )

    payload = {
        "basket_name": args.basket_name,
        "as_of": args.as_of,
        "notional_total": float(args.amount),
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "rule": str(cand.iloc[0].get("rule", "")),
        "positions": positions,
        "source_candidates_path": str(cpath.resolve()),
    }
    h = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    payload["basket_hash"] = h

    baskets_dir().mkdir(parents=True, exist_ok=True)
    out = baskets_dir() / f"{args.basket_name}_{args.as_of}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Frozen basket -> {out}")


if __name__ == "__main__":
    main()
