---
doc_id: DOC-027-024
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# WP17-R - PETSc environment and 1M solver remediation

## Decision

WP17-R is **PARTIAL**. A pinned, headless Docker runtime now provides a
reproducible PETSc/MPI path, and the explicit PETSc `CG + GAMG` route completes
a real 1,029,000-DOF TET4 solve. The frozen WP14 equilibrium criterion still
fails, so this is not a WP16 qualification and does not authorize WP18.

The implementation source used for the numerical runs is
`ec7e0af7dad399be8d1a1fe1fc90e95a81fec78a`. The controlled state is
`qualification/0_2_7/wp17r_state.json`; the machine-readable summary is
`qualification/0_2_7/wp17_runtime/wp17r_summary.json`.

## Reproducible environment

The host `.venv` does not provide `petsc4py` or `mpi4py`. The isolated runtime
is built from `tools/containers/large/wp17r.Dockerfile`, using the pinned
Dolfinx base image and the following versions:

| Component | Version |
| --- | --- |
| Python | 3.12.3 |
| NumPy | 2.4.6 |
| SciPy | 1.17.1 |
| h5py | 3.13.0 |
| mpi4py | 4.1.2 |
| PETSc / petsc4py | 3.25.1 |
| MPI runtime | MPICH 5.0.1 / MPI 5.0 |

Image digest:
`qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e`.
Python imports and a two-rank `mpiexec` version smoke both pass. No GUI is
used and backend selection remains explicit with no implicit fallback.

## Frozen route and reaction diagnosis

The run keeps the WP14 contract: TET4, linear static, CG, AIJ, contiguous
partitioning, two MPI ranks, `rtol=1e-8`, `atol=0`, and `max_iterations=10000`.
PETSc uses the **unpreconditioned** stopping norm explicitly. This aligns the
KSP stopping condition with the physical residual used by WP14; it is not a
change to the WP14 tolerance.

The remaining 1M equilibrium discrepancy is not a summation fix opportunity.
At 1,029,000 DOF, the free relative residual is `9.953694e-9`, while the
equilibrium metric is `3.503430e-7`. The free-residual/equilibrium identity
closes at `4.395904e-11` relative and compensated summation changes the
equilibrium only from `3.5034304846e-7` to `3.5034304222e-7`. No reaction
reconstruction, floating-point reduction, BC, or FEM operator bug is
demonstrated. The frozen equilibrium limit remains `1e-8`.

## Preconditioner evidence

| Backend / preconditioner | DOF | Iterations | Total [s] | Peak RSS | Equilibrium |
| --- | ---: | ---: | ---: | ---: | ---: |
| Matrix-free / nodal block-Jacobi | 107,811 | 486 | 8.288 | 125,374,464 | 2.192e-8 |
| PETSc / Jacobi | 107,811 | 468 | 3.423 | 312,205,312 | 7.193e-8 |
| PETSc / GAMG | 107,811 | 178 | 13.884 | 496,660,480 | 4.525e-8 |
| PETSc / Hypre BoomerAMG | 107,811 | 82 | 63.728 | 1,775,947,776 | 2.558e-8 |

GAMG is retained as the diagnostic 1M choice because it completed the
distributed run. Hypre has fewer iterations but is slower and more memory
intensive on the controlled medium probe. No public/default preconditioner is
changed.

The existing matrix-free-versus-assembled subscale evidence remains PASS.
The new PETSc-GAMG-versus-matrix-free medium comparison is FAIL under the
unchanged `1e-8` comparison policy: displacement differs by `1.197e-12`, but
equilibrium differs by `2.333e-8` and energy by `4.211e-11`.

## 1M diagnostic and replay

The model has 343,000 nodes, 1,971,054 TET4 elements and 1,029,000 true DOF.
Both two-rank GAMG runs complete without timeout or resource-limited status:

| Run | Iterations | Total [s] | Peak RSS | Residual | Equilibrium | Acceptance |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 301 | 166.703 | 3,520,552,960 | 9.954e-9 | 3.503e-7 | FAIL |
| 2 | 301 | 164.939 | 3,519,496,192 | 9.954e-9 | 3.503e-7 | FAIL |

Replay is **PASS**: source SHA, input digest, configuration digest, DOF,
matvec count, residual, equilibrium and energy are identical within the
declared replay tolerance. The two acceptance failures are therefore
reproducible failures, not missing or ambiguous runs.

Relative to the WP16 matrix-free baseline (1,052 iterations, 1,371.059 s,
575,700,992 bytes), the best PETSc run uses 301 iterations and 164.939 s,
about `8.31x` faster. Peak RSS is about `6.12x` higher, and equilibrium is
worse than the baseline. This is a performance diagnostic, not a qualification
claim.

## Gate consequence

- `WP16 = FAIL` remains the release blocker because equilibrium exceeds the
  frozen `1e-8` criterion.
- `WP17-R = PARTIAL`: the PETSc environment, explicit backend/options,
  instrumentation, diagnostics and replay are controlled; no qualifying route
  is established.
- `WP18 = NOT READY`: no 3M work is authorized while the WP16 blocker remains.
- No FEM formulation, existing element route or WP14 tolerance was changed.

Raw controlled records are stored in
`qualification/0_2_7/wp17_runtime/wp17r_run1.json` and
`qualification/0_2_7/wp17_runtime/wp17r_run2.json`, with audit records beside
them. The prior WP17 evidence remains preserved as the historical parent
checkpoint.
