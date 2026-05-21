"""Event classifier, dedup, and importance tests."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.events.classifier import classify_and_enrich, classify_news, process_event_batch  # noqa: E402
from marketquest.events.event_deduper import dedupe_events  # noqa: E402


def test_classify_tariff_headline():
    assert classify_news("New tariffs on China steel and aluminum imports") == "tariff_trade"


def test_classify_inflation():
    assert classify_news("CPI inflation comes in hot above expectations") == "macro_inflation"


def test_dedupe_events():
    raw = [
        {"title": "Markets rise on earnings", "headline": "Markets rise on earnings"},
        {"title": "Markets rise on earnings!", "headline": "Markets rise on earnings!"},
        {"title": "Oil spikes on OPEC news", "headline": "Oil spikes"},
    ]
    out = dedupe_events(raw)
    assert len(out) == 2


def test_classify_and_enrich_has_impact_fields():
    raw = {
        "source": "rss",
        "source_url": "https://example.com",
        "fetched_at_utc": "2026-05-20T12:00:00+00:00",
        "published_at_utc": "2026-05-20T12:00:00+00:00",
        "raw_title": "Mark Carney unveils Canada infrastructure funding plan",
        "summary": "Infrastructure ports pipelines energy",
        "symbols": [],
    }
    ev = classify_and_enrich(raw, ROOT)
    assert ev.get("event_type")
    assert "importance_score" in ev
    assert ev.get("entities") or ev.get("candidate_tickers")


def test_process_event_batch_sorted():
    raw_events = [
        {
            "source": "government",
            "source_url": "http://x",
            "fetched_at_utc": "2026-05-20T12:00:00+00:00",
            "published_at_utc": "2026-05-20T12:00:00+00:00",
            "raw_title": "Fed holds rates steady",
            "summary": "FOMC decision",
            "symbols": ["SPY"],
        },
        {
            "source": "rss",
            "source_url": "http://y",
            "fetched_at_utc": "2026-05-20T12:00:00+00:00",
            "published_at_utc": "2026-05-20T12:00:00+00:00",
            "raw_title": "Brookfield announces asset sale",
            "summary": "Brookfield infrastructure",
            "symbols": ["BAM"],
        },
    ]
    batch = process_event_batch(raw_events, ROOT, watchlist=["SPY", "BAM"])
    assert len(batch) >= 2
    assert batch[0].get("importance_score") >= batch[-1].get("importance_score")
