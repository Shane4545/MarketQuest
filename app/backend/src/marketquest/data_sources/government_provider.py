"""Official government RSS feeds."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from marketquest.data_sources.base import ProviderResult, utc_now_iso
from marketquest.freshness import age_minutes

DEFAULT_GOV_FEEDS = [
    ("https://www.bankofcanada.ca/content_type/press/feed/", "bank_of_canada"),
    ("https://www.federalreserve.gov/feeds/press_all.xml", "federal_reserve"),
]


def _normalized_record(
    *,
    source: str,
    source_url: str,
    fetched_at: str,
    published_at: str,
    raw_title: str,
    summary: str,
    symbols: list[str] | None = None,
) -> dict[str, Any]:
    pub = published_at or fetched_at
    return {
        "source": source,
        "source_url": source_url,
        "fetched_at_utc": fetched_at,
        "published_at_utc": pub,
        "symbols": symbols or [],
        "entities": [],
        "raw_title": raw_title[:200],
        "summary": summary[:300],
        "confidence": 0.8,
        "freshness_minutes": age_minutes(pub) if pub else 0,
        "license_note": "headline only, no full article stored",
    }


def fetch_government_feeds() -> tuple[list[dict[str, Any]], ProviderResult]:
    fetched = utc_now_iso()
    try:
        import feedparser  # type: ignore
    except ImportError:
        return [], ProviderResult(
            provider="government",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error="feedparser not installed",
        )

    records: list[dict[str, Any]] = []
    for url, source in DEFAULT_GOV_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:10]:
                title = str(getattr(entry, "title", "") or "")[:200]
                if not title:
                    continue
                link = str(getattr(entry, "link", "") or "")
                pub = getattr(entry, "published_parsed", None)
                pub_iso = (
                    datetime(*pub[:6], tzinfo=timezone.utc).isoformat()
                    if pub
                    else fetched
                )
                summary = str(getattr(entry, "summary", title) or title)[:300]
                records.append(
                    _normalized_record(
                        source=f"government:{source}",
                        source_url=link,
                        fetched_at=fetched,
                        published_at=pub_iso,
                        raw_title=title,
                        summary=summary,
                    )
                )
        except Exception:
            continue

    res = ProviderResult(
        provider="government",
        ok=bool(records),
        fetched_at=fetched,
        freshness="DELAYED" if records else "OFFLINE",
    )
    return records, res
