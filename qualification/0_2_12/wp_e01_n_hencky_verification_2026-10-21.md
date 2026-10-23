# WP-E01-N — Hencky bounded numerical verification

Date: 2026-10-21  
Scope: one fixed-target Windows-supervised collection and execution of the frozen WP-E01-M material-point module.

## Result

The fixed-target supervisor collected exactly **36 authorized nodes** from **23 test functions**, then executed that same collection once. The result was **35 passed, 1 failed, 0 skipped, 0 xfailed, 0 xpassed**. The failed node was `test_left_rotation_of_stretch_is_objective_for_all_stress_measures`. No test, production source, registry, or scientific threshold was changed after the run. Numerical execution stopped after the failure as required.

The failure is in a componentwise PK2 objectivity assertion with zero absolute tolerance. It reports a `9.57020104e-06 Pa` off-diagonal value against an expected exact zero while the diagonal PK2 stresses are about `1.155017e10` to `3.764486e10 Pa`. The reviewer’s independent read-only assessment is that this magnitude is consistent with floating-point roundoff in the generated rotation, `C = F^T F`, and the spectral transform; it is not evidence of a production stress-transform defect. The assertion uses `rtol=2e-13` and NumPy’s default `atol=0`, so any nonzero value compared with a zero reference fails. This is a likely test-oracle tolerance defect, but no correction or rerun is authorized by this campaign.

The objective test passed its prior checks for Hencky strain, energy, and logarithmic-strain-conjugate stress invariance. It stopped at the PK2 comparison; its subsequent PK1 covariance and Cauchy objectivity assertions were not reached. A separate non-rotated stress-transformation test passed.

## Repository and frozen identities

The starting repository was `C:\wpc01-frictionless-public-integration-wt\wp-e01-m`, origin `https://github.com/emptiesvoid-cloud/QF_solver.git`, branch `codex/qf-wp-e01-m-logarithmic-strain-20261021`, HEAD `702841c4807f8963794440175e1b8172a4d93d33`. The supervisor now checks the actual Git metadata HEAD against that exact starting commit before launching either phase.

The test, production kernel, registry, and original M manifest stayed unchanged:

| Artifact | SHA-256 |
|---|---|
| `tests/unit/test_wp_e01m_hencky_material_point.py` | `55e8cb65c77f724799b40415451759dc8a99f980194e95c4ccb2eacfadec6e83` |
| `src/solveur/materials/finite_strain_hencky.py` | `b318dad553073f848b96528c61589ab2015c1eb1dd8fa52cb0bd52d13b09eab2` |
| `tests/conftest.py` | `8b90d1556f7f611759378fe051bca716905832ecb2731e38d111d001a2500261` |
| Original WP-E01-M static manifest | `42ca471ba4ae6379efa819573ed1c19f743754f48b4d21213bbc2673fdde75ed` |
| Pinned Job Object helper | `9bd8c75b19b49c758f9558cf9299eeedc18762b1e40dbd69968377a94d6c9090` |

Prepared execution-profile files:

| Artifact | SHA-256 |
|---|---|
| `experiments/wp_e01m_hencky_supervisor.py` | `c68da0b6d6b8993536b6cdcc7594f1090dea8207241453f875ee4718f8b92642` |
| `experiments/wp_e01m_hencky_collection_guard.py` | `65b5da366eaf76d7ac9587e72ebce5006a70d42fcb3cf9d047755181dc07849d` |
| `qualification/0_2_12/wp_e01_n_hencky_runtime_execution_manifest_2026-10-21.json` | `069561e8c54b543b8d4500d94e96008bcdc45ee7793245d00e8790859fd0c3a3` |

The runtime manifest pins the supervisor, guard, helper, all 26 frozen source-map entries, Python 3.13.1, pytest 8.4.1, NumPy 2.2.6, exact target, test classification, and requested limits. The supervisor and collection guard fail closed on any identity or inventory mismatch. The final static preflight passed.

## Supervisor and execution chronology

The supervisor used one Python pytest child per phase. Each child was created suspended, assigned to a Windows Job Object before resume, and verified by Job Object limit readback. Enforced settings were:

Parent invocation (the only launch command used): `C:\Python313\python.exe -m experiments.wp_e01m_hencky_supervisor`.

* Process committed-memory cap: 268,435,456 bytes.
* Job committed-memory cap: 268,435,456 bytes.
* Parent deadline: 120 seconds per phase.
* Active process limit: 1.
* Kill-on-job-close enabled; breakaway disabled.
* BLAS thread environment variables set to 1; pytest parallelization and automatic retry disabled.

Four earlier parent invocations failed at preflight and launched no child. They exposed and were corrected in the new profile only: (1) an extra descriptive target field, (2) unsorted function names in the target inventory, (3) the manifest’s enforcement description omitted from the supervisor’s exact resource binding, and (4) the original M manifest’s authorization flags being nested under `execution_state`. The frozen M manifest was not edited. The profile now validates its nested values as `execution_authorized=false`, `collection_authorized=false`, `numerical_tests_run=false`, `owner_go_required=true`, and `production_solver_or_fem_authorized=false`.

The initial child environment uses Python `-S`, a fixed `PATH`/`PYTHONPATH`, plugin autoload off, and an explicit collection-guard plugin. Because `-S` does not load `sitecustomize`, the manifest no longer claims that it does. Child processes are prevented by the Job Object active-process cap of one and no-breakaway policy. The target AST contains only `numpy`, `pytest`, and `solveur` imports and no prohibited process, network, native-FEM, Gmsh, or public-solver imports/calls. The source-level import-closure review found the `solveur.materials` package initializer imports Python material definitions; this is a reviewed, pinned-source finding, not an automatically computed complete import closure.

### Observed collection

The guarded collection returned exactly **36 unique node IDs**, covering the bound 23 functions. All nodes were under the approved module, had the `numerical_unit` marker, had no `unclassified` marker, and used only the guard’s allowed fixtures. The full node inventory is preserved in `wp_e01_n_runs/20261021T132318Z/collection/collection_nodes.json`.

### Resource and process evidence

| Phase | Exit | Elapsed | Peak process commit | Peak job commit | PID after resume → exit | Cleanup |
|---|---:|---:|---:|---:|---|---|
| Collection | 0 | 2.036644 s | 36,237,312 B | 36,237,312 B | 36360 → none | `VERIFIED_WINDOWS_JOB_CLOSED` |
| Execution | 1 (test failure) | 1.224583 s | 70,111,232 B | 70,111,232 B | 36648 → none | `VERIFIED_WINDOWS_JOB_CLOSED` |

Both peaks were below the 256 MiB caps. The execution child exited normally after pytest reported the failure; this was not a timeout, resource-cap event, or cleanup failure. Stderr was empty for both phases. No additional process was observed by the Job Object. Memory figures are committed-memory accounting, not RSS/working-set measurements.

## Scientific evidence

| Area | Observed result | Interpretation and limit |
|---|---|---|
| Identity deformation | Pass | Zero energy and stress within the proposed check. |
| Proper rigid rotations | Pass | Stress-free rotation cases passed. |
| Principal stretches and closed-form responses | Pass | Uniaxial, isotropic volumetric, isochoric, and simple-shear checks passed. |
| Objectivity under left rotation | Partial | Strain, energy, and conjugate-stress assertions passed; PK2 comparison failed at a zero reference component. PK1 and Cauchy assertions later in this test did not execute. |
| Small-strain limit | Pass | Three amplitudes passed the stated asymptotic bound. |
| Repeated and near-repeated spectra | Pass | Finite/symmetric response and the specified near-repeat resolution check passed; this is not a tangent validation. |
| Invalid F | Pass | Singular, inverted, nonfinite, and complex inputs were refused under the tested cases. |
| Principal strain / energy definition | Pass | Reconstruction and energy-definition checks passed; these include self-consistency assertions using returned kinematics. |
| PK1 energy derivative | 3 pass | Three fixed directions passed at the single `h=2e-6` centered-difference step. No step-size convergence plateau was evaluated. |
| PK1/PK2/Cauchy transformation | Partial | The non-rotated explicit `P=F S`, `sigma=F S F^T/J`, and Cauchy-symmetry case passed. Full rotated covariance was not completed because the objective test stopped at PK2. |
| TET4/HEX8 affine gradients | Pass | Constant F was recovered at the TET4 point and all eight existing HEX8 quadrature points for the test affine maps. |
| TET4/HEX8 force references | Pass | Force-only local adapters matched the analytical uniform-PK1 reference for the tested affine uniaxial stretch; nodal resultant checks passed. No global assembly or FEM solve was used. |
| Invalid reference geometry | Pass | Tested inverted/degenerate TET4 and inverted HEX8 geometry were rejected. |
| Consistent tangent | Pass as refusal | Response reports `NOT_IMPLEMENTED`; no tangent correctness claim follows. |

The force oracle uses the analytic uniaxial response

`P11=(4 mu/3+kappa) log(lambda)/lambda`, `P22=P33=(kappa-2 mu/3) log(lambda)`

with independently formed constant-TET4 shape gradients and the exact unit-cube integrated HEX8 shape gradients. It is bounded element-local algebra, not global element assembly. The test output did not emit per-case numerical error maxima for passing assertions; none are inferred here.

For the failing PK2 component, the expected value is exactly zero, so the comparison’s effective allowance is exactly zero regardless of the supplied relative tolerance. Using the printed stress scale (about `5e10 Pa` in norm), the observed `9.57e-6 Pa` residual is approximately `2e-16` relative; this ratio is a post-run estimate from rounded printed values, not a metric emitted by the test. The independent reviewer agrees this supports roundoff/tolerance as the most likely explanation, but does not independently prove the transform accurate across all spectra.

## Follow-up preparation

### Energy derivative convergence

The existing three PK1 directional-energy checks use a single centered step `h=2e-6`. A future test-only extension should evaluate a geometric sequence `h_k=h_0/2^k`, checking positive determinant and finite spectral admissibility at `F +/- h_k D`. Record

`D_h = [W(F+hD)-W(F-hD)]/(2h)` and `g = P(F):D`.

Report absolute error `|D_h-g|`, a normalized error using both `|g|` and `||P||_F ||D||_F`, and a Richardson estimate `(4 D_(h/2)-D_h)/3`. Confirm the expected centered-difference `O(h^2)` regime before a roundoff plateau, and report when no stable window exists as `NOT_EVALUABLE`. Keep all new step ranges and tolerances proposed. Do not alter this executed test identity or imply these checks were run.

### Future consistent tangent design

For `E_H=1/2 log(C)`, `C=F^T F`, and `M_H=dW/dE_H=2 mu dev(E_H)+kappa tr(E_H) I`, the work-conjugate PK2 stress is `S = Dlog_C[M_H]`. For perturbation `H=dF`,

`dC = F^T H + H^T F`,

`dE_H = 1/2 Dlog_C[dC]`,

`dM_H = 2 mu dev(dE_H)+kappa tr(dE_H) I`,

`dS = D^2log_C[dC, M_H] + Dlog_C[dM_H]`,

`dP = H S + F dS`.

The material tangent is the fourth-order action `A:H=dP`, with stable first- and second-divided differences of `log` and continuous repeated/clustered-eigenvalue limits. In a total-Lagrangian element, the `H S` contribution is the initial-stress/geometric part and `F dS` is the constitutive/material part. A future V&V package should compare the independent material-point action against centered PK1 finite differences, test repeated spectra and rigid rotation, then verify the assembled force derivative and material/geometric decomposition separately. No tangent is implemented or verified here.

## Review, blockers, and next Owner decision

An authorized separate reviewer completed a read-only assessment of the run output and source formula. The review classified the sole mismatch as consistent with roundoff against an overstrict zero-component comparison, not as demonstrated production defect; it also cautioned that this case does not establish PK2 accuracy generally. This is independent of the primary execution agent, but not an external laboratory review.

Required next Owner decision: authorize a new, exact-hash campaign after reviewing a proposed test-only objective-invariance assertion with a stress-scaled absolute/normwise floor (threshold remains Owner-controlled), plus multi-step PK1 energy-derivative diagnostics. The new test/registry/supervisor/manifest identity must be frozen and reviewed before any rerun. No correction, rerun, FEM integration, tangent implementation, qualification, or promotion is implied by this report.

Current scientific statuses:

* `LOGARITHMIC_STRAIN_VNV`: `PARTIAL` (35/36; one objective PK2 assertion failed).
* `HENCKY_ELASTIC_MATERIAL_VNV`: `PARTIAL`.
* `STRESS_MEASURE_TRANSFORMATIONS`: `PARTIAL`.
* `TET4_HEX8_FORCE_REFERENCE`: `VERIFIED_BOUNDED` for the tested force-only local algebra.
* `HENCKY_CONSISTENT_TANGENT`: `NOT_IMPLEMENTED`.
* `ENERGY_DERIVATIVE_CONVERGENCE`: `INCOMPLETE / PREPARED_NOT_RUN`.
* `GLOBAL_HENCKY_FEM_ASSEMBLY`: `NOT_RUN`.
* `FINITE_STRAIN_J2`: `NOT_IMPLEMENTED`.
* `PRODUCTION_NEWTON_ARMIJO`: `NOT_VERIFIED`.
* `SCIENTIFIC_QUALIFICATION`: `NOT_ACQUIRED`.
* `WP_E01_STATUS`: `OPEN / EXPERIMENTAL_TARGET`.

All run artifacts and their hashes are preserved under `qualification/0_2_12/wp_e01_n_runs/20261021T132318Z/`. The runtime `evidence_hashes.json` covers phase logs, phase results, collection inventory, preflight, and pytest node results; its own SHA-256 is recorded in the final handoff.
