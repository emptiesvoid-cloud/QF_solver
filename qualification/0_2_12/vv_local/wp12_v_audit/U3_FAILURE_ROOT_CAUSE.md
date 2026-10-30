# WP12-U U3 failure root-cause audit

## Finding

The archived `TET4-ROUTE-CROSSCHECK-001` execution is a real test **FAIL**: the final assertion requires the assembled batched global stiffness to be exactly symmetric, and the archived matrix is not. The failed assertion is not enough to classify the discrepancy as benign. The observed defect is one ULP at one recorded reciprocal pair, while the test's relative-error and residual diagnostics are otherwise small; those facts bound its observed scale, but do not waive the exact-symmetry requirement or prove the governing result is unaffected.

The asserted condition is `exact_stiffness_symmetric and scalar_stiffness_symmetric and assembled_stiffness_symmetric` at `tests/unit/test_wp12_u_tet4_route_crosscheck.py:637`. The archived values are:

| Matrix / entry | K[14,22] | K[22,14] | exact stored symmetry |
|---|---:|---:|---|
| exact binary-input rational reference rounded to float | -44871794871.79487 | -44871794871.79487 | yes |
| scalar element assembly | -44871794871.794876 | -44871794871.794876 | yes |
| chunked SciPy batch assembly | -44871794871.79487 | -44871794871.794876 | no |

The matrix-wide diagnostics archived in the same JSON are scalar-relative-to-exact `9.63860460493275e-17`, batch-relative-to-exact `9.050773047627961e-17`, and scalar-to-batch `9.229878417674968e-17`. These are Frobenius-relative diagnostics, not a substitute for exact stored symmetry. The separate `audit_large.json` records relative symmetry error `1.7446481952466456e-17` and its tolerance-based audit status is PASS; the test assertion checks `np.array_equal(K, K.T)`, a strictly stronger contract. The audit PASS does not invalidate the U3 FAIL.

## Trace through the test and implementation

- `test_wp12_u_tet4_route_crosscheck.py:286-316` constructs scalar global K by looping over `model.tet4`, adds `Tet4Element.stiffness()` into dense slices, converts `assembly.stiffness` to dense, and checks exact equality with its transpose. The same block creates the exact rational reference and computes the relative errors.
- `solveur/elements/solid/tet4.py:44-51` computes scalar TET4 stiffness and returns `symmetrize(ke)`.
- `solveur/large/tet4_batch.py:8-27` computes the batch TET4 kernel with `einsum` and returns `0.5 * (K + K.T)` for every element. Thus both local kernel implementations explicitly symmetrize each local stiffness; the archived scalar global matrix is also exactly symmetric.
- `solveur/large/assembler.py:48-99, 380-399` is the executed `ChunkedScipyAssembler` path: one chunk is built from flattened element matrices using `csr_matrix((vals, (rows, cols)), shape=...)`, then submitted to `SparseCsrAccumulator`. This fixture has 12 elements and the test uses chunk size 8192, so there is one chunk; pairwise accumulator merging across chunks is not involved in this specific run. `SparseCsrAccumulator.finalize()` still calls `sum_duplicates()`.
- In the archived SciPy 1.15.2 implementation, the `(data, (rows, cols))` CSR constructor routes through COO-to-compressed conversion and calls `sum_duplicates`; COO-to-CSR initially preserves duplicates, and the compressed duplicate path sorts column indices then adds equal-column values sequentially. The source's comparator for the sort compares only the column index, so it does not state a stable order among equal-column duplicates. Therefore floating-point duplicate coalescence can produce different low bits for reciprocal global entries even if local element matrices are bitwise symmetric. This is a plausible mechanism consistent with the evidence, not a proved exact ordering for this pair.
- The route comparison builds a matrix-free operator from scalar `Tet4Element` templates (`solveur/large/matrix_free.py:80-115, 230-234`) and scatters nodal contributions using `np.bincount` (`:211-227`). It is a distinct accumulation route. The direct SciPy solver uses the assembled matrix restricted to free DOFs (`solveur/large/solver.py:108-135`). Here DOFs 14 and 22 are free; the archived fixed set is 0 through 11. The discrepancy is therefore present in the free matrix used by the direct route, not only in a constrained row or column that the solve discards.

## Contributions and order: what is and is not established

The archived connectivity identifies the only elements incident to both nodes 4 and 7 (the global pair is node 4, component z / node 7, component y): zero-based element indices **0, 8, and 9**. Their local reciprocal matrix positions are respectively `(5,10)/(10,5)`, `(2,7)/(7,2)`, and `(2,4)/(4,2)`. That incidence follows from the archived connectivity array and the DOF map `3*node+component` in `tet4_batch.py:39-44`.

The U3 run archives the full rational reference and assembled global matrices, connectivity, test stdout and solver output, but no local matrices for elements 8 or 9 and no trace of duplicate values or their post-sort order at CSR coalescence. A related earlier archived U2 run (`TET4-AFFINE-ORACLE-001`, `20261026T120231Z-ba477b0a779b`) exposes scalar, batch, and exact 12-by-12 local matrices for the first TET4. Its first-element coordinates exactly match U3 connectivity element 0: `[[0,0,0],[2,0,0],[2,0.4,0],[2,0.4,0.4]]` m; U2 and U3 cite the same fixture SHA-256 `4807fea4cde876f57ef1e376f9b0791f5367526d182e236655b39e73e57baa7d`, and both record material `E=70000000000 Pa`, `nu=0.3`. For element 0, U2 records local scalar and batch K[5,10] = K[10,5] = `-8974358974.358974 N/m`; the exact reference rounds to the same displayed values. This is one of the three contributors. Values for elements 8 and 9 and the CSR duplicate order remain NOT_RECORDED, so the exact summed sequence and precise production cause cannot be proven from the campaign archive.
## Classification and scope

- **Demonstrated:** exact-rational reference symmetric; scalar assembled global matrix symmetric; batch assembled global matrix not symmetric; recorded reciprocal mismatch is 1 ULP; assertion fails on that condition; affected pair lies in free DOFs and has three shared-element contributors.
- **Mechanism supported by implementation, not pairwise-proven:** IEEE-754 non-associativity combined with sparse duplicate coalescence whose equal-key order is not contractually stable can explain low-bit asymmetry.
- **Not established:** physical/continuum accuracy, reproducibility across SciPy/compiler/platform variations, or which element's rounded entry/order accounts for the final ULP. The separate [archived-data review](MATRIX_FREE_DIRECT_EVIDENCE_REVIEW.md) section 3.1 verifies an exact-rational perturbation bound for the stored free matrices: their effect on the same-RHS mathematical H1 solution is bounded at approximately 1.25e-12 relatively for batch. That new audit result bounds this fixture's operator effect; it does not identify the summation order or certify physical accuracy.
- **Classification:** primary `FLOATING_POINT_ASSERTION_DEFECT`: the global batch/CSR path has no source or API contract guaranteeing bitwise symmetric storage after independent duplicate coalescence, yet the U3 assertion requires it. The observed producer stage is the global batched sparse assembly/coalescence path; this identifies where the gap appears, not a proven exact summation sequence. `ASSEMBLY_ORDER_ROUNDOFF` remains a plausible production mechanism, not a demonstrated cause for the final ULP. The precise production cause is `INCONCLUSIVE` from the available per-element records.
- **Disposition:** retain the execution as FAIL pending an explicitly reviewed criterion/contract decision or evidence that directly resolves the discrepancy. The one-ULP mismatch alone establishes neither a major mechanical defect nor mechanical harmlessness. A tolerance-based audit PASS and a small global relative norm do not by themselves reclassify it.

## Evidence identities

- Science source checkout: `00428adf38e9397340ac136f6f503a268eb671da`.
- U tests checkout: `9c7df65403fc15dc6d12365534172eac87f2ee70`.
- Runner checkout: `0bd8ebb5a886ac89a8216e65ff37d59fb510fb61`.
- Archived run: `WP12-U-TARGETED-001/TET4-ROUTE-CROSSCHECK-001/20261026T120509Z-3a69e91f9b42`, status FAIL, exit code 1, selected nodeid `tests/unit/test_wp12_u_tet4_route_crosscheck.py::test_tet4_route_crosscheck_001`.
- `receipt.json` SHA-256 `c47a566d97998746a58823ce3f88b5f4950b7cf597bf62129f72aa54c3956542` (also recorded by `receipt.sha256.json`).
- `stdout.log` SHA-256 `03f033e0d8369704307b7d1d9d95ff962534f359ab2c2fdb472be39ad42f625e`.
- archived `assembled_direct/audit_large.json` SHA-256 `109ca98e1d77c4a3c80b8554a9fe57ebf3e00a66f9cb723008cbcffd15347b44`.
- archived `assembled_direct/summary.json` SHA-256 `9861a3718f7d943be5b003e0f31e4211a79d55d8b905686a8e98f79edc18941b`.
- U2 first-element local-matrix run `TET4-AFFINE-ORACLE-001/20261026T120231Z-ba477b0a779b`, status `PYTEST_PASS_ONLY`; `receipt.json` SHA-256 `c5be56b7af3496ec6c34017bea42e452e5f1f44e2c984f48948bc0dc6aea2475`, `stdout.log` SHA-256 `4fb1117dcb0532a44e4d573fa070dbe2b75b3d3089879e61388e9c5100579f3e`.
- Source module and test hashes were checked during this audit; the separate check summary is in the accompanying floating-point symmetry report.

No tests, kernels, solver, benchmark, or new assembly were run for this audit. No evidence, source, or test file was changed.
