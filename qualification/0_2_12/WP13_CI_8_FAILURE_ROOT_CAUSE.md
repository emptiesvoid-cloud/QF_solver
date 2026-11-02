# WP13 CI #41509887231 — Root Cause Analysis

## Scope and identity

The reviewed baseline is commit `056b4405112de0681a9c34d236e9efe98f8f14eb` (tree `68c8c70d2384ecb1c373239343c1921c0ceebb59`), the exact head of [CI run #41509887231](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41509887231). The run was a `workflow_dispatch` on `emptiesvoids-cloud/0.2.12`; all three compatibility cells passed, while the Ubuntu/Python 3.13 reference cell reported eight failures. The extended jobs were skipped as requested.

The run reported 4,779 passed, 8 failed, 32 skipped and 150 deselected; branch coverage was 84.775535%, above the unchanged 80% gate. No full CI rerun was performed for this remediation.

## DA-001 — Contact validation test fixture

The failing test `test_common_penalty_rejects_invalid_penetration_limit_before_assembly` reused `_model()`, whose model contained a discrete stabilizing spring and no finite elements. It changed the analysis route to `nonlinear_static` and expected `MeshValidationError` for `contact_max_penetration=0.0`.

The production route intentionally rejects unsupported springs before mesh validation. Its exception was therefore consistent with the route contract; the test fixture was inconsistent with the behavior it intended to test. Once the spring was removed, the JSON schema also required at least one finite element. The fixture now includes a valid, nondegenerate TET4 and elastic material, with no discrete springs. It reaches the invalid contact-parameter check before degree-of-freedom, load, or nonlinear assembly work. The spring rejection order in production code is unchanged.

**Classification:** test-fixture defect. No production spring behavior was changed.

## DA-005 — Residual certification for real sparse systems

All seven failures reached the conservative roundoff certificate after the directly recomputed residual had already passed the unchanged `1e-7` threshold. The prior certificate used a generic `32·eps·(k+1)` factor for each row regardless of the actual real CSR operation count. Its reported relative upper bounds ranged from `1.145068e-7` to `3.209453e-6`.

The captured float64 CSR arrays were independently evaluated using 100-decimal-digit arithmetic over the exact binary64 inputs and returned solution. The exact represented-system relative residuals were between `5.01e-11` and `1.91e-9`, all below `1e-7`. The computed residuals and backward errors were also small. This identifies excessive conservatism in this real CSR certificate, rather than an insufficient residual solution, as the cause of these seven rejections. It does not establish small forward solution error: a small residual can be amplified by matrix conditioning.

| Case | Shape / nnz | Previous upper bound | Recomputed relative residual | High-precision relative residual | New upper bound | Estimated κ₂ | η∞ backward error |
|---|---:|---:|---:|---:|---:|---:|---:|
| MITC4 laminate, ratio 0.001 | 288×288 / 6,016 | 3.209e-6 | 2.004e-9 | 1.909e-9 | 9.732e-8 | 3.628e10 | 2.471e-18 |
| Arc-length turning point | 6×6 / 36 | 7.827e-7 | 1.317e-9 | 8.513e-10 | 2.225e-8 | 1.632e7 | 8.291e-17 |
| Arc-length restart, before turn | 6×6 / 36 | 7.827e-7 | 1.317e-9 | 8.513e-10 | 2.225e-8 | 1.632e7 | 8.291e-17 |
| Arc-length restart, after turn | 6×6 / 36 | 7.827e-7 | 1.317e-9 | 8.513e-10 | 2.225e-8 | 1.632e7 | 8.291e-17 |
| Arc-length rollback | 6×6 / 36 | 7.820e-7 | 6.160e-10 | 9.341e-10 | 2.155e-8 | 1.632e7 | 4.145e-17 |
| TET4/TET10 reference artifacts | 108×108 / 4,672 | 1.145e-7 | 2.329e-11 | 2.148e-11 | 3.540e-9 | 1.076e6 | 2.513e-17 |
| Centered-load TET4/TET10 reference | 78×78 / 3,362 | 1.522e-7 | 5.807e-11 | 5.010e-11 | 4.724e-9 | 1.140e6 | 6.262e-17 |

Condition numbers are dense NumPy 2-norm estimates for the captured matrices, not certified bounds. The independent high-precision calculation verifies the residual of the represented inputs and returned solution; it is not an independent solve and does not establish forward error.

### Cause classification

| Category | Finding |
|---|---|
| Insufficient solution residual | Not supported for these seven captured states: high-precision residual ratios are below the unchanged limit. |
| Excessively conservative certification | Demonstrated: old bounds exceeded the limit while the high-precision residuals passed; the operation-count bound produces finite upper bounds below the same limit. |
| Poor conditioning | Present to differing degrees, especially the MITC4 case, but it does not explain the certificate's overstatement. Forward-error risk remains distinct. |
| Formulation or assembly defect | Not indicated as the cause of the seven residual-certificate failures. The TET reference summaries still fail their 1% TET10 criterion and remain WARNING; the artifact tests do not claim physical acceptance. This is not a general FEM qualification. |
| Oracle/test incompatibility | DA-001 had a fixture/route mismatch. The TET artifact tests deliberately assert output/contract behavior while allowing WARNING summaries. The seven DA-005 residual thresholds and all physical/reference criteria were not changed. |

The post-fix MITC4 cantilever tip displacement was `-0.2956497788612951` against the analytical reference `-0.29629896296296293` (relative difference `0.002191`, within the test's `0.003` tolerance and ratio floor `0.99`). Arc-length crossing reported one turning point at step 75, maximum residual `2.8114e-11`, and positive minimum `det(F)=0.4414`; restart suffix and final displacement errors were zero in both restart positions, and rollback recovered cleanly after one rejected increment.

The two TET reference-runner tests passed their artifact/contract assertions, but their summaries remain `WARNING` at maturity `stable_candidate`. The historical 1% TET10 reference criterion remains false: TET10 relative reference errors are 12.53% and 4.46% for the default study, and 27.44% and 9.61% for the centered-load study. Their tests assert machine-readable outputs and load-contract metadata, not physical qualification. These warning results are unchanged and are not converted into PASS by the residual correction.

## Evidence limits

The failure run was Ubuntu/Python 3.13.17. Local reproduction and post-fix validation used Windows/Python 3.13.1 with NumPy 2.2.6, SciPy 1.15.2 and pytest 8.4.1. The exact eight-nodeid checks passed locally, but there was no post-fix Linux run and no CI rerun. Full unit/integration CI, WP12 campaigns, the six v8 installed-package FEM smokes and global scientific qualification were not run. The captured matrices, logs and high-precision calculations are retained outside the repository; this public report does not include machine-specific paths.

The distribution artifacts v8 and their smoke evidence remain tied to commit `056b440…`. Since this remediation changes distributed solver code, those artifacts do not qualify the resulting corrective commit. A new package candidate and corresponding validations are required after integration.

## Conclusion

The eight failures have distinct demonstrated causes: one invalid DA-001 test fixture and seven false-negative residual certificates for real float64 CSR states. A targeted correction is justified without changing scientific thresholds, solver formulas, or expected physical results.
