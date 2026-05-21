"""Correlation skeptic — vetoes spurious cross-asset relationships."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso


def run_correlation_skeptic(
    other_picks: list[dict[str, Any]],
    snapshot: dict[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or (snapshot.get("timestamp_utc") or today_iso())[:10]
    cross = snapshot.get("cross_asset") or {}
    correlations = cross.get("correlations") or []
    divergences = cross.get("divergences") or []

    fx_picks = [p for p in other_picks if p.get("agent_id") in ("fx_agent", "cross_asset_agent", "regime_agent")]
    target = fx_picks[0] if fx_picks else (other_picks[0] if other_picks else {"symbol": "SPY"})
    sym = str(target.get("symbol", "SPY")).upper()

    risks: list[str] = []
    score = 0.0

    weak_corrs = [c for c in correlations if c.get("symbol") == sym and c.get("sample_count", 0) < 5]
    if weak_corrs:
        risks.append(f"Only {weak_corrs[0].get('sample_count', 1)} sample(s) for {sym} correlation — unstable")
        score += 0.35

    unstable = [c for c in correlations if c.get("symbol") == sym and c.get("direction") == "unstable"]
    if unstable:
        risks.append("Correlation direction unstable in current snapshot")
        score += 0.25

    if not correlations:
        risks.append("No correlation data — cross-asset thesis unverified")
        score += 0.2

    stale_fx = [
        f for f in (cross.get("forex") or [])
        if f.get("status") in ("STALE", "OFFLINE") or f.get("last") is None
    ]
    if len(stale_fx) >= 3:
        risks.append(f"{len(stale_fx)} FX pairs offline/stale — currency thesis unreliable")
        score += 0.3

    if divergences:
        for d in divergences:
            if d.get("symbol") == sym:
                risks.append(f"Active divergence vs {d.get('driver')} — relationship may be broken today")
                score += 0.2
                break

    if not risks:
        risks.append("Cross-asset links look plausible but still paper-only — correlation ≠ causation")

    confidence = min(max(score, 0.15), 0.9)
    prediction_type = "avoid" if confidence >= 0.55 else "watch"

    return make_pick(
        symbol=sym,
        agent_id="correlation_skeptic",
        as_of=as_of,
        score=confidence,
        predicted_bias="bearish" if confidence >= 0.5 else "neutral",
        headline=f"Correlation skeptic review of {sym}",
        bullets=risks[:5],
        features={"risk_count": len(risks), "correlation_count": len(correlations)},
        prediction_type=prediction_type,
        horizon="1h",
        confidence=confidence,
        expected_direction="unclear",
        reasons=risks[:3],
        risks=risks,
        data_mode="live",
        player_type="agent",
    )
