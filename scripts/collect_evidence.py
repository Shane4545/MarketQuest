"""
Run task test/lint commands in the worktree and save evidence artifacts.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
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
    for t in data.get("tasks") or []:
        if t.get("id") == task_id:
            return t
    eprint(f"ERROR: task id {task_id!r} not found in tasks.yaml")
    sys.exit(1)


def worktree_path(repo_root: Path, task_id: str) -> Path:
    return repo_root.parent / "worktrees" / f"{repo_root.name}__{task_id}"


def run_command_capture(
    cmd: str,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect test/lint evidence for a task.")
    parser.add_argument("--task-id", required=True, help="Task id.")
    args = parser.parse_args()

    validate_task_id(args.task_id)
    repo_root = repo_root_from_script()
    subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    task = load_task(repo_root, args.task_id)
    wt = worktree_path(repo_root, args.task_id)
    if not wt.is_dir():
        eprint(f"ERROR: worktree not found: {wt}")
        sys.exit(1)

    evidence_dir = repo_root / "agent_workspace" / "evidence" / args.task_id
    evidence_dir.mkdir(parents=True, exist_ok=True)

    test_cmd = (task.get("test_command") or "").strip()
    lint_cmd = (task.get("lint_command") or "").strip()
    ui_required = bool(task.get("ui_required"))

    failed = False
    test_exit: int | None = None
    lint_exit: int | None = None

    if not test_cmd:
        eprint("ERROR: test_command is required for evidence collection")
        sys.exit(1)

    tr = run_command_capture(test_cmd, wt)
    test_exit = tr.returncode
    test_log = evidence_dir / "test_results.txt"
    test_log.write_text((tr.stdout or "") + (tr.stderr or ""), encoding="utf-8")
    if tr.returncode != 0:
        failed = True

    lint_log = evidence_dir / "lint_results.txt"
    if lint_cmd:
        lr = run_command_capture(lint_cmd, wt)
        lint_exit = lr.returncode
        lint_log.write_text((lr.stdout or "") + (lr.stderr or ""), encoding="utf-8")
        if lr.returncode != 0:
            failed = True
    else:
        lint_exit = None
        lint_log.write_text(
            "Lint skipped: lint_command is empty or not configured.\n",
            encoding="utf-8",
        )

    ui_proof = evidence_dir / "ui_proof.png"
    if ui_required and not ui_proof.is_file():
        note = evidence_dir / "UI_PROOF_REQUIRED.txt"
        note.write_text(
            "UI proof was required (ui_required: true) but ui_proof.png was not present.\n"
            "Add a real screenshot to ui_proof.png; this file is not a substitute.\n",
            encoding="utf-8",
        )
        failed = True

    summary_path = repo_root / "agent_workspace" / "logs" / f"{args.task_id}_collect_summary.json"
    summary = {
        "task_id": args.task_id,
        "worktree": str(wt),
        "test_command": test_cmd,
        "test_exit_code": test_exit,
        "lint_command": lint_cmd or None,
        "lint_exit_code": lint_exit,
        "evidence_dir": str(evidence_dir),
        "failed": failed,
    }
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    if failed:
        eprint("ERROR: evidence collection failed (tests, lint, or UI proof requirement).")
        sys.exit(1)


if __name__ == "__main__":
    main()
