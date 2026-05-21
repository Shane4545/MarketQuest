"""Weekly competition scoring helpers."""

from __future__ import annotations

from typing import Any


def score_entry(
    *,
    weekly_return_pct: float = 0.0,
    max_drawdown_pct: float = 0.0,
    hit_rate: float = 0.0,
    explanation_score: float = 0.0,
    learning_points: float = 0.0,
    beat_random: bool = False,
) -> float:
    """Composite for leaderboard ordering."""
    risk_adj = weekly_return_pct - 0.5 * abs(max_drawdown_pct)
    bonus = 0.1 * hit_rate + 0.05 * explanation_score + 0.02 * learning_points
    if beat_random:
        bonus += 0.5
    return risk_adj + bonus


def score_learning_attempt(
    *,
    explanation_quality: float,
    uncertainty_identified: bool,
    concept_mastery: float,
    beat_random: bool = False,
) -> dict[str, Any]:
    points = explanation_quality * 2 + concept_mastery
    if uncertainty_identified:
        points += 1.0
    if beat_random:
        points += 0.5
    return {
        "learning_points": round(points, 2),
        "breakdown": {
            "explanation_quality": explanation_quality,
            "uncertainty_identified": uncertainty_identified,
            "concept_mastery": concept_mastery,
            "beat_random_bonus": beat_random,
        },
    }
