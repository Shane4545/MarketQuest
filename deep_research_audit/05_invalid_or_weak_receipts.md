## Invalid Or Weak Receipts Audit

### Hard invalid receipts (`valid_receipt=false`)

- R008 (weak alternative benchmark evidence)
- R019 (indirect institution inference from FINOS org page)
- R020 (negative institution claim inferred from generic FINOS org page)
- R033 (partial institution attribution only)
- R035 (small-footprint organization-only evidence)
- R037 (organization-level evidence without feature verification)
- R043 (MIT attribution not proven from opened source)
- R046 (profile-level evidence, weak attribution)
- R074 (project explicitly unmaintained upstream)
- R088 (article-level source, not repository evidence)
- R100 (club-level org reference with low technical depth)

### Weak but still valid receipts (`valid_receipt=true`, low confidence or indirect source)

None currently counted as weak-valid after the strict repair pass.

### Rule-trigger examples found in previous narrative that were removed from counting

- Aggregated phrasing like "multiple", "mixed", "set", "several repos", and range rows (for example `S009-S016`) are not counted as valid evidence in this hardened audit.
- Any entry without exact `exact_source_url` is excluded from valid-receipt counts.

### New reconciliation rejections from ChatGPT report claims

- **Helm-Path**: no exact GitHub project verified from targeted fresh search (`R132` rejected).
- **HuntKit as OSINT case-management platform**: verified as pentest/security toolkit, not case-management evidence system (`R130` rejected).
- **hunter-kit as direct case-management evidence platform**: verified as pentest automation framework (`R131` rejected).
- **Siemens-OKE llm-query-pipeline as supply-chain KG thesis evidence**: repository is NLQ-to-SPARQL pipeline and does not directly validate supply-chain KG claim (`R143` rejected).
