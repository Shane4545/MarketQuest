"""Alpaca market data (REST; optional stream cache)."""

from __future__ import annotations

import os
from typing import Any

from marketquest.data_sources.base import ProviderResult, QuoteRecord, utc_now_iso
from marketquest.data_sources.market_hours import is_regular_session_open
from marketquest.freshness import attach_provenance

_stream_cache: dict[str, dict[str, Any]] = {}


def _keys() -> tuple[str | None, str | None]:
    return os.environ.get("ALPACA_API_KEY"), os.environ.get("ALPACA_SECRET_KEY")


def fetch_quotes(symbols: list[str]) -> ProviderResult:
    fetched = utc_now_iso()
    key, secret = _keys()
    if not key or not secret:
        return ProviderResult(
            provider="alpaca",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error="ALPACA_API_KEY/ALPACA_SECRET_KEY not set",
        )

    # Prefer stream cache if populated
    if _stream_cache:
        session_open = is_regular_session_open()
        quotes = []
        for sym in symbols:
            c = _stream_cache.get(sym.upper())
            if c:
                quotes.append(
                    QuoteRecord(
                        symbol=sym.upper(),
                        last=float(c.get("last", 0)),
                        change_pct=float(c.get("change_pct", 0)),
                        volume=int(c.get("volume", 0)),
                    )
                )
        if quotes:
            return ProviderResult(
                provider="alpaca",
                ok=True,
                fetched_at=fetched,
                freshness="LIVE",
                fallback=False,
                quotes=quotes,
            )

    try:
        from alpaca.data.historical import StockHistoricalDataClient  # type: ignore
        from alpaca.data.requests import StockLatestQuoteRequest  # type: ignore
    except ImportError:
        return ProviderResult(
            provider="alpaca",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error="alpaca-py not installed",
        )

    try:
        client = StockHistoricalDataClient(key, secret)
        req = StockLatestQuoteRequest(symbol_or_symbols=symbols)
        resp = client.get_stock_latest_quote(req)
    except Exception as e:
        return ProviderResult(
            provider="alpaca",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            error=str(e),
        )

    quotes: list[QuoteRecord] = []
    for sym in symbols:
        q = resp.get(sym) if hasattr(resp, "get") else getattr(resp, sym, None)
        if not q:
            continue
        bid = float(getattr(q, "bid_price", 0) or 0)
        ask = float(getattr(q, "ask_price", 0) or 0)
        last = (bid + ask) / 2 if bid and ask else bid or ask
        quotes.append(
            QuoteRecord(
                symbol=sym.upper(),
                last=round(last, 4),
                change_pct=0.0,
                volume=0,
            )
        )

    return ProviderResult(
        provider="alpaca",
        ok=bool(quotes),
        fetched_at=fetched,
        freshness="LIVE" if quotes else "OFFLINE",
        fallback=False,
        quotes=quotes,
    )


def quotes_with_provenance(symbols: list[str]) -> tuple[list[dict], ProviderResult]:
    fetched = utc_now_iso()
    session_open = is_regular_session_open()
    result = fetch_quotes(symbols)
    rows: list[dict] = []
    for q in result.quotes:
        d = q.to_dict()
        d["provenance"] = attach_provenance(
            provider="alpaca",
            fetched_at=fetched,
            market_timestamp=fetched,
            market_session_open=session_open,
            provider_ok=result.ok,
            is_fallback=False,
            error=result.error,
        )
        rows.append(d)
    return rows, result


def update_stream_cache(symbol: str, last: float, change_pct: float = 0.0, volume: int = 0) -> None:
    _stream_cache[symbol.upper()] = {
        "last": last,
        "change_pct": change_pct,
        "volume": volume,
    }


def stream_cache_size() -> int:
    return len(_stream_cache)


def try_start_stream(symbols: list[str]) -> bool:
    """Optional WebSocket cache when MARKETQUEST_STREAM=1 and keys present."""
    import os

    if os.environ.get("MARKETQUEST_STREAM", "").lower() not in ("1", "true", "yes"):
        return False
    key, secret = _keys()
    if not key or not secret:
        return False
    # REST polling fallback seeds cache; full WS can be enabled in a future sprint.
    result = fetch_quotes(symbols[:5])
    for q in result.quotes:
        update_stream_cache(q.symbol, q.last, q.change_pct, q.volume)
    return stream_cache_size() > 0
