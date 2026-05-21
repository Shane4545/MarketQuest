"""MarketQuest API aggregation tests (mock mode)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.api import (  # noqa: E402
    get_agents_debate,
    get_careers_panel,
    get_challenges_active,
    get_cross_asset,
    get_currencies,
    get_dashboard,
    get_entity_graph,
    get_events,
    get_glossary_panel,
    get_learning_report,
    get_lessons_panel,
    get_picks,
    get_regime,
    get_research_registry,
    get_snapshot_latest,
    get_status,
    get_watchlist,
)


def test_get_dashboard_training_structure():
    dash = get_dashboard(ROOT, mock=True, refresh=True)
    assert dash["product"] == "MarketQuest"
    assert dash.get("offline_training_mode") is True
    assert dash["tagline"]
    assert "disclaimer" in dash
    assert "watchlist" in dash
    assert dash["watchlist"].get("quotes")
    assert len(dash["picks"]["picks"]) >= 7
    assert dash["portfolio"].get("cash_usd") is not None
    assert dash["leaderboard"].get("entries")
    assert dash["education"].get("glossary")
    assert dash.get("cross_asset")
    assert dash.get("careers", {}).get("count") == 12
    assert dash.get("active_challenge")
    assert dash.get("benchmark_comparisons") is not None
    assert len(dash["agents_arena"]) >= 7
    assert "entity_graph" in dash
    assert dash.get("regime")
    assert len(dash.get("currencies") or []) >= 7
    assert "freshness" in dash or dash.get("provider_status")


def test_get_status_training():
    st = get_status(ROOT, mock=True)
    assert "market_session" in st or "market_status" in st
    assert "provider_status" in st


def test_get_events_training():
    ev = get_events(ROOT, mock=True, refresh=True)
    assert "events" in ev


def test_get_entity_graph():
    g = get_entity_graph(ROOT)
    assert "people" in g
    assert "relationships" in g


def test_get_agents_debate():
    d = get_agents_debate(ROOT, mock=True, refresh=True)
    assert d.get("agents")
    assert d.get("all_picks")


def test_get_snapshot_latest_training():
    snap = get_snapshot_latest(ROOT, mock=True, refresh=True)
    assert snap.get("timestamp_utc") or snap.get("offline_training_mode") is not None


def test_get_learning_report():
    rep = get_learning_report(ROOT)
    assert "summary" in rep


def test_get_watchlist_training():
    wl = get_watchlist(ROOT, mock=True, refresh=True)
    assert len(wl.get("quotes", [])) >= 1


def test_get_glossary_panel():
    g = get_glossary_panel(ROOT)
    assert len(g.get("terms", [])) >= 15


def test_get_careers_panel():
    c = get_careers_panel(ROOT)
    assert c["count"] == 12


def test_get_challenges_active_training():
    ch = get_challenges_active(ROOT, mock=True)
    assert ch.get("type")
    assert ch.get("prompt")


def test_get_research_registry():
    reg = get_research_registry(ROOT)
    assert reg["count"] >= 10


def test_get_lessons_panel():
    lessons = get_lessons_panel(ROOT, context="filing")
    assert "cards" in lessons


def test_get_picks_training():
    picks = get_picks(ROOT, mock=True, refresh=True)
    assert len(picks["picks"]) >= 7


def test_get_currencies_training():
    cur = get_currencies(ROOT, mock=True, refresh=True)
    assert cur.get("count", 0) >= 7


def test_get_cross_asset_training():
    ca = get_cross_asset(ROOT, mock=True, refresh=True)
    assert ca.get("cross_asset")


def test_get_regime_training():
    reg = get_regime(ROOT, mock=True, refresh=True)
    assert reg.get("regime", {}).get("regime")
