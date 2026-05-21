"""Reality score explainability."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.scoring.reality_score import compute_reality_score  # noqa: E402


def test_reality_score_has_reasons():
    r = compute_reality_score(
        "NVDA",
        price_row={"symbol": "NVDA", "change_pct": 5, "rvol": 4, "gap_pct": 6},
        news_for_sym=[{"category": "earnings", "headline": "earnings beat"}],
        filings_for_sym=[],
        macro=[],
        agent_picks=[{"symbol": "NVDA", "agent_id": "momentum"}],
    )
    assert 0 <= r["reality_score"] <= 100
    assert len(r["reasons"]) >= 1
    assert "delta" in r["reasons"][0]
