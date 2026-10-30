# WP12-S — Quantitative local V&V preparation

**Status:** `EXECUTION_RECORDED` — 8 authorized cases run; 7 `PYTEST_PASS_ONLY`, 1 `FAIL`.<br>
**Numerical execution:** `PERFORMED` for the eight cases below; no qualification verdict assigned.<br>
**WP12:** `OPEN`

This package contains the preparation, authorized execution record, verified numeric payloads, derived tables and internal SVG figures for eight WP12-S cases. The earlier WP12-R receipts remain immutable: they report `PYTEST_PASS_ONLY` with numeric observables `NOT_EXPOSED`. The current results come from separate instrumented runs and must not be attributed to WP12-R.

**Prepared manifest SHA-256:** `df8c1401a122d18be270ba25bbd0f77c92ede5ff667d9fe4b87da62c10745d9c`.

## Navigation

- [Campaign plan and approval boundary](WP12_S_CAMPAIGN_PLAN.md)
- [WP12-S execution report and per-case interpretation](WP12_S_EXECUTION_REPORT.md)
- [Q1–Q4 extraction review](Q1_Q4_NUMERICAL_EXTRACTION.md)
- [Executed Q1–Q4 result table](results/WP12-S-QUANT-001-20261026T095251Z/Q1_Q4_EXECUTED_RESULTS.csv)
- [Eight-case status matrix](WP12_S_CASE_STATUS.csv)
- [All-case results and receipt hashes](results/WP12-S-QUANT-001-20261026T095251Z/WP12_S_ALL_CASE_RESULTS.csv)
- [Derived-results integrity index](results/WP12-S-QUANT-001-20261026T095251Z/RESULTS_INDEX.json)
- [TET4 per-level results](results/WP12-S-QUANT-001-20261026T095251Z/FEM-TET4-H-001-levels.csv)
- [Newmark displacement history](results/WP12-S-QUANT-001-20261026T095251Z/DYN-SDOF-QUANT-001-history.csv)
- [Independent 2-DOF polynomial oracle](MODAL_2DOF_INDEPENDENT_ORACLE.md)
- [BEAM2 two-plane analytical benchmark](BEAM2_BENCHMARK_REPORT.md)
- [TET4 refinement characterization](TET4_CONVERGENCE_REPORT.md)
- [Generated internal figures](results/WP12-S-QUANT-001-20261026T095251Z/figures/)
- [Current scientific evidence summary](SCIENTIFIC_RESULTS_SUMMARY.md)
- [Publication data index](PUBLICATION_DATA_INDEX.md)
- [Gaps and next actions](GAP_AND_NEXT_ACTIONS.md)
- [Prepared manifest](WP12_S_QUANTITATIVE_MANIFEST.json)
- [Owner decision package](WP12_S_OWNER_DECISION_PACKAGE.md)

The instrumented nodeids live in [`tests/unit/test_wp12_s_quantitative_extraction.py`](../../../../tests/unit/test_wp12_s_quantitative_extraction.py). The local V&V runner's structured-output handling is separately identified in the runner checkout; scientific source remains pinned to the WP12-0 commit. Each case required exactly one payload using the manifest-pinned schema. A pytest pass without it would be an infrastructure error.

## Evidence rule

No value may be inferred from an assertion-only receipt. For this campaign, the eight marker payloads are observed outputs from the exact nodes executed once after case-specific Owner approval. The raw receipts record payloads, selection, checkout identities, and environment. The payloads are not by themselves independent oracle verdicts or qualification decisions. Earlier WP12-R receipts remain assertion-only with numeric values `NOT_EXPOSED`.

The manifest remains immutable at its approved SHA-256; its `PREPARED_NOT_AUTHORIZED` field is not rewritten after the separate Owner decisions. Eight case-specific non-cryptographic decision records and the raw receipts are preserved in the local evidence archive referenced by the manifest. The figures and tables are internal derived artifacts only. No WP12 closure, maturity change, release or external publication is produced here.
