---
doc_id: DOC-027-WP17-FINAL
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# WP17 - Final PETSc/MPI large solver path closure

## Decision

WP17 is `PASS_WITH_LIMITATIONS`. This closeout consumes the controlled
WP17-R, WP16 retry and WP18 Silver evidence; it does not claim a new heavy
benchmark. The earlier WP17 and WP17-R `PARTIAL` records remain preserved as
historical checkpoints and are not rewritten.

The closed scope is the explicit PETSc 3.25.1 / MPICH 5.0.1 route using CG,
GAMG, AIJ storage, two MPI ranks and the pinned container image. It is a
bounded TET4 linear-static large-model path, not a universal PETSc, HPC or
performance claim.

## Frozen contract and runtime

The WP14 contract remains authoritative. Its acceptance tolerance is `1e-8`;
the supplemental PETSc route uses the predeclared internal solver target
`1e-10` and an explicit unpreconditioned KSP stopping norm. No acceptance
tolerance was changed and no post-result tuning was used.

| Item | Recorded value |
| --- | --- |
| Container | `qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e` |
| PETSc / petsc4py | `3.25.1` |
| MPI | `MPICH 5.0.1 / MPI 5.0` |
| Backend / solver / PC | PETSc / CG / GAMG |
| Matrix format | AIJ |
| MPI size / threads | 2 / 1 |
| Fallback | explicit; no silent fallback |
| Host PETSc | `UNAVAILABLE` |

The normal SciPy and matrix-free paths remain available. PETSc is not a
mandatory runtime dependency; a requested unavailable backend must fail
closed rather than silently changing route.

## Closure evidence

| Evidence | Result | Key metrics |
| --- | --- | --- |
| Same-configuration subscale comparison | `PASS` | displacement `8.341e-15`, equilibrium `9.279e-10`, energy `1.598e-12` |
| WP16 official 1M retry | `PASS` | 1,029,000 true DOF, two replays, residual `9.704e-11`, equilibrium `5.339e-10`, energy `8.484e-14` |
| Supplemental strict PETSc 1M route | `PASS` | 431 iterations, about 186 s total per replay |
| WP18 Silver | `PASS` | 3,000,000 true DOF, 619 iterations, two replays, about 2,660 s total, approximately 10.08 GB peak RSS |

The official WP16 and Silver evidence includes complete model, load, BC,
solve, reaction/equilibrium, energy, finite-output and replay checks. Their
source SHA, input digest, backend, preconditioner, environment and runtime
records remain in the referenced JSON artifacts.

## Performance boundary

On the recorded 1M case, the old matrix-free baseline used 1,052 iterations
and `1371.06 s`; the strict PETSc CG/GAMG route used 431 iterations and about
`185 s`, an observed speedup of about `7.4x`. This is a measurement for the
declared case and environment only. It is not a promise of universal speedup,
hardware independence or general 1M/3M scaling.

The AIJ route uses approximately `3.52 GiB` at 1M DOF and `10.08 GB` at 3M
DOF. WP18 Gold restart/checkpoint and distinct-second-case evidence remain
unattempted and unclaimed. GPU, general HPC and alternate preconditioner
qualification remain outside this closeout.

## Owner boundary

The closeout does not change any FEM formulation, WP14 criterion, public
default backend or capability maturity. It closes the PETSc/MPI path as a
reproducible, bounded engineering route with explicit resource limitations.
The machine-readable closeout is
`qualification/0_2_7/wp17_final_state.json`; historical records are listed in
that file for provenance.

`FULL_REGRESSION = SKIPPED_BY_POLICY`; no functional source changed in this
documentary closeout.
