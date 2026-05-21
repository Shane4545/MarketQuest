"""Provider fallback labeling."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from marketquest.data_sources import yfinance_fallback  # noqa: E402
from marketquest.reality_engine.collector import _merge_quotes  # noqa: E402


def test_yfinance_marks_fallback():
    with patch.object(yfinance_fallback, "fetch_quotes") as m:
        from marketquest.data_sources.base import ProviderResult, QuoteRecord

        m.return_value = ProviderResult(
            provider="yfinance",
            ok=True,
            fallback=True,
            freshness="DELAYED",
            quotes=[QuoteRecord("SPY", 500, 0, 1000)],
        )
        rows, status = yfinance_fallback.quotes_with_provenance(["SPY"])
    assert status.fallback is True
    assert rows[0]["provenance"]["fallback"] is True


def test_merge_quotes_uses_finnhub_first():
    with patch("marketquest.data_sources.finnhub_provider.quotes_with_provenance") as fh:
        with patch("marketquest.data_sources.alpaca_data_provider.quotes_with_provenance") as al:
            with patch("marketquest.data_sources.yfinance_fallback.quotes_with_provenance") as yf:
                from marketquest.data_sources.base import ProviderResult

                fh.return_value = (
                    [{"symbol": "NVDA", "last": 1, "provenance": {"freshness": "LIVE"}}],
                    ProviderResult("finnhub", True, freshness="LIVE"),
                )
                al.return_value = ([], ProviderResult("alpaca", False))
                yf.return_value = ([], ProviderResult("yfinance", False, fallback=True))
                prices, st = _merge_quotes(["NVDA"])
    assert prices[0]["symbol"] == "NVDA"
    assert "finnhub" in st
