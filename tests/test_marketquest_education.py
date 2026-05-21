"""Education layer tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.education.explanation_scoring import score_explanation  # noqa: E402
from marketquest.education.glossary import get_glossary  # noqa: E402
from marketquest.education.lesson_cards import get_lessons  # noqa: E402
from marketquest.education.quiz_engine import CHALLENGE_TYPES, build_active_challenge, submit_challenge  # noqa: E402


def test_glossary_json_loads():
    g = get_glossary(ROOT)
    terms = g.get("terms", [])
    assert len(terms) >= 15
    terms_lower = {t["term"].lower() for t in terms}
    assert "stock" in terms_lower
    assert "ticker" in terms_lower


def test_lesson_cards_load():
    lessons = get_lessons(repo=ROOT)
    assert lessons["count"] >= 4


def test_five_challenge_types():
    assert len(CHALLENGE_TYPES) == 5


def test_build_active_challenge():
    snap = {"timestamp_utc": "2026-05-20T12:00:00+00:00", "news_events": [{"title": "Oil rises"}], "cross_asset": {}}
    ch = build_active_challenge(snap)
    assert ch["type"] in CHALLENGE_TYPES
    assert ch.get("prompt")


def test_explanation_scoring_uncertainty_bonus():
    r = score_explanation("Tech might rise but oil could hurt airlines — uncertain.")
    assert r["uncertainty_bonus"] is True
    assert r["score"] > 0


def test_submit_challenge_persists_points(tmp_path):
    repo = tmp_path
    (repo / "app" / "data" / "marketquest" / "learning").mkdir(parents=True)
    result = submit_challenge(repo, challenge_id="test", answer="Energy sector might be affected by oil.")
    assert result["ok"] is True
    assert result["total_learning_points"] > 0
