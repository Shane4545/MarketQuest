"""Acquisition planning document helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .exporter import NORMALIZED_COLUMNS
from .provenance import utc_now_iso, write_json


@dataclass
class AcquisitionPlan:
    """Planned run configuration."""

    run_id: str
    requested_symbols: list[str]
    symbol_source: str
    requested_start_date: str
    requested_end_date: str
    preferred_provider: str
    fallback_providers: list[str]
    known_limitations_before_run: list[str]
    partial_coverage_allowed: bool

    def to_payload(self) -> dict[str, Any]:
        """Convert plan to JSON payload."""
        return {
            "run_id": self.run_id,
            "requested_symbols": self.requested_symbols,
            "symbol_source": self.symbol_source,
            "requested_start_date": self.requested_start_date,
            "requested_end_date": self.requested_end_date,
            "preferred_provider": self.preferred_provider,
            "fallback_providers": self.fallback_providers,
            "expected_output_schema": list(NORMALIZED_COLUMNS),
            "known_limitations_before_run": self.known_limitations_before_run,
            "partial_coverage_allowed": self.partial_coverage_allowed,
            "full_coverage_claimed": False,
            "planned_at": utc_now_iso(),
        }


def write_plan(plan: AcquisitionPlan, run_dir: Path) -> Path:
    """Write acquisition plan JSON."""
    path = run_dir / "acquisition_plan.json"
    write_json(path, plan.to_payload())
    return path

