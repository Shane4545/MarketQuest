"""Benchmark player registry — 10 required Wall Street-style baselines."""

from __future__ import annotations

from typing import Any

BENCHMARK_REGISTRY: list[dict[str, Any]] = [
    {"id": "random_baseline", "display_name": "Random Baseline", "mandatory": True, "player_type": "benchmark"},
    {"id": "spy_baseline", "display_name": "SPY Baseline", "mandatory": True, "player_type": "benchmark"},
    {"id": "qqq_baseline", "display_name": "QQQ Baseline", "mandatory": True, "player_type": "benchmark"},
    {"id": "equal_weight_baseline", "display_name": "Equal-Weight Watchlist", "mandatory": True, "player_type": "benchmark"},
    {"id": "momentum_baseline", "display_name": "Simple Momentum Baseline", "mandatory": True, "player_type": "benchmark"},
    {"id": "news_only", "display_name": "News-Only Agent", "mandatory": True, "player_type": "agent"},
    {"id": "macro", "display_name": "Macro Agent", "mandatory": True, "player_type": "agent"},
    {"id": "filing_event", "display_name": "Filing Agent", "mandatory": True, "player_type": "agent"},
    {"id": "entity_graph", "display_name": "Entity Graph Agent", "mandatory": True, "player_type": "agent"},
    {"id": "ensemble", "display_name": "Ensemble Agent", "mandatory": True, "player_type": "agent"},
]

BENCHMARK_IDS = [b["id"] for b in BENCHMARK_REGISTRY]

COMPARISON_PAIRS = [
    ("ensemble", "random_baseline"),
    ("ensemble", "spy_baseline"),
    ("ensemble", "qqq_baseline"),
    ("ensemble", "momentum_baseline"),
    ("news_only", "random_baseline"),
    ("macro", "spy_baseline"),
]


def get_benchmark(id_: str) -> dict[str, Any] | None:
    return next((b for b in BENCHMARK_REGISTRY if b["id"] == id_), None)


def display_name(id_: str) -> str:
    b = get_benchmark(id_)
    return b["display_name"] if b else id_
