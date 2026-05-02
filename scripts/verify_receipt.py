"""
Verify receipt JSON against tasks.yaml policy and git-reported changes in the worktree.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import fnmatch
from pathlib import Path
from typing import Any

import subprocess

import yaml

TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_task_id(task_id: str) -> None:
    if not TASK_ID_PATTERN.fullmatch(task_id):
        eprint(f"ERROR: invalid task id {task_id!r}; allowed pattern: letters, digits, underscore, dash.")
        sys.exit(1)


def load_task(repo_root: Path, task_id: str) -> dict[str, Any]:
    tasks_path = repo_root / "agent_workspace" / "tasks" / "tasks.yaml"
    if not tasks_path.is_file():
        eprint(f"ERROR: missing tasks file: {tasks_path}")
        sys.exit(1)
    try:
        data = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        eprint(f"ERROR: invalid YAML in {tasks_path}: {exc}")
        sys.exit(1)
    tasks = data.get("tasks") or []
    for t in tasks:
        if t.get("id") == task_id:
            return t
    eprint(f"ERROR: task id {task_id!r} not found in tasks.yaml")
    sys.exit(1)


def worktree_path(repo_root: Path, task_id: str) -> Path:
    return repo_root.parent / "worktrees" / f"{repo_root.name}__{task_id}"


def load_receipt(repo_root: Path, task_id: str) -> dict[str, Any]:
    path = repo_root / "agent_workspace" / "receipts" / f"{task_id}.json"
    if not path.is_file():
        eprint(f"ERROR: missing receipt: {path}")
        sys.exit(1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        eprint(f"ERROR: invalid JSON in {path}: {exc}")
        sys.exit(1)


def normalize_rel_path(p: str) -> str:
    return Path(p).as_posix().lstrip("./")


def resolve_effective_base(worktree: Path, preferred: str) -> str:
    for candidate in (preferred, "main", "master"):
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", candidate],
            cwd=worktree,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return candidate
    eprint(
        f"ERROR: base branch {preferred!r} (and fallbacks main/master) not found in {worktree}"
    )
    sys.exit(1)


def git_changed_files(worktree: Path, base_branch: str) -> list[str]:
    proc = subprocess.run(
        ["git", "diff", "--name-only", f"{base_branch}...HEAD"],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        eprint(proc.stderr.strip() or proc.stdout.strip() or "git diff failed")
        raise RuntimeError("git diff failed")
    lines = [normalize_rel_path(line) for line in proc.stdout.splitlines() if line.strip()]
    return sorted(set(lines))


def path_matches_forbidden(path: str, patterns: list[str]) -> bool:
    norm = normalize_rel_path(path)
    for pat in patterns:
        p = pat.strip()
        if not p:
            continue
        if "*" in p or "?" in p or "[" in p:
            if fnmatch.fnmatch(norm, p):
                return True
        else:
            if norm == normalize_rel_path(p):
                return True
    return False


def check_allowed_files(task: dict[str, Any], changed: set[str]) -> tuple[bool, str | None]:
    if "allowed_files" not in task:
        return True, None
    allowed = task.get("allowed_files")
    if not isinstance(allowed, list):
        return False, "allowed_files must be a list when present"
    allowed_set = {normalize_rel_path(str(x)) for x in allowed}
    if len(allowed_set) == 0 and len(changed) > 0:
        return False, "allowed_files is empty; no file changes are permitted"
    if len(allowed_set) > 0:
        for c in changed:
            if c not in allowed_set:
                return False, f"changed file not allowed by whitelist: {c}"
    return True, None


def check_forbidden_files(task: dict[str, Any], changed: set[str]) -> tuple[bool, str | None]:
    forbidden = task.get("forbidden_files") or []
    if not isinstance(forbidden, list):
        return False, "forbidden_files must be a list"
    for c in changed:
        if path_matches_forbidden(c, [str(x) for x in forbidden]):
            return False, f"forbidden file changed: {c}"
    return True, None


def check_required_evidence(repo_root: Path, task_id: str, task: dict[str, Any]) -> tuple[bool, list[str]]:
    req = task.get("required_evidence") or []
    if not isinstance(req, list):
        return False, ["required_evidence must be a list"]
    missing: list[str] = []
    ev_base = repo_root / "agent_workspace" / "evidence" / task_id
    for name in req:
        rel = str(name).strip()
        if not rel:
            continue
        p = ev_base / rel
        if not p.is_file():
            missing.append(rel)
    return len(missing) == 0, missing


def verify_task(task_id: str, base_branch: str, repo_root: Path | None = None) -> dict[str, Any]:
    repo_root = repo_root or repo_root_from_script()
    validate_task_id(task_id)
    task = load_task(repo_root, task_id)
    receipt = load_receipt(repo_root, task_id)

    failed_checks: list[str] = []

    if receipt.get("task_id") != task_id:
        failed_checks.append("receipt.task_id does not match parameter")

    wt = worktree_path(repo_root, task_id)
    if not wt.is_dir():
        failed_checks.append(f"worktree missing: {wt}")

    receipt_files_raw = receipt.get("changed_files")
    if not isinstance(receipt_files_raw, list):
        failed_checks.append("receipt.changed_files must be a list")
        receipt_paths: set[str] = set()
    else:
        receipt_paths = {normalize_rel_path(str(x)) for x in receipt_files_raw if str(x).strip()}

    actual_paths: set[str] = set()
    if wt.is_dir():
        base_use = resolve_effective_base(wt, base_branch)
        try:
            actual_list = git_changed_files(wt, base_use)
            actual_paths = set(actual_list)
        except RuntimeError:
            failed_checks.append("could not compute git changed files")

    if receipt_paths != actual_paths:
        only_actual = actual_paths - receipt_paths
        only_receipt = receipt_paths - actual_paths
        if only_actual:
            failed_checks.append(f"receipt omits changed files: {sorted(only_actual)}")
        if only_receipt:
            failed_checks.append(f"receipt lists files not changed: {sorted(only_receipt)}")

    ok_allowed, allowed_msg = check_allowed_files(task, actual_paths)
    if not ok_allowed and allowed_msg:
        failed_checks.append(allowed_msg)

    ok_forbid, forbid_msg = check_forbidden_files(task, actual_paths)
    if not ok_forbid and forbid_msg:
        failed_checks.append(forbid_msg)

    ok_ev, missing_ev = check_required_evidence(repo_root, task_id, task)
    if not ok_ev:
        failed_checks.append(f"missing required evidence: {missing_ev}")

    passed = len(failed_checks) == 0
    message = "OK" if passed else "; ".join(failed_checks)

    return {
        "task_id": task_id,
        "pass": passed,
        "message": message,
        "failed_checks": failed_checks,
        "actual_changed_files": sorted(actual_paths),
        "receipt_changed_files": sorted(receipt_paths),
        "required_evidence_checked": task.get("required_evidence") or [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify receipt and git reality for a task.")
    parser.add_argument("--task-id", required=True, help="Task id (letters, digits, underscore, dash).")
    parser.add_argument(
        "--base-branch",
        default="main",
        help="Base branch for git diff comparison (default: main).",
    )
    args = parser.parse_args()

    rr = repo_root_from_script()
    subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=rr,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    result = verify_task(args.task_id, args.base_branch, rr)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
