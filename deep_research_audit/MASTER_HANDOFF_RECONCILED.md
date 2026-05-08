# MASTER HANDOFF (Reconciled)

Use this single file as the posting anchor for your other agent.

## Current Reconciled Status

- Total receipts claimed: **155**
- Valid receipts: **125**
- Invalid receipts: **30**
- Candidate rows with exact URLs: **110**
- Accepted projects with valid receipts: **96**
- Rejected projects with valid receipts: **14**
- Deep-analysis rows (valid receipt supported): **55**
- Research ready for app build: **NO**

Reason still NO:
- `S055`-`S084` remain `UNVERIFIED` and map to invalid receipts `R055`-`R084`.

## What Was Added in Reconciliation

Verified and merged new claims for:
- Quant/finance: ABIDES, ABIDES-JPMC (ABIDES-Gym context), BackDash, QuantDash, BatesStocks, Open Paper Trading MCP (reconfirmed), Vibe-Trading.
- OSINT/case: Owlculus, GHOST-osint-crm, Flowintel.
- KG/entity-resolution: DerwenAI Strwythura, DerwenAI ERKG, Neo4j entity-resolution example, KBpedia, RahulNYK knowledge_graph, Senzing+Kuzu example.
- Forecast/risk/eval: nci/scores, FSSprob, properscoring, xskillscore, pycontrolcharts.
- MLOps/validation: Evidently, Dagster, Great Expectations, DVC, MLflow, OpenLineage, Marquez.

Rejected claim mappings (captured as negative evidence):
- Helm-Path (not verified)
- HuntKit/hunter-kit as case-management platforms (category mismatch)
- Siemens-OKE llm-query-pipeline as supply-chain KG thesis proof (scope mismatch)

## Canonical Files (Source of Truth)

1. `deep_research_audit/01_search_log.csv`
2. `deep_research_audit/02_receipts.csv`
3. `deep_research_audit/03_candidate_inventory.csv`
4. `deep_research_audit/04_deep_analysis_matrix.csv`
5. `deep_research_audit/05_invalid_or_weak_receipts.md`
6. `deep_research_audit/06_verified_architecture_recommendations.md`
7. `deep_research_audit/07_final_cursor_build_prompt.md`
8. `deep_research_audit/ACCEPTANCE_REPORT.md`

## Quick Instructions for the Other Agent

1. Treat `02_receipts.csv` as the receipt validity source of truth.
2. Use only `valid_receipt=true` rows for architecture and matrix conclusions.
3. Keep rejected/negative findings; do not delete them.
4. Do not flip readiness to YES until invalid areas are resolved.

