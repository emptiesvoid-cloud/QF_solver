---
doc_id: DOC-027-WP16-001
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# WP16 - True 1M DOF qualification

## Decision

WP16 is **PASS** on the official retry executed with the PETSc route selected
by WP17-R. The frozen WP14 acceptance criteria were used without change. The
historical matrix-free failure remains preserved as historical evidence and
is not overwritten.

The official model contains 343,000 nodes, 1,971,054 structured six-tet TET4
elements and 1,029,000 true displacement DOF. It uses the WP14 SI material,
fixed `x=0` translations, a uniform 1,000,000 N nodal load on `x=1`, 4,900
load nodes and 14,700 fixed DOF. The retry source SHA is
`b8db2211536eaaf1c026ddfb7a5843b61b2e3733`.

## Frozen execution route

The route is PETSc 3.25.1 with MPICH 5.0.1, two MPI ranks, CG, GAMG, AIJ
storage, contiguous partitioning and one thread. The PETSc environment is
the pinned image
`qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e`.
All relevant PETSc options are explicit and `PETSC_OPTIONS` is unset. The
internal solver target is `1e-10`, pre-declared by WP17-R; WP14 acceptance
remains `rtol=1e-8`, `atol=0` and `max_iterations=10000`.

## Official replays

| Run | Setup [s] | Solve [s] | Reactions [s] | Energy/post [s] | Total [s] | Iterations | Peak RSS [bytes] | Residual | Equilibrium | Energy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| run1 | 113.2639 | 66.3369 | 3.3231 | 2.9063 | 184.0757 | 431 | 3,519,639,552 | 9.704e-11 | 5.339e-10 | 8.484e-14 |
| run2 | 113.4333 | 67.4453 | 3.1541 | 2.7512 | 185.1151 | 431 | 3,520,733,184 | 9.704e-11 | 5.339e-10 | 8.484e-14 |

Both runs completed the complete model-to-solve-to-post path without timeout,
resource-limited status, NaN/Inf, or implicit fallback. The finite-output,
SPD/CG, residual, equilibrium and energy checks all pass the WP14 limits.

Raw controlled records are:

- `qualification/0_2_7/wp16_runtime/wp16_retry_run1_raw.json`
- `qualification/0_2_7/wp16_runtime/wp16_retry_run2_raw.json`

The official index and replay comparison are in
`qualification/0_2_7/wp16_runtime/wp16_retry_summary.json`.

## Subscale equivalence

The same PETSc configuration and internal solver target were compared with
the existing matrix-free route on the 107,811-DOF subscale. The comparison
passes with displacement error `8.341e-15`, equilibrium difference
`9.279e-10`, energy difference `1.598e-12` and matrix-free residual
`9.290e-11`, all below the unchanged `1e-8` comparison limit.

The raw subscale record is
`qualification/0_2_7/wp16_runtime/wp16_retry_subscale_raw.json`.

## Replay policy

The two official replays use the same source SHA, input digest and
configuration digest. Their recorded numerical observables and iteration
counts are identical; the replay verdict is `PASS` under the WP14 policy.

Input digest:
`b65b1cd72a067551490ed5364beb1fcc2d7e55d07a9075f6f7b8899f535d7f92`

Configuration digest:
`e44ef191461ec5e4c6c0c0de31bcda3f674c3e45949513d38a4ce8a067bf9fe6f`

## Historical negative attempt

The earlier matrix-free/nodal-block-Jacobi attempt remains available at
`qualification/0_2_7/wp16_runtime/wp16_run1.json`. It completed 1,029,000
DOF but recorded equilibrium `3.81975e-8` against the frozen `1e-8` limit.
That result is retained as historical evidence and is not used as the active
WP16 verdict.

## Scope and limitations

- This is a bounded qualification of the declared TET4 linear-static model,
  PETSc CG/GAMG route and pinned two-rank environment.
- The PETSc AIJ route reaches approximately 3.52 GiB peak RSS at 1M DOF.
- PETSc is unavailable in the normal host environment; the pinned container
  is required for this evidence.
- This result does not qualify 3M DOF or any other element family/backend.
- WP14 acceptance thresholds and existing FEM formulations were not changed.

The machine-readable state is
`qualification/0_2_7/wp16_state.json`; the governing contract is
`qualification/0_2_7/wp14_execution_contract.json`.
