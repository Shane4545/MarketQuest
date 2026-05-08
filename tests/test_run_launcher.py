from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "app" / "backend" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from acquisition.launcher_trading_scope import ALLOWED_RUN_PURPOSES  # noqa: E402
from acquisition.run_launcher import (  # noqa: E402
    build_launcher_options,
    execute_launch,
    load_launcher_status,
    validate_launch_request,
)


def test_validate_rejects_live_without_symbols() -> None:
    body = {
        "mode": "live",
        "provider": "yfinance",
        "start_date": "2026-01-01",
        "end_date": "2026-01-10",
        "as_of_date": "2026-01-08",
        "review_date": "2026-01-08",
        "rule": "momentum_volume_pressure",
        "basket_name": "b",
        "amount": 100,
        "symbols": "",
    }
    v = validate_launch_request(ROOT, body)
    assert v["valid"] is False
    assert any("symbols" in e.lower() for e in v["errors"])


def test_validate_accepts_fixture_minimal() -> None:
    body = {
        "mode": "fixture",
        "provider": "fixture",
        "start_date": "2026-01-01",
        "end_date": "2026-01-10",
        "as_of_date": "2026-01-08",
        "review_date": "2026-01-08",
        "rule": "momentum_volume_pressure",
        "basket_name": "fx_basket",
        "amount": 1000,
    }
    v = validate_launch_request(ROOT, body)
    assert v["valid"] is True
    assert not v["errors"]


def test_validate_rejects_invalid_run_purpose_token() -> None:
    body = {
        "mode": "fixture",
        "provider": "fixture",
        "start_date": "2026-01-01",
        "end_date": "2026-01-10",
        "as_of_date": "2026-01-08",
        "review_date": "2026-01-08",
        "rule": "momentum_volume_pressure",
        "basket_name": "x",
        "amount": 1,
        "run_purpose": "not_allowed_value",
    }
    v = validate_launch_request(ROOT, body)
    assert v["valid"] is False
    assert any("run_purpose" in e.lower() for e in v["errors"])


def test_build_launcher_options_includes_scan_rules() -> None:
    opts = build_launcher_options(ROOT)
    assert "momentum_volume_pressure" in opts["available_rules"]
    assert set(opts["allowed_run_purpose"]) == ALLOWED_RUN_PURPOSES


def test_execute_launch_rejected_returns_without_side_effects(tmp_path: Path) -> None:
    body = {"mode": "fixture", "provider": "yfinance"}
    out = execute_launch(tmp_path / "missing_repo_root", body)
    assert out["accepted"] is False
    assert out["status"] == "rejected"


def test_load_launcher_status_missing(tmp_path: Path) -> None:
    assert load_launcher_status(tmp_path, "nope") is None


def test_fixture_launch_writes_request_with_safe_trading_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[list[str]] = []

    def fake_check_call(argv: list[str], cwd: str | None = None) -> None:
        recorded.append(list(argv))

    monkeypatch.setattr("acquisition.run_launcher.subprocess.check_call", fake_check_call)

    run_id = "pytest_launcher_mock_only"
    body = {
        "mode": "fixture",
        "provider": "fixture",
        "start_date": "2026-01-01",
        "end_date": "2026-01-10",
        "as_of_date": "2026-01-08",
        "review_date": "2026-01-08",
        "rule": "momentum_volume_pressure",
        "basket_name": "mock_basket",
        "amount": 500,
        "run_id": run_id,
        "run_purpose": "paper_research",
    }
    out = execute_launch(ROOT, body)
    assert out["accepted"] is True
    assert out["run_id"] == run_id

    req_path = ROOT / "app" / "data" / "acquisition_runs" / run_id / "launcher_request.json"
    data = json.loads(req_path.read_text(encoding="utf-8"))
    assert data["trading_enabled"] is False
    assert data["live_orders_enabled"] is False
    assert data["paper_only"] is True
    assert data["run_purpose"] == "paper_research"

    assert recorded, "expected mocked subprocess calls"
    acquire_argv = next(a for a in recorded if "acquire_openbb_prices.py" in a[-1] or "acquire_openbb_prices.py" in str(a))
    assert "--fixture" in acquire_argv

    # Cleanup generated run folder for local hygiene
    import shutil

    shutil.rmtree(ROOT / "app" / "data" / "acquisition_runs" / run_id, ignore_errors=True)
    raw_csv = ROOT / "app" / "data" / "raw" / f"launcher_{run_id}_prices.csv"
    if raw_csv.is_file():
        raw_csv.unlink()
