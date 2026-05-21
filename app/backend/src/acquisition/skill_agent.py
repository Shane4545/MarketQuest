"""Governed data acquisition skill agent around providers/adapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .acquisition_plan import AcquisitionPlan, write_plan
from .exporter import NORMALIZED_COLUMNS, write_csv
from .openbb_adapter import acquire_prices
from .provider_registry import choose_provider
from .provenance import sha256_file, utc_now_iso, write_json


@dataclass
class SkillAgentOutcome:
    """Final result from a governed acquisition run."""

    normalized_csv_path: Path
    manifest_path: Path
    source_log_path: Path
    plan_path: Path
    result_path: Path
    ready_for_pipeline: bool
    partial_coverage: bool


def _build_manifest(
    *,
    run_id: str,
    provider: str,
    start_date: str,
    end_date: str,
    symbols_requested: list[str],
    symbols_returned_count: int,
    normalized_rows_count: int,
    output_csv: Path,
    output_sha: str,
    openbb_version: str | None,
    provider_source_reference: str,
    row_level_source_url_available: bool,
    partial_coverage: bool,
    skipped_symbols_count: int,
    rejected_rows_count: int,
    warnings: list[str],
    limitations: list[str],
) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "created_at": utc_now_iso(),
        "adapter_name": "openbb_thin_acquisition_adapter",
        "openbb_version": openbb_version,
        "provider": provider,
        "start_date": start_date,
        "end_date": end_date,
        "symbols_requested_count": len(symbols_requested),
        "symbols_returned_count": symbols_returned_count,
        "normalized_rows_count": normalized_rows_count,
        "skipped_symbols_count": skipped_symbols_count,
        "rejected_rows_count": rejected_rows_count,
        "output_csv": str(output_csv),
        "output_csv_sha256": output_sha,
        "provider_source_reference": provider_source_reference,
        "row_level_source_url_available": row_level_source_url_available,
        "partial_coverage": partial_coverage,
        "limitations": limitations,
        "warnings": warnings,
        "no_hardcoded_symbols_assertion": True,
        "real_ticker_seed_list_used": False,
        "prior_chat_ticker_leakage_found": False,
    }


def run_acquisition_skill(
    *,
    repo_root: Path,
    run_id: str,
    symbols: list[str],
    symbol_source: str,
    start_date: str,
    end_date: str,
    preferred_provider: str,
    fallback_providers: list[str],
    output_csv: Path,
    mode: str,
    partial_coverage_allowed: bool,
    fixture_path: Path | None = None,
    market_cap_fixture: Path | None = None,
) -> SkillAgentOutcome:
    """Plan, execute adapter, assess readiness, and emit governed artifacts."""
    run_dir = repo_root / "app" / "data" / "acquisition_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    plan = AcquisitionPlan(
        run_id=run_id,
        requested_symbols=symbols,
        symbol_source=symbol_source,
        requested_start_date=start_date,
        requested_end_date=end_date,
        preferred_provider=preferred_provider,
        fallback_providers=fallback_providers,
        known_limitations_before_run=[
            "Provider coverage may be partial.",
            "Row-level source_url may be unavailable for some providers.",
            "full_coverage_claimed remains false unless independently proven.",
        ],
        partial_coverage_allowed=partial_coverage_allowed,
    )
    plan_path = write_plan(plan, run_dir)

    selection = choose_provider(preferred_provider, fallback_providers)
    result = acquire_prices(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        provider=selection.provider_used,
        mode=mode,
        fixture_path=fixture_path,
        market_cap_fixture=market_cap_fixture,
    )

    write_csv(result.mapping.normalized, output_csv)
    normalized_csv = run_dir / "openbb_normalized_prices.csv"
    skipped_csv = run_dir / "openbb_skipped_symbols.csv"
    rejected_csv = run_dir / "openbb_rejected_rows.csv"
    source_log_path = run_dir / "openbb_source_log.json"
    manifest_path = run_dir / "openbb_acquisition_manifest.json"

    write_csv(result.mapping.normalized, normalized_csv)
    result.mapping.skipped_symbols.to_csv(skipped_csv, index=False)
    result.mapping.rejected_rows.to_csv(rejected_csv, index=False)
    write_json(source_log_path, result.source_log)

    partial_coverage = (
        result.mapping.skipped_symbols.shape[0] > 0
        or result.mapping.rejected_rows.shape[0] > 0
        or not result.row_level_source_url_available
    )

    output_sha = sha256_file(output_csv)
    manifest = _build_manifest(
        run_id=run_id,
        provider=selection.provider_used,
        start_date=start_date,
        end_date=end_date,
        symbols_requested=symbols,
        symbols_returned_count=int(result.mapping.normalized["symbol"].astype(str).nunique())
        if not result.mapping.normalized.empty
        else 0,
        normalized_rows_count=int(result.mapping.normalized.shape[0]),
        output_csv=output_csv,
        output_sha=output_sha,
        openbb_version=result.openbb_version,
        provider_source_reference=result.provider_source_reference,
        row_level_source_url_available=result.row_level_source_url_available,
        partial_coverage=partial_coverage,
        skipped_symbols_count=int(result.mapping.skipped_symbols.shape[0]),
        rejected_rows_count=int(result.mapping.rejected_rows.shape[0]),
        warnings=result.warnings,
        limitations=result.limitations,
    )
    write_json(manifest_path, manifest)

    has_schema = list(result.mapping.normalized.columns) == list(NORMALIZED_COLUMNS)
    has_rows = result.mapping.normalized.shape[0] > 0
    coverage_ok = partial_coverage_allowed or (not partial_coverage)
    ready_for_pipeline = bool(has_schema and has_rows and coverage_ok)

    acquisition_result = {
        "run_id": run_id,
        "provider_used": selection.provider_used,
        "fallback_used": selection.fallback_used,
        "symbols_requested": symbols,
        "symbols_returned": sorted(result.mapping.normalized["symbol"].astype(str).unique().tolist())
        if not result.mapping.normalized.empty
        else [],
        "symbols_skipped": result.mapping.skipped_symbols.to_dict(orient="records"),
        "rows_normalized": int(result.mapping.normalized.shape[0]),
        "rejected_rows": int(result.mapping.rejected_rows.shape[0]),
        "partial_coverage": partial_coverage,
        "limitations": result.limitations,
        "ready_for_pipeline": ready_for_pipeline,
        "normalized_csv_path": str(output_csv),
        "manifest_path": str(manifest_path),
        "source_log_path": str(source_log_path),
        "result_created_at": utc_now_iso(),
        "full_coverage_claimed": False,
    }
    result_path = run_dir / "acquisition_result.json"
    write_json(result_path, acquisition_result)

    return SkillAgentOutcome(
        normalized_csv_path=output_csv,
        manifest_path=manifest_path,
        source_log_path=source_log_path,
        plan_path=plan_path,
        result_path=result_path,
        ready_for_pipeline=ready_for_pipeline,
        partial_coverage=partial_coverage,
    )

