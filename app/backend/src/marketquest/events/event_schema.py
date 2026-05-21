"""Normalized event record schema."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class EventRecord:
    event_id: str
    title: str
    summary: str
    event_type: str
    entities: list[str] = field(default_factory=list)
    candidate_tickers: list[str] = field(default_factory=list)
    expected_time_horizons: list[str] = field(default_factory=lambda: ["15m", "1h", "1d", "1w"])
    possible_positive_impacts: list[str] = field(default_factory=list)
    possible_negative_impacts: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    source_links: list[str] = field(default_factory=list)
    importance_score: float = 0.0
    freshness_minutes: float = 0.0
    source: str = ""
    source_url: str = ""
    fetched_at_utc: str = ""
    published_at_utc: str = ""
    symbols: list[str] = field(default_factory=list)
    confidence: float = 0.5
    license_note: str = "headline only, no full article stored"
    why_this_may_matter: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_event_id(title: str, source: str, published_at: str) -> str:
    raw = f"{title}|{source}|{published_at}".lower().strip()
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def raw_to_event_dict(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert provider raw record to partial event dict."""
    title = str(raw.get("raw_title") or raw.get("headline") or raw.get("title") or "")[:200]
    source = str(raw.get("source") or "")
    pub = str(raw.get("published_at_utc") or raw.get("published_at") or "")
    return {
        "event_id": raw.get("event_id") or make_event_id(title, source, pub),
        "title": title,
        "summary": str(raw.get("summary") or title)[:300],
        "source": source,
        "source_url": str(raw.get("source_url") or raw.get("url") or ""),
        "fetched_at_utc": str(raw.get("fetched_at_utc") or raw.get("fetched_at") or ""),
        "published_at_utc": pub,
        "symbols": [str(s).upper() for s in (raw.get("symbols") or [])],
        "entities": list(raw.get("entities") or []),
        "confidence": float(raw.get("confidence") or 0.5),
        "freshness_minutes": float(raw.get("freshness_minutes") or 0),
        "license_note": str(raw.get("license_note") or "headline only, no full article stored"),
        "source_links": [str(raw.get("source_url") or raw.get("url") or "")],
    }
