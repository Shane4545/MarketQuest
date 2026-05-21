"""Cross-asset agent — oil/yields/sectors vs individual stocks."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso


def run_cross_asset_agent(snapshot: dict[str, Any], *, as_of: str | None = None) -> dict[str, Any]:
    as_of = as_of or (snapshot.get("timestamp_utc") or today_iso())[:10]
    cross = snapshot.get("cross_asset") or {}
    matrix = cross.get("matrix") or []
    divergences = cross.get("divergences") or []
    symbols = snapshot.get("symbols_checked") or ["SPY"]

    if divergences:
        d = divergences[0]
        return make_pick(
            symbol=str(d.get("symbol", symbols[0])).upper(),
            agent_id="cross_asset_agent",
            as_of=as_of,
            score=float(d.get("divergence_score") or 0.4),
            predicted_bias="neutral",
            headline=f"Divergence: {d.get('symbol')} vs {d.get('driver')}",
            bullets=d.get("possible_interpretations") or [],
            features={"divergence": d},
            prediction_type="watch",
            horizon="1h",
            confidence=min(float(d.get("divergence_score") or 0.3) + 0.2, 0.75),
            expected_direction=str(d.get("expected_direction", "unclear")),
            reasons=[f"Expected {d.get('expected_direction')} from {d.get('driver')}, saw {d.get('actual_direction')}"],
            risks=["Divergence may resolve or relationship may be invalid"],
            data_mode="live",
        )

    if matrix:
        row = matrix[0]
        sym = str(row.get("symbol", symbols[0])).upper()
        fx = row.get("strongest_currency_correlation") or {}
        return make_pick(
            symbol=sym,
            agent_id="cross_asset_agent",
            as_of=as_of,
            score=0.45,
            predicted_bias="neutral",
            headline=f"Cross-asset context for {sym}",
            bullets=[
                f"Regime: {row.get('regime_alignment')}",
                f"FX link: {fx.get('related_asset')} ({fx.get('direction', 'n/a')})",
            ],
            features={"matrix_row": row},
            prediction_type="watch",
            horizon="1d",
            confidence=float(row.get("regime_confidence") or 0.4),
            reasons=["Cross-asset matrix alignment check"],
            risks=[str(row.get("skeptic_warning", ""))],
            data_mode="live",
        )

    sym = str(symbols[0]).upper()
    return make_pick(
        symbol=sym,
        agent_id="cross_asset_agent",
        as_of=as_of,
        score=0.15,
        predicted_bias="neutral",
        headline="Cross-asset data sparse — watch only",
        bullets=["Need index/sector/commodity proxies in watchlist"],
        features={},
        prediction_type="watch",
        horizon="1d",
        confidence=0.15,
        data_mode="live",
    )
