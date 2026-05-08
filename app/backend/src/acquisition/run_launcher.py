"""Governed local run launcher (fixture / dry-run / live). No broker APIs."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from .launcher_trading_scope import (
    ALLOWED_RUN_PURPOSES,
    merge_launcher_request_payload,
    merge_launcher_status_payload,
)
from .provider_registry import SUPPORTED_PROVIDERS

LAUNCH_MODES = frozenset({"fixture", "dry_run", "live"})
FIXTURE_DEFAULT_START = "2026-01-01"
FIXTURE_DEFAULT_END = "2026-01-10"

_RUN_ID_SAFE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,127}$")


def _rules_path(repo_root: Path) -> Path:
    return repo_root / "app" / "backend" / "src" / "core" / "config" / "pattern_rules.yaml"


def load_scan_rule_names(repo_root: Path) -> list[str]:
    p = _rules_path(repo_root)
    if not p.is_file():
        return []
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    return sorted(str(k) for k in data.keys() if isinstance(k, str))


def parse_symbols_csv(raw: str | None) -> list[str]:
    if not raw or not str(raw).strip():
        return []
    return [tok.strip() for tok in str(raw).split(",") if tok.strip()]


def generate_run_id() -> str:
    return f"launcher_{uuid.uuid4().hex[:12]}"


def build_launcher_options(repo_root: Path) -> dict[str, Any]:
    return {
        "available_providers": sorted(SUPPORTED_PROVIDERS),
        "available_modes": sorted(LAUNCH_MODES),
        "available_rules": load_scan_rule_names(repo_root),
        "allowed_run_purpose": sorted(ALLOWED_RUN_PURPOSES),
        "default_dates_fixture": {"start_date": FIXTURE_DEFAULT_START, "end_date": FIXTURE_DEFAULT_END},
        "default_fixture_relative_paths": {
            "fixture": "tests/fixtures/openbb_historical_sample.json",
            "market_cap_fixture": "tests/fixtures/openbb_market_cap_sample.json",
        },
        "warnings": [
            "Live smoke mode proves connectivity only. It does not prove broad coverage or strategy quality.",
            "Do not treat launcher output as trading advice.",
        ],
    }


def _validate_iso_date(label: str, value: str | None) -> list[str]:
    errs: list[str] = []
    if not value or not str(value).strip():
        errs.append(f"{label} is required")
        return errs
    try:
        datetime.strptime(str(value).strip()[:10], "%Y-%m-%d")
    except ValueError:
        errs.append(f"{label} must be a valid ISO date (YYYY-MM-DD)")
    return errs


def validate_launch_request(repo_root: Path, body: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    mode = str(body.get("mode") or "").strip()
    if mode not in LAUNCH_MODES:
        errors.append(f"mode must be one of: {', '.join(sorted(LAUNCH_MODES))}")

    provider = str(body.get("provider") or "").strip()
    if not provider:
        errors.append("provider is required")
    elif provider not in SUPPORTED_PROVIDERS:
        errors.append(f"provider must be one of: {', '.join(sorted(SUPPORTED_PROVIDERS))}")

    rp = str(body.get("run_purpose") or "research").strip()
    if rp and rp not in ALLOWED_RUN_PURPOSES:
        errors.append(f"run_purpose must be one of: {', '.join(sorted(ALLOWED_RUN_PURPOSES))}")

    if mode == "fixture" and provider != "fixture":
        errors.append("fixture mode requires provider=fixture")

    if mode == "live" and provider == "fixture":
        errors.append("live mode cannot use provider=fixture")

    rule = str(body.get("rule") or "").strip()
    rules = load_scan_rule_names(repo_root)
    if not rule:
        errors.append("rule is required")
    elif rule not in rules:
        errors.append(f"rule must be a configured scan rule; known: {', '.join(rules)}")

    basket_name = str(body.get("basket_name") or "").strip()
    if not basket_name:
        errors.append("basket_name is required")

    start_date = str(body.get("start_date") or "").strip()
    end_date = str(body.get("end_date") or "").strip()
    errors.extend(_validate_iso_date("start_date", start_date))
    errors.extend(_validate_iso_date("end_date", end_date))

    as_of_date = str(body.get("as_of_date") or "").strip()
    review_date = str(body.get("review_date") or "").strip()
    errors.extend(_validate_iso_date("as_of_date", as_of_date))
    errors.extend(_validate_iso_date("review_date", review_date))

    try:
        amount = float(body.get("amount"))
        if not (amount > 0) or amount != amount:
            raise ValueError
    except (TypeError, ValueError):
        errors.append("amount must be a positive number")

    symbols = parse_symbols_csv(body.get("symbols") if isinstance(body.get("symbols"), str) else None)
    if mode == "live" and not symbols:
        errors.append("live mode requires non-empty symbols (comma-separated)")

    run_id_in = str(body.get("run_id") or "").strip()
    planned_run_id = run_id_in if run_id_in else generate_run_id()
    if run_id_in and not _RUN_ID_SAFE.match(run_id_in):
        errors.append("run_id must be alphanumeric with ._- only, max 128 chars")

    if mode == "live":
        warnings.append(build_launcher_options(repo_root)["warnings"][0])

    expected_artifacts = [
        f"app/data/acquisition_runs/{planned_run_id}/launcher_request.json",
        f"app/data/acquisition_runs/{planned_run_id}/launcher_status.json",
        f"app/data/acquisition_runs/{planned_run_id}/acquisition_plan.json",
        f"app/data/acquisition_runs/{planned_run_id}/acquisition_result.json",
    ]
    if mode != "dry_run":
        expected_artifacts.append(f"app/data/acquisition_runs/{planned_run_id}/pipeline_terminal_status.json")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "planned_run_id": planned_run_id,
        "expected_artifacts": expected_artifacts,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _amount_str(amount: float) -> str:
    if amount == int(amount):
        return str(int(amount))
    return str(amount)


def execute_launch(
    repo_root: Path,
    body: dict[str, Any],
    *,
    viewer_base_path: str = "/run-viewer",
) -> dict[str, Any]:
    """Run governed acquisition (+ pipeline when applicable). Synchronous."""
    val = validate_launch_request(repo_root, body)
    if not val["valid"]:
        return {
            "accepted": False,
            "run_id": val.get("planned_run_id", ""),
            "status": "rejected",
            "run_dir": "",
            "viewer_url": "",
            "errors": val["errors"],
            "warnings": val["warnings"],
        }

    run_id = val["planned_run_id"]
    mode = str(body["mode"]).strip()
    provider = str(body["provider"]).strip()
    start_date = str(body["start_date"]).strip()
    end_date = str(body["end_date"]).strip()
    as_of_date = str(body["as_of_date"]).strip()
    review_date = str(body["review_date"]).strip()
    rule = str(body["rule"]).strip()
    basket_name = str(body["basket_name"]).strip()
    amount = float(body["amount"])
    symbols = parse_symbols_csv(body.get("symbols") if isinstance(body.get("symbols"), str) else None)
    run_purpose_in = str(body.get("run_purpose") or "research").strip()

    run_dir = repo_root / "app" / "data" / "acquisition_runs" / run_id
    out_name = f"launcher_{run_id}_prices.csv"
    output_rel = f"app/data/raw/{out_name}"
    viewer_url = f"{viewer_base_path}?run_id={run_id}"

    opts = build_launcher_options(repo_root)
    fixture_rel = opts["default_fixture_relative_paths"]["fixture"]
    mcap_rel = opts["default_fixture_relative_paths"]["market_cap_fixture"]
    fixture_path_str = str(body.get("fixture_path") or "").strip() or fixture_rel
    mcap_path_str = str(body.get("market_cap_fixture") or "").strip() or mcap_rel

    symbol_source = "launcher_symbols_arg" if symbols else "fixture_inference_or_empty"

    if mode == "dry_run" and not symbols:
        symbols = ["TEST_A"]
        symbol_source = "launcher_default_synthetic"

    trading_req = merge_launcher_request_payload({"run_purpose": run_purpose_in})

    req_core: dict[str, Any] = {
        "run_id": run_id,
        "created_at": _utc_now(),
        "mode": mode,
        "provider": provider,
        "symbols": symbols,
        "symbol_source": symbol_source,
        "start_date": start_date,
        "end_date": end_date,
        "as_of_date": as_of_date,
        "review_date": review_date,
        "rule": rule,
        "basket_name": basket_name,
        "amount": amount,
        "fixture_path": fixture_path_str if mode == "fixture" else None,
        "market_cap_fixture": mcap_path_str if mode == "fixture" else None,
        "requested_by": "local_user",
        "full_coverage_claimed": False,
        "output_csv_relative": output_rel,
    }
    launcher_request = {**req_core, **trading_req}
    _write_json(run_dir / "launcher_request.json", launcher_request)

    py = sys.executable
    scripts = repo_root / "app" / "scripts"
    commands: list[str] = []

    errors: list[str] = []
    warnings: list[str] = list(val.get("warnings") or [])
    if mode == "live":
        warnings.append(opts["warnings"][0])

    trading_status_base = merge_launcher_status_payload({"run_purpose": run_purpose_in})

    def base_status() -> dict[str, Any]:
        return {
            **trading_status_base,
            "run_id": run_id,
            "status": "running",
            "started_at": _utc_now(),
            "completed_at": "",
            "commands_or_functions_called": [],
            "acquisition_status": "UNKNOWN",
            "validation_status": "UNKNOWN",
            "scan_status": "UNKNOWN",
            "basket_status": "UNKNOWN",
            "review_status": "UNKNOWN",
            "overall_pipeline_status": "UNKNOWN",
            "terminal_status_path": str(run_dir / "pipeline_terminal_status.json"),
            "acquisition_result_path": str(run_dir / "acquisition_result.json"),
            "launcher_request_path": str(run_dir / "launcher_request.json"),
            "launcher_status_path": str(run_dir / "launcher_status.json"),
            "viewer_url": viewer_url,
            "errors": [],
            "warnings": [],
        }

    status = base_status()
    _write_json(run_dir / "launcher_status.json", status)

    def run_cmd(argv: list[str]) -> None:
        commands.append(" ".join(argv))
        subprocess.check_call(argv, cwd=str(repo_root))

    try:
        if mode == "fixture":
            acq = [
                py,
                str(scripts / "acquire_openbb_prices.py"),
                "--provider",
                "fixture",
                "--start-date",
                start_date,
                "--end-date",
                end_date,
                "--output",
                output_rel,
                "--run-id",
                run_id,
                "--mode",
                "fixture",
                "--fixture",
                fixture_path_str,
                "--market-cap-fixture",
                mcap_path_str,
            ]
            if symbols:
                acq.extend(["--symbols", ",".join(symbols)])
            run_cmd(acq)

            ar_path = run_dir / "acquisition_result.json"
            acquisition_ready = False
            if ar_path.is_file():
                acquisition_ready = bool(json.loads(ar_path.read_text(encoding="utf-8")).get("ready_for_pipeline"))

            status["commands_or_functions_called"] = commands
            status["acquisition_status"] = "PASS"

            if acquisition_ready:
                pipe = [
                    py,
                    str(scripts / "run_openbb_acquired_pipeline.py"),
                    "--provider",
                    "fixture",
                    "--start-date",
                    start_date,
                    "--end-date",
                    end_date,
                    "--as-of",
                    as_of_date,
                    "--rule",
                    rule,
                    "--basket-name",
                    basket_name,
                    "--amount",
                    _amount_str(amount),
                    "--review-date",
                    review_date,
                    "--run-id",
                    run_id,
                    "--output",
                    output_rel,
                    "--fixture",
                    fixture_path_str,
                ]
                if symbols:
                    pipe.extend(["--symbols", ",".join(symbols)])
                run_cmd(pipe)
                status["validation_status"] = "PASS"
                term_file = run_dir / "pipeline_terminal_status.json"
                if term_file.is_file():
                    term = json.loads(term_file.read_text(encoding="utf-8"))
                    status["scan_status"] = term.get("scan_status", "UNKNOWN")
                    status["basket_status"] = term.get("basket_status", "UNKNOWN")
                    status["review_status"] = term.get("review_status", "UNKNOWN")
                    status["overall_pipeline_status"] = term.get("overall_pipeline_status", "UNKNOWN")
                else:
                    status["validation_status"] = "UNKNOWN"
                    status["overall_pipeline_status"] = "UNKNOWN"
            else:
                status["validation_status"] = "NOT_RUN"
                status["scan_status"] = "NOT_RUN"
                status["basket_status"] = "NOT_RUN"
                status["review_status"] = "NOT_RUN"
                status["overall_pipeline_status"] = "PIPELINE_SKIPPED_NOT_READY"
                warnings.append("Acquisition marked ready_for_pipeline=false; pipeline not started.")

        elif mode == "dry_run":
            acq = [
                py,
                str(scripts / "acquire_openbb_prices.py"),
                "--provider",
                provider,
                "--start-date",
                start_date,
                "--end-date",
                end_date,
                "--output",
                output_rel,
                "--run-id",
                run_id,
                "--mode",
                "dry-run",
                "--symbols",
                ",".join(symbols),
            ]
            run_cmd(acq)
            status["commands_or_functions_called"] = commands
            status["acquisition_status"] = "PASS"
            status["validation_status"] = "NOT_RUN"
            status["scan_status"] = "NOT_RUN"
            status["basket_status"] = "NOT_RUN"
            status["review_status"] = "NOT_RUN"
            status["overall_pipeline_status"] = "ACQUISITION_PROVENANCE_ONLY"

        elif mode == "live":
            acq = [
                py,
                str(scripts / "acquire_openbb_prices.py"),
                "--provider",
                provider,
                "--start-date",
                start_date,
                "--end-date",
                end_date,
                "--output",
                output_rel,
                "--run-id",
                run_id,
                "--mode",
                "live",
                "--symbols",
                ",".join(symbols),
            ]
            run_cmd(acq)
            status["commands_or_functions_called"] = commands
            status["acquisition_status"] = "PASS"

            ar_path = run_dir / "acquisition_result.json"
            res_data = json.loads(ar_path.read_text(encoding="utf-8")) if ar_path.is_file() else {}
            acquisition_ready = bool(res_data.get("ready_for_pipeline"))

            if acquisition_ready:
                pipe = [
                    py,
                    str(scripts / "run_openbb_acquired_pipeline.py"),
                    "--provider",
                    provider,
                    "--start-date",
                    start_date,
                    "--end-date",
                    end_date,
                    "--as-of",
                    as_of_date,
                    "--rule",
                    rule,
                    "--basket-name",
                    basket_name,
                    "--amount",
                    _amount_str(amount),
                    "--review-date",
                    review_date,
                    "--run-id",
                    run_id,
                    "--output",
                    output_rel,
                    "--symbols",
                    ",".join(symbols),
                ]
                run_cmd(pipe)
                status["validation_status"] = "PASS"
                term_file = run_dir / "pipeline_terminal_status.json"
                if term_file.is_file():
                    term = json.loads(term_file.read_text(encoding="utf-8"))
                    status["scan_status"] = term.get("scan_status", "UNKNOWN")
                    status["basket_status"] = term.get("basket_status", "UNKNOWN")
                    status["review_status"] = term.get("review_status", "UNKNOWN")
                    status["overall_pipeline_status"] = term.get("overall_pipeline_status", "UNKNOWN")
            else:
                status["validation_status"] = "NOT_RUN"
                status["scan_status"] = "NOT_RUN"
                status["basket_status"] = "NOT_RUN"
                status["review_status"] = "NOT_RUN"
                status["overall_pipeline_status"] = "PIPELINE_SKIPPED_NOT_READY"
                warnings.append("Acquisition marked ready_for_pipeline=false; pipeline not started.")

        status["status"] = "completed"
        status["completed_at"] = _utc_now()
        status["errors"] = errors
        status["warnings"] = warnings
        status.update(merge_launcher_status_payload({"run_purpose": run_purpose_in}))
        _write_json(run_dir / "launcher_status.json", status)

        return {
            "accepted": True,
            "run_id": run_id,
            "status": "completed",
            "run_dir": str(run_dir),
            "viewer_url": viewer_url,
            "errors": errors,
            "warnings": warnings,
        }

    except subprocess.CalledProcessError as exc:
        errors.append(f"Command failed with exit code {exc.returncode}")
        status["status"] = "failed"
        status["completed_at"] = _utc_now()
        status["errors"] = errors
        status["warnings"] = warnings
        status["acquisition_status"] = "FAIL"
        status.update(merge_launcher_status_payload({"run_purpose": run_purpose_in}))
        _write_json(run_dir / "launcher_status.json", status)
        return {
            "accepted": False,
            "run_id": run_id,
            "status": "failed",
            "run_dir": str(run_dir),
            "viewer_url": viewer_url,
            "errors": errors,
            "warnings": warnings,
        }
    except Exception as exc:
        errors.append(str(exc))
        status["status"] = "failed"
        status["completed_at"] = _utc_now()
        status["errors"] = errors
        status["warnings"] = warnings
        status.update(merge_launcher_status_payload({"run_purpose": run_purpose_in}))
        _write_json(run_dir / "launcher_status.json", status)
        return {
            "accepted": False,
            "run_id": run_id,
            "status": "failed",
            "run_dir": str(run_dir),
            "viewer_url": viewer_url,
            "errors": errors,
            "warnings": warnings,
        }


def load_launcher_status(repo_root: Path, run_id: str) -> dict[str, Any] | None:
    p = repo_root / "app" / "data" / "acquisition_runs" / run_id / "launcher_status.json"
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
