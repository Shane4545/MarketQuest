"""Watchlist quotes — live yfinance with fixture fallback."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from marketquest.config import load_config, mock_requested, today_iso
from marketquest.data_sources.prices import fetch_prices_yfinance, latest_close_by_symbol
from marketquest.paths import fixtures_dir, snapshots_dir


def _load_fixture(repo: Path, name: str) -> dict[str, Any]:
    path = fixtures_dir(repo) / name
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _fetch_live_quotes(symbols: list[str]) -> list[dict[str, Any]]:
    try:
        import yfinance as yf  # type: ignore
    except ImportError:
        return []

    rows: list[dict[str, Any]] = []
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
            chg_pct = ((last - prev) / prev * 100) if prev else 0.0
            vol = int(info.get("last_volume") or info.get("lastVolume") or 0)
            rows.append(
                {
                    "symbol": sym.upper(),
                    "last": round(last, 4),
                    "change_pct": round(chg_pct, 4),
                    "volume": vol,
                    "currency": "USD",
                }
            )
        except Exception:
            continue
    return rows


def load_watchlist(
    repo: Path,
    *,
    as_of: str | None = None,
    mock: bool | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    as_of = as_of or today_iso()
    cfg = load_config(repo)
    use_mock = mock_requested(mock)
    snap_path = snapshots_dir(repo) / f"{as_of}.json"

    if not refresh and snap_path.is_file() and not use_mock:
        cached = json.loads(snap_path.read_text(encoding="utf-8"))
        if cached.get("quotes"):
            cached["data_mode"] = cached.get("data_mode", "live")
            return cached

    if use_mock:
        fixture = _load_fixture(repo, "watchlist.json")
        fixture.setdefault("as_of", as_of)
        fixture["data_mode"] = "mock"
        return fixture

    symbols = cfg["symbols"]
    quotes = _fetch_live_quotes(symbols)
    data_mode = "live"
    if not quotes:
        fixture = _load_fixture(repo, "watchlist.json")
        fixture.setdefault("as_of", as_of)
        fixture["data_mode"] = "mock"
        fixture["fallback_reason"] = "live fetch failed"
        return fixture

    prices_df = fetch_prices_yfinance(symbols)
    closes = latest_close_by_symbol(prices_df)
    for q in quotes:
        sym = q["symbol"]
        if sym in closes and not q.get("last"):
            q["last"] = closes[sym]

    payload = {
        "as_of": as_of,
        "data_mode": data_mode,
        "quotes": quotes,
        "symbol_count": len(quotes),
    }
    snapshots_dir(repo).mkdir(parents=True, exist_ok=True)
    snap_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload
