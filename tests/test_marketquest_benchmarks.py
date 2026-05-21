"""Benchmark agent tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.agents.benchmarks.registry import BENCHMARK_IDS  # noqa: E402
from marketquest.agents.benchmarks.qqq_baseline import run_qqq_baseline  # noqa: E402
from marketquest.agents.benchmarks.spy_baseline import run_spy_baseline  # noqa: E402
from marketquest.scoring.orchestrator import run_all_agents  # noqa: E402


def test_benchmark_registry_has_ten():
    assert len(BENCHMARK_IDS) == 10


def test_spy_baseline_tracks_spy():
    snap = {"prices": [{"symbol": "SPY", "change_pct": 1.2, "last": 500}]}
    pick = run_spy_baseline(snap)
    assert pick["symbol"] == "SPY"
    assert pick["agent_id"] == "spy_baseline"
    assert pick["player_type"] == "benchmark"


def test_qqq_baseline_tracks_qqq():
    snap = {"prices": [{"symbol": "QQQ", "change_pct": -0.5, "last": 400}]}
    pick = run_qqq_baseline(snap)
    assert pick["symbol"] == "QQQ"
    assert pick["agent_id"] == "qqq_baseline"


def test_training_includes_benchmarks():
    payload = run_all_agents(ROOT, mock=True, refresh=True)
    ids = {p["agent_id"] for p in payload.get("picks", [])}
    assert "spy_baseline" in ids
    assert "qqq_baseline" in ids
    assert "random_baseline" in ids
    assert "ensemble" in ids
