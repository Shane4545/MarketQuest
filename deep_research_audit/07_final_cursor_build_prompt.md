## Cursor Build Prompt (Fail-Closed, Data Engine First)

You are building a **local-first financial signal investigation lab** for educational paper-basket research.

This is **not** a live trading bot.
This is **not** investment advice.
Do not emit buy/sell/hold recommendations.

### Critical failure rule

If you build the UI before the data engine, formulas, tests, frozen entries, and review scripts pass, the project is a failure.

---

## 1) Required Folder Structure

Create exactly:

```text
app/
  backend/
    src/
      api/
      core/
      data_ingest/
      data_validation/
      features/
      baskets/
      controls/
      simulation/
      evidence/
      catalyst/
      risk/
      postmortem/
      schemas/
    tests/
      unit/
      integration/
      regression/
      no_hindsight/
      acceptance/
    pyproject.toml
  frontend/
    src/
      pages/
      components/
      stores/
      services/
    tests/
  data/
    raw/
    staged/
    curated/
    snapshots/
  manifests/
    runs/
    evidence/
    coverage/
  scripts/
    ingest.py
    validate.py
    compute_features.py
    freeze_basket.py
    build_controls.py
    simulate.py
    postmortem.py
    generate_evidence_manifest.py
    generate_coverage_report.py
  reports/
    acceptance/
```

---

## 2) Backend Stack

- Python 3.11+
- FastAPI for API surface
- Pydantic for strict schema contracts
- DuckDB for analytical storage
- Parquet for immutable snapshots
- SQLite (or Postgres optional) for metadata/event logs
- Pytest for tests

---

## 3) Frontend Stack (only after backend gates pass)

- React + TypeScript + Vite
- Table/chart stack suitable for high-density evidence views
- No frontend work until CLI/data engine acceptance gates pass

---

## 4) Data Schemas (minimum)

Define Pydantic models and SQL tables for:

1. `ohlcv_bars`
2. `company_reference` (market cap, float availability flags)
3. `candidate_signal`
4. `catalyst_event`
5. `risk_flag`
6. `frozen_basket_entry`
7. `rejected_candidate_entry`
8. `control_basket_entry`
9. `simulation_run`
10. `evidence_manifest`
11. `coverage_report`
12. `postmortem_record`

Each record must include:

- `source_id`
- `source_url`
- `ingested_at`
- `confidence_score`
- `point_in_time_timestamp`

---

## 5) CLI Commands (must work before UI)

Implement:

```bash
python scripts/ingest.py --as-of YYYY-MM-DD
python scripts/validate.py --as-of YYYY-MM-DD
python scripts/compute_features.py --as-of YYYY-MM-DD
python scripts/freeze_basket.py --as-of YYYY-MM-DD --basket-name BASKET_ID
python scripts/build_controls.py --basket-name BASKET_ID --method random_matched
python scripts/simulate.py --basket-name BASKET_ID --horizon 5d
python scripts/postmortem.py --run-id RUN_ID
python scripts/generate_evidence_manifest.py --run-id RUN_ID
python scripts/generate_coverage_report.py --run-id RUN_ID
```

---

## 6) Feature/Formula Requirements

Implement deterministic, point-in-time features for:

- volume surge
- dollar volume pressure
- prior-week momentum
- close location value
- intraday fade
- gap behavior
- post-spike confirmation
- catalyst presence score
- dilution risk flags
- reverse split risk flags
- compliance warning flags
- going-concern / late filing warning flags

No feature may use future timestamps relative to `as-of`.

---

## 7) Frozen / Reject / Control Baskets

### Frozen paper basket

When frozen:

- entry set is immutable
- feature snapshot hash is immutable
- source manifest hash is immutable
- all entries include point-in-time evidence references

### Reject basket

Store rejected candidates with:

- rejection reason code
- evidence references
- risk flags
- timestamp

### Random matched controls

Build controls matched on:

- market cap bucket
- liquidity bucket
- recent volatility bucket
- sector/industry where available

---

## 8) No-Hindsight Rules

Hard fail if:

- any joined dataset has timestamp > basket freeze timestamp
- any label/outcome is used in feature generation
- control basket was sampled after outcome window

Create explicit no-hindsight tests in `tests/no_hindsight/`.

---

## 9) Evidence Manifests

Generate machine-readable manifests:

- `manifests/runs/<run_id>.json`
- `manifests/evidence/<run_id>.json`
- `manifests/coverage/<run_id>.json`

Each manifest must include:

- command executed
- input datasets with hashes
- output artifacts with hashes
- validation results
- failed checks (if any)
- data coverage limitations

---

## 10) Acceptance Gates

Before any UI:

1. `ingest` succeeds
2. `validate` succeeds
3. feature tests pass
4. no-hindsight tests pass
5. freeze command produces immutable basket artifacts
6. control basket generation succeeds
7. simulation run emits deterministic outputs
8. evidence manifest generated
9. coverage report generated

If any fails: stop and output failure report; do not continue to UI.

---

## 11) UI Scope (only after gates)

Implement pages:

1. Candidate Inventory
2. Frozen Baskets
3. Reject Basket
4. Control Basket Comparison
5. Evidence Center (timeline + source confidence)
6. Postmortem Review
7. Data Coverage Limitations

UI must display confidence and provenance fields for every major panel.

---

## 12) Testing Requirements

Minimum required:

- unit tests for feature formulas
- integration tests for ingest->validate->feature pipeline
- regression tests for deterministic simulation replay
- no-hindsight leakage tests
- acceptance tests for required manifests

No test skipping by default.

---

## 13) Final Deliverables

Produce:

- working CLI pipeline
- passing tests
- manifests and coverage reports
- acceptance report under `reports/acceptance/`

The final report must list:

- commands run
- pass/fail status per gate
- total candidates, frozen entries, rejected entries, controls
- known data coverage limitations

