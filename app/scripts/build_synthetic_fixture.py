"""
Generate app/data/raw/synthetic_prices.csv — synthetic symbols TEST_A…TEST_J only.

Run from repo root:
  python app/scripts/build_synthetic_fixture.py

Validates fixture constraints for Phase 1 demos (no real tickers).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[2]
sys.path.insert(0, str(_REPO / "app" / "backend" / "src"))

from phase1.paths import raw_dir  # noqa: E402


def trading_calendar() -> list[pd.Timestamp]:
    return list(pd.bdate_range("2025-12-15", "2026-01-23"))


def build_rows() -> pd.DataFrame:
    """Piecewise OHLCV paths tuned for scanner + review windows."""
    days = trading_calendar()
    idx = {d.date(): i for i, d in enumerate(days)}

    as_of = pd.Timestamp("2026-01-08").date()
    review = pd.Timestamp("2026-01-13").date()

    rows: list[dict] = []

    def add(sym: str, d, o, h, l, c, v, mc, ex="SYN", cur="USD"):
        rows.append(
            {
                "symbol": sym,
                "date": d,
                "open": o,
                "high": h,
                "low": l,
                "close": c,
                "volume": int(v),
                "market_cap": mc,
                "exchange": ex,
                "currency": cur,
                "source_url": "https://fixture.local/synthetic",
            }
        )

    # --- TEST_A: clear PASS (momentum + volume surge + strong close) ---
    sym = "TEST_A"
    base = 50.0
    for d in days:
        dd = d.date()
        di = idx[dd]
        # Unbounded slow drift; coefficient tuned so 5-trading-day return into as-of clears rule thresholds
        ramp = 1.0 + di * 0.045
        o = base * ramp
        vol = 350_000 + di * 500
        if dd == as_of:
            h, l, c = o * 1.09, o * 1.01, o * 1.07
            vol = 3_000_000  # spike vs ~400k avg prior window
        elif dd == review:
            h, l, c = o * 1.02, o * 0.98, o * 1.01
            vol = 800_000
        else:
            h, l, c = o * 1.03, o * 0.97, o * 1.015
        add(sym, dd, o, h, l, c, vol, 55_000_000)

    # --- TEST_B: FAIL weak close on as-of ---
    sym = "TEST_B"
    for d in days:
        dd = d.date()
        di = idx[dd]
        o = 40 + di * 0.35
        if dd == as_of:
            h, l, c = o + 6, o - 1, o - 0.8  # close near low of range
            vol = 900_000
        elif dd == review:
            h, l, c = o * 1.01, o * 0.99, o
            vol = 700_000
        else:
            h, l, c = o + 2, o - 2, o + 0.5
            vol = 650_000 + di * 1000
        add(sym, dd, o, h, l, c, vol, 82_000_000)

    # --- TEST_C: FAIL blowoff (extreme run + extreme volume on as-of) ---
    sym = "TEST_C"
    for d in days:
        dd = d.date()
        di = idx[dd]
        o = 12 + di * 0.08
        if dd == as_of:
            h, l, c = o * 2.2, o * 1.05, o * 2.0  # huge extension
            vol = 12_000_000
        elif dd == review:
            h, l, c = o * 1.05, o * 0.95, o * 1.02
            vol = 4_000_000
        else:
            h, l, c = o * 1.08, o * 0.96, o * 1.05
            vol = 1_200_000
        add(sym, dd, o, h, l, c, vol, 120_000_000)

    # --- TEST_D: FAIL missing market_cap ---
    sym = "TEST_D"
    for d in days:
        dd = d.date()
        di = idx[dd]
        o = 25 + di * 0.05
        h, l, c = o * 1.04, o * 0.96, o * 1.02
        add(sym, dd, o, h, l, c, 500_000 + di * 2000, "")  # blank MC

    # --- TEST_E: includes high==low stale session + otherwise marginal ---
    sym = "TEST_E"
    flat_day = pd.Timestamp("2025-12-22").date()
    for d in days:
        dd = d.date()
        di = idx[dd]
        o = 33 + di * 0.06
        if dd == flat_day:
            h = l = c = o
            vol = 120_000
        elif dd == as_of:
            h, l, c = o + 1.5, o - 1.5, o + 0.2  # mediocre CLV / momentum
            vol = 700_000
        elif dd == review:
            h, l, c = o * 1.01, o * 0.99, o * 1.005
            vol = 400_000
        else:
            h, l, c = o + 1.2, o - 1.2, o + 0.4
            vol = 550_000 + di * 300
        add(sym, dd, o, h, l, c, vol, 205_000_000)

    # --- TEST_F: marginal FAIL (barely misses surge or CLV depending); tuned fail surge ---
    sym = "TEST_F"
    for d in days:
        dd = d.date()
        di = idx[dd]
        o = 60 + di * 0.12
        if dd == as_of:
            h, l, c = o * 1.04, o * 0.99, o * 1.03
            vol = 700_000  # <2x vs prior week average
        elif dd == review:
            h, l, c = o * 1.01, o * 0.99, o
            vol = 500_000
        else:
            h, l, c = o * 1.02, o * 0.98, o * 1.01
            vol = 480_000
        add(sym, dd, o, h, l, c, vol, 48_000_000)

    # --- TEST_G: FAIL low volume pattern ---
    sym = "TEST_G"
    for d in days:
        dd = d.date()
        di = idx[dd]
        o = 70 + di * 0.02
        h, l, c = o * 1.01, o * 0.99, o * 1.005
        vol = 12_000 + di * 50  # thin
        add(sym, dd, o, h, l, c, vol, 95_000_000)

    # --- TEST_H: PASS with pronounced volume spike ---
    sym = "TEST_H"
    for d in days:
        dd = d.date()
        di = idx[dd]
        o = 10 + di * 0.40
        if dd == as_of:
            h, l, c = o * 1.15, o * 1.02, o * 1.12
            vol = 8_000_000
        elif dd == review:
            h, l, c = o * 1.03, o * 0.97, o * 1.01
            vol = 2_000_000
        else:
            h, l, c = o * 1.06, o * 0.98, o * 1.04
            vol = 450_000
        add(sym, dd, o, h, l, c, vol, 31_000_000)

    # --- TEST_I: micro-cap PASS ---
    sym = "TEST_I"
    for d in days:
        dd = d.date()
        di = idx[dd]
        o = 3.0 + di * 0.05
        if dd == as_of:
            h, l, c = o * 1.28, o * 1.05, o * 1.24
            vol = 4_500_000
        elif dd == review:
            h, l, c = o * 1.05, o * 0.97, o * 1.03
            vol = 1_000_000
        else:
            h, l, c = o * 1.12, o * 0.94, o * 1.08
            vol = 600_000 + di * 4000
        add(sym, dd, o, h, l, c, vol, 6_000_000)

    # --- TEST_J: large-cap slow drift FAIL momentum ---
    sym = "TEST_J"
    for d in days:
        dd = d.date()
        di = idx[dd]
        o = 200 + di * 0.08
        if dd == as_of:
            h, l, c = o * 1.01, o * 0.995, o * 1.006
            vol = 5_000_000
        elif dd == review:
            h, l, c = o * 1.002, o * 0.998, o * 1.001
            vol = 4_000_000
        else:
            h, l, c = o * 1.004, o * 0.996, o * 1.001
            vol = 4_500_000
        add(sym, dd, o, h, l, c, vol, 50_000_000_000)

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df


def main() -> None:
    out = raw_dir() / "synthetic_prices.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df = build_rows()
    df.to_csv(out, index=False)
    print(f"Wrote {len(df)} rows to {out}")


if __name__ == "__main__":
    main()
