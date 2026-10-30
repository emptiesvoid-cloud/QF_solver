# WP12-U matrix symmetry and floating-point audit

## Contract summary

This audit distinguishes three things that should not be conflated:

1. **Local element symmetry:** the scalar and batched elastic TET4 stiffness kernels explicitly symmetrize each 12×12 element matrix. For finite, ordinary values, their returned reciprocal local entries are bitwise equal by construction.
2. **Global assembled matrix symmetry:** the SciPy batch assembler coalesces duplicate contributions for each global coordinate independently. The path does not impose or validate `K == K.T` after global assembly, and floating-point duplicate summation is not a contract that preserves exact reciprocal equality.
3. **Tolerance diagnostics:** the archived matrix audit classifies symmetry using a relative norm threshold `1e-9`; its PASS means only that this tolerance test was satisfied. The U3 test separately asserts exact array equality. These contracts have different meanings and the tolerance result cannot convert the failed exact check into a pass.

## Source trace

### Scalar element and global accumulation

`solveur/elements/solid/tet4.py:44-51` forms `ke = volume * (B.T @ D @ B)` and returns `symmetrize(ke)`. The test at `tests/unit/test_wp12_u_tet4_route_crosscheck.py:286-292` accumulates each local matrix into a dense global matrix by element order. In the archived run, this scalar global result is exactly symmetric under `np.array_equal(K, K.T)`.

The exact reference uses rational arithmetic over the binary floating-point model/material inputs in the test helper functions (`test_wp12_u_tet4_route_crosscheck.py:31-116`), and its archived global matrix is exactly symmetric. It is a comparison oracle over the stored binary inputs, not an independent physical/material-data validation.

### Batched element and SciPy global accumulation

`solveur/large/tet4_batch.py:8-27` builds batched local stiffness matrices and applies `0.5 * (stiffness + stiffness.transpose(0, 2, 1))`. The local batch kernel therefore returns exactly symmetric matrices, but that alone does not imply exact symmetry after global duplicate coalescence.

`solveur/large/assembler.py:48-99, 380-399` passes row-major flattened local stiffness values with their global row/column indices to `csr_matrix((vals, (rows, cols)), shape=...)`, then adds the chunk to `SparseCsrAccumulator`. The run has one chunk (12 elements; chunk size 8192), so the accumulator's multi-chunk pairwise merge is not implicated in this execution. The `SparseCsrAccumulator.finalize()` source (`solveur/core/assembly/sparse.py:35-45`) calls `sum_duplicates()` and eliminates explicit zeros.

The archived SciPy 1.15.2 source establishes this chain:

- CSR tuple construction with `(data, (row, col))` uses the COO conversion path and invokes `sum_duplicates()` in [`_compressed.py` at SciPy v1.15.2](https://github.com/scipy/scipy/blob/v1.15.2/scipy/sparse/_compressed.py#L49-L55).
- COO-to-CSR conversion first writes entries into CSR, preserving duplicate coordinates, then calls `sum_duplicates()` in [`_coo.py`](https://github.com/scipy/scipy/blob/v1.15.2/scipy/sparse/_coo.py#L319-L347).
- `sum_duplicates()` sorts columns and calls the sparse kernel in [`_compressed.py`](https://github.com/scipy/scipy/blob/v1.15.2/scipy/sparse/_compressed.py#L1121-L1133).
- The CSR sort comparator compares only column indices, and uses `std::sort`, in [`csr.h`](https://github.com/scipy/scipy/blob/v1.15.2/scipy/sparse/sparsetools/csr.h#L326-L364). The duplicate coalescing loop then sums equal-column values sequentially in their resulting order in [`csr.h`](https://github.com/scipy/scipy/blob/v1.15.2/scipy/sparse/sparsetools/csr.h#L950-L993).

This source does not specify stable order among equal-index duplicates. IEEE-754 addition is order-dependent, so the source makes low-bit differences during duplicate coalescence a technically supported explanation. A related U2 archive does provide the first of this pair's three element contributions: its first-TET4 coordinates exactly equal the U3 fixture's connectivity element 0 coordinates `[[0,0,0],[2,0,0],[2,0.4,0],[2,0.4,0.4]]` m; both archives identify fixture SHA-256 `4807fea4cde876f57ef1e376f9b0791f5367526d182e236655b39e73e57baa7d`, material `E=70000000000 Pa`, `nu=0.3`, and same connectivity element 0 `[0,4,6,7]`. U2 archived local scalar and batched matrices both have K[5,10] = K[10,5] = `-8974358974.358974 N/m`. Contributions for elements 8 and 9 and the actual post-sort duplicate order are NOT_RECORDED.

The precise order is not needed to state a standard forward-error bound for three sequential additions: under the usual binary64 model with unit roundoff `u=2^-53`, absent overflow/underflow, each direction's summation error is bounded by `gamma_2 * S`, where `gamma_2 = 2u/(1-2u)` and `S` is the sum of absolute values of the three rounded element contributions. Since each local reciprocal entry is bitwise equal, both directions have the same exact sum and S, so their stored difference is bounded above by `2 * gamma_2 * S`, independent of permutation/order. This is a bound, not a computed result: it cannot be evaluated for this pair from the archive because two contributions, hence S, are not recorded. Neither this bound nor the observed one-ULP mismatch proves mechanical harmlessness. Thus sparse duplicate order is a plausible production mechanism, but the precise cause of this stored pair remains inconclusive.

### Matrix-free route

`solveur/large/matrix_free.py:80-115, 230-234` obtains local element templates from the scalar TET4 kernel. It applies local matrices to element displacements and accumulates nodal vector contributions via `np.bincount` (`:130-149, 211-227`). This route does not form a global CSR matrix whose stored `K` can be checked with `array_equal`; its archived deterministic operator-product comparisons against exact and direct references answer a different check. The matrix-free solve restricts the operator to free DOFs (`:32-61`). Exact global matrix symmetry is not asserted by this operator API.

### Constraints and direct solver

For this SciPy route, `ChunkedScipyAssembler.assemble()` returns the full assembled matrix and fixed DOF indices; it does not zero constrained rows/columns (`assembler.py:48-99`). `_solve_scipy()` forms the free submatrix using those indices before solution (`solveur/large/solver.py:108-135`). U3 also checks the pre-reduction full global matrix at test line 316. The failing entries, 14 and 22, are free DOFs for the fixture, so they are also part of the direct route's reduced operator. Boundary treatment does not account for the asymmetry observed here.

Other backends use different mechanisms. The PETSc batch route applies a homogeneous element constraint mask before insertion (`assembler.py:152-190`), but neither that path nor its qualification contract was exercised by U3. No universal symmetry guarantee across all backends should be inferred from this SciPy observation.

## Exact and tolerance-based checks

- The test asserts exact element/global matrix checks at `test_wp12_u_tet4_route_crosscheck.py:311-316`, then asserts `exact_stiffness_symmetric and scalar_stiffness_symmetric and assembled_stiffness_symmetric` at line 637. In this archive, the first two booleans are true and the batched global one is false.
- The run records K[14,22] = `-44871794871.79487` and K[22,14] = `-44871794871.794876`; the separation is one representable float step at this magnitude.
- `solveur/core/audit.py:64-99` uses a norm-relative threshold `1e-9` to set the sparse audit's `is_symmetric` boolean. Its archived relative error is `1.7446481952466456e-17` and it returns PASS. That is a tolerance-based quality diagnostic, not a proof of bitwise symmetry or a replacement for the test's exact assertion.
- Modal analysis has its own split contract: `solveur/core/analyses/modal_basis_numerics.py:170-205` exposes exact sparse symmetry detection and requires exactly symmetric stored stiffness for the exact-symmetry bilinear projection unless the caller provides prior validation; `modal_basis.py:149-154` separately gates relative K/M errors by tolerance. This illustrates why tolerance acceptance and exact-storage symmetry must remain separate. It does not establish that this WP12-U test's exact condition is merely advisory.
- `1e-12` in U3 is a prospective element-matrix/operator-product comparison criterion (`test_wp12_u_tet4_route_crosscheck.py:25-28, 579`), marked `PROPOSED_OWNER_REVIEW_REQUIRED`; it is not an approved criterion for relaxing exact global matrix symmetry.

## Audit conclusions

- **Demonstrated:** both local TET4 kernels explicitly symmetrize; the scalar and exact oracle global results are exactly symmetric; the batch sparse global matrix is not; SciPy's duplicate coalescence path sums floating values and does not promise a stable tie order; the tolerance audit passes at its declared threshold while the exact test correctly reports its separate assertion failure.
- **Partially recorded:** U2 establishes the exact archived binary64 values of element 0 local pair (5,10)/(10,5), but values for elements 8 and 9 and the duplicate order are NOT_RECORDED.
- **Not demonstrated:** all per-element values for the affected pair (one is available from U2), the summation sequence that produced the ULP, cross-version/platform reproducibility, or physical accuracy. The separate [evidence review](MATRIX_FREE_DIRECT_EVIDENCE_REVIEW.md) section 3.1 does bound the stored H1 operator's same-RHS solution perturbation with exact rational verification; this is a value/conditioning result, not a reconstruction of the reduction.
- **Classification:** primary `FLOATING_POINT_ASSERTION_DEFECT`, because exact symmetric storage after independent global duplicate coalescence is not guaranteed by this path while U3 asserts it. `ASSEMBLY_ORDER_ROUNDOFF` remains plausible but unproven for this pair; the exact production cause is inconclusive.
- **Practical status:** preserve the U3 FAIL pending a contract disposition or additional evidence that resolves exact symmetry for this assembled route. Do not reinterpret the tolerance audit PASS as a waiver.

## Identities

Source identities are the frozen science commit `00428adf38e9397340ac136f6f503a268eb671da`, test commit `9c7df65403fc15dc6d12365534172eac87f2ee70`, and runner commit `0bd8ebb5a886ac89a8216e65ff37d59fb510fb61`. The U3 run is `20261026T120509Z-3a69e91f9b42`.
The related U2 first-element local-matrix archive is `TET4-AFFINE-ORACLE-001/20261026T120231Z-ba477b0a779b` (`PYTEST_PASS_ONLY`); `receipt.json` SHA-256 `c5be56b7af3496ec6c34017bea42e452e5f1f44e2c984f48948bc0dc6aea2475`, `stdout.log` SHA-256 `4fb1117dcb0532a44e4d573fa070dbe2b75b3d3089879e61388e9c5100579f3e`.

SHA-256 values observed for source/test files:

| File | SHA-256 |
|---|---|
| `tests/unit/test_wp12_u_tet4_route_crosscheck.py` | `c2e103ce8b195640af69de9d42dba8239eed91d63b3cfbc90b54c9c9d5ae9d38` |
| `src/solveur/elements/solid/tet4.py` | `0517683946a0292e2224d77ba197229ebdbc91dcf935b57d9b75e728d9be3d0b` |
| `src/solveur/large/tet4_batch.py` | `f647c9dd7d63250b383d23a9cbc2c54af85f6603f9361f470912bbc0eae32962` |
| `src/solveur/large/assembler.py` | `fc2df69250692b73539b1c67cac3c62903da27d1852d198cca20bfc1694ba1c1` |
| `src/solveur/large/matrix_free.py` | `de9cf63466ff95bdc70806950c6942c85a50f02266524e605140cde7ea03b191` |
| `src/solveur/core/assembly/sparse.py` | `5999f94a132dc762d8f92dfc3a5dd27815426d4fec0ceb04df2bbf4199cd4b96` |

Archived receipt SHA-256 is `c47a566d97998746a58823ce3f88b5f4950b7cf597bf62129f72aa54c3956542`; archived `stdout.log` SHA-256 is `03f033e0d8369704307b7d1d9d95ff962534f359ab2c2fdb472be39ad42f625e`. No source, test, manifest, or proof artifact was changed by this audit, and no numerical run was performed.
