# WP12-V2-R3 — H1 TET4 development results

**DEVELOPMENT_ONLY · NUMERICAL_EXECUTION_PERFORMED · FORMAL_QUALIFICATION_NOT_PERFORMED · WP12_STATUS=OPEN · WP13_STATUS=OPEN**

Date: 2026-10-26. Scope: one H1 TET4 operator audit using the frozen scientific checkout and archived WP12-U fields. The authorized development allowance was at most 10 sequential H1 invocations of 300 seconds; three were used. No new linear solve, mesh refinement, large benchmark, or WP12-W case was run.

## Identities and provenance

| Role | Commit | Git tree | Use |
|---|---|---|---|
| Scientific source | `00428adf38e9397340ac136f6f503a268eb671da` | `df4ec667bf746b042c900fad1f86bf542e1a437b` | Frozen candidate source; `solveur.__file__` resolved inside this checkout. |
| Runner | `731fd9d6b05efe227de60e8cb19ba095cc8b29d9` | `19b775be2d49890b890c41b6d56f5b1be082279b` | Preserved R2 local V&V runner; not modified. |
| Test/integration snapshot | `77e83b53859d3ad1e13afded6335d29d2f8c4d27` | `78436375a7ef674dfd5130f55edbc0757f7f1056` | Prospective R3 test and synthetic diagnostics. |

Development environment observed in the child: Python 3.13.17, pytest 8.4.1, NumPy 2.2.6, SciPy 1.15.2, h5py 3.14.0 and threadpoolctl 3.6.0. `solveur.__file__` resolved to the frozen science checkout. All six configured thread environment variables and the loaded numerical library thread counts were observed at one. This is local development provenance, not OS sandboxing or formal attestation.

The full attempt folders are preserved outside the repository under `E:\QFSolverWP12B\wp12-development\wp12_v2_r3\`. Run IDs and key artifact hashes:

| Attempt | Run ID | Pytest | Scientific classification | Key result hash |
|---|---|---|---|---|
| 1 | `20261026T152755Z-44c8aad4d2` | FAIL, 1 failure | INCOMPLETE; no numeric payload | `result.json` SHA-256 `1eaea84ac8bf45be090a86121826194d6989894363d2085352d257dc6f767ed9` |
| 2 | `20261026T153048Z-8254b00f22` | PASS, 1 test | INCONCLUSIVE; gamma assumptions unverified | payload SHA-256 `02194a517953573319c73e76d87e4dca6ec500d438beb69df25368f357c439f2` |
| 3 | `20261026T153321Z-8eb10a693a` | PASS, 1 test | INCONCLUSIVE; gamma assumptions unverified | payload SHA-256 `b696df0dbebc4dedfcdec10fcf2cc596634aa62555bc970a5cb5048d6eee28b9` |

Attempt 1 failed in the prospective test's element-incidence diagnostic: frozen connectivity gives contributors `[0, 5, 8, 9]` for global pair `(14,22)`, while the test expected `[0, 8, 9]`. This was a test instrumentation error, not a demonstrated production-physics failure. The expected incidence was corrected without changing any numerical threshold. Attempt 2 passed the test; attempt 3 changed only the emitted execution-state label and passed again. A read-only comparison found the numeric payloads identical between attempts 2 and 3 apart from that label.

Attempt 3 preserved `result.json` SHA-256 `252a31a78f5f168d287dd2cfc17c992ca9f52d791f35ccab8aa2e30b07091e12`, JUnit SHA-256 `eaf1a74c3389e2500442413bb940a56b5e199970b005c22f6bd3b0f1d4c309c3`, and the 1,131,839-byte numeric payload above. The selection record shows exactly the approved nodeid, `exact_match=true`, `source_import_ok=true` and unchanged `sys.path`.

## Test and diagnostic corrections

In `tests/unit/test_wp12_v2_tet4_operator_audit.py`:

- Replaced tuple indexing on the Python list `scalar_local` with list-then-matrix indexing in both transposed accesses.
- Added helpers to retain element-pair contribution values for scalar-list and batch-array representations.
- Added explicit construction and traversal of all 24 canonical matrix-free basis columns.
- Corrected the H1 `(14,22)` contributor list to `[0, 5, 8, 9]`, verified against the frozen connectivity/DOF incidence.
- Changed the payload state from a prospective placeholder to `RESULT_EMITTED_DURING_NODE_EXECUTION`.

Added `tests/synthetic/test_wp12_v2_r3_h1_diagnostics.py` for fake-matrix contribution indexing, all 24 columns, JSON/finite-value checks and rejection of non-finite values. These tests do not import `solveur` or assemble FEM matrices. Numerical assertions, thresholds, gamma assumptions, production source and fixtures were not changed.

## Quantitative H1 observations from attempt 3

The model contains 12 TET4 elements, 12 nodes, 36 total DOFs, 12 fixed DOFs and 24 free DOFs in SI units. The four archived terminal-node vertical loads sum to `(0, 0, -1) N`. The calculation reassembled stiffness and evaluated matrix-free products against the archived U3 displacement fields; it did not perform a new linear solve.

### Assembly and exact-rational reference

The rational reference was independently formed from the exact binary64 fixture coordinates and material values using rational arithmetic. This is independent arithmetic for the **same discrete H1 model**; it is not an independent continuum solution or external-solver validation.

| Quantity | Observed | Existing criterion | Interpretation |
|---|---:|---:|---|
| Scalar assembled global relative Frobenius error | `7.764696219188759e-17` | `1e-12` | Within criterion. |
| Batch assembled global relative Frobenius error | `8.348118354249543e-17` | `1e-12` | Within criterion. |
| Exact-reference global stiffness symmetry | exact | identity | Holds for the rational reference. |
| Batch global relative symmetry Frobenius error | `1.74464819524665e-17` | no separate aggregate threshold | A stored asymmetric entry exists despite locally symmetric element matrices. |

For global pair `(14,22)`, the batch stored difference `K[14,22]-K[22,14]` is exactly `1/131072 = 7.62939453125e-6 N/m`. Each side receives elements `[0,5,8,9]`; the exact-fraction gamma diagnostic encloses the difference. The stored local entries for elements 0/8 are `-0x1.0b74ecdf2df2ep+33`, and for 5/9 are `-0x1.912f634ec4ec5p+33`, mirrored consistently between scalar and batch paths. Because the runtime rounding mode and every internal reduction intermediate were not independently established, satisfying the computed bound does not make the gamma conclusion a PASS.

### Matrix-free operator

All 24 canonical free-DOF columns were evaluated.

| Comparison | Observed relative Frobenius error |
|---|---:|
| Matrix-free vs exact rational free matrix | `6.26907206209747e-17` |
| Direct assembled vs exact rational free matrix | `8.61992882461894e-17` |
| Matrix-free vs direct assembled | `7.26092245156046e-17` |
| Maximum column error, normalized by exact free-matrix Frobenius norm | `2.262611926781596e-17` |

The matrix-free/direct absolute difference has Frobenius norm `4.05339632746761e-5 N/m`, infinity norm `3.52859497070312e-5 N/m`, and maximum entry `3.0517578125e-5 N/m`. The componentwise kernel-plus-scatter bounds were computed and satisfied conditionally. These are finite-dimensional operator comparisons for this fixture, not a general complexity or convergence result.

### Archived field residuals, reactions and energy identities

- Matrix-free archived-field relative free residual: `8.01766808946804e-9`, against the inherited `1e-8` criterion. This passes narrowly, with about 1.25× margin.
- Direct archived-field relative free residual: `1.1492670024590035e-13`, against the inherited `1e-7` criterion.
- Direct residual normalization retains the inherited denominator `max(||f||, ||Ku||, 1)` in SI numerical values. The constant `1` mixes dimensions and makes the metric unit-system dependent; the frozen criterion was not changed, and this result must not be described as unit-invariant.
- Recomputed support reactions (direct) are approximately `(-2.5591e-14, 7.4274e-14, 1.000000000000065) N`; matrix-free reactions are approximately `(9.4051e-11, -9.8934e-12, 0.9999999999905717) N`.
- Recomputed support moments about the fixture origin (direct) are approximately `(0.19999999999995957, -4.000000000000251, 2.4692e-13) N·m`; matrix-free moments are approximately `(0.19999999999759668, -4.000000000001199, -1.6028e-12) N·m`.
- Exact residual-projection identities and their Cauchy bounds for force and moment balance hold for both routes. These are discrete equilibrium identities.
- The exact energy/work identity `2U-W = u_freeᵀr_free` holds for both routes. Approximate direct `U=2.574636570305104e-9 J`, `W=5.1492731406099025e-9 J`; matrix-free `U=2.5746365703056126e-9 J`, `W=5.14927314061041e-9 J`. This identity checks algebraic consistency of the archived solution and residual; it does not establish physical accuracy or convergence.
- The archived fields' relative L2 difference is `4.259605142952878e-12`. Mean terminal-face `UZ` and load-conjugate displacement are approximately `-5.14927314061e-9 m` for both routes.
- Seven synthetic negative controls detected the configured corruptions (missing contribution, shifted DOF map, mirrored local perturbation, symmetric wrong matrix, perturbed matrix-free column, inconsistent residual and non-finite data).

## Verdict and limits

- Development pytest: PASS on attempts 2 and 3.
- Mandatory numerical assertions: 12 PASS on attempt 3.
- Gamma-conditional assertion records: four `NOT_REACHED`; rounding assumptions remain unverified.
- `gamma_scientific_status=INCONCLUSIVE` and `overall_scientific_status=INCONCLUSIVE` are required and preserved. The diagnostic booleans `gamma_bound_evaluated=true` and `gamma_bound_satisfied=true` do not override the missing rounding/reduction evidence.
- Attempt 1 remains a preserved test instrumentation FAIL. The formal R2 failure, its one-attempt ledger and U3 historical FAIL are unchanged.
- No continuum mesh-convergence evidence, external-solver comparison, general TET4 qualification, WP12-W execution or formal R3 attempt was performed.
- Local runs were non-attested and lacked a filesystem sandbox and hard CPU/RAM/disk limits. Timings are test-invocation timings, not performance benchmarks.
