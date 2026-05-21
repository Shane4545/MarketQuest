"""MarketQuest agent orchestrator tests (mock mode)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.agents.skeptic_agent import run_skeptic  # noqa: E402
from marketquest.scoring.orchestrator import run_all_agents  # noqa: E402

REQUIRED_PICK_KEYS = {
    "symbol",
    "agent_id",
    "as_of",
    "score",
    "predicted_bias",
    "explanation",
    "features",
    "data_mode",
    "prediction_type",
    "horizon",
    "confidence",
}


def test_run_all_agents_training_returns_seven_picks():
    payload = run_all_agents(ROOT, mock=True, refresh=True)
    picks = payload.get("picks", [])
    assert len(picks) >= 7
    agent_ids = {p["agent_id"] for p in picks}
    assert "random_baseline" in agent_ids
    assert "momentum" in agent_ids
    assert "skeptic" in agent_ids
    assert "public_figure" in agent_ids
    assert "entity_graph" in agent_ids
    assert "fx_agent" in agent_ids
    assert "cross_asset_agent" in agent_ids
    assert "regime_agent" in agent_ids
    assert "correlation_skeptic" in agent_ids
    for p in picks:
        assert REQUIRED_PICK_KEYS.issubset(p.keys())
        assert "headline" in (p.get("explanation") or {})


def test_skeptic_flags_stale_data():
    pick = {"symbol": "NVDA", "agent_id": "momentum"}
    sk = run_skeptic([pick], {"scoring_data_eligible": False, "prices": [], "news_events": []})
    assert sk["agent_id"] == "skeptic"
    assert sk.get("risks")
