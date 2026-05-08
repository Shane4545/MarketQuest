"""Thin OpenBB-powered acquisition adapter."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .schema_mapper import MappingResult, map_openbb_rows


@dataclass
class AcquireResult:
    """Acquisition result object."""

    mapping: MappingResult
    source_log: dict[str, Any]
    openbb_version: str | None
    row_level_source_url_available: bool
    provider_source_reference: str
    warnings: list[str]
    limitations: list[str]


def _provider_source_reference(provider: str) -> str:
    if provider == "fixture":
        return "fixture://openbb_historical_sample"
    if provider == "yfinance":
        return "https://finance.yahoo.com/"
    if provider == "tmx":
        return "https://www.tsx.com/"
    return f"provider://{provider}"


def _load_fixture_rows(fixture_path: Path) -> list[dict[str, Any]]:
    with open(fixture_path, encoding="utf-8") as fh:
        payload = json.load(fh)
    if isinstance(payload, dict) and "rows" in payload:
        rows = payload["rows"]
    elif isinstance(payload, list):
        rows = payload
    else:
        raise ValueError("Fixture must be a list of rows or {'rows': [...]} object")
    if not isinstance(rows, list):
        raise ValueError("Fixture rows must be a list")
    return rows


def _fetch_openbb_rows(
    symbols: list[str],
    start_date: str,
    end_date: str,
    provider: str,
) -> tuple[list[dict[str, Any]], str]:
    try:
        import openbb  # type: ignore
        from openbb import obb  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "OpenBB is not installed or importable. Install with: pip install openbb openbb-yfinance"
        ) from exc

    try:
        version = getattr(openbb, "__version__", None)
        response = obb.equity.price.historical(
            symbol=symbols,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
        )
        # Keep the index as a column so date/time survives schema mapping.
        rows = response.to_df().reset_index().to_dict(orient="records")
    except Exception as exc:
        raise RuntimeError(
            f"OpenBB fetch failed for provider={provider}. Check provider package, credentials, network, or rate limits. Error: {exc}"
        ) from exc
    return rows, version


def _attach_market_cap(
    base_df: pd.DataFrame,
    provider: str,
    market_cap_fixture: Path | None = None,
) -> pd.DataFrame:
    if base_df.empty:
        return base_df

    if market_cap_fixture:
        with open(market_cap_fixture, encoding="utf-8") as fh:
            payload = json.load(fh)
        rows = payload.get("rows", payload if isinstance(payload, list) else [])
        cap_df = pd.DataFrame(rows)
    else:
        cap_df = pd.DataFrame()

    if cap_df.empty:
        return base_df

    for col in ["symbol", "date", "market_cap"]:
        if col not in cap_df.columns:
            return base_df

    merged = base_df.merge(
        cap_df.loc[:, ["symbol", "date", "market_cap"]],
        on=["symbol", "date"],
        how="left",
        suffixes=("", "_cap"),
    )
    if "market_cap_cap" in merged.columns:
        merged["market_cap"] = merged["market_cap"].where(
            merged["market_cap"].astype(str) != "",
            merged["market_cap_cap"],
        )
        merged = merged.drop(columns=["market_cap_cap"])
    elif "market_cap" not in merged.columns:
        merged["market_cap"] = ""
    return merged


def acquire_prices(
    *,
    symbols: list[str],
    start_date: str,
    end_date: str,
    provider: str,
    mode: str,
    fixture_path: Path | None = None,
    market_cap_fixture: Path | None = None,
) -> AcquireResult:
    """Acquire and map price rows in fixture/live/dry-run modes."""
    warnings: list[str] = []
    limitations: list[str] = []
    reference = _provider_source_reference(provider)
    requested_at = pd.Timestamp.now(tz="UTC").isoformat()
    openbb_version: str | None = None
    row_level_source_url_available = False

    if mode == "dry-run":
        mapping = map_openbb_rows([], symbols, provider, source_url=reference)
        source_log = {
            "provider": provider,
            "request_type": "dry_run",
            "symbols_requested": symbols,
            "start_date": start_date,
            "end_date": end_date,
            "requested_at": requested_at,
            "response_status": "not_fetched",
            "rows_returned": 0,
            "notes": "Provenance-only dry-run; no network fetch performed.",
        }
        limitations.append("Dry-run mode does not fetch data.")
        return AcquireResult(
            mapping=mapping,
            source_log=source_log,
            openbb_version=openbb_version,
            row_level_source_url_available=row_level_source_url_available,
            provider_source_reference=reference,
            warnings=warnings,
            limitations=limitations,
        )

    if mode == "fixture":
        if not fixture_path:
            raise ValueError("Fixture mode requires --fixture path.")
        rows = _load_fixture_rows(fixture_path)
        frame = pd.DataFrame(rows)
        if "source_url" in frame.columns and frame["source_url"].notna().all():
            row_level_source_url_available = True
        frame = _attach_market_cap(frame, provider, market_cap_fixture)
        rows = frame.to_dict(orient="records")
        source_log = {
            "provider": provider,
            "request_type": "fixture",
            "symbols_requested": symbols,
            "start_date": start_date,
            "end_date": end_date,
            "requested_at": requested_at,
            "response_status": "fixture_loaded",
            "rows_returned": len(rows),
            "notes": f"Loaded fixture from {fixture_path}",
        }
    elif mode == "live":
        rows, openbb_version = _fetch_openbb_rows(symbols, start_date, end_date, provider)
        frame = pd.DataFrame(rows)
        row_level_source_url_available = "source_url" in frame.columns and frame["source_url"].notna().all()
        source_log = {
            "provider": provider,
            "request_type": "live_openbb",
            "symbols_requested": symbols,
            "start_date": start_date,
            "end_date": end_date,
            "requested_at": requested_at,
            "response_status": "success",
            "rows_returned": len(rows),
            "notes": "OpenBB historical fetch completed.",
        }
    else:
        raise ValueError("mode must be one of: fixture, live, dry-run")

    if not row_level_source_url_available:
        limitations.append(
            "Row-level source_url not available for all rows; provider-level reference used."
        )

    mapping = map_openbb_rows(rows, symbols, provider, source_url=reference)
    if mapping.skipped_symbols.shape[0] > 0:
        warnings.append("Some requested symbols were skipped.")
    if mapping.rejected_rows.shape[0] > 0:
        warnings.append("Some rows were rejected due to missing required fields.")

    return AcquireResult(
        mapping=mapping,
        source_log=source_log,
        openbb_version=openbb_version,
        row_level_source_url_available=row_level_source_url_available,
        provider_source_reference=reference,
        warnings=warnings,
        limitations=limitations,
    )

