# WP17 - Large solver stack and preconditioning

## Decision

This document records the original WP17 diagnostic checkpoint. Its `PARTIAL`
status is preserved as historical evidence; the active WP17 closeout is
`docs/verification/0_2_7/0_2_7_wp17_final.md`.

WP17 is **PARTIAL**. The existing structured TET4 matrix-free route was
instrumented and compared with a diagnostic diagonal-Jacobi alternative. No
solver, formulation, WP14 tolerance or public backend selection was changed.
The WP16 1M equilibrium failure therefore remains a release blocker.

The implementation and measurement source is
`6c975e9fc80854814cb40d1e3d9377f1042f216e`. The full machine-readable probe is
`qualification/0_2_7/wp17_runtime/wp17_probe.json` and the summarized state is
`qualification/0_2_7/wp17_state.json`.

## Instrumented route

The probe uses the existing generated homogeneous six-TET-per-cell TET4 model,
SciPy `LinearOperator`, CG, chunk size 4096 and the frozen WP14 settings
(`rtol=1e-8`, `atol=0`, `maxiter=10000`). It records model setup, operator and
preconditioner setup, solve, reaction calculation, energy/post processing and
total time, together with iterations, matvecs, sampled residual history and
peak RSS.

The medium model has 35,937 nodes, 196,608 TET4 elements and 107,811 true
DOF. It is a diagnostic probe only and is not a 1M qualification run.

| Route | Iterations | Matvecs | Residual | Equilibrium | Energy | Total [s] | Peak RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Nodal block-Jacobi | 486 | 486 | 9.713e-9 | 2.192e-8 | 1.531e-15 | 8.288 | 125,374,464 |
| Diagonal-Jacobi | 468 | 468 | 9.797e-9 | 7.193e-8 | 4.975e-14 | 7.815 | 125,227,008 |

Nodal block-Jacobi remains the selected WP14-compatible preconditioner. The
diagonal candidate is not retained: it reduces iterations and is faster in this
medium probe, but its equilibrium result is worse than the frozen `1e-8` limit.
That timing result is diagnostic only and does not justify a WP14 route change.
No implicit fallback is introduced.

## Reaction diagnosis

The compensated reaction reduction changes the equilibrium metric by only
`2.65e-13` relative. The identity between the global equilibrium balance and
the accumulated free residual is `1.66e-12` relative. Together with the
subscale operator/displacement/reaction/energy comparison, this classifies the
observed WP16 error as **iterative residual amplification**, not a demonstrated
reaction reconstruction, floating-point summation, BC or matrix-free operator
mismatch. No post-processing-only correction is used to mask the result.

The frozen WP14 subscale comparison remains PASS across 81, 375, 2,187 and
14,739 DOF. Its maximum errors are `1.25e-14` for operator action,
`3.45e-13` for displacement, `2.30e-9` for reaction, `7.97e-14` for energy and
`8.78e-9` for relative residual.

## PETSc status and next gate

`petsc4py` and `mpi4py` were unavailable in the local environment; `mpiexec`
was present but no PETSc backend was run. The result is recorded as
`UNAVAILABLE`, not PASS, and the matrix-free route was selected explicitly.

WP17 does not claim a 1M improvement, PETSc support, distributed scaling or a
3M solve. A future WP16 retry requires a separately justified numerical change
or a solver-path improvement that satisfies the unchanged WP14 equilibrium
criterion. WP18 is not considered ready from this diagnostic-only checkpoint.
