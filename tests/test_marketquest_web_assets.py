"""MarketQuest static asset smoke tests."""

from __future__ import annotations

from pathlib import Path


def test_marketquest_web_assets_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "web" / "marketquest.html").is_file()
    assert (root / "web" / "marketquest.js").is_file()
    assert (root / "web" / "marketquest.css").is_file()
    html = (root / "web" / "marketquest.html").read_text(encoding="utf-8")
    assert "event-radar" in html
    assert "agent-debate" in html
    assert "entity-graph-content" in html
    assert "panel-cross-asset" in html
    assert "panel-benchmarks" in html
    assert "panel-career" in html
    assert "panel-scout" in html
    assert "Future Builder" in html


def test_marketquest_data_seeds_exist():
    root = Path(__file__).resolve().parents[1]
    assert (root / "app" / "data" / "marketquest" / "entity_seed.json").is_file()
    assert (root / "app" / "data" / "marketquest" / "watchlists" / "default.json").is_file()


def test_marketquest_fixtures_exist():
    root = Path(__file__).resolve().parents[1]
    fixtures = root / "app" / "data" / "marketquest" / "fixtures"
    assert (fixtures / "watchlist.json").is_file()
    assert (fixtures / "agent_picks.json").is_file()
    assert (fixtures / "leaderboard.json").is_file()
    assert (fixtures / "portfolio_default.json").is_file()
