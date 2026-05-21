"""FX agent — currency moves and cross-border hypotheses."""

from __future__ import annotations

from typing import Any

from marketquest.agents._pick import make_pick
from marketquest.config import today_iso
from marketquest.cross_asset.currency_impact_rules import apply_currency_rules


def run_fx_agent(snapshot: dict[str, Any], *, as_of: str | None = None) -> dict[str, Any]:
    as_of = as_of or (snapshot.get("timestamp_utc") or today_iso())[:10]
    forex = (snapshot.get("cross_asset") or {}).get("forex") or snapshot.get("currencies") or []
    symbols = snapshot.get("symbols_checked") or ["SPY"]

    if not forex:
        return make_pick(
            symbol=str(symbols[0]).upper(),
            agent_id="fx_agent",
            as_of=as_of,
            score=0.1,
            predicted_bias="neutral",
            headline="FX data offline — watch only",
            bullets=["Configure FINNHUB_API_KEY or use yfinance fallback"],
            features={},
            prediction_type="watch",
            horizon="1h",
            confidence=0.1,
            reasons=["No FX quotes in snapshot"],
            risks=["Currency shocks can move multinationals quickly"],
        )

    active = [f for f in forex if f.get("last") is not None]
    if not active:
        active = forex
    best = max(active, key=lambda f: abs(float(f.get("change_pct_1d") or f.get("change_pct") or 0)))
    pair = str(best.get("pair", "USD/CAD"))
    chg = float(best.get("change_pct_1d") or best.get("change_pct") or 0)
    rules = apply_currency_rules(pair, chg)

    # Map pair to watchlist symbol
    sym_map = {"USD/CAD": "BAM", "USD/JPY": "SPY", "EUR/USD": "MSFT", "USD/CNH": "AAPL"}
    sym = sym_map.get(pair, str(symbols[0]).upper())
    for s in symbols:
        if s.upper() in ("BAM", "BN", "ENB") and pair == "USD/CAD":
            sym = s.upper()
            break

    return make_pick(
        symbol=sym,
        agent_id="fx_agent",
        as_of=as_of,
        score=min(abs(chg) / 5, 0.75),
        predicted_bias="bullish" if chg > 0.1 else ("bearish" if chg < -0.1 else "neutral"),
        headline=f"FX watch: {pair} {chg:+.2f}% — educational hypothesis",
        bullets=[
            rules.get("positive_hypothesis", "")[:100],
            rules.get("negative_hypothesis", "")[:100],
            f"Status: {best.get('status', 'OFFLINE')}",
        ],
        features={"pair": pair, "change_pct": chg, "provider": best.get("provider")},
        prediction_type="watch",
        horizon="1h",
        confidence=min(abs(chg) / 8 + 0.2, 0.7),
        expected_direction="unclear",
        reasons=[
            f"{pair} moved {chg:+.2f}%",
            rules.get("positive_hypothesis", "")[:80],
        ],
        risks=[rules.get("uncertainty", "Correlation is not causation")],
        data_mode="live",
    )
