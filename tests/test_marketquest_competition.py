"""Competition rules — $100k long-only."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.config import load_config  # noqa: E402
from marketquest.game.competition import score_entry, score_learning_attempt  # noqa: E402
from marketquest.game.leaderboard import build_benchmark_comparisons, build_leaderboard_from_picks  # noqa: E402
from marketquest.game.portfolio import paper_trade  # noqa: E402


def test_starting_cash_100k():
    cfg = load_config(ROOT)
    assert cfg["starting_cash_usd"] == 100_000
    assert cfg["long_only"] is True


def test_benchmark_comparisons():
    entries = [
        {"id": "ensemble", "rank": 1, "score_pct": 5.0},
        {"id": "spy_baseline", "rank": 3, "score_pct": 3.0},
        {"id": "random_baseline", "rank": 2, "score_pct": 4.0},
    ]
    comp = build_benchmark_comparisons(entries, "2026-W21")
    assert "pairs" in comp
    assert comp.get("ai_disclosure") is None or isinstance(comp["ai_disclosure"], str)


def test_score_learning_attempt():
    r = score_learning_attempt(explanation_quality=3, uncertainty_identified=True, concept_mastery=2)
    assert r["learning_points"] > 0


def test_score_entry_beat_random_bonus():
    base = score_entry(weekly_return_pct=2.0)
    boosted = score_entry(weekly_return_pct=2.0, beat_random=True)
    assert boosted > base


def test_long_only_rejects_sell_without_position(tmp_path):
    repo = tmp_path
    (repo / "app" / "data" / "marketquest" / "fixtures").mkdir(parents=True)
    (repo / "app" / "data" / "marketquest" / "fixtures" / "watchlist.json").write_text(
        json.dumps({"quotes": [{"symbol": "SPY", "last": 500, "change_pct": 0, "volume": 0}]}),
        encoding="utf-8",
    )
    (repo / "config").mkdir(exist_ok=True)
    (repo / "config" / "marketquest.yaml").write_text("starting_cash_usd: 100000\nlong_only: true\n", encoding="utf-8")
    r = paper_trade(repo, {"symbol": "SPY", "side": "sell", "qty": 1, "user_id": "default"}, mock=True)
    assert "error" in r
