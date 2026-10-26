# WP12-S publication data index

**Status:** `EXECUTION_RECORDED` — internal data and figures only.<br>
**Numerical execution:** `PERFORMED` for eight Owner-approved cases.<br>
**WP12:** `OPEN`

## Available data

- [Execution report](WP12_S_EXECUTION_REPORT.md) with run IDs, receipt hashes, actual values, criteria, failures and limitations.
- [All-case CSV](results/WP12-S-QUANT-001-20261026T095251Z/WP12_S_ALL_CASE_RESULTS.csv), [Q1–Q4 executed CSV](results/WP12-S-QUANT-001-20261026T095251Z/Q1_Q4_EXECUTED_RESULTS.csv), [TET4 levels](results/WP12-S-QUANT-001-20261026T095251Z/FEM-TET4-H-001-levels.csv), and [Newmark time history](results/WP12-S-QUANT-001-20261026T095251Z/DYN-SDOF-QUANT-001-history.csv).
- [Integrity index](results/WP12-S-QUANT-001-20261026T095251Z/RESULTS_INDEX.json), linking each derivative to its raw receipt SHA-256.
- [Five internal SVG figures](results/WP12-S-QUANT-001-20261026T095251Z/figures/).
- Case formulas, accepted criteria and scope limits in the [campaign plan](WP12_S_CAMPAIGN_PLAN.md) and domain reports.
- Prior WP12-R process receipts and their `NOT_EXPOSED` status in [`FIRST_CAMPAIGN_ORACLE_REVIEW.md`](../FIRST_CAMPAIGN_ORACLE_REVIEW.md); these remain historical and unchanged.

## Evidence location and limitations

Raw JUnit, stdout/stderr, receipts, the TET4 summary/CSV/HDF5 models, attempt records and per-case decision records remain in the local external evidence root declared by the frozen manifest. The committed derived tables use stable `evidence://` references and receipt hashes rather than machine-specific absolute paths. The repository contains derived values and figures, not the full binary evidence archive. `PYTEST_PASS_ONLY` is not a scientific PASS. The modal polynomial test remains `FAIL`; TET4's helper remains `WARNING`.

## Publication boundary

The figures and tables are internal review artifacts, not approved publication claims. External publication, website updates, package releases and release tags remain unauthorized. Any later publication sheet must retain the candidate/runner/test identities, raw receipt hashes, exact oracle, criteria and limits, and must distinguish algebraic identity, same-backend modal consistency, analytical beam/discrete checks, conditional transient integration, and bounded mesh characterization.
