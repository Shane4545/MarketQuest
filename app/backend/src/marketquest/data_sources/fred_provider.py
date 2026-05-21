"""FRED macro series — optional API key."""

from __future__ import annotations

import json
import os
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from marketquest.data_sources.base import MacroPoint, ProviderResult, utc_now_iso

DEFAULT_SERIES = [
    ("FEDFUNDS", "Fed Funds Rate"),
    ("CPIAUCSL", "CPI"),
    ("UNRATE", "Unemployment Rate"),
    ("VIXCLS", "VIX"),
    ("DCOILWTICO", "WTI Crude Oil"),
    ("DGS10", "10-Year Treasury Yield"),
    ("DEXCAUS", "USD/CAD Exchange Rate"),
]


def fetch_macro() -> ProviderResult:
    fetched = utc_now_iso()
    key = os.environ.get("FRED_API_KEY")
    points: list[MacroPoint] = []
    for series_id, name in DEFAULT_SERIES:
        try:
            val, obs = _latest_observation(series_id, key)
            if val is not None:
                points.append(
                    MacroPoint(
                        series_id=series_id,
                        name=name,
                        value=val,
                        observation_date=obs or "",
                    )
                )
        except Exception:
            continue
    return ProviderResult(
        provider="fred",
        ok=bool(points),
        fetched_at=fetched,
        freshness="DELAYED" if points else "OFFLINE",
        macro=points,
    )


def _latest_observation(series_id: str, api_key: str | None) -> tuple[float | None, str | None]:
    params = {"series_id": series_id, "sort_order": "desc", "limit": 1, "file_type": "json"}
    if api_key:
        params["api_key"] = api_key
        base = "https://api.stlouisfed.org/fred/series/observations"
    else:
        base = "https://api.stlouisfed.org/fred/series/observations"
        if not api_key:
            return _fred_public_graph_fallback(series_id)
    url = base + "?" + urlencode(params)
    req = Request(url)
    with urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    obs = (data.get("observations") or [{}])[0]
    v = obs.get("value")
    if v in (".", None):
        return None, None
    return float(v), str(obs.get("date", ""))


def _fred_public_graph_fallback(series_id: str) -> tuple[float | None, str | None]:
    return None, None
