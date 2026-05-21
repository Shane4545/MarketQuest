"""Regime agent — picks aligned with detected market regime."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso
from marketquest.cross_asset.regime_detector import detect_regime


def run_regime_agent(snapshot: dict[str, Any], *, as_of: str | None = None) -> dict[str, Any]:
    as_of = as_of or (snapshot.get("timestamp_utc") or today_iso())[:10]
    regime = snapshot.get("regime") or (snapshot.get("cross_asset") or {}).get("regime")
    if not regime:
        regime = detect_regime(snapshot)

    regime_name = str(regime.get("regime", "event_uncertain"))
    confidence = float(regime.get("confidence") or 0.35)
    evidence = list(regime.get("evidence") or [])

    regime_symbols = {
        "tech_momentum": "NVDA",
        "oil_shock": "XLE",
        "USD_strength": "SPY",
        "risk_off": "XLU",
        "defensive_rotation": "XLP",
        "small_cap_momentum": "IWM",
    }
    symbols = snapshot.get("symbols_checked") or ["SPY"]
    sym = regime_symbols.get(regime_name, str(symbols[0]).upper())
    if sym not in [s.upper() for s in symbols]:
        sym = str(symbols[0]).upper()

    prices = {p["symbol"]: p for p in snapshot.get("prices", []) if p.get("symbol")}
    row = prices.get(sym)
    chg = float(row.get("change_pct") or 0) if row else 0

    return make_pick(
        symbol=sym,
        agent_id="regime_agent",
        as_of=as_of,
        score=confidence,
        predicted_bias="bullish" if chg > 0 else ("bearish" if chg < 0 else "neutral"),
        headline=f"Regime: {regime_name.replace('_', ' ')} — paper watch on {sym}",
        bullets=evidence[:4] or ["Mixed signals across indexes and FX"],
        features={"regime": regime_name, "regime_scores": regime.get("scores")},
        prediction_type="watch",
        horizon="1d",
        confidence=confidence,
        expected_direction="up" if chg > 0.2 else ("down" if chg < -0.2 else "unclear"),
        reasons=[f"Current regime classified as {regime_name}"] + evidence[:2],
        risks=["Regime labels can flip intraday — not investment advice"],
        data_mode="live",
    )
