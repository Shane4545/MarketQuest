"""
Create git branch task/<task_id> and a sibling worktree under ../worktrees/.
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


def git_branch_exists(repo_root: Path, branch: str) -> bool:
    proc = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=repo_root,
        check=False,
    )
    return proc.returncode == 0


def resolve_base_ref(repo_root: Path) -> str:
    for name in ("main", "master"):
        proc = subprocess.run(
            ["git", "rev-parse", "--verify", f"refs/heads/{name}"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            return name
    return "HEAD"


def main() -> None:
    parser = argparse.ArgumentParser(description="Create task branch and git worktree (non-destructive).")
    parser.add_argument("--task-id", required=True, help="Task id (letters, digits, underscore, dash).")
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="Allow using an existing local branch task/<task_id>.",
    )
    args = parser.parse_args()

    validate_task_id(args.task_id)
    repo_root = repo_root_from_script()

    subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.DEVNULL,
    )

    branch = branch_name(args.task_id)
    wt_path = worktree_path(repo_root, args.task_id)

    if wt_path.exists():
        eprint(f"ERROR: worktree path already exists: {wt_path}")
        sys.exit(1)

    exists = git_branch_exists(repo_root, branch)
    if exists and not args.reuse:
        eprint(f"ERROR: branch already exists: {branch} (use --reuse to attach)")
        sys.exit(1)

    if not exists:
        base = resolve_base_ref(repo_root)
        subprocess.run(["git", "branch", branch, base], cwd=repo_root, check=True)

    subprocess.run(
        ["git", "worktree", "add", str(wt_path), branch],
        cwd=repo_root,
        check=True,
    )

    print(f"Created worktree at {wt_path} on branch {branch}")


if __name__ == "__main__":
    main()
