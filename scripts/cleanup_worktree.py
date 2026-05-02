"""
DESTRUCTIVE: remove a task worktree and delete the local task branch after explicit confirmation.

Never run automatically. Requires Human Supreme intent.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import subprocess

TASK_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_task_id(task_id: str) -> None:
    if not TASK_ID_PATTERN.fullmatch(task_id):
        eprint(f"ERROR: invalid task id {task_id!r}; allowed pattern: letters, digits, underscore, dash.")
        sys.exit(1)


def branch_name(task_id: str) -> str:
    return f"task/{task_id}"


def worktree_path(repo_root: Path, task_id: str) -> Path:
    return repo_root.parent / "worktrees" / f"{repo_root.name}__{task_id}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DESTRUCTIVE: remove worktree and delete branch (manual approval only).",
    )
    parser.add_argument("--task-id", required=True)
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required. Without this flag, the script refuses to run.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow cleanup even when judge report is missing (dangerous).",
    )
    args = parser.parse_args()

    validate_task_id(args.task_id)

    if not args.confirm:
        eprint("ERROR: refusing to run without --confirm (destructive operation).")
        sys.exit(1)

    rr = repo_root_from_script()
    subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=rr,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    judge_path = rr / "agent_workspace" / "judge" / f"{args.task_id}.json"
    if not judge_path.is_file() and not args.force:
        eprint(
            "ERROR: judge report missing; supply --force only if Human Supreme accepts the risk."
        )
        sys.exit(1)

    branch = branch_name(args.task_id)
    wt = worktree_path(rr, args.task_id)

    print("DESTRUCTIVE CLEANUP PLAN:")
    print(f"  worktree path: {wt}")
    print(f"  branch to delete: {branch}")
    if not wt.exists():
        eprint(f"ERROR: worktree path does not exist: {wt}")
        sys.exit(1)

    subprocess.run(
        ["git", "worktree", "remove", "--force", str(wt)],
        cwd=rr,
        check=True,
    )

    proc = subprocess.run(
        ["git", "branch", "-d", branch],
        cwd=rr,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        eprint(proc.stderr.strip() or proc.stdout.strip() or "branch delete failed")
        sys.exit(1)

    print("Cleanup completed.")


if __name__ == "__main__":
    main()
