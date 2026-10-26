# V2 experiment plan — TET4-H1-OPERATOR-AUDIT-002

**PREPARATION_ONLY · NUMERICAL_EXECUTION_NOT_PERFORMED · WP12_STATUS=OPEN**
Manifest status: `PREPARED_NOT_AUTHORIZED`.

## Questions

1. Is the recorded one-ULP asymmetry in the assembled H1 stiffness consistent with the observed element contributions and a predeclared binary64 summation bound?
2. Do the matrix-free and assembled-direct operators agree over every one of the 24 free H1 DOFs, and do both agree with an exact-rational discrete reference?
3. Do the two archived U3 displacement fields satisfy the prespecified discrete residual, force/moment, and energy/work identities when re-evaluated against that reference?

This is a bounded operator and archived-state audit. It is not a mesh-convergence study, an external-solver comparison, or physical validation.

## Bound input and provenance

Use only the H1 file `tests/fixtures/wp12_u/tet4_h1_level1_model.h5` (12 TET4, 12 nodes, 36 DOFs, 24 free DOFs; SHA-256 `4807fea4cde876f57ef1e376f9b0791f5367526d182e236655b39e73e57baa7d`) and the derived archived-field fixture `tests/fixtures/wp12_v2/u3_archived_solution_fields.json` (SHA-256 `a862bd016bb408566459491b3c726694e2cd408e084031b4f693223883429ba8`). The test verifies both hashes and checks the derived fixture's U3 receipt/manifest identities, run ID, fixture hash, DOF maps, exact free matrix and residual fractions before using the archived fields.

The new JSON is an explicitly derived subset of the verified U3 receipt. It does not replace, rewrite, or claim to contain the entire original archive. The receipt SHA-256 is `c47a566d97998746a58823ce3f88b5f4950b7cf597bf62129f72aa54c3956542`; the U3 manifest SHA-256 is `3f10c7156c6f4e5eaf07f0bf66a92fe3f7cc6ef9031c200c1e41ca1087bf2a1c`. The original U3 failure remains unchanged.

## Execution outline, if separately authorized

1. Verify the H1 and derived-archive hashes, model counts, SI units, one-material scope, free/fixed maps, loads, and material data. Reconstruct the node/component DDL map independently and compare it to `element_dofs_batch`.
2. Capture all 12 batch local stiffness matrices by wrapping the assembler's `_stiffness_batch` call. Separately obtain all 12 scalar `Tet4Element.stiffness` matrices. Record each local matrix in binary64 hexadecimal form.
3. Wrap the assembler's CSR constructor as a pass-through and capture the exact emitted value, row-index and column-index arrays before duplicate reduction. Record their order as generated and handed to SciPy. Do **not** claim that this reveals SciPy's internal duplicate-reduction order; the runner records it as unobserved.
4. Reconstruct the exact rational element and global matrices from the input coordinates and binary64 E/nu values. Compare scalar and batch global matrices with this independent discrete formulation and verify the H1 free/fixed map.
5. Evaluate `StructuredBlockOperator @ e_j` for each of the 24 free canonical vectors. Record all 24 output columns and the assembled-direct columns, componentwise differences and matrix norms. No conjugate-gradient or other solve is called.
6. Re-evaluate the archived matrix-free and direct U3 displacement fields against exact-rational `K` and the H1 load vector. Compute residuals, support reactions, force/moment identities, elastic energy, external work, the displacement-field difference, terminal-face mean UZ, and load-conjugate displacement. Also record exact rational differences between recalculated reactions/moments and the archived binary64 summaries; these deltas are diagnostic and have no new tolerance.
7. Run the embedded synthetic negative controls on copies only. They are checks of the acceptance predicates, not additional nodeids or solver evidence.
8. Emit one result payload before acceptance assertions so a future failure retains diagnostic observations in stdout and the runner receipt.

## Captured H1 asymmetry pair

The audited pair is global `K[14,22]` and `K[22,14]`. WP12-U recorded an absolute difference of one ULP, `7.62939453125e-6 N/m`, and attributed both entries to elements 0, 8 and 9. V2 records the four contributions from each scalar/batch route as exact binary64 hex values, along with complete maps and emitted CSR arrays. It rechecks that the contributor set is exactly `[0, 8, 9]`. This expected set is a fixture identity guard, not a claim about reduction order.

For each transposed pair, let `a_e` and `b_e` be the captured scalar/batch inputs from the same contributing elements. V2 records `L = Σ_e |a_e-b_e|`, `S_a = Σ_e |a_e|`, `S_b = Σ_e |b_e|` and the respective addition counts. It compares the stored global difference to `L + γ_(m_a-1) S_a + γ_(m_b-1) S_b`, where `u=2^-53` and `γ_p=pu/(1-pu)`. Sums of binary64 input values used to evaluate the bound are exact `Fraction` sums. The test separately reports `||K-Kᵀ||_F/||K||_F` and each componentwise difference/bound.

The usual summation bound is conditional on finite binary64 operations without overflow/underflow and round-to-nearest behavior. The output records subnormal observations, but it cannot inspect every internal intermediate or the runtime rounding mode. If the required floating-point assumptions cannot be accepted or established during preflight, the symmetry-bound result must be treated as INCONCLUSIVE; no tolerance may be changed after seeing the result.

## Matrix-free coverage

For each free basis vector, the operator output is one full column of the 24×24 free operator. The test compares it to the corresponding assembled-direct column and exact-rational matrix column. It records the full exact-fraction `K_matrix-free - K_direct` matrix, Frobenius norm, matrix infinity norm (maximum absolute row sum), largest absolute entry, and relative versions normalized respectively by the exact free matrix Frobenius norm, infinity norm and largest entry. It also records each column's error normalized by the exact full-matrix Frobenius norm, matching the U3 criterion definition.

The componentwise bound separates the difference between each matrix-free element template and that element's exact-rational local entry from a `γ_(m-1) Σ|template contribution|` scatter bound. The fixed DOF mapping and the matrix-free template assignment must cover each expected element exactly once. This bound is conditional on the stated binary64 model; the route-to-exact and route-to-route comparisons remain separate tests.

## Archived field and balance calculations

No displacement is recomputed by a solver. For each archived field `u`, use exact binary64 rationalizations and exact-rational H1 `K` and `f`:

- `r = K u - f`; report the full and free residuals. Matrix-free relative free residual is `||r_free||₂ / ||f_free||₂`. The direct residual is `||r_free||₂ / max(||f_free||₂, ||(K u)_free||₂, 1)` as in U3.
- Reactions are fixed-DOF residual components. Force and moment defects (`support + external`) are related exactly to the free residual's projections onto rigid translation and rotation fields; report the corresponding Cauchy bounds. Moments use the fixture coordinate origin.
- Compare recalculated reaction/moment values to the archived binary64 summaries by exact rational differences. These comparisons support provenance review but do not add an acceptance threshold.
- `U = 1/2 uᵀKu`, `W = uᵀf`; check exactly `2U-W = u_freeᵀr_free` for homogeneous zero fixed displacements.
- Report the relative L2 difference of the two archived free displacement fields, mean UZ at the terminal face `x=4 m`, and the load-conjugate displacement `W / ΣFz` with sign retained.

These are discrete algebraic identities over one archived model. A small residual is not a continuum error estimate; force/moment and energy identities are not independent physical validation.

## Test identity and command

Exact nodeid: `tests/unit/test_wp12_v2_tet4_operator_audit.py::test_tet4_h1_operator_audit_002`.

The test source is gated to the local V&V plugin's exact-node environment. The runner must launch only that nodeid from the dedicated, clean test checkout, with no shell command, no broad selector, no conftest or unrelated plugin autoload, and the manifest-pinned Python/import environment. The precise fixed command profile is recorded in `V2_MANIFEST.json`; do not run it directly or use pytest collection as a substitute for Owner authorization.

Proposed maximum: one attempt, no automatic retry. Proposed timeout: 300 seconds. The runner's 16 MiB per-stream output cap is a software-polled limit, not a hard disk quota. Both values require the V2 Owner decision. Evidence belongs only under the distinct namespace `<evidence_root>/WP12-V2-H1-OPERATOR-AUDIT-002/TET4-H1-OPERATOR-AUDIT-002/<run_id>/`.

## Failure disposition

Any hash, source/import, model identity, load/constraint, map, selection, or environment mismatch is a pre-execution stop or infrastructure error. Preserve a scientific assertion failure as FAIL; do not rerun or patch the test to pass. If an oracle's assumptions cannot be met, classify that assertion INCONCLUSIVE. Keep execution status, oracle assessment and qualification decision separate. No outcome changes a WP or maturity status automatically.
