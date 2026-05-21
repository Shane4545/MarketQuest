"""Simple momentum baseline — transparent top-momentum rule."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso

TOP_N = 3


def run_momentum_baseline(
    snapshot: dict[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    prices = list(snapshot.get("prices") or [])
    if not prices:
        sym = (snapshot.get("symbols_checked") or ["SPY"])[0]
        return make_pick(
            symbol=sym,
            agent_id="momentum_baseline",
            as_of=as_of,
            score=0,
            predicted_bias="neutral",
            headline="Momentum baseline (no prices)",
            bullets=[f"Rule: buy top {TOP_N} by recent change_pct"],
            features={"rule": "top_momentum"},
            prediction_type="watch",
            horizon="1w",
            confidence=0.3,
            player_type="benchmark",
        )
    ranked = sorted(prices, key=lambda p: float(p.get("change_pct") or 0), reverse=True)
    top = ranked[0]
    sym = top["symbol"]
    chg = float(top.get("change_pct") or 0)
    runners = [p["symbol"] for p in ranked[1:TOP_N]]
    return make_pick(
        symbol=sym,
        agent_id="momentum_baseline",
        as_of=as_of,
        score=abs(chg) / 10,
        predicted_bias="bullish" if chg > 0 else "bearish",
        headline=f"Momentum baseline: top mover {sym} ({chg:.2f}%)",
        bullets=[
            f"Transparent rule: rank by change_pct, pick #{1}",
            f"Runners-up: {', '.join(runners) or 'none'}",
            "Rebalance weekly in paper scoring",
        ],
        features={"change_pct": chg, "rule": "top_momentum", "benchmark": True},
        data_mode="live",
        prediction_type="paper_long" if chg > 0 else "watch",
        horizon="1w",
        confidence=min(abs(chg) / 20, 0.7),
        reasons=[f"Top momentum: {sym} at {chg:.2f}%"],
        risks=["Momentum reversals are common"],
        runners_up=runners,
        player_type="benchmark",
    )
