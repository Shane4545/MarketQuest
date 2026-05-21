"""Forex quotes — Finnhub, FRED, yfinance fallback for 7+ major pairs."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from marketquest.data_sources.base import DataProvenance, ProviderResult, utc_now_iso
from marketquest.data_sources.fred_provider import _latest_observation

# pair -> (finnhub_rate_key, fred_series_id, yfinance_symbol)
PAIR_CONFIG: dict[str, tuple[str, str | None, str]] = {
    "EUR/USD": ("EURUSD", None, "EURUSD=X"),
    "GBP/USD": ("GBPUSD", None, "GBPUSD=X"),
    "USD/JPY": ("USDJPY", None, "JPY=X"),
    "USD/CAD": ("USDCAD", "DEXCAUS", "CAD=X"),
    "AUD/USD": ("AUDUSD", None, "AUDUSD=X"),
    "NZD/USD": ("NZDUSD", None, "NZDUSD=X"),
    "USD/CHF": ("USDCHF", None, "CHF=X"),
    "USD/CNH": ("USDCNH", None, "CNH=X"),
    "USD/MXN": ("USDMXN", None, "MXN=X"),
    "USD/NOK": ("USDNOK", None, "NOK=X"),
}

WHY_IT_MATTERS = {
    "USD/CAD": "CAD moves with oil and Bank of Canada policy — affects Canadian exporters and energy names.",
    "EUR/USD": "Euro strength reflects EU growth and ECB policy — affects multinational earnings.",
    "GBP/USD": "Sterling reflects UK growth and BoE policy — affects global banks and multinationals.",
    "USD/JPY": "JPY crosses often signal risk-on/risk-off and yield differentials.",
    "AUD/USD": "AUD is commodity-sensitive — links to China demand and metals.",
    "NZD/USD": "NZD tracks dairy/commodity cycles and risk appetite.",
    "USD/CHF": "CHF often strengthens in risk-off — safe-haven signal.",
    "USD/CNH": "Offshore yuan reflects China trade and tariff sensitivity.",
    "USD/MXN": "Peso reflects EM and US-Mexico trade dynamics.",
    "USD/NOK": "NOK links to oil and European energy markets.",
}


def _load_pairs(repo: Path | None) -> list[str]:
    if repo is None:
        return list(PAIR_CONFIG.keys())[:7]
    try:
        from marketquest.cross_asset.currency_watchlist import all_pairs

        pairs = all_pairs(repo)
        return pairs if pairs else list(PAIR_CONFIG.keys())[:7]
    except Exception:
        return list(PAIR_CONFIG.keys())[:7]


def fetch_forex(repo: Path | None = None) -> ProviderResult:
    fetched = utc_now_iso()
    quotes = fetch_cross_asset_quotes(repo)
    errors: list[str] = []
    for pair in _load_pairs(repo):
        if not any(q.get("pair") == pair for q in quotes):
            errors.append(f"{pair}: no data")
    freshness = "LIVE" if quotes else "OFFLINE"
    if quotes and any(q.get("status") == "DELAYED" or (q.get("provenance") or {}).get("freshness") == "DELAYED" for q in quotes):
        freshness = "DELAYED"
    return ProviderResult(
        provider="forex",
        ok=bool(quotes),
        fetched_at=fetched,
        freshness=freshness,
        error="; ".join(errors) if errors and len(quotes) < 3 else None,
        quotes=[],  # type: ignore[arg-type]
    )


def fetch_cross_asset_quotes(repo: Path | None = None) -> list[dict[str, Any]]:
    """Return cross-asset FX quote dicts for snapshot cross_asset block."""
    fetched = utc_now_iso()
    key = os.environ.get("FINNHUB_API_KEY")
    pairs = _load_pairs(repo)
    quotes: list[dict[str, Any]] = []
    finnhub_rates: dict[str, float] | None = None

    if key:
        finnhub_rates = _finnhub_all_rates(key)

    for pair in pairs:
        cfg = PAIR_CONFIG.get(pair)
        if not cfg:
            continue
        finn_key, fred_series, yf_sym = cfg
        q = None
        if finnhub_rates:
            q = _quote_from_finnhub(pair, finn_key, finnhub_rates, fetched)
        if q is None and fred_series:
            q = _fetch_fred_forex(pair, fred_series, fetched)
        if q is None:
            q = _fetch_yfinance_forex(pair, yf_sym, fetched)
        if q:
            quotes.append(q)
        else:
            quotes.append(_offline_placeholder(pair, fetched))

    return quotes


def _finnhub_all_rates(api_key: str) -> dict[str, float] | None:
    try:
        import finnhub  # type: ignore

        client = finnhub.Client(api_key=api_key)
        data = client.forex_rates(exchange="oanda")
        return (data or {}).get("quote") or {}
    except Exception:
        return None


def _quote_from_finnhub(
    pair: str,
    rate_key: str,
    rates: dict[str, float],
    fetched: str,
) -> dict[str, Any] | None:
    val = rates.get(rate_key)
    if val is None:
        return None
    return _make_quote(pair, float(val), "finnhub", "LIVE", fetched, fallback=False)


def _fetch_fred_forex(pair: str, series_id: str, fetched: str) -> dict[str, Any] | None:
    key = os.environ.get("FRED_API_KEY")
    try:
        val, obs = _latest_observation(series_id, key)
        if val is None:
            return None
        q = _make_quote(pair, float(val), "fred", "DELAYED", fetched, fallback=True)
        q["observation_date"] = obs
        return q
    except Exception:
        return None


def _fetch_yfinance_forex(pair: str, yf_sym: str, fetched: str) -> dict[str, Any] | None:
    try:
        import yfinance as yf  # type: ignore

        t = yf.Ticker(yf_sym)
        hist = t.history(period="5d")
        if hist is None or hist.empty:
            return None
        last = float(hist["Close"].iloc[-1])
        chg = 0.0
        if len(hist) > 1:
            prev = float(hist["Close"].iloc[-2])
            chg = ((last - prev) / prev * 100) if prev else 0.0
        q = _make_quote(pair, last, "yfinance", "DELAYED", fetched, fallback=True)
        q["change_pct"] = round(chg, 4)
        q["change_pct_1d"] = round(chg, 4)
        return q
    except Exception:
        return None


def _make_quote(
    pair: str,
    last: float,
    provider: str,
    freshness: str,
    fetched: str,
    *,
    fallback: bool,
) -> dict[str, Any]:
    prov = DataProvenance(provider=provider, fetched_at=fetched, freshness=freshness, fallback=fallback)
    return {
        "pair": pair,
        "bid": None,
        "ask": None,
        "mid": round(last, 6),
        "last": round(last, 6),
        "change_pct": 0.0,
        "change_pct_1d": 0.0,
        "provider": provider,
        "freshness": freshness,
        "status": freshness,
        "fetched_at": fetched,
        "fetched_at_utc": fetched,
        "why_it_matters": WHY_IT_MATTERS.get(pair, ""),
        "provenance": prov.to_dict(),
    }


def _offline_placeholder(pair: str, fetched: str) -> dict[str, Any]:
    return {
        "pair": pair,
        "last": None,
        "provider": "offline",
        "freshness": "OFFLINE",
        "status": "OFFLINE",
        "fetched_at": fetched,
        "fetched_at_utc": fetched,
        "why_it_matters": WHY_IT_MATTERS.get(pair, ""),
        "errors": [f"No provider returned data for {pair}"],
        "provenance": DataProvenance(provider="offline", fetched_at=fetched, freshness="OFFLINE", fallback=True).to_dict(),
    }
