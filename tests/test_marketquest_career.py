"""Career mode tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.career.careers import get_careers, load_careers  # noqa: E402


def test_twelve_career_cards():
    careers = load_careers(ROOT)
    assert len(careers) == 12


def test_career_card_fields():
    panel = get_careers(ROOT)
    assert panel["title"] == "Future Builder"
    c = panel["careers"][0]
    assert c.get("title")
    assert c.get("skills")
    assert c.get("marketquest_teaches")
    assert c.get("beginner_project")
    assert c.get("school_subjects")
