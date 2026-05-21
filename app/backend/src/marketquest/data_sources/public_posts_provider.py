"""X/Twitter public posts via official API only when bearer token configured."""

from __future__ import annotations

import os
from typing import Any

import requests

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
    entities: list[str],
    confidence: float = 0.6,
) -> dict[str, Any]:
    pub = published_at or fetched_at
    return {
        "source": source,
        "source_url": source_url,
        "fetched_at_utc": fetched_at,
        "published_at_utc": pub,
        "symbols": symbols,
        "entities": entities,
        "raw_title": raw_title[:200],
        "summary": summary[:300],
        "confidence": confidence,
        "freshness_minutes": age_minutes(pub) if pub else 0,
        "license_note": "X API metadata only; headline/summary generated; not full post stored",
    }


def fetch_public_posts(
    query: str = "tariffs OR infrastructure OR earnings lang:en -is:retweet",
    *,
    max_results: int = 10,
) -> ProviderResult:
    fetched = utc_now_iso()
    token = os.environ.get("X_BEARER_TOKEN", "").strip()
    if not token:
        return ProviderResult(
            provider="x_api",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error="X_BEARER_TOKEN not configured — official API required",
        )

    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "query": query,
        "max_results": min(max_results, 100),
        "tweet.fields": "created_at,author_id",
    }
    records: list[dict[str, Any]] = []
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        for tw in data.get("data") or []:
            text = str(tw.get("text", ""))[:200]
            tid = tw.get("id", "")
            created = str(tw.get("created_at", fetched))
            records.append(
                _normalized_record(
                    source="x_api",
                    source_url=f"https://twitter.com/i/web/status/{tid}" if tid else "",
                    fetched_at=fetched,
                    published_at=created,
                    raw_title=text,
                    summary=text[:120],
                    symbols=[],
                    entities=[],
                    confidence=0.65,
                )
            )
        return ProviderResult(
            provider="x_api",
            ok=bool(records),
            fetched_at=fetched,
            freshness="LIVE" if records else "OFFLINE",
            news=[],  # stored as raw dicts via collector
        )
    except Exception as exc:
        return ProviderResult(
            provider="x_api",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error=str(exc)[:200],
        )


def fetch_public_posts_records(**kwargs: Any) -> tuple[list[dict[str, Any]], ProviderResult]:
    res = fetch_public_posts(**kwargs)
    # Re-fetch if we got OK but empty news - actually records built inside
    token = os.environ.get("X_BEARER_TOKEN", "").strip()
    if not token:
        return [], res
    fetched = utc_now_iso()
    records: list[dict[str, Any]] = []
    try:
        url = "https://api.twitter.com/2/tweets/search/recent"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "query": kwargs.get("query", "tariffs OR infrastructure lang:en -is:retweet"),
            "max_results": min(kwargs.get("max_results", 10), 100),
            "tweet.fields": "created_at",
        }
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()
        for tw in resp.json().get("data") or []:
            text = str(tw.get("text", ""))[:200]
            tid = tw.get("id", "")
            created = str(tw.get("created_at", fetched))
            records.append(
                _normalized_record(
                    source="x_api",
                    source_url=f"https://twitter.com/i/web/status/{tid}" if tid else "",
                    fetched_at=fetched,
                    published_at=created,
                    raw_title=text,
                    summary=text[:120],
                    symbols=[],
                    entities=[],
                )
            )
        res.ok = bool(records)
        res.freshness = "LIVE" if records else "OFFLINE"
    except Exception as exc:
        res.error = str(exc)[:200]
    return records, res
