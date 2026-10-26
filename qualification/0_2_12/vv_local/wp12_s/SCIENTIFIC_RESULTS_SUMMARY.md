# WP12-S scientific results summary

**Status:** `EXECUTION_RECORDED` — 8/8 cases executed; 7 `PYTEST_PASS_ONLY`, 1 `FAIL`.<br>
**Numerical execution:** `PERFORMED`; oracle and qualification conclusions remain scoped below.<br>
**WP12:** `OPEN`

WP12-R's four prior receipts remain `PYTEST_PASS_ONLY` with numeric payload `NOT_EXPOSED`; none of the values below are reconstructed from them. The eight separate instrumented WP12-S executions are recorded in the [execution report](WP12_S_EXECUTION_REPORT.md), with raw values in the manifest-linked external receipts and derived machine-readable tables under `results/WP12-S-QUANT-001-20261026T095251Z/`.

Results include an exact recorded projection identity; a spring/mass frequency agreeing with its analytic reference; same-backend modal consistency; a single-dt Newmark free-vibration history; an independent scalar modal-root comparison whose overall test is `FAIL` on a separate zero-atol projected-stiffness assertion; two one-element BEAM2 comparisons; and a three-level TET4 characterization whose helper status is `WARNING`.

The results do not establish general physical validation, modal-basis qualification, temporal convergence, asymptotic spatial convergence, or qualification of all BEAM2/TET4 uses. The polynomial `FAIL` and TET4 `WARNING` are preserved. The reported TET4 orders are descriptive only; the 1-D beam formula is a diagnostic reference, not a 3-D continuum oracle. No maturity or work-package status was changed; WP12 and WP13 remain open, and WP11 remains closed.
