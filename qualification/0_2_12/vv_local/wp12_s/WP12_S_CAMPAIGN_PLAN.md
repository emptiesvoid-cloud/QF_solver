# WP12-S campaign plan

**Status:** `EXECUTION_RECORDED`<br>
**Numerical execution:** `PERFORMED_FOR_EIGHT_AUTHORIZED_CASES`<br>
**WP12:** `OPEN`

## Objective and identities

Produce actual numerical observables for the defined small checks, then preserve the raw values, references, errors, residuals, per-level data, and review. WP12-R established only assertion execution for its four cases; those receipts do not contain the numerical values.

The scientific checkout remains frozen at commit `00428adf38e9397340ac136f6f503a268eb671da`, tree `df4ec667bf746b042c900fad1f86bf542e1a437b`. The test checkout is a distinct clean tree containing the fixed WP12-S wrappers and their pinned helper tests. The runner checkout is separately pinned and includes only a fixed local-V&V command profile. The exact commits/trees, interpreter, packages, file digests, and command profile are recorded in [the prepared manifest](WP12_S_QUANTITATIVE_MANIFEST.json); none substitutes for the scientific commit.

## Approval boundary

WP12-R's Owner decision was bound to manifest SHA-256 `ea8f32e24d9eaded198230b0bc5f8aab45ed76293c3e73bdf77533e0bf08a0db`. It authorized the four original nodes only and does not authorize these instrumented wrappers or new cases. This new manifest remains `PREPARED_NOT_AUTHORIZED`, with `execution_authorized: false`.

The Owner subsequently approved all eight cases individually against the exact manifest hash, displayed oracle/criteria, interpreter, exact nodeids, one attempt, timeouts/log cap, evidence root, and non-attested local limits. TET4 was approved as characterization only, without a convergence acceptance or 3-D validation claim. Actual outcomes are in [the execution report](WP12_S_EXECUTION_REPORT.md). This plan remains the scope snapshot; the manifest's historical prepared status was not rewritten.

## Prepared units

| Case | Exact selected node | Purpose and evidence class | Frozen criterion | Proposed wall timeout |
|---|---|---|---|---:|
| `ALG-PROJ-QUANT-001` | `tests/unit/test_wp12_s_quantitative_extraction.py::test_wp12_s_alg_proj_001` | Structured projection versus dense bilinear identity; algebraic, no FEM | Existing `rtol=2e-16`, `atol=2e-16`, exact symmetry checks | 120 s |
| `MODAL-DISCRETE-QUANT-001` | `tests/unit/test_wp12_s_quantitative_extraction.py::test_wp12_s_modal_discrete_001` | One-node ground spring/concentrated-mass modal response | Existing frequency `rel=1e-12`; relative modal residual `<1e-12` | 120 s |
| `MODAL-2DOF-QUANT-001` | `tests/unit/test_wp12_s_quantitative_extraction.py::test_wp12_s_modal_2dof_001` | Coupled two-DOF basis and projected operators; same-SciPy-backend consistency | Existing eigenvalue `rtol=atol=1e-12`; projected mass `atol=1e-12`; projected stiffness/reconstruction `rtol=atol=1e-11` | 120 s |
| `DYN-SDOF-QUANT-001` | `tests/unit/test_wp12_s_quantitative_extraction.py::test_wp12_s_dyn_sdof_001` | Newmark free-vibration history, error and energy drift | Existing final-displacement `rtol=2e-4`, `atol=1e-9`; projection `<1e-12`; reduced equilibrium `<1e-7` | 180 s |
| `MODAL-2DOF-POLY-001` | `tests/unit/test_wp12_s_quantitative_extraction.py::test_wp12_s_modal_2dof_poly_001` | Scalar characteristic-polynomial roots versus production eigenvalues | WP04 eigenvalue relative tolerance `1e-10`; modal residual and mass-orthogonality limits `1e-8` | 120 s |
| `STAT-BEAM-UY-001` | `tests/unit/test_wp12_s_quantitative_extraction.py::test_wp12_s_stat_beam_uy_001` | One-element BEAM2 bending in global UY with RZ rotation | Existing Timoshenko displacement/rotation `rel=1e-12` | 180 s |
| `STAT-BEAM-UZ-001` | `tests/unit/test_wp12_s_quantitative_extraction.py::test_wp12_s_stat_beam_uz_001` | One-element BEAM2 bending in global UZ with RY rotation | Existing Timoshenko displacement/rotation `rel=1e-12` | 180 s |
| `FEM-TET4-H-001` | `tests/unit/test_wp12_s_quantitative_extraction.py::test_wp12_s_fem_tet4_h_001` | Three nested matrix-free TET4 meshes; bounded characterization | Expected mesh inventory and finite outputs only. No convergence or physical PASS threshold; beam-theory difference and helper status are diagnostic | 1,800 s |

The timeouts and 16 MiB per-stream log cap are operational proposals, not Owner-approved resource guarantees. CPU/RAM are not hard-limited, file access is not sandboxed, and the local runner cannot guarantee descendant termination. The Owner previously accepted these limits only for the four WP12-R cases. The new cases need a new per-case acceptance of the limits.

## Execution sequence after approval

The authorized sequence was run one exact node per process, in table order, with one attempt maximum. Raw evidence and partial outputs were preserved; there were no retries. One pytest failure (`MODAL-2DOF-POLY-001`) remains `FAIL`; the TET4 helper reported `WARNING`. See the execution report for classification, payloads, and independent review. No separate oracle verdict or qualification status is assigned here.

The TET4 case runs only its three declared factors, sequentially, through a fixed wrapper. The corrected element counts are 12/96/768, not the 24/192/1536 values in the older planning page; see [the TET4 review](TET4_CONVERGENCE_REPORT.md). Its mesh-to-mesh changes, solver residuals, time and estimated operator memory are reported separately. No asymptotic order or 3-D validation is inferred.

## Output handling

For small tests, the wrapper emits one JSON line with schema `qf-wp12-s-observables-v1` and the exact `case_id`. Every prepared case pins that exact schema in its manifest. The local runner streams pytest output (`-s`), requires the marker when the manifest declares it, checks exact schema and case identity, and rejects duplicates. A pytest pass with a missing required payload is `INFRA_ERROR`; a JUnit scientific assertion failure remains `FAIL` even if the payload is malformed or absent. The wrappers emit measured values before their post-computation acceptance assertions so a failure can retain the measurements.

The TET4 wrapper writes the solver's `summary.json` and `report.md`, an additional `results.csv`, and all three generated model HDF5 files under the fresh pytest temporary directory. These are preserved inside that attempt directory. The helper's `status` field is not the WP12-S scientific verdict.

## Cost and evidence limits

- Projection and discrete/modal scalar cases: low runtime, algebraic or small-system oracle.
- Newmark and BEAM2: low-to-moderate local runtime, analytical checks bounded to one reduced DOF and one straight one-element beam respectively.
- TET4: moderate bounded local CPU/memory and disk use; no hard quota is available. Its reference is 1-D beam theory, not exact 3-D elasticity.
- No case performs mesh/time-step convergence except the three TET4 resolutions. The three levels can characterize a trend but may not demonstrate an asymptotic regime.
- No external solver, experiment, publication figure, or release claim is included.
