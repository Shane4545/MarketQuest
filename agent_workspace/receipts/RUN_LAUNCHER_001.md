# Receipt — RUN_LAUNCHER_001 (acceptance verification)

## Scope

Acceptance verification only: real HTTP smoke, artifact inspection, pytest, evidence lock. No strategy/threshold changes; no broker execution or trade UI.

## Commands run

- `python -m pytest -q` → see `agent_workspace/evidence/RUN_LAUNCHER_001/pytest_output.txt`
- `python app/scripts/run_viewer_api.py --port 8010` (background; see `server_start_output.txt`)
- HTTP smoke via Python `urllib` (same requests as documented below):
  - `GET /api/run-launcher/options` → `options_endpoint_output.json`
  - `POST /api/run-launcher/launch` invalid body `{"mode":"live"}` → `invalid_request_output.json`
  - `POST` fixture acceptance payload → `fixture_launch_request.json`, `fixture_launch_output.json`
  - `POST` dry-run acceptance payload → `dryrun_launch_request.json`, `dryrun_launch_output.json`
  - `GET /api/runs/launcher_fixture_acceptance` → `run_viewer_fixture_output.txt`
- Copied launcher artifacts into evidence: `fixture_launcher_*_artifact.json`, `dryrun_launcher_*_artifact.json`
- `git status -sb` → `git_status.txt`
- `python scripts/judge_gate.py --task-id RUN_LAUNCHER_001` → **failed**: task id not present in `agent_workspace/tasks/tasks.yaml` (automation gate unavailable until Chief Planner adds the task definition).

## Pytest result

**32 passed** (see `pytest_output.txt`).

## Invalid request validation

- HTTP **200** with JSON body `accepted: false`, `status: "rejected"`, non-empty `errors` list (not `accepted: true`).
- No acquisition run directory created for invalid-only probe beyond auto-generated `run_id` in JSON response for validation bookkeeping (`invalid_request_output.json`).

## Real fixture launcher smoke (`launcher_fixture_acceptance`)

- API: `accepted: true`, `status: completed` (`fixture_launch_output.json`).
- Artifacts on disk under `app/data/acquisition_runs/launcher_fixture_acceptance/` including `launcher_request.json`, `launcher_status.json`, `acquisition_plan.json`, `acquisition_result.json`, `pipeline_terminal_status.json` (pipeline completed with candidates for fixture data).

## Real dry-run launcher smoke (`launcher_dryrun_acceptance`)

- API: `accepted: true`, `status: completed` (`dryrun_launch_output.json`).
- Artifacts: `launcher_request.json`, `launcher_status.json`, `acquisition_plan.json`, `acquisition_result.json` present; `overall_pipeline_status` in launcher status is **ACQUISITION_PROVENANCE_ONLY** (pipeline not invoked for dry-run by design).

## Run Viewer integration

- `GET /api/runs/launcher_fixture_acceptance` shows `paths.launcher_request_json`, `paths.launcher_status_json`, acquisition artifacts, `pipeline_terminal_status_json`, governance limitations as recorded (`run_viewer_fixture_output.txt`).

## Safe trading flags (artifacts)

Confirmed **false/false/false/true/true** for trading / broker execution / live orders / approval required / paper_only on both fixture and dry-run launcher JSON copies in evidence.

## Broker execution / live orders / trade UI

- **Not enabled** in artifacts; no trade buttons or order tickets in launcher UI; orchestration remains script subprocess calls only.

## Future trading architecture note

- `docs/FUTURE_TRADING_ARCHITECTURE.md` contains the required authorized-account-owner sentence; no age/minor-oriented wording identified in spot-check.

## Real ticker leakage (evidence pack)

- Acceptance payloads use fixture symbols **TEST_A**, **TEST_B** only in captured requests/artifacts.

## Prior chat ticker leakage

- Not evaluated in automated form; evidence files contain no prohibited ticker seeds from `tests/test_run_viewer_api.py` banned list.

## Files touched this verification pass

- `agent_workspace/evidence/RUN_LAUNCHER_001/*` (evidence bundle listed in task requirements)
- `agent_workspace/receipts/RUN_LAUNCHER_001.md` (this file)

## Remaining limitations / blockers

- **Judge gate**: `RUN_LAUNCHER_001` not registered in `tasks.yaml`; Human Supreme may still accept based on manual evidence review.
- Governance evidence/receipt linking still optional unless `governance_links.json` populated (viewer reports honestly).

## Human Supreme note

Merge/integration approval remains human per `AGENTS.md`; this receipt documents verification commands and outcomes only.
