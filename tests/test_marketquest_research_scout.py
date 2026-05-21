"""Research scout tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.research_scout.ai_tool_registry import query_registry  # noqa: E402
from marketquest.research_scout.weekly_research_report import generate_report  # noqa: E402


def test_registry_loads_seed_projects():
    reg = query_registry(ROOT)
    names = {e["name"] for e in reg["entries"]}
    assert "FinRL" in names
    assert "Finnhub" in names
    assert "FRED" in names
    assert reg["count"] >= 10


def test_generate_research_report(tmp_path):
    repo = tmp_path
    (repo / "app" / "data" / "marketquest" / "research").mkdir(parents=True)
    import shutil

    src = ROOT / "app" / "data" / "marketquest" / "research"
    for f in src.glob("*.json"):
        shutil.copy(f, repo / "app" / "data" / "marketquest" / "research" / f.name)
    report = generate_report(repo)
    assert "MarketQuest Research Scout" in report["report"]
