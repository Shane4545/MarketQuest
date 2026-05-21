"""Finnhub quotes and company news."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from marketquest.data_sources.base import NewsEvent, ProviderResult, QuoteRecord, utc_now_iso
from marketquest.data_sources.market_hours import is_regular_session_open
from marketquest.freshness import attach_provenance


def _api_key() -> str | None:
    return os.environ.get("FINNHUB_API_KEY") or None


def fetch_quotes(symbols: list[str]) -> ProviderResult:
    fetched = utc_now_iso()
    key = _api_key()
    if not key:
        return ProviderResult(
            provider="finnhub",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error="FINNHUB_API_KEY not set",
        )
    try:
        import finnhub  # type: ignore

        client = finnhub.Client(api_key=key)
    except ImportError:
        return ProviderResult(
            provider="finnhub",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error="finnhub-python not installed",
        )

    session_open = is_regular_session_open()
    quotes: list[QuoteRecord] = []
    for sym in symbols:
        try:
            q = client.quote(sym)
            c = float(q.get("c") or 0)
            pc = float(q.get("pc") or 0)
            chg = ((c - pc) / pc * 100) if pc else 0.0
            ts = q.get("t")
            mkt = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat() if ts else fetched
            quotes.append(
                QuoteRecord(
                    symbol=sym.upper(),
                    last=round(c, 4),
                    change_pct=round(chg, 4),
                    volume=0,
                )
            )
        except Exception:
            continue

    fresh = attach_provenance(
        provider="finnhub",
        fetched_at=fetched,
        market_timestamp=fetched,
        market_session_open=session_open,
        provider_ok=bool(quotes),
        is_fallback=False,
    )["freshness"]

    return ProviderResult(
        provider="finnhub",
        ok=bool(quotes),
        fetched_at=fetched,
        freshness=fresh,
        fallback=False,
        quotes=quotes,
    )


def fetch_company_news(symbols: list[str], *, days: int = 2) -> list[NewsEvent]:
    key = _api_key()
    if not key:
        return []
    try:
        import finnhub  # type: ignore

        client = finnhub.Client(api_key=key)
    except ImportError:
        return []

    end = datetime.now(timezone.utc).date()
    start = end - timedelta(days=days)
    out: list[NewsEvent] = []
    fetched = utc_now_iso()
    for sym in symbols[:8]:
        try:
            items = client.company_news(sym, _to_unix(start), _to_unix(end))
            for it in items[:10]:
                headline = str(it.get("headline") or "")
                if not headline:
                    continue
                pub = datetime.fromtimestamp(it.get("datetime", 0), tz=timezone.utc).isoformat()
                out.append(
                    NewsEvent(
                        headline=headline[:200],
                        source=str(it.get("source") or "finnhub"),
                        url=str(it.get("url") or ""),
                        published_at=pub,
                        summary=headline[:120],
                        symbols=[sym.upper()],
                        category="news",
                        sentiment=0.0,
                    )
                )
        except Exception:
            continue
    return out


def quotes_with_provenance(symbols: list[str]) -> tuple[list[dict], ProviderResult]:
    fetched = utc_now_iso()
    session_open = is_regular_session_open()
    result = fetch_quotes(symbols)
    rows: list[dict] = []
    for q in result.quotes:
        d = q.to_dict()
        d["provenance"] = attach_provenance(
            provider="finnhub",
            fetched_at=fetched,
            market_timestamp=fetched,
            market_session_open=session_open,
            provider_ok=result.ok,
            is_fallback=False,
            error=result.error,
        )
        rows.append(d)
    return rows, result


def _to_unix(d) -> int:
    return int(datetime.combine(d, datetime.min.time()).replace(tzinfo=timezone.utc).timestamp())
