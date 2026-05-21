"""Read-only helpers for acquisition/pipeline run inspection."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

_SELECTED_COLUMN_ORDER = [
    "symbol",
    "score",
    "_score",
    "prior_5d_return_pct",
    "volume_surge",
    "close_location_value",
    "close_weak_flag",
    "blowoff_flag",
    "market_cap_missing_flag",
    "scan_reason",
    "rule",
    "as_of",
    "status",
    "insufficient_evidence",
    "missing_required_ohlcv",
    "market_cap_value",
]

_REJECTED_COLUMN_ORDER = [
    "symbol",
    "rejection_reason",
    "failed_rule",
    "scan_reason",
    "rule",
    "prior_5d_return_pct",
    "volume_surge",
    "close_location_value",
    "close_weak_flag",
    "blowoff_flag",
    "market_cap_missing_flag",
    "as_of",
    "status",
]

MSG_EVIDENCE_NOT_LINKED = "not linked to run_id"
MSG_RECEIPT_NOT_LINKED = "not linked to run_id"


def list_run_ids(repo_root: Path) -> list[str]:
    runs_dir = repo_root / "app" / "data" / "acquisition_runs"
    if not runs_dir.is_dir():
        return []
    return sorted([p.name for p in runs_dir.iterdir() if p.is_dir()])


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _csv_count(path: Path) -> int | None:
    if not path.is_file():
        return None
    return int(pd.read_csv(path).shape[0])


def _json_safe_value(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val
    if isinstance(val, (int,)):
        return int(val)
    if isinstance(val, float):
        if math.isnan(val):
            return None
        return float(val)
    try:
        if pd.isna(val):
            return None
    except (ValueError, TypeError):
        pass
    if hasattr(val, "item"):
        try:
            return _json_safe_value(val.item())
        except Exception:
            return str(val)
    return str(val)


def _order_columns(columns: list[str], preferred: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for key in preferred:
        if key in columns and key not in seen:
            out.append(key)
            seen.add(key)
    for key in columns:
        if key not in seen:
            out.append(key)
            seen.add(key)
    return out


def _dataframe_to_records(df: pd.DataFrame) -> tuple[list[str], list[dict[str, Any]]]:
    columns = list(df.columns)
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        rec: dict[str, Any] = {}
        for col in columns:
            rec[col] = _json_safe_value(row[col])
        rows.append(rec)
    return columns, rows


def _resolve_parquet_path(
    repo_root: Path,
    terminal: dict[str, Any],
    path_key: str,
    fallback_relative: str,
) -> tuple[Path | None, list[str]]:
    """Pick first existing path from terminal absolute path or curated fallback using terminal as_of."""
    tried: list[str] = []
    raw = terminal.get(path_key)
    if raw:
        p = Path(str(raw))
        if not p.is_absolute():
            p = (repo_root / raw).resolve()
        tried.append(str(p))
        if p.is_file():
            return p, tried

    as_of = terminal.get("as_of")
    if as_of:
        fb = repo_root / "app" / "data" / "curated" / fallback_relative.format(as_of=as_of)
        tried.append(str(fb))
        if fb.is_file():
            return fb, tried

    return None, tried


def load_parquet_candidate_artifact(
    repo_root: Path,
    terminal: dict[str, Any] | None,
    *,
    kind: str,
) -> dict[str, Any]:
    """Load selected or rejected candidates from parquet; paths come from terminal or curated fallback."""
    terminal = terminal or {}
    if kind == "selected":
        path_key = "candidates_path"
        fallback = "candidates_{as_of}.parquet"
        preferred = _SELECTED_COLUMN_ORDER
    elif kind == "rejected":
        path_key = "rejected_candidates_path"
        fallback = "rejected_candidates_{as_of}.parquet"
        preferred = _REJECTED_COLUMN_ORDER
    else:
        raise ValueError(f"unknown kind: {kind}")

    resolved, tried = _resolve_parquet_path(repo_root, terminal, path_key, fallback)
    if resolved is None:
        return {
            "artifact_path": str(terminal.get(path_key) or ""),
            "resolved_path": "",
            "columns": [],
            "rows": [],
            "error": (
                "Candidate parquet not found. Checked pipeline_terminal_status paths and "
                f"app/data/curated fallback for as_of. Attempted: {tried}"
            ),
        }

    try:
        df = pd.read_parquet(resolved)
    except Exception as exc:
        return {
            "artifact_path": str(resolved),
            "resolved_path": str(resolved),
            "columns": [],
            "rows": [],
            "error": f"Failed to read parquet: {exc}",
        }

    cols, rows = _dataframe_to_records(df)
    if kind == "selected":
        for r in rows:
            if r.get("_score") is not None and r.get("score") is None:
                r["score"] = r["_score"]
        cols = list(rows[0].keys()) if rows else cols
        cols = _order_columns(cols, _SELECTED_COLUMN_ORDER)
    else:
        for r in rows:
            if r.get("scan_reason") is not None and r.get("rejection_reason") is None:
                r["rejection_reason"] = r["scan_reason"]
            if r.get("rule") is not None and r.get("failed_rule") is None:
                r["failed_rule"] = r["rule"]
        cols = list(rows[0].keys()) if rows else cols
        cols = _order_columns(cols, _REJECTED_COLUMN_ORDER)

    ordered_rows: list[dict[str, Any]] = []
    for r in rows:
        ordered_rows.append({c: r.get(c) for c in cols})

    return {
        "artifact_path": str(terminal.get(path_key) or ""),
        "resolved_path": str(resolved),
        "columns": cols,
        "rows": ordered_rows,
        "error": None,
    }


def load_frozen_basket_detail(
    repo_root: Path,
    *,
    terminal: dict[str, Any] | None,
    launcher_request: dict[str, Any] | None,
    overall_pipeline_status: str | None,
    no_candidates_message: str | None,
) -> dict[str, Any]:
    terminal = terminal or {}
    lr = launcher_request or {}

    if overall_pipeline_status == "COMPLETE_NO_CANDIDATES":
        return {
            "status": "no_basket",
            "message": no_candidates_message
            or "No basket was generated because no candidates passed the configured scan rule.",
        }

    if not terminal.get("basket_frozen"):
        bs = str(terminal.get("basket_status") or "")
        if bs.startswith("NOT_RUN") or "NO_CANDIDATES" in bs:
            return {
                "status": "not_run",
                "message": terminal.get("reason") or "Basket freeze did not run for this pipeline state.",
            }
        return {
            "status": "no_basket",
            "message": terminal.get("reason") or "Basket was not marked frozen in terminal status.",
        }

    basket_name = lr.get("basket_name")
    as_of = terminal.get("as_of")
    if not basket_name or not as_of:
        return {
            "status": "missing_metadata",
            "message": "Cannot locate basket JSON: launcher_request.json missing basket_name or terminal missing as_of.",
        }

    basket_path = repo_root / "app" / "data" / "baskets" / f"{basket_name}_{as_of}.json"
    if not basket_path.is_file():
        return {
            "status": "artifact_missing",
            "expected_path": str(basket_path),
            "message": f"Frozen basket JSON not found at expected path: {basket_path}",
        }

    payload = _read_json(basket_path)
    return {"status": "ok", "artifact_path": str(basket_path), "basket": payload}


def load_review_result_detail(
    repo_root: Path,
    *,
    terminal: dict[str, Any] | None,
    launcher_request: dict[str, Any] | None,
    overall_pipeline_status: str | None,
    no_candidates_message: str | None,
) -> dict[str, Any]:
    terminal = terminal or {}
    lr = launcher_request or {}

    if overall_pipeline_status == "COMPLETE_NO_CANDIDATES":
        return {
            "status": "not_run",
            "message": no_candidates_message
            or "Review was not generated because no candidates passed the configured scan rule.",
        }

    if not terminal.get("review_generated"):
        return {
            "status": "not_run",
            "message": terminal.get("reason") or "Review output was not generated for this run.",
        }

    basket_name = lr.get("basket_name")
    review_date = lr.get("review_date")
    if not basket_name or not review_date:
        return {
            "status": "missing_metadata",
            "message": "Cannot locate review JSON: launcher_request.json missing basket_name or review_date.",
        }

    review_path = repo_root / "app" / "data" / "baskets" / f"{basket_name}_review_{review_date}.json"
    if not review_path.is_file():
        return {
            "status": "artifact_missing",
            "expected_path": str(review_path),
            "message": f"Review JSON not found at expected path: {review_path}",
        }

    payload = _read_json(review_path)
    return {"status": "ok", "artifact_path": str(review_path), "review": payload}


def build_terminal_status_detail(terminal: dict[str, Any] | None) -> dict[str, Any]:
    if not terminal:
        return {
            "missing": True,
            "message": "pipeline_terminal_status.json is missing or unreadable.",
            "pipeline_fields": {},
            "errors_list": [],
            "warnings_list": [],
            "full_terminal": {},
        }

    pipeline_fields = {
        "acquisition_status": terminal.get("acquisition_status"),
        "validation_status": terminal.get("validation_status"),
        "scan_status": terminal.get("scan_status"),
        "basket_status": terminal.get("basket_status"),
        "review_status": terminal.get("review_status"),
        "overall_pipeline_status": terminal.get("overall_pipeline_status"),
    }

    err_raw = terminal.get("errors")
    warn_raw = terminal.get("warnings")
    errors_list = err_raw if isinstance(err_raw, list) else ([err_raw] if err_raw not in (None, "") else [])
    warnings_list = warn_raw if isinstance(warn_raw, list) else ([warn_raw] if warn_raw not in (None, "") else [])

    return {
        "missing": False,
        "message": "",
        "pipeline_fields": pipeline_fields,
        "errors_list": errors_list,
        "warnings_list": warnings_list,
        "full_terminal": terminal,
    }


def _collect_str_list(payload: dict[str, Any] | None, *keys: str) -> list[str]:
    if not payload:
        return []
    out: list[str] = []
    for key in keys:
        val = payload.get(key)
        if val is None:
            continue
        if isinstance(val, str) and val.strip():
            out.append(val.strip())
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip())
    seen: set[str] = set()
    deduped: list[str] = []
    for p in out:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    return deduped


def _resolve_repo_path(repo_root: Path, raw: str) -> Path:
    p = Path(raw)
    if p.is_absolute():
        return p
    return (repo_root / raw).resolve()


def _resolve_governance(
    repo_root: Path,
    run_id: str,
    run_dir: Path,
    terminal: dict[str, Any] | None,
    manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve governance evidence/receipt paths without silent guessing."""
    gl_file = _read_json(run_dir / "governance_links.json")
    central_path = repo_root / "agent_workspace" / "run_viewer_governance_map.json"
    central = _read_json(central_path) if central_path.is_file() else None
    central_run = (central or {}).get("by_run_id", {}).get(run_id) if isinstance((central or {}).get("by_run_id"), dict) else None

    evidence_raw = (
        _collect_str_list(terminal, "governance_evidence_folders", "governance_evidence_folder")
        + _collect_str_list(manifest, "governance_evidence_folders", "governance_evidence_folder")
        + _collect_str_list(gl_file, "evidence_folders", "evidence_folder")
        + _collect_str_list(central_run if isinstance(central_run, dict) else None, "evidence_folders", "evidence_folder")
    )
    receipt_raw = (
        _collect_str_list(terminal, "governance_receipt_files", "governance_receipt_file")
        + _collect_str_list(manifest, "governance_receipt_files", "governance_receipt_file")
        + _collect_str_list(gl_file, "receipt_files", "receipt_file")
        + _collect_str_list(central_run if isinstance(central_run, dict) else None, "receipt_files", "receipt_file")
    )

    evidence_entries: list[dict[str, Any]] = []
    for raw in evidence_raw:
        resolved = _resolve_repo_path(repo_root, raw)
        evidence_entries.append(
            {
                "path": str(resolved),
                "exists": resolved.is_dir(),
            }
        )

    receipt_entries: list[dict[str, Any]] = []
    for raw in receipt_raw:
        resolved = _resolve_repo_path(repo_root, raw)
        receipt_entries.append(
            {
                "path": str(resolved),
                "exists": resolved.is_file(),
            }
        )

    gov_limitations: list[str] = []
    if not evidence_raw and not receipt_raw:
        gov_limitations.append(
            "Governance evidence/receipt paths are not recorded for this run_id "
            "(no entries in pipeline_terminal_status.json, manifest, governance_links.json, or run_viewer_governance_map.json)."
        )

    def build_side(
        *,
        entries: list[dict[str, Any]],
        raw_count: int,
        not_linked_msg: str,
        is_dir: bool,
    ) -> dict[str, Any]:
        if raw_count == 0:
            return {
                "link_status": "not_recorded",
                "entries": [],
                "primary_display": not_linked_msg,
            }
        existing = [e for e in entries if e["exists"]]
        missing = [e for e in entries if not e["exists"]]
        if existing and not missing:
            link_status = "linked"
        elif existing and missing:
            link_status = "partial"
        else:
            link_status = "missing_paths"
            gov_limitations.append(
                "Governance paths were recorded but none resolve to existing "
                + ("directories" if is_dir else "files")
                + " on disk."
            )
        primary = existing[0]["path"] if existing else (entries[0]["path"] if entries else not_linked_msg)
        return {
            "link_status": link_status,
            "entries": entries,
            "primary_display": primary if isinstance(primary, str) else str(primary),
        }

    evidence_gov = build_side(
        entries=evidence_entries,
        raw_count=len(evidence_raw),
        not_linked_msg=MSG_EVIDENCE_NOT_LINKED,
        is_dir=True,
    )
    receipt_gov = build_side(
        entries=receipt_entries,
        raw_count=len(receipt_raw),
        not_linked_msg=MSG_RECEIPT_NOT_LINKED,
        is_dir=False,
    )

    return {
        "evidence": evidence_gov,
        "receipt": receipt_gov,
        "limitations": gov_limitations,
    }


def _artifact_paths(
    repo_root: Path,
    run_id: str,
    governance: dict[str, Any],
) -> dict[str, str]:
    """Artifact paths for UI; evidence_folder and receipt_file are explicit (never vague '--')."""
    run_dir = repo_root / "app" / "data" / "acquisition_runs" / run_id
    ev_gov = governance["evidence"]
    rc_gov = governance["receipt"]

    def legacy_evidence_path() -> str | None:
        p = repo_root / "agent_workspace" / "evidence" / run_id
        return str(p) if p.is_dir() else None

    def legacy_receipt_path() -> str | None:
        md = repo_root / "agent_workspace" / "receipts" / f"{run_id}.md"
        js = repo_root / "agent_workspace" / "receipts" / f"{run_id}.json"
        if md.is_file():
            return str(md)
        if js.is_file():
            return str(js)
        return None

    evidence_display = ev_gov["primary_display"]
    if ev_gov["link_status"] == "not_recorded":
        leg = legacy_evidence_path()
        evidence_display = leg if leg else MSG_EVIDENCE_NOT_LINKED

    receipt_display = rc_gov["primary_display"]
    if rc_gov["link_status"] == "not_recorded":
        leg = legacy_receipt_path()
        receipt_display = leg if leg else MSG_RECEIPT_NOT_LINKED

    return {
        "run_dir": str(run_dir) if run_dir.is_dir() else "",
        "acquisition_plan_json": str(run_dir / "acquisition_plan.json")
        if (run_dir / "acquisition_plan.json").is_file()
        else "",
        "acquisition_result_json": str(run_dir / "acquisition_result.json")
        if (run_dir / "acquisition_result.json").is_file()
        else "",
        "openbb_acquisition_manifest_json": str(run_dir / "openbb_acquisition_manifest.json")
        if (run_dir / "openbb_acquisition_manifest.json").is_file()
        else "",
        "openbb_source_log_json": str(run_dir / "openbb_source_log.json")
        if (run_dir / "openbb_source_log.json").is_file()
        else "",
        "openbb_normalized_prices_csv": str(run_dir / "openbb_normalized_prices.csv")
        if (run_dir / "openbb_normalized_prices.csv").is_file()
        else "",
        "openbb_skipped_symbols_csv": str(run_dir / "openbb_skipped_symbols.csv")
        if (run_dir / "openbb_skipped_symbols.csv").is_file()
        else "",
        "openbb_rejected_rows_csv": str(run_dir / "openbb_rejected_rows.csv")
        if (run_dir / "openbb_rejected_rows.csv").is_file()
        else "",
        "pipeline_terminal_status_json": str(run_dir / "pipeline_terminal_status.json")
        if (run_dir / "pipeline_terminal_status.json").is_file()
        else "",
        "governance_links_json": str(run_dir / "governance_links.json")
        if (run_dir / "governance_links.json").is_file()
        else "",
        "launcher_request_json": str(run_dir / "launcher_request.json")
        if (run_dir / "launcher_request.json").is_file()
        else "",
        "launcher_status_json": str(run_dir / "launcher_status.json")
        if (run_dir / "launcher_status.json").is_file()
        else "",
        "evidence_folder": evidence_display,
        "receipt_file": receipt_display,
    }


def load_run_summary(repo_root: Path, run_id: str) -> dict[str, Any]:
    run_dir = repo_root / "app" / "data" / "acquisition_runs" / run_id
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run not found: {run_id}")

    plan = _read_json(run_dir / "acquisition_plan.json")
    launcher_request = _read_json(run_dir / "launcher_request.json")
    result = _read_json(run_dir / "acquisition_result.json")
    manifest = _read_json(run_dir / "openbb_acquisition_manifest.json")
    source_log = _read_json(run_dir / "openbb_source_log.json")
    terminal = _read_json(run_dir / "pipeline_terminal_status.json")

    governance = _resolve_governance(repo_root, run_id, run_dir, terminal, manifest)
    paths = _artifact_paths(repo_root, run_id, governance)

    optional_path_keys = {
        "evidence_folder",
        "receipt_file",
        "governance_links_json",
        "launcher_request_json",
        "launcher_status_json",
    }
    missing_artifacts = [
        name
        for name, value in paths.items()
        if name not in optional_path_keys and not value
    ]
    skipped_count = _csv_count(run_dir / "openbb_skipped_symbols.csv")
    rejected_count = _csv_count(run_dir / "openbb_rejected_rows.csv")
    normalized_count = _csv_count(run_dir / "openbb_normalized_prices.csv")

    provider = (result or {}).get("provider_used") or (manifest or {}).get("provider") or (source_log or {}).get("provider")
    start_date = (manifest or {}).get("start_date") or (source_log or {}).get("start_date") or (plan or {}).get("start_date")
    end_date = (manifest or {}).get("end_date") or (source_log or {}).get("end_date") or (plan or {}).get("end_date")
    symbols_requested = (result or {}).get("symbols_requested") or (source_log or {}).get("symbols_requested") or []
    symbols_returned = (result or {}).get("symbols_returned") or []
    symbols_skipped = (result or {}).get("symbols_skipped") or []
    limitations = list((result or {}).get("limitations") or (manifest or {}).get("limitations") or [])
    warnings = (manifest or {}).get("warnings") or []
    overall_pipeline_status = (terminal or {}).get("overall_pipeline_status")
    pipeline_status = (terminal or {}).get("pipeline_status")
    no_candidates_message = None
    if overall_pipeline_status == "COMPLETE_NO_CANDIDATES":
        no_candidates_message = (
            "This run completed successfully with zero selected candidates. "
            "No basket or review was generated because no candidates passed the configured scan rule."
        )

    limitations.extend(governance.get("limitations") or [])

    selected_candidates = load_parquet_candidate_artifact(repo_root, terminal, kind="selected")
    rejected_candidates = load_parquet_candidate_artifact(repo_root, terminal, kind="rejected")
    frozen_basket = load_frozen_basket_detail(
        repo_root,
        terminal=terminal,
        launcher_request=launcher_request,
        overall_pipeline_status=overall_pipeline_status,
        no_candidates_message=no_candidates_message,
    )
    review_result = load_review_result_detail(
        repo_root,
        terminal=terminal,
        launcher_request=launcher_request,
        overall_pipeline_status=overall_pipeline_status,
        no_candidates_message=no_candidates_message,
    )
    terminal_status_detail = build_terminal_status_detail(terminal)

    return {
        "run_id": run_id,
        "provider": provider,
        "start_date": start_date,
        "end_date": end_date,
        "symbols_requested": symbols_requested,
        "symbols_returned": symbols_returned,
        "symbols_skipped": symbols_skipped,
        "normalized_rows": (result or {}).get("rows_normalized", normalized_count),
        "rejected_rows": (result or {}).get("rejected_rows", rejected_count),
        "skipped_symbols_count": skipped_count,
        "rejected_rows_count": rejected_count,
        "candidate_count": (terminal or {}).get("selected_candidate_count"),
        "rejected_candidate_count": (terminal or {}).get("rejected_candidate_count"),
        "partial_coverage": (result or {}).get("partial_coverage"),
        "full_coverage_claimed": (result or {}).get("full_coverage_claimed"),
        "ready_for_pipeline": (result or {}).get("ready_for_pipeline"),
        "overall_pipeline_status": overall_pipeline_status,
        "pipeline_status": pipeline_status,
        "no_candidates_message": no_candidates_message,
        "source_log_rows_returned": (source_log or {}).get("rows_returned"),
        "provider_source_reference": (manifest or {}).get("provider_source_reference"),
        "limitations": limitations,
        "warnings": warnings,
        "paths": paths,
        "governance": governance,
        "missing_artifacts": missing_artifacts,
        "selected_candidates": selected_candidates,
        "rejected_candidates": rejected_candidates,
        "frozen_basket": frozen_basket,
        "review_result": review_result,
        "terminal_status_detail": terminal_status_detail,
    }
