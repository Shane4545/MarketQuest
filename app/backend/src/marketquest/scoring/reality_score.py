"""Reality Score 0-100 with explainable reasons."""

from __future__ import annotations

from typing import Any


def compute_reality_score(
    symbol: str,
    *,
    price_row: dict[str, Any] | None,
    news_for_sym: list[dict],
    filings_for_sym: list[dict],
    macro: list[dict],
    agent_picks: list[dict],
) -> dict[str, Any]:
    reasons: list[dict[str, Any]] = []
    score = 50.0

    pr = price_row or {}
    gap = float(pr.get("gap_pct") or abs(float(pr.get("change_pct") or 0)))
    rvol = float(pr.get("rvol") or 1.0)
    chg = float(pr.get("change_pct") or 0)

    if rvol >= 2:
        d = min(18, rvol * 4)
        score += d
        reasons.append({"delta": round(d, 1), "label": f"relative volume {rvol:.1f}x normal"})
    if gap >= 3:
        d = min(14, gap * 2)
        score += d
        reasons.append({"delta": round(d, 1), "label": f"gap/move {gap:.1f}%"})
    if chg > 0:
        reasons.append({"delta": 5, "label": "positive intraday trend"})
        score += 5
    elif chg < -2:
        reasons.append({"delta": -8, "label": "negative price momentum"})
        score -= 8

    fresh_news = [n for n in news_for_sym if n.get("category") in ("earnings", "headline")]
    if fresh_news:
        d = 14
        score += d
        reasons.append({"delta": d, "label": f"recent news ({len(fresh_news)} items)"})

    if filings_for_sym:
        d = 12
        score += d
        reasons.append({"delta": d, "label": "SEC filing activity"})

    if macro and macro[0].get("series_id") == "VIXCLS":
        vix = float(macro[0].get("value") or 20)
        if vix > 25:
            reasons.append({"delta": -10, "label": "high volatility risk (VIX elevated)"})
            score -= 10

    agreeing = sum(1 for p in agent_picks if p.get("symbol") == symbol.upper())
    if agreeing >= 2:
        d = 10
        score += d
        reasons.append({"delta": d, "label": f"model agreement ({agreeing} agents)"})

    prov = (pr.get("provenance") or {})
    if prov.get("freshness") == "STALE":
        reasons.append({"delta": -20, "label": "stale price data — score penalized"})
        score -= 20
    if prov.get("fallback"):
        reasons.append({"delta": -8, "label": "fallback/delayed data source"})
        score -= 8

    score = max(0.0, min(100.0, score))
    reasons.sort(key=lambda r: -abs(r["delta"]))
    return {
        "symbol": symbol.upper(),
        "reality_score": round(score, 1),
        "reasons": reasons[:5],
    }


def score_universe_from_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    prices = {p["symbol"]: p for p in snapshot.get("prices", [])}
    news = snapshot.get("news_events", [])
    filings = snapshot.get("sec_filings", [])
    macro = snapshot.get("macro_indicators", [])
    picks = snapshot.get("ai_agent_picks", [])
    out = []
    for sym in snapshot.get("symbols_checked", []):
        n_sym = [n for n in news if sym in (n.get("symbols") or []) or sym in str(n.get("headline", ""))]
        f_sym = [f for f in filings if f.get("symbol") == sym]
        out.append(
            compute_reality_score(
                sym,
                price_row=prices.get(sym),
                news_for_sym=n_sym,
                filings_for_sym=f_sym,
                macro=macro,
                agent_picks=picks,
            )
        )
    out.sort(key=lambda x: -x["reality_score"])
    return out
