"""Entity graph resolver and Carney/Brookfield chain tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.entity_graph.graph_store import GraphStore  # noqa: E402
from marketquest.entity_graph.resolver import resolve_entities  # noqa: E402
from marketquest.entity_graph.ticker_mapper import map_text_to_tickers  # noqa: E402


def test_carney_brookfield_ticker_mapping():
    text = "Mark Carney discusses infrastructure and Brookfield renewable assets"
    tickers = map_text_to_tickers(text, ROOT)
    assert "BAM" in tickers or "BN" in tickers


def test_tariff_theme_tickers():
    text = "New tariffs on imports may affect steel and retail"
    resolved = resolve_entities(text, "tariff_trade", ROOT)
    assert resolved.get("candidate_tickers")
    assert resolved.get("why_this_may_matter")


def test_graph_store_merge():
    store = GraphStore(ROOT)
    events = [
        {
            "event_id": "test1",
            "title": "Carney infrastructure plan",
            "entities": ["Mark Carney", "Canada"],
            "candidate_tickers": ["BAM", "ENB"],
            "event_type": "government_policy",
        }
    ]
    updates = store.merge_from_events(events)
    assert len(updates) >= 1
    exported = store.export_for_api()
    assert exported.get("recent_chains")
