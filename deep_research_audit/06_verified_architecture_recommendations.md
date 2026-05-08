## Verified Architecture Recommendations

All recommendation lines include only valid receipt IDs from `02_receipts.csv`.  
Rule applied: at least two valid receipt IDs required; otherwise marked **PROVISIONAL**.

1. **Backend service architecture (`FastAPI`, modular domains, strict typed contracts)**  
   Support: `R001`, `R003`, `R089`  
   Status: Verified

2. **Core simulation engine must be event-driven with deterministic replay mode**  
   Support: `R006`, `R086`, `R090`  
   Status: Verified

3. **Local analytical storage with DuckDB + Parquet for reproducible research snapshots**  
   Support: `R005`, `R007`, `R089`  
   Status: Verified

4. **Semantic domain modeling for candidate/risk/evidence objects before UI work**  
   Support: `R009`, `R010`, `R014`  
   Status: Verified

5. **Validation gates before acceptance (`schema`, `data quality`, `run manifest`)**  
   Support: `R049`, `R053`, `R054`  
   Status: Verified

6. **Runtime provenance/event logging on every ingest, feature build, and simulation run**  
   Support: `R051`, `R052`, `R106`  
   Status: Verified

7. **Evidence-center UI should be timeline and graph-first, not prediction-first**  
   Support: `R111`, `R116`, `R117`  
   Status: Verified

8. **Source confidence scoring and entity-resolution layer for catalyst evidence**  
   Support: `R109`, `R117`, `R118`  
   Status: Verified

9. **Frozen paper baskets: immutable entries with run hash and feature snapshot**  
   Support: `R003`, `R049`, `R090`  
   Status: Verified

10. **Reject basket: persist rejected candidates with reasons and supporting evidence IDs**  
    Support: `R022`, `R028`, `R130`  
    Status: Verified

11. **Random matched control baskets required for no-hindsight and false-positive checks**  
    Support: `R044`, `R119`, `R122`  
    Status: Verified

12. **AI assistant limited to review/postmortem support and adversarially evaluated**  
    Support: `R113`, `R114`, `R015`  
    Status: Verified

13. **Inter-app interoperability patterns for modular workstation composition**  
    Support: `R012`, `R092`  
    Status: Verified

14. **Institutional governance checklist for OSS policy and auditability**  
    Support: `R021`, `R024`, `R093`  
    Status: Verified

15. **High-frequency/market-microstructure modeling track**  
    Support: `R097`, `R123`, `R124`  
    Status: Verified

16. **Knowledge-graph/entity-resolution layer for issuer and catalyst linkage**  
    Support: `R136`, `R137`, `R138`  
    Status: Verified

17. **MLOps quality and lineage stack as mandatory acceptance gate**  
    Support: `R149`, `R151`, `R152`, `R154`, `R155`  
    Status: Verified

---

**Gap-closure note (audit only):** Search rows `S055`–`S084` and receipts `R055`–`R084` were reconstructed with exact GitHub URLs and README-derived facts in the final closure pass. Optional supplementary receipts for the same projects include `R055`–`R066` (orchestration, lineage, stores); recommendation lines above were **not** rewritten and remain as previously verified.

