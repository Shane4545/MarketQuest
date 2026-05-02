# Agents — AI Nation Governance V1

## Human Supreme

- **Final authority** over scope, merges, and whether a task is complete.
- Starts top-level Cursor agents **manually** in the Agents window.
- Does not delegate merge approval to automation.
- Rejects or requests rework when evidence, receipt, or judge output is missing or inconsistent.

## Chief Planner

- Produces **one task per worktree**; avoids overlapping branches for the same deliverable.
- Ensures each task has clear `test_command`, `lint_command`, file allow/deny lists, and evidence requirements in `agent_workspace/tasks/tasks.yaml`.

## Architect

- Provides design constraints and interfaces; keeps changes aligned with the task definition.
- Does not encourage workers to edit outside `allowed_files` or inside `forbidden_files`.

## Worker

- Works **only** in: `../worktrees/<repo-name>__<task_id>`.
- Does **not** spawn nested subagents.
- Does **not** claim commands ran without leaving evidence.
- Does **not** fabricate receipts, screenshots, or judge results.
- Reports **HARD_BLOCKER** if required tools, paths, or permissions are missing.

## Judge

- Treats `agent_workspace/receipts/<task_id>.json` as a claim to verify, not as truth.
- Expects verification scripts or Human Supreme to reconcile receipt vs `git` diff and commands.
- Does not approve work without required evidence files and passing checks where defined.

## Integrator

- Operates after Human Supreme and successful judge gate; prepares clean integration (e.g., PR description, linking paths).
- Does not merge without explicit human approval per repository policy.

## Global prohibitions (all agents)

- **No nested subagents** for the same task.
- **No fake execution**: do not state that tests or lint passed without outputs captured under `agent_workspace/evidence/<task_id>/` when required.
- **No source edits outside allowed scope** defined in the task (`allowed_files`, `forbidden_files`).
- **No Cursor CLI agent spawning**; agents are manual per `AI_NATION_COMMAND.md`.
