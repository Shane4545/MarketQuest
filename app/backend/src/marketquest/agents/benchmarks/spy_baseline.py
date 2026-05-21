"""SPY baseline — paper-tracks S&P 500 proxy."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso


def run_spy_baseline(
    snapshot: dict[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    prices = {p["symbol"]: p for p in snapshot.get("prices", [])}
    spy = prices.get("SPY", {})
    chg = float(spy.get("change_pct") or 0)
    return make_pick(
        symbol="SPY",
        agent_id="spy_baseline",
        as_of=as_of,
        score=abs(chg) / 10,
        predicted_bias="bullish" if chg >= 0 else "bearish",
        headline="SPY Baseline — S&P 500 proxy",
        bullets=[
            "Passive benchmark: tracks SPY return",
            "Measures whether players beat the broad market",
        ],
        features={"change_pct": chg, "benchmark": True},
        data_mode="live",
        prediction_type="paper_long",
        horizon="1w",
        confidence=0.5,
        reasons=["Index benchmark — no stock selection skill"],
        risks=["Broad market exposure"],
        player_type="benchmark",
    )
