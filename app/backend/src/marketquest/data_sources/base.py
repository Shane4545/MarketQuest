"""Provider abstraction — shared records and metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class DataProvenance:
    provider: str
    fetched_at: str
    market_timestamp: str | None = None
    age_minutes: float = 0.0
    freshness: str = "OFFLINE"  # LIVE | DELAYED | STALE | OFFLINE
    fallback: bool = False
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QuoteRecord:
    symbol: str
    last: float
    change_pct: float
    volume: int
    currency: str = "USD"
    provenance: DataProvenance | None = None
    gap_pct: float | None = None
    rvol: float | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "symbol": self.symbol.upper(),
            "last": self.last,
            "change_pct": self.change_pct,
            "volume": self.volume,
            "currency": self.currency,
            "gap_pct": self.gap_pct,
            "rvol": self.rvol,
        }
        if self.provenance:
            d["provenance"] = self.provenance.to_dict()
        return d


@dataclass
class NewsEvent:
    headline: str
    source: str
    url: str
    published_at: str
    summary: str
    symbols: list[str]
    category: str
    sentiment: float = 0.0
    confidence: float = 0.5
    provenance: DataProvenance | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.provenance:
            d["provenance"] = self.provenance.to_dict()
        return d


@dataclass
class FilingEvent:
    symbol: str
    form_type: str
    filed_at: str
    url: str
    category: str
    provenance: DataProvenance | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "symbol": self.symbol,
            "form_type": self.form_type,
            "filed_at": self.filed_at,
            "url": self.url,
            "category": self.category,
        }
        if self.provenance:
            d["provenance"] = self.provenance.to_dict()
        return d


@dataclass
class MacroPoint:
    series_id: str
    name: str
    value: float
    observation_date: str
    provenance: DataProvenance | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "series_id": self.series_id,
            "name": self.name,
            "value": self.value,
            "observation_date": self.observation_date,
        }
        if self.provenance:
            d["provenance"] = self.provenance.to_dict()
        return d


@dataclass
class ProviderResult:
    provider: str
    ok: bool
    fetched_at: str = field(default_factory=utc_now_iso)
    freshness: str = "OFFLINE"
    fallback: bool = False
    error: str | None = None
    quotes: list[QuoteRecord] = field(default_factory=list)
    news: list[NewsEvent] = field(default_factory=list)
    filings: list[FilingEvent] = field(default_factory=list)
    macro: list[MacroPoint] = field(default_factory=list)

    def status_dict(self) -> dict[str, Any]:
        return {
            "status": self.freshness,
            "fetched_at": self.fetched_at,
            "fallback": self.fallback,
            "error": self.error,
            "ok": self.ok,
        }
