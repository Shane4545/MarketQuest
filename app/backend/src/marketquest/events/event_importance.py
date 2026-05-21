"""Score event importance for radar display."""

from __future__ import annotations

from typing import Any

SOURCE_TIER = {
    "sec_edgar": 0.9,
    "fred": 0.85,
    "finnhub": 0.75,
    "government": 0.85,
    "company_press": 0.8,
    "x_api": 0.7,
    "rss": 0.6,
    "yahoo": 0.55,
    "marketwatch": 0.55,
}


def score_importance(event: dict[str, Any], watchlist: list[str] | None = None) -> float:
    wl = {s.upper() for s in (watchlist or [])}
    base = 30.0
    source = str(event.get("source") or "").lower()
    for key, tier in SOURCE_TIER.items():
        if key in source:
            base += tier * 20
            break
    else:
        base += 10

    freshness = float(event.get("freshness_minutes") or 0)
    if freshness <= 60:
        base += 20
    elif freshness <= 240:
        base += 10
    elif freshness > 1440:
        base -= 15

    entities = event.get("entities") or []
    base += min(len(entities) * 5, 15)

    tickers = event.get("candidate_tickers") or event.get("symbols") or []
    overlap = sum(1 for t in tickers if str(t).upper() in wl)
    base += overlap * 8

    et = str(event.get("event_type") or "")
    high_impact = {
        "sec_8k",
        "macro_inflation",
        "macro_rates",
        "tariff_trade",
        "government_policy",
        "merger_acquisition",
        "public_figure_statement",
    }
    if et in high_impact:
        base += 15

    return round(min(max(base, 0), 100), 1)
