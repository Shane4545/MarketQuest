"""Skeptic agent — mandatory counter-thesis to kill weak picks."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso


def run_skeptic(
    other_picks: list[dict[str, Any]],
    snapshot: dict[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or (snapshot.get("timestamp_utc") or today_iso())[:10]
    ai_picks = [
        p
        for p in other_picks
        if p.get("agent_id")
        not in ("skeptic", "ensemble", "random_baseline", "human_baseline")
    ]
    target = ai_picks[0] if ai_picks else {"symbol": "SPY", "agent_id": "unknown"}
    sym = str(target.get("symbol", "SPY")).upper()

    risks: list[str] = []
    score = 0.0

    if not snapshot.get("scoring_data_eligible"):
        risks.append("Stale or offline data — exclude from high-confidence scoring")
        score += 0.4

    fresh = snapshot.get("freshness") or {}
    if fresh.get("label") == "stale":
        risks.append("Quote freshness STALE during market hours")
        score += 0.3

    news = snapshot.get("news_events") or []
    sym_news = [n for n in news if sym in (n.get("candidate_tickers") or n.get("symbols") or [])]
    if not sym_news:
        risks.append("No direct news/filing link to ticker in current snapshot")
        score += 0.2

    if len({p.get("symbol") for p in ai_picks}) == 1 and len(ai_picks) > 2:
        risks.append("All agents agree — possible herding / already priced in")
        score += 0.15

    price_row = next((p for p in snapshot.get("prices", []) if p.get("symbol") == sym), None)
    if price_row:
        chg = abs(float(price_row.get("change_pct") or 0))
        if chg > 5:
            risks.append(f"Large move already ({chg:.1f}%) — timing risk")
            score += 0.2
        vol = int(price_row.get("volume") or 0)
        if vol < 100_000:
            risks.append("Low liquidity — paper fill assumptions may diverge")
            score += 0.1

    if not risks:
        risks.append("No major red flags — skeptic still recommends paper-only watch")

    confidence = min(max(score, 0.2), 0.9)
    prediction_type = "avoid" if confidence >= 0.6 else "watch"

    return make_pick(
        symbol=sym,
        agent_id="skeptic",
        as_of=as_of,
        score=confidence,
        predicted_bias="bearish" if confidence >= 0.5 else "neutral",
        headline=f"Skeptic review of {sym} ({target.get('agent_id', 'consensus')} thesis)",
        bullets=risks[:5],
        features={"risk_count": len(risks), "target_agent": target.get("agent_id")},
        prediction_type=prediction_type,
        horizon="1h",
        confidence=confidence,
        expected_direction="down" if confidence >= 0.6 else "unclear",
        reasons=risks[:3],
        risks=risks,
        data_mode="live",
    )
