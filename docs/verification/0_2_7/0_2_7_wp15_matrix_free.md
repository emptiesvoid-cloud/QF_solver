---
doc_id: DOC-027-WP15-001
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# WP15 - Matrix-free TET4 V2

## Decision

WP15 is **PASS_WITH_LIMITATIONS**. The structured homogeneous TET4 matrix-free
route remains a SciPy `LinearOperator` solved with CG and nodal block-Jacobi.
The evidence is a subscale readiness result for WP16, not a one-million-DOF
qualification.

The frozen WP14 model and tolerances were reused: six TET4 per structured cell,
uniform nodal load, SI material data, chunk size 4096, `rtol=1e-8`, `atol=0`
and `maxiter=10000`. The benchmark covers 81, 375, 2,187 and 14,739 DOF.
The machine-readable record is
`qualification/0_2_7/wp15_matrix_free_benchmark.json`.

## Kept optimization

`StructuredBlockOperator` now reuses private full-vector, internal-force and
preconditioner buffers in repeated SciPy callbacks. `apply_full` still returns
an independent result, so callers cannot observe workspace reuse as an aliasing
change. No global stiffness matrix is densified.

At 14,739 DOF, the Python allocation peak proxy fell from 306,192 to 259,008
bytes per matvec (15.4%). The observed RSS remained in the same range. The
timing result is deliberately reported without a speed-up claim: matvec time
was 2.159 to 2.220 ms and total solve time 0.498 to 0.543 s in the recorded
before/after runs. The scatter `bincount` remains the main next profiling
target. A tested `np.add.at` replacement was reverted because it was not faster.

## Numerical equivalence and SPD evidence

The maximum recorded matrix-free versus assembled errors were:

| Observable | Maximum relative error | WP14 limit |
| --- | ---: | ---: |
| Operator action | 1.25e-14 | 1e-8 |
| Displacement | 3.45e-13 | 1e-8 |
| Strain energy | 7.97e-14 | 1e-8 |

The largest free residual was 8.78e-9 under the frozen `rtol=1e-8` solve
contract. Energy balance was below 2e-16 in the recorded cases. Deterministic
bilinear symmetry and positive quadratic-form checks are included in the
targeted tests. These are evidence for the covered constrained structured
route, not a universal SPD theorem for arbitrary models.

## Preconditioning

Nodal block-Jacobi remains selected because it is the WP14-compatible route and
converged in 240 iterations at 14,739 DOF. Diagonal-Jacobi was characterized
as an alternative: 245 iterations and 0.471 s versus 240 iterations and
0.593 s for block-Jacobi in that run. It is a promising candidate, but this
subscale timing alone does not promote it as the default for all hardware or
problem sizes.

## Boundary

This evidence applies only to the generated homogeneous structured TET4 route
and the subscale configurations above. It does not claim WP16, 1M DOF
completion, general unstructured matrix-free support, PETSc/MPI support, or
matrix-free support for other element families. WP14 tolerances and existing
element formulations were not changed.
