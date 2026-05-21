"""Equal-weight watchlist baseline."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso


def run_equal_weight_baseline(
    snapshot: dict[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    prices = snapshot.get("prices", [])
    if not prices:
        sym = (snapshot.get("symbols_checked") or ["SPY"])[0]
        return make_pick(
            symbol=sym,
            agent_id="equal_weight_baseline",
            as_of=as_of,
            score=0,
            predicted_bias="neutral",
            headline="Equal-weight watchlist (no prices)",
            bullets=["Equal weight all eligible names"],
            features={"equal_weight": True},
            prediction_type="watch",
            horizon="1w",
            confidence=0.3,
            player_type="benchmark",
        )
    avg_chg = sum(float(p.get("change_pct") or 0) for p in prices) / len(prices)
    top = max(prices, key=lambda p: abs(float(p.get("change_pct") or 0)))
    sym = top["symbol"]
    return make_pick(
        symbol=sym,
        agent_id="equal_weight_baseline",
        as_of=as_of,
        score=abs(avg_chg) / 10,
        predicted_bias="bullish" if avg_chg >= 0 else "bearish",
        headline=f"Equal-weight watchlist ({len(prices)} names, avg {avg_chg:.2f}%)",
        bullets=[
            f"Equal weight across {len(prices)} watchlist symbols",
            f"Average change: {avg_chg:.2f}%",
            "Representative pick shown for display",
        ],
        features={"avg_change_pct": round(avg_chg, 4), "symbol_count": len(prices), "benchmark": True},
        data_mode="live",
        prediction_type="paper_long",
        horizon="1w",
        confidence=0.4,
        reasons=["Diversified equal-weight basket"],
        risks=["No stock-picking edge — diversification baseline"],
        player_type="benchmark",
    )
