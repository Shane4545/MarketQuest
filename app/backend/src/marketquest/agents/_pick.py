"""Shared pick record builder."""

from __future__ import annotations

from typing import Any


def _bias_to_direction(predicted_bias: str) -> str:
    b = predicted_bias.lower()
    if b in ("bullish", "up", "long"):
        return "up"
    if b in ("bearish", "down", "short"):
        return "down"
    return "unclear"


def make_pick(
    *,
    symbol: str,
    agent_id: str,
    as_of: str,
    score: float,
    predicted_bias: str,
    headline: str,
    bullets: list[str],
    features: dict[str, Any],
    news: list[dict[str, Any]] | None = None,
    data_mode: str = "live",
    runners_up: list[str] | None = None,
    prediction_type: str | None = None,
    horizon: str = "1d",
    confidence: float | None = None,
    expected_direction: str | None = None,
    reasons: list[str] | None = None,
    risks: list[str] | None = None,
    source_event_ids: list[str] | None = None,
    player_type: str | None = None,
) -> dict[str, Any]:
    conf = confidence if confidence is not None else min(max(abs(float(score)), 0.1), 1.0)
    direction = expected_direction or _bias_to_direction(predicted_bias)
    ptype = prediction_type or (
        "avoid" if agent_id == "skeptic" and direction == "down" else "paper_long"
    )
    if agent_id == "skeptic" and ptype == "paper_long":
        ptype = "watch"
    reason_list = reasons if reasons is not None else bullets
    return {
        "symbol": symbol.upper(),
        "agent_id": agent_id,
        "as_of": as_of,
        "score": round(float(score), 4),
        "predicted_bias": predicted_bias,
        "prediction_type": ptype,
        "horizon": horizon,
        "confidence": round(float(conf), 4),
        "expected_direction": direction,
        "reasons": reason_list,
        "risks": risks or [],
        "source_event_ids": source_event_ids or [],
        "explanation": {"headline": headline, "bullets": bullets},
        "news": news or [],
        "features": features,
        "data_mode": data_mode,
        "runners_up": runners_up or [],
        "player_type": player_type or ("benchmark" if "baseline" in agent_id else "agent"),
    }


def ensure_pick_schema(p: dict[str, Any]) -> dict[str, Any]:
    """Upgrade legacy fixture picks to full schema."""
    if p.get("prediction_type") and p.get("confidence") is not None:
        return p
    ex = p.get("explanation") or {}
    return make_pick(
        symbol=str(p.get("symbol", "SPY")),
        agent_id=str(p.get("agent_id", "unknown")),
        as_of=str(p.get("as_of", "")),
        score=float(p.get("score") or 0),
        predicted_bias=str(p.get("predicted_bias") or "neutral"),
        headline=str(ex.get("headline") or ""),
        bullets=list(ex.get("bullets") or []),
        features=dict(p.get("features") or {}),
        news=list(p.get("news") or []),
        data_mode=str(p.get("data_mode") or "mock"),
        runners_up=list(p.get("runners_up") or []),
    )
