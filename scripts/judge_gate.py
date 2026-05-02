"""
Run verification plus independent test/lint reruns; write judge JSON (fail closed).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import subprocess

import yaml


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def load_verify_module():
    path = Path(__file__).resolve().parent / "verify_receipt.py"
    spec = importlib.util.spec_from_file_location("verify_receipt_mod", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load verify_receipt.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_task(repo_root: Path, task_id: str) -> dict[str, Any]:
    tasks_path = repo_root / "agent_workspace" / "tasks" / "tasks.yaml"
    data = yaml.safe_load(tasks_path.read_text(encoding="utf-8"))
    for t in data.get("tasks") or []:
        if t.get("id") == task_id:
            return t
    eprint(f"ERROR: task id {task_id!r} not found in tasks.yaml")
    sys.exit(1)


def worktree_path(repo_root: Path, task_id: str) -> Path:
    return repo_root.parent / "worktrees" / f"{repo_root.name}__{task_id}"


def run_cmd_shell(cmd: str, cwd: Path) -> int:
    proc = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode


def main() -> None:
    parser = argparse.ArgumentParser(description="Judge gate: verify receipt + rerun tests/lint.")
    parser.add_argument("--task-id", required=True)
    parser.add_argument("--base-branch", default="main")
    args = parser.parse_args()

    rr = repo_root_from_script()
    subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=rr,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    vmod = load_verify_module()
    vmod.validate_task_id(args.task_id)

    wt = worktree_path(rr, args.task_id)

    verify_result = vmod.verify_task(args.task_id, args.base_branch, rr)

    task = load_task(rr, args.task_id)
    test_cmd = (task.get("test_command") or "").strip()
    lint_cmd = (task.get("lint_command") or "").strip()

    test_exit: int | None = None
    lint_exit: int | None = None
    failed_checks = list(verify_result.get("failed_checks") or [])

    if wt.is_dir():
        if test_cmd:
            test_exit = run_cmd_shell(test_cmd, wt)
            if test_exit != 0:
                failed_checks.append(f"test_command failed with exit code {test_exit}")
        else:
            failed_checks.append("test_command missing in tasks.yaml (required for judge gate)")

        if lint_cmd:
            lint_exit = run_cmd_shell(lint_cmd, wt)
            if lint_exit != 0:
                failed_checks.append(f"lint_command failed with exit code {lint_exit}")
    else:
        test_exit = None
        lint_exit = None

    passed = len(failed_checks) == 0
    message = "OK" if passed else "; ".join(failed_checks)

    out = {
        "task_id": args.task_id,
        "pass": passed,
        "message": message,
        "failed_checks": failed_checks,
        "actual_changed_files": verify_result.get("actual_changed_files", []),
        "required_evidence_checked": verify_result.get("required_evidence_checked", []),
        "test_exit_code": test_exit,
        "lint_exit_code": lint_exit,
    }

    judge_path = rr / "agent_workspace" / "judge" / f"{args.task_id}.json"
    judge_path.parent.mkdir(parents=True, exist_ok=True)
    judge_path.write_text(json.dumps(out, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    print(json.dumps(out, ensure_ascii=False, sort_keys=True))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
