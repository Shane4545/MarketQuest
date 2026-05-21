"""Classify current market regime from indexes, FX, commodities, sectors."""

from __future__ import annotations

from typing import Any


def detect_regime(snapshot: dict[str, Any]) -> dict[str, Any]:
    prices = {p["symbol"]: p for p in snapshot.get("prices", []) if p.get("symbol")}
    fx = {f["pair"]: f for f in (snapshot.get("cross_asset") or {}).get("forex") or [] if f.get("pair")}

    def chg(sym: str) -> float | None:
        row = prices.get(sym.upper())
        return float(row.get("change_pct") or 0) if row else None

    def fx_chg(pair: str) -> float | None:
        row = fx.get(pair)
        if not row:
            return None
        return float(row.get("change_pct_1d") or row.get("change_pct") or 0)

    evidence: list[str] = []
    scores: dict[str, float] = {}

    spy = chg("SPY")
    qqq = chg("QQQ")
    iwm = chg("IWM")
    xle = chg("XLE")
    xlk = chg("XLK")
    xlf = chg("XLF")
    gld = chg("GLD")
    usd_cad = fx_chg("USD/CAD")
    usd_jpy = fx_chg("USD/JPY")

    if spy is not None and qqq is not None:
        if spy > 0.3 and qqq > spy:
            scores["tech_momentum"] = scores.get("tech_momentum", 0) + 0.35
            evidence.append("QQQ outperforming SPY")
        if spy > 0.3 and iwm is not None and iwm > spy:
            scores["small_cap_momentum"] = scores.get("small_cap_momentum", 0) + 0.3
            evidence.append("IWM outperforming SPY")

    if usd_cad is not None and usd_cad > 0.2:
        scores["USD_strength"] = scores.get("USD_strength", 0) + 0.25
        evidence.append(f"USD/CAD up {usd_cad:.2f}%")
    if usd_jpy is not None and usd_jpy > 0.2:
        scores["risk_on"] = scores.get("risk_on", 0) + 0.2
        evidence.append(f"USD/JPY up {usd_jpy:.2f}%")

    if gld is not None and spy is not None and gld > 0.3 and spy < 0:
        scores["risk_off"] = scores.get("risk_off", 0) + 0.35
        evidence.append("Gold up while equities weak")

    if xle is not None and xle > 1.0:
        scores["oil_shock"] = scores.get("oil_shock", 0) + 0.3
        evidence.append(f"Energy sector (XLE) up {xle:.2f}%")

    if xlf is not None and xlk is not None and xlf > xlk and spy is not None and spy < 0:
        scores["defensive_rotation"] = scores.get("defensive_rotation", 0) + 0.25
        evidence.append("Financials leading tech on down day")

    macro = snapshot.get("macro_indicators") or []
    vix = next((m for m in macro if m.get("series_id") == "VIXCLS"), None)
    if vix and float(vix.get("value") or 0) > 22:
        scores["risk_off"] = scores.get("risk_off", 0) + 0.3
        evidence.append(f"VIX elevated at {vix.get('value')}")

    if not scores:
        regime = "event_uncertain"
        confidence = 0.35
        if not evidence:
            evidence.append("Mixed or flat moves across indexes and FX")
    else:
        regime = max(scores, key=scores.get)
        confidence = min(0.35 + scores[regime], 0.85)

    sensitive = _sensitive_groups(regime)
    return {
        "regime": regime,
        "confidence": round(confidence, 3),
        "evidence": evidence[:6],
        "likely_sensitive_groups": sensitive,
        "scores": scores,
    }


def _sensitive_groups(regime: str) -> list[str]:
    mapping = {
        "USD_strength": ["multinationals", "commodity producers", "importers/exporters"],
        "USD_weakness": ["commodities", "EM-exposed names", "multinationals"],
        "risk_on": ["high beta tech", "cyclicals", "small caps"],
        "risk_off": ["utilities", "staples", "gold proxies", "bonds"],
        "oil_shock": ["energy producers", "airlines", "transports", "inflation-sensitive"],
        "tech_momentum": ["AI/semis", "software", "high beta growth"],
        "defensive_rotation": ["utilities", "staples", "healthcare"],
        "event_uncertain": ["watchlist broad", "event-driven names"],
    }
    return mapping.get(regime, ["general watchlist"])
