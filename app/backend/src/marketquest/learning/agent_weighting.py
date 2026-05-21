"""Simple rolling weights for ensemble by event type."""

from __future__ import annotations

from typing import Any

from marketquest.learning.performance_tracker import load_scores


def agent_weights(repo) -> dict[str, float]:
    data = load_scores(repo)
    agents = data.get("agents") or {}
    weights: dict[str, float] = {}
    for aid, rec in agents.items():
        weights[aid] = float(rec.get("hit_rate") or 0.5)
    if not weights:
        return {"momentum": 1.0, "news": 1.0, "ensemble": 1.0}
    return weights


def weight_for_event_type(repo, event_type: str) -> float:
    data = load_scores(repo)
    et = (data.get("event_types") or {}).get(event_type)
    if not et or not et.get("total"):
        return 0.5
    return round(et.get("wins", 0) / et["total"], 4)
