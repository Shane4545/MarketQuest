# AI Nation Command — Cursor Governance Package V1

## Purpose (V1)

This repository ships a **verification-first** governance layer for controlled multi-agent work in Cursor 3.0. V1 emphasizes **manual human control**, **evidence**, and **fail-closed checks**—not automation that spawns agents or merges code on its own.

**Human Supreme** holds final authority. Cursor agents are started **only manually** from the Cursor Agents window. There is **one task per git worktree**, **no nested subagents**, and **no automatic Cursor-agent spawning** from scripts or CI.

## Roles

| Role | Responsibility |
|------|------------------|
| **Human Supreme** | Approves scope, starts agents, approves merges, resolves disputes. |
| **Chief Planner** | Breaks work into tasks that fit one worktree and one branch. |
| **Architect** | Shape design and constraints; does not bypass evidence or judge. |
| **Worker** | Implements in the assigned worktree only; produces receipts and evidence. |
| **Judge** | Independent verification against receipt, diff, tests, and lint. |
| **Integrator** | Prepares merge-ready state after Human Supreme and judge approval. |

## Manual agent startup

1. Define or select a task in `agent_workspace/tasks/tasks.yaml`.
2. Human Supreme runs `scripts/create_worktree.py` (or equivalent git steps) to create `task/<task_id>` and the worktree at `../worktrees/<repo-name>__<task_id>`.
3. Open **Cursor → Agents**, choose the role prompt from `agent_workspace/prompts/*.md`, paste or attach context (task id, paths, constraints).
4. **Do not** nest subagents. **Do not** rely on CLI to spawn agents.

## Worktree flow

- Each task uses branch name **`task/<task_id>`**.
- Workers operate **only** inside: `../worktrees/<repo-name>__<task_id>`.
- One task id maps to one worktree folder name suffix `__<task_id>`.

## Evidence flow

1. Worker (or scripts run by Human Supreme) produces:
   - **`agent_workspace/receipts/<task_id>.json`** — claimed changed files and metadata (no fiction).
   - **`agent_workspace/evidence/<task_id>/`** — command outputs, optional `ui_proof.png` when required.
2. **`scripts/collect_evidence.py`** runs tests and lint in the worktree and writes evidence files and a collection summary under `agent_workspace/logs/`.
3. **`scripts/verify_receipt.py`** compares the receipt to **actual** `git` diffs and policy lists (`allowed_files`, `forbidden_files`, `required_evidence`).

## Judge gate

- **`scripts/judge_gate.py`** re-verifies the receipt, re-runs tests and lint in the worktree, and writes **`agent_workspace/judge/<task_id>.json`** with pass/fail and structured reasons.
- If any required check fails, the judge report marks **pass: false** and the script exits non-zero (fail closed).

## Human merge approval

- Merging to the main integration branch requires **Human Supreme** approval after:
  - Receipt verified against git reality.
  - Evidence and judge report present and passing.
  - CI green where applicable.
- Use `.github/PULL_REQUEST_TEMPLATE.md` checkboxes for explicit human and CI confirmation.

## Exact operating steps (happy path)

1. Add or update the task entry in `agent_workspace/tasks/tasks.yaml`.
2. Run `python scripts/create_worktree.py --task-id <id>` (add `--reuse` only if reusing an existing branch intentionally).
3. Start the **Worker** agent manually with `agent_workspace/prompts/worker.md`; work only in the new worktree path.
4. When implementation is ready, write **`agent_workspace/receipts/<task_id>.json`** with accurate `changed_files` (Human Supreme or Worker per your policy).
5. Run `python scripts/collect_evidence.py --task-id <id>`; fix failures before continuing.
6. Run `python scripts/verify_receipt.py --task-id <id>` and inspect JSON on stdout.
7. Run `python scripts/judge_gate.py --task-id <id>`; read `agent_workspace/judge/<task_id>.json`.
8. Open a PR using the template; Human Supreme checks boxes and merges when satisfied.
9. Optionally run `python scripts/cleanup_worktree.py --task-id <id> --confirm` after merge (destructive; requires confirmation).

## Fail-closed summary

Missing receipt, missing evidence, test/lint failure, forbidden file touched, receipt not matching `git` reality, or invalid YAML/JSON → **failure**. Scripts exit non-zero where specified.
