"""Ensemble agent — blend of other agent picks with skeptic adjustment."""

from __future__ import annotations

from collections import Counter
from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso


def run_ensemble(
    picks: list[dict[str, Any]],
    *,
    as_of: str | None = None,
    skeptic: dict[str, Any] | None = None,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    exclude = {"random_baseline", "human_baseline", "ensemble", "skeptic"}
    ai = [p for p in picks if p.get("agent_id") not in exclude]
    if not ai:
        return make_pick(
            symbol="SPY",
            agent_id="ensemble",
            as_of=as_of,
            score=0,
            predicted_bias="neutral",
            headline="No eligible agent picks for ensemble",
            bullets=[],
            features={},
            prediction_type="watch",
            horizon="1d",
            confidence=0.1,
        )
    counts = Counter(p["symbol"] for p in ai)
    sym, votes = counts.most_common(1)[0]
    avg_score = sum(float(p.get("score") or 0) for p in ai if p.get("symbol") == sym) / max(votes, 1)
    confidence = min(avg_score, 0.85)
    prediction_type = "paper_long"
    horizon = "1d"

    if skeptic and skeptic.get("symbol") == sym:
        sk_conf = float(skeptic.get("confidence") or 0)
        if sk_conf >= 0.6:
            prediction_type = "watch"
            confidence = max(confidence - sk_conf * 0.5, 0.15)
        elif sk_conf >= 0.4:
            confidence = max(confidence - 0.15, 0.2)

    return make_pick(
        symbol=sym,
        agent_id="ensemble",
        as_of=as_of,
        score=round(avg_score, 4),
        predicted_bias="bullish" if avg_score > 0 else "neutral",
        headline=f"Ensemble paper hypothesis: {sym} ({votes} agents agree)",
        bullets=[
            f"Votes: {votes}",
            f"Blended score: {avg_score:.3f}",
            "Not investment advice — paper prediction only",
        ],
        features={"votes": votes, "agents": len(ai)},
        data_mode=ai[0].get("data_mode", "live"),
        prediction_type=prediction_type,
        horizon=horizon,
        confidence=round(confidence, 4),
        expected_direction="up" if prediction_type == "paper_long" else "unclear",
        reasons=[f"{votes} agents selected {sym}", "Ensemble weighted consensus"],
        risks=(skeptic.get("risks", [])[:2] if skeptic else []),
    )
