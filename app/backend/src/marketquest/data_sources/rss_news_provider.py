"""Public RSS headlines — headline/url/source only."""

from __future__ import annotations

from datetime import datetime, timezone

from marketquest.data_sources.base import NewsEvent, ProviderResult, utc_now_iso

DEFAULT_FEEDS = [
    ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US", "yahoo"),
    ("https://www.marketwatch.com/rss/topstories", "marketwatch"),
]


def fetch_headlines(symbols: list[str] | None = None) -> ProviderResult:
    fetched = utc_now_iso()
    symbols = symbols or []
    try:
        import feedparser  # type: ignore
    except ImportError:
        return ProviderResult(
            provider="rss",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error="feedparser not installed",
        )

    news: list[NewsEvent] = []
    for url, source in DEFAULT_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:15]:
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
                matched = [s for s in symbols if s.upper() in title.upper()]
                news.append(
                    NewsEvent(
                        headline=title,
                        source=source,
                        url=link,
                        published_at=pub_iso,
                        summary=title[:120],
                        symbols=matched or [],
                        category="headline",
                    )
                )
        except Exception:
            continue

    return ProviderResult(
        provider="rss",
        ok=bool(news),
        fetched_at=fetched,
        freshness="DELAYED" if news else "OFFLINE",
        news=news,
    )
