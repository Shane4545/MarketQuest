"""Company investor relations / press release RSS feeds."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from marketquest.data_sources.base import ProviderResult, utc_now_iso
from marketquest.freshness import age_minutes


def _normalized_record(
    *,
    source: str,
    source_url: str,
    fetched_at: str,
    published_at: str,
    raw_title: str,
    summary: str,
    symbols: list[str],
) -> dict[str, Any]:
    pub = published_at or fetched_at
    return {
        "source": source,
        "source_url": source_url,
        "fetched_at_utc": fetched_at,
        "published_at_utc": pub,
        "symbols": symbols,
        "entities": [],
        "raw_title": raw_title[:200],
        "summary": summary[:300],
        "confidence": 0.75,
        "freshness_minutes": age_minutes(pub) if pub else 0,
        "license_note": "headline only, no full article stored",
    }


def fetch_company_press(press_rss: list[dict[str, str]] | None = None) -> tuple[list[dict[str, Any]], ProviderResult]:
    fetched = utc_now_iso()
    feeds = press_rss or []
    if not feeds:
        return [], ProviderResult(
            provider="company_press",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error="no press RSS configured in watchlist",
        )

    try:
        import feedparser  # type: ignore
    except ImportError:
        return [], ProviderResult(
            provider="company_press",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error="feedparser not installed",
        )

    records: list[dict[str, Any]] = []
    for item in feeds:
        url = str(item.get("url") or "")
        sym = str(item.get("symbol") or "").upper()
        label = str(item.get("label") or sym or "company_press")
        if not url:
            continue
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:8]:
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
                records.append(
                    _normalized_record(
                        source=f"company_press:{label}",
                        source_url=link,
                        fetched_at=fetched,
                        published_at=pub_iso,
                        raw_title=title,
                        summary=title[:120],
                        symbols=[sym] if sym else [],
                    )
                )
        except Exception:
            continue

    res = ProviderResult(
        provider="company_press",
        ok=bool(records),
        fetched_at=fetched,
        freshness="DELAYED" if records else "OFFLINE",
    )
    return records, res
