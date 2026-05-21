"""yfinance provider — always labeled DELAYED fallback."""

from __future__ import annotations

from marketquest.data_sources.base import ProviderResult, QuoteRecord, utc_now_iso
from marketquest.data_sources.market_hours import is_regular_session_open
from marketquest.freshness import attach_provenance


def fetch_quotes(symbols: list[str]) -> ProviderResult:
    fetched = utc_now_iso()
    session_open = is_regular_session_open()
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return ProviderResult(
            provider="yfinance",
            ok=False,
            fetched_at=fetched,
            freshness="OFFLINE",
            fallback=True,
            error="yfinance not installed",
        )

    quotes: list[QuoteRecord] = []
    for sym in symbols:
        try:
            t = yf.Ticker(sym)
            info = t.fast_info
            hist = t.history(period="5d")
            last = float(info.get("last_price") or info.get("lastPrice") or 0)
            prev = float(info.get("previous_close") or info.get("previousClose") or 0)
            if last <= 0 and hist is not None and not hist.empty:
                last = float(hist["Close"].iloc[-1])
                if len(hist) > 1:
                    prev = float(hist["Close"].iloc[-2])
            chg = ((last - prev) / prev * 100) if prev else 0.0
            vol = int(info.get("last_volume") or info.get("lastVolume") or 0)
            quotes.append(
                QuoteRecord(
                    symbol=sym.upper(),
                    last=round(last, 4),
                    change_pct=round(chg, 4),
                    volume=vol,
                )
            )
        except Exception:
            continue

    fresh = "DELAYED" if quotes else "OFFLINE"
    return ProviderResult(
        provider="yfinance",
        ok=bool(quotes),
        fetched_at=fetched,
        freshness=fresh,
        fallback=True,
        quotes=quotes,
    )


def quotes_with_provenance(symbols: list[str]) -> tuple[list[dict], ProviderResult]:
    """Return quote dicts with provenance attached."""
    fetched = utc_now_iso()
    session_open = is_regular_session_open()
    result = fetch_quotes(symbols)
    rows: list[dict] = []
    for q in result.quotes:
        d = q.to_dict()
        d["provenance"] = attach_provenance(
            provider="yfinance",
            fetched_at=fetched,
            market_timestamp=fetched,
            market_session_open=session_open,
            provider_ok=True,
            is_fallback=True,
        )
        rows.append(d)
    return rows, result
