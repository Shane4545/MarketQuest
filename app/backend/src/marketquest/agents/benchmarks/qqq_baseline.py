"""QQQ baseline — paper-tracks large-cap tech proxy."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso


def run_qqq_baseline(
    snapshot: dict[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    prices = {p["symbol"]: p for p in snapshot.get("prices", [])}
    qqq = prices.get("QQQ", {})
    chg = float(qqq.get("change_pct") or 0)
    return make_pick(
        symbol="QQQ",
        agent_id="qqq_baseline",
        as_of=as_of,
        score=abs(chg) / 10,
        predicted_bias="bullish" if chg >= 0 else "bearish",
        headline="QQQ Baseline — Nasdaq-100 proxy",
        bullets=[
            "Passive benchmark: tracks QQQ return",
            "Measures whether players beat large-cap tech",
        ],
        features={"change_pct": chg, "benchmark": True},
        data_mode="live",
        prediction_type="paper_long",
        horizon="1w",
        confidence=0.5,
        reasons=["Tech index benchmark"],
        risks=["Concentrated in mega-cap tech"],
        player_type="benchmark",
    )
