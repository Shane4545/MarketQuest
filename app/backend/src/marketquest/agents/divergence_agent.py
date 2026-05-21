"""Divergence agent — highlights stock vs driver mismatches."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso
from marketquest.cross_asset.divergence_detector import detect_divergences


def run_divergence_agent(snapshot: dict[str, Any], *, as_of: str | None = None) -> dict[str, Any]:
    as_of = as_of or (snapshot.get("timestamp_utc") or today_iso())[:10]
    divergences = (snapshot.get("cross_asset") or {}).get("divergences")
    if divergences is None:
        divergences = detect_divergences(snapshot)
    symbols = snapshot.get("symbols_checked") or ["SPY"]

    if not divergences:
        sym = str(symbols[0]).upper()
        return make_pick(
            symbol=sym,
            agent_id="divergence_agent",
            as_of=as_of,
            score=0.1,
            predicted_bias="neutral",
            headline="No significant divergences detected",
            bullets=["Drivers and stocks moving in expected directions"],
            features={},
            prediction_type="watch",
            horizon="1h",
            confidence=0.15,
            data_mode="live",
        )

    d = max(divergences, key=lambda x: float(x.get("divergence_score") or 0))
    sym = str(d.get("symbol", symbols[0])).upper()
    return make_pick(
        symbol=sym,
        agent_id="divergence_agent",
        as_of=as_of,
        score=float(d.get("divergence_score") or 0.4),
        predicted_bias="neutral",
        headline=f"Divergence watch: {sym} vs {d.get('driver')}",
        bullets=d.get("possible_interpretations") or [],
        features={"divergence": d},
        prediction_type="watch",
        horizon="15m",
        confidence=min(float(d.get("divergence_score") or 0.3) + 0.25, 0.8),
        expected_direction=str(d.get("expected_direction", "unclear")),
        reasons=[
            f"{sym} {d.get('actual_direction')} while {d.get('driver')} suggests {d.get('expected_direction')}",
        ],
        risks=["Divergence does not auto-trigger a paper pick — debate only"],
        data_mode="live",
    )
