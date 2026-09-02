---
doc_id: DOC-027-LU2-WP04-001
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
source_sha: 3c579e4a51a2e9edca23b7583cdbfc48c7f80368
---

# LU2-WP04 - 5M Bronze

## Decision

`LU2-WP04 = RESOURCE_LIMITED`. The deterministic 5M TET4 workload and
preflight were completed, but the frozen AIJ construction path was stopped by
the explicit time guard before PETSc/GAMG readiness. The 5M Bronze acceptance
criteria therefore remain unmet. No 5M Silver or converged-solve claim is made.

The next action is the conditional C1 matrix-free capacity investigation. It
must remain scoped to the frozen TET4 linear-static route and must not change
WP02 tolerances or the FEM formulation.

## Frozen contract

- Freeze ID: `LU2-WP02-FREEZE-bfd1975b012453a3`
- Freeze digest: `bfd1975b012453a3b492cc79c968ceeba6ae6951a293e3ce65ddda548d8339a1`
- Runtime image: `qf-solver-large@sha256:d6a1718001fc36772906d1a9505637bbd0a4b7e1d8ccc9afdbcb6f67b7ff6d0e`
- PETSc 3.25.1, MPICH 5.0.1, 8 MPI ranks, contiguous partition, AIJ, CG, GAMG
- No rank, partition, matrix, solver, preconditioner or tolerance change was made

The predeclared contract is
[`wp04_execution_contract.json`](../../../qualification/0_2_7/wp04_execution_contract.json).

## Workload and preflight

The workload is a real structured TET4 linear-static FEM model with
`5,012,640` true DOF and `9,773,946` elements. It uses a homogeneous isotropic
linear-elastic material, all translations fixed at `x=0`, and a uniform
`1,000,000 N` x-direction nodal load at `x=length`.

Two independent generator runs produced the same input digest:

`ff73bc9debd0c8e1ae7355cb6b42e62734c619efa87423e484284878449a55ec`

The preflight estimated `10,135,530,000` bytes of RAM and
`4,090,089,600` bytes for two model recreations on the pinned Docker route;
the preflight classification was `PASS`. The machine-readable records are
[`wp04_preflight.json`](../../../qualification/0_2_7/wp04_runtime/wp04_preflight.json),
[`workload_5m_run1_build.json`](../../../qualification/0_2_7/wp04_runtime/workload_5m_run1_build.json),
and [`workload_5m_run2_build.json`](../../../qualification/0_2_7/wp04_runtime/workload_5m_run2_build.json).

## Controlled stop

The comparable reference was the two WP02 3M 8-rank replays. Their total times
were `1568.651002509 s` and `1596.150367223 s`, with mean
`1582.400684866 s`. The explicit guard was `3164.801369732 s` (`2x` the
mean). A five-hour (`18,000 s`) upper wall-time ceiling was allowed, but the
earlier comparable-time guard had precedence.

Run 1 remained CPU-bound in the AIJ operator assembly beyond that threshold;
eight ranks were active, no OOM or MPI error was observed, and no fallback was
observed. The run was interrupted under the guard at approximately `12,500 s`.
No completed raw result was written, so matrix construction, PETSc
initialization and GAMG readiness are `NOT_PROVED`. Run 2 was not started
after the controlled stop.

The interruption is recorded in
[`wp04_resource_guard_audit.json`](../../../qualification/0_2_7/wp04_runtime/wp04_resource_guard_audit.json)
and summarized in
[`wp04_summary.json`](../../../qualification/0_2_7/wp04_runtime/wp04_summary.json).

## Boundary and next step

The evidence proves deterministic 5M workload construction and a passing
resource preflight only. It does not prove 5M operator readiness, GAMG
initialization, a converged solve, or a performance claim. The measured
blocker is the current AIJ assembly cost at this scale; C1 is triggered for a
scoped matrix-free capacity investigation. No 5M Silver attempt is authorized
until the Bronze readiness blocker is addressed under its own contract.
