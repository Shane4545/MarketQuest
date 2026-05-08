from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acquisition.run_viewer import list_run_ids, load_run_summary  # noqa: E402


def _mk_run(repo: Path, run_id: str, *, with_terminal: bool = True) -> Path:
    run_dir = repo / "app" / "data" / "acquisition_runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "acquisition_plan.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "start_date": "2026-03-02",
                "end_date": "2026-03-20",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "acquisition_result.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "provider_used": "yfinance",
                "symbols_requested": ["HAS", "SYY"],
                "symbols_returned": ["HAS", "SYY"],
                "symbols_skipped": [],
                "rows_normalized": 30,
                "rejected_rows": 0,
                "partial_coverage": True,
                "full_coverage_claimed": False,
                "ready_for_pipeline": True,
                "limitations": ["provider-level source reference used"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "openbb_acquisition_manifest.json").write_text(
        json.dumps(
            {
                "provider": "yfinance",
                "start_date": "2026-03-02",
                "end_date": "2026-03-20",
                "provider_source_reference": "https://finance.yahoo.com/",
                "warnings": ["Some rows had blank optional fields."],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "openbb_source_log.json").write_text(
        json.dumps(
            {
                "provider": "yfinance",
                "rows_returned": 30,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    pd.DataFrame(
        [{"symbol": "HAS", "date": "2026-03-02", "open": 1, "high": 1, "low": 1, "close": 1, "volume": 1}]
    ).to_csv(run_dir / "openbb_normalized_prices.csv", index=False)
    pd.DataFrame(columns=["symbol", "reason"]).to_csv(run_dir / "openbb_skipped_symbols.csv", index=False)
    pd.DataFrame(columns=["symbol", "reason", "raw_row"]).to_csv(run_dir / "openbb_rejected_rows.csv", index=False)
    if with_terminal:
        (run_dir / "pipeline_terminal_status.json").write_text(
            json.dumps(
                {
                    "pipeline_status": "SCAN_COMPLETE_NO_CANDIDATES",
                    "overall_pipeline_status": "COMPLETE_NO_CANDIDATES",
                    "selected_candidate_count": 0,
                    "rejected_candidate_count": 2,
                    "basket_frozen": False,
                    "controls_built": False,
                    "review_generated": False,
                    "reason": "no candidates passed configured scan rule",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    return run_dir


def test_list_run_ids_reads_directories(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _mk_run(repo, "run_b")
    _mk_run(repo, "run_a")
    assert list_run_ids(repo) == ["run_a", "run_b"]


def test_load_run_summary_preserves_coverage_and_no_candidates_state(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _mk_run(repo, "live_smoke")
    summary = load_run_summary(repo, "live_smoke")

    assert summary["run_id"] == "live_smoke"
    assert summary["provider"] == "yfinance"
    assert summary["partial_coverage"] is True
    assert summary["full_coverage_claimed"] is False
    assert summary["ready_for_pipeline"] is True
    assert summary["overall_pipeline_status"] == "COMPLETE_NO_CANDIDATES"
    assert "zero selected candidates" in (summary["no_candidates_message"] or "").lower()
    assert summary["paths"]["evidence_folder"] == "not linked to run_id"
    assert summary["paths"]["receipt_file"] == "not linked to run_id"
    assert summary["paths"]["evidence_folder"] != "--"
    assert any("Governance evidence/receipt paths are not recorded" in x for x in summary["limitations"])


def test_missing_optional_artifacts_are_reported_honestly(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    run_dir = _mk_run(repo, "no_terminal", with_terminal=False)
    (run_dir / "openbb_rejected_rows.csv").unlink()
    summary = load_run_summary(repo, "no_terminal")
    assert "pipeline_terminal_status_json" in summary["missing_artifacts"]
    assert "openbb_rejected_rows_csv" in summary["missing_artifacts"]
    assert summary["overall_pipeline_status"] is None


def test_governance_mapping_resolves_existing_paths(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _mk_run(repo, "mapped_run")
    run_dir = repo / "app" / "data" / "acquisition_runs" / "mapped_run"
    (run_dir / "governance_links.json").write_text(
        json.dumps(
            {
                "evidence_folders": ["agent_workspace/evidence/TASK_VIEWER_001"],
                "receipt_files": ["agent_workspace/receipts/TASK_VIEWER_001.md"],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    ev_dir = repo / "agent_workspace" / "evidence" / "TASK_VIEWER_001"
    ev_dir.mkdir(parents=True)
    rc_file = repo / "agent_workspace" / "receipts" / "TASK_VIEWER_001.md"
    rc_file.parent.mkdir(parents=True)
    rc_file.write_text("# receipt\n", encoding="utf-8")

    summary = load_run_summary(repo, "mapped_run")
    assert summary["governance"]["evidence"]["link_status"] == "linked"
    assert summary["governance"]["receipt"]["link_status"] == "linked"
    assert str(ev_dir.resolve()) in summary["paths"]["evidence_folder"] or summary["paths"]["evidence_folder"].endswith(
        "TASK_VIEWER_001"
    )
    assert "TASK_VIEWER_001.md" in summary["paths"]["receipt_file"]


def test_no_real_ticker_seed_list_in_run_viewer_files() -> None:
    banned = {
        "".join(chr(c) for c in seq)
        for seq in [
            (65, 65, 80, 76),
            (77, 83, 70, 84),
            (71, 79, 79, 71),
            (70, 66),
            (78, 70, 76, 88),
        ]
    }
    files = [
        ROOT / "app" / "backend" / "src" / "acquisition" / "run_viewer.py",
        ROOT / "app" / "scripts" / "run_viewer_api.py",
        ROOT / "web" / "run_viewer.js",
        ROOT / "web" / "run_viewer.html",
        ROOT / "web" / "run_launcher.js",
        ROOT / "web" / "run_launcher.html",
    ]
    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        for symbol in banned:
            assert symbol not in text, f"Found banned symbol {symbol} in {file_path}"
