"""Macro agent — FRED alignment."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso


def run_macro_from_snapshot(
    snapshot: dict[str, Any],
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    as_of = as_of or snapshot.get("timestamp_utc", today_iso())[:10]
    macro = snapshot.get("macro_indicators", [])
    symbols = snapshot.get("symbols_checked") or ["SPY"]
    sym = symbols[0]
    bullets = []
    bias = "neutral"
    for m in macro:
        bullets.append(f"{m.get('name')}: {m.get('value')} ({m.get('observation_date')})")
        if m.get("series_id") == "VIXCLS" and float(m.get("value") or 0) > 22:
            bias = "bearish"
        if m.get("series_id") == "FEDFUNDS":
            bias = "neutral"
    if not bullets:
        bullets = ["No macro series in snapshot — check FRED_API_KEY"]
    return make_pick(
        symbol=sym.upper(),
        agent_id="macro",
        as_of=as_of,
        score=0.5,
        predicted_bias=bias,
        headline=f"Macro context pick: {sym}",
        bullets=bullets[:4],
        features={"macro_count": len(macro)},
        data_mode="live",
    )
