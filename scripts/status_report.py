"""
Print governance status for all tasks in tasks.yaml.
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


def worktree_path(repo_root: Path, task_id: str) -> Path:
    return repo_root.parent / "worktrees" / f"{repo_root.name}__{task_id}"


def branch_name(task_id: str) -> str:
    return f"task/{task_id}"


def load_all_tasks(repo_root: Path) -> list[dict[str, Any]]:
    p = repo_root / "agent_workspace" / "tasks" / "tasks.yaml"
    if not p.is_file():
        eprint(f"ERROR: missing {p}")
        sys.exit(1)
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        eprint(f"ERROR: invalid YAML: {exc}")
        sys.exit(1)
    return list(data.get("tasks") or [])


def required_evidence_status(repo_root: Path, task_id: str, task: dict[str, Any]) -> str:
    req = task.get("required_evidence") or []
    if not req:
        return "none"
    ev = repo_root / "agent_workspace" / "evidence" / task_id
    parts: list[str] = []
    for name in req:
        rel = str(name).strip()
        if not rel:
            continue
        ok = (ev / rel).is_file()
        parts.append(f"{rel}:{'ok' if ok else 'missing'}")
    return "; ".join(parts)


def judge_status(repo_root: Path, task_id: str) -> str:
    jp = repo_root / "agent_workspace" / "judge" / f"{task_id}.json"
    if not jp.is_file():
        return "missing"
    try:
        data = json.loads(jp.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "invalid_json"
    if data.get("pass") is True:
        return "pass"
    return "fail"


def git_short_status(worktree: Path) -> str:
    proc = subprocess.run(
        ["git", "status", "-sb"],
        cwd=worktree,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return proc.stderr.strip() or "git status failed"
    return proc.stdout.strip().replace("\n", " | ")


def main() -> None:
    parser = argparse.ArgumentParser(description="Governance status report for all tasks.")
    parser.parse_args()

    rr = repo_root_from_script()
    subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=rr,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    tasks = load_all_tasks(rr)
    if not tasks:
        print("No tasks defined in agent_workspace/tasks/tasks.yaml")
        return

    for task in tasks:
        tid = task.get("id")
        if not tid or not isinstance(tid, str):
            eprint("ERROR: task entry missing string id")
            sys.exit(1)
        if not TASK_ID_PATTERN.fullmatch(tid):
            eprint(f"ERROR: invalid task id in yaml: {tid!r}")
            sys.exit(1)

        wt = worktree_path(rr, tid)
        branch = branch_name(tid)
        receipt = rr / "agent_workspace" / "receipts" / f"{tid}.json"

        print(f"task_id: {tid}")
        print(f"  branch: {branch}")
        print(f"  worktree_path: {wt}")
        print(f"  worktree_exists: {'yes' if wt.is_dir() else 'no'}")
        print(f"  receipt_exists: {'yes' if receipt.is_file() else 'no'}")
        print(f"  required_evidence: {required_evidence_status(rr, tid, task)}")
        print(f"  judge: {judge_status(rr, tid)}")
        if wt.is_dir():
            print(f"  git_status: {git_short_status(wt)}")
        else:
            print("  git_status: (worktree missing)")
        print()


if __name__ == "__main__":
    main()
