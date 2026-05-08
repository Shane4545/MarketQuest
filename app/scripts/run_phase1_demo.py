"""Run full Phase 1 synthetic demo pipeline (subprocesses — paths relative to repo cwd)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo = Path(__file__).resolve().parents[2]
    py = sys.executable
    script = Path(__file__).parent

    def run(cmd: list[str]) -> None:
        print("+", " ".join(cmd), flush=True)
        subprocess.check_call(cmd, cwd=repo)

    run(
        [
            py,
            str(script / "ingest.py"),
            "--input",
            str(repo / "app" / "data" / "raw" / "synthetic_prices.csv"),
        ]
    )
    run(
        [
            py,
            str(script / "validate.py"),
            "--input",
            str(repo / "app" / "data" / "staged" / "prices.parquet"),
        ]
    )
    run([py, str(script / "compute_features.py"), "--as-of", "2026-01-08"])
    run(
        [
            py,
            str(script / "scan_candidates.py"),
            "--as-of",
            "2026-01-08",
            "--rule",
            "momentum_volume_pressure",
        ]
    )
    run(
        [
            py,
            str(script / "freeze_basket.py"),
            "--as-of",
            "2026-01-08",
            "--basket-name",
            "demo_auto_selected",
            "--amount",
            "100",
            "--from-candidates",
            str(repo / "app" / "data" / "curated" / "candidates_2026-01-08.parquet"),
        ]
    )
    run([py, str(script / "build_controls.py"), "--basket-name", "demo_auto_selected"])
    run(
        [
            py,
            str(script / "review_basket.py"),
            "--basket-name",
            "demo_auto_selected",
            "--review-date",
            "2026-01-13",
        ]
    )
    run([py, str(script / "generate_evidence_manifest.py"), "--run-id", "latest", "--as-of", "2026-01-08"])
    run([py, str(script / "generate_coverage_report.py"), "--run-id", "latest", "--as-of", "2026-01-08"])
    print("Phase 1 demo pipeline completed OK.")


if __name__ == "__main__":
    main()
