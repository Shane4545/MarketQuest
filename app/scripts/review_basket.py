"""
Review basket outcomes: forward 1, 3, 5 *trading* day returns from as-of close.

Uses staged prices only (synthetic or future CSV imports).
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd

from _bootstrap import ensure_phase1_path

ensure_phase1_path()

from phase1.paths import baskets_dir, staged_dir  # noqa: E402


def nth_trading_day_after(cal: list[date], start: date, n: int) -> date | None:
    """Return calendar date n sessions forward from start (same-day index + n)."""
    try:
        idx = cal.index(start)
    except ValueError:
        idx = next(i for i, d in enumerate(cal) if d >= start)
        if cal[idx] != start:
            idx -= 1  # anchor on last session <= start when holiday mismatch
    j = idx + n
    return cal[j] if j < len(cal) else None


def trading_calendar_from_df(df: pd.DataFrame) -> list[date]:
    days = sorted(df["date"].unique())
    return [d.date() if hasattr(d, "date") else d for d in days]


def close_on(df: pd.DataFrame, sym: str, d: date) -> float | None:
    sub = df[(df["symbol"].astype(str) == sym) & (df["date"] == d)]
    if sub.empty:
        return None
    return float(sub.iloc[0]["close"])


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--basket-name", required=True)
    ap.add_argument("--review-date", required=True, help="Primary label date (e.g. report snapshot)")
    args = ap.parse_args()

    review_d = date.fromisoformat(args.review_date)

    basket_files = [p for p in baskets_dir().glob(f"{args.basket_name}_*.json") if "_controls_" not in p.name]
    if not basket_files:
        raise SystemExit("Basket json not found")
    basket_path = sorted(basket_files, key=lambda p: p.stat().st_mtime)[-1]
    with open(basket_path, encoding="utf-8") as f:
        basket = json.load(f)

    as_of = date.fromisoformat(basket["as_of"])

    prices = pd.read_parquet(staged_dir() / "prices.parquet")
    prices["date"] = pd.to_datetime(prices["date"]).dt.date
    cal = trading_calendar_from_df(prices)

    rows = []
    for pos in basket["positions"]:
        sym = pos["symbol"]
        e0 = close_on(prices, sym, as_of)
        d1 = nth_trading_day_after(cal, as_of, 1)
        d3 = nth_trading_day_after(cal, as_of, 3)
        d5 = nth_trading_day_after(cal, as_of, 5)
        r_entry_review = None
        if e0 is not None:
            er = close_on(prices, sym, review_d)
            if er is not None:
                r_entry_review = (er / e0 - 1.0) * 100.0

        def ret_fwd(n: int) -> float | None:
            dn = nth_trading_day_after(cal, as_of, n)
            if e0 is None or dn is None:
                return None
            ex = close_on(prices, sym, dn)
            if ex is None:
                return None
            return (ex / e0 - 1.0) * 100.0

        rows.append(
            {
                "symbol": sym,
                "entry_close_as_of": e0,
                "review_date": str(review_d),
                "close_on_review_date": close_on(prices, sym, review_d),
                "return_pct_asof_to_review": r_entry_review,
                "forward_return_1d_pct": ret_fwd(1),
                "forward_return_3d_pct": ret_fwd(3),
                "forward_return_5d_pct": ret_fwd(5),
            }
        )

    out = baskets_dir() / f"{args.basket_name}_review_{args.review_date}.json"
    payload = {
        "basket_name": args.basket_name,
        "as_of": str(as_of),
        "review_date": args.review_date,
        "rows": rows,
    }
    with open(out, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print(f"Wrote review -> {out}")


if __name__ == "__main__":
    main()
