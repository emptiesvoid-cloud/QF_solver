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

`LU2-WP04 = USER_INTERRUPTED_INCONCLUSIVE`. The deterministic 5M TET4
workload and preflight were completed, but the owner-interrupted frozen AIJ
construction path did not produce a completion record before PETSc/GAMG
readiness. The 5M Bronze acceptance criteria therefore remain unmet. No 5M
Silver or converged-solve claim is made.

The next action is a supervised WP04 retry with progress and resource
telemetry. C1 is not confirmed: the 2x reference time was exceeded, but that
elapsed overrun is not a resource-limit proof after a manual interruption.
Any retry must remain scoped to the frozen TET4 linear-static route and must
not change WP02 tolerances or the FEM formulation.

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
`1582.400684866 s`; the 2x reference point was `3164.801369732 s`. The
previous record noted an elapsed time of approximately `12,500 s`, while
forensic Docker inspection found the same container still running after about
`14,531 s`. All eight Python ranks were runnable and reported approximately
`99.9%` CPU. No OOM, MPI error or fallback was observed.

The last confirmed phase was the per-element AIJ insertion loop. The runner
creates and sets up the PETSc AIJ object before that loop, but it calls
`matrix.assemble()`, RHS setup and `ksp.setUp()` only afterward. No completed
raw result was written, so operator completion and GAMG readiness are
`NOT_PROVED`. Run 2 was not started after the owner interruption. The full
assembly progress counter, peak RSS and swap telemetry were not persisted by
this historical run. S1 installs opt-in rank-zero progress telemetry for the
supervised retry; it does not alter this historical result.

The original time-budget observation is retained in
[`wp04_resource_guard_audit.json`](../../../qualification/0_2_7/wp04_runtime/wp04_resource_guard_audit.json)
and the corrected forensic classification is recorded in
[`wp04_forensic_audit.json`](../../../qualification/0_2_7/wp04_runtime/wp04_forensic_audit.json)
and summarized in
[`wp04_summary.json`](../../../qualification/0_2_7/wp04_runtime/wp04_summary.json).

## Boundary and next step

The evidence proves deterministic 5M workload construction and a passing
resource preflight only. It does not prove 5M operator readiness, GAMG
initialization, a converged solve, or a performance claim. CPU activity is
consistent with continued work, but no assembly percentage can be recovered;
therefore `RESOURCE_LIMITED_PROVEN = NO` and `C1_TRIGGER_CONFIRMED = NO`.
WP05 remains locked until a supervised retry completes the Bronze contract.
