# 0.2.7 F6 numerical and performance regression audit

Audit start SHA: `f6cfde036f5866c15e688bce70be5ed21b493ff1`
Branch: `codex/0.2.7-foundation`
Status: `PASS_WITH_LIMITATIONS`

## Decision

The active qualified numerical results remain applicable to the current
release candidate. Targeted element, solver, BC/load/material, post-processing,
MPI/PETSc and governance checks passed. The full suite completed with
`2147 passed, 3 failed, 184 skipped, 2 warnings`; the three failures are the
same visible F4 failures in experimental or stale nonlinear paths. No P0 or P1
release finding remains.

No numerical source, tolerance, active baseline or maturity record was changed
by F6. No 5M or 10M replay was required: F6 is a controlled regression audit,
and no relevant source change occurred during F3-F6. Existing heavy evidence
and current representative AIJ evidence remain traceable.

## Active evidence

| Area | Active evidence | Result | Boundary |
| --- | --- | --- | --- |
| Golden set | `qualification/0_2_7/golden/evidence.json` | 9 records PASS | recorded cases and declared routes |
| 1M TET4 | `qualification/0_2_7/wp16_runtime/wp16_retry_summary.json` | 2 replays, 431 iterations | recorded PETSc/MPI host and workload |
| 3M TET4 | `qualification/0_2_7/wp18_runtime/wp18_summary.json` | 2 Silver replays, 619 iterations | bounded single-host evidence |
| 5M TET4 | `qualification/0_2_7/wp05_runtime/wp05_5m_silver_replay.json` | 2 Silver replays, 1243 iterations | recorded host, input and frozen configuration |
| 10M TET4 | `qualification/0_2_7/c3_10m_runtime/c3_10m_replay_summary.json` | C3 PASS, bounded | zero-weight capacity exploration; no universal claim |
| AIJ preallocation | `qualification/0_2_7/c3_10m_mpiaij_preallocation_remediation.json` | representative improvement and zero post-remediation malloc signal | medium representative case only |
| External | Code_Aster bounded; CalculiX `NOT_COMPARABLE` | unchanged | no new F6 external claim |

The 5M Silver replays recorded 5,012,640 DOF, 9,773,946 TET4 elements,
1243 iterations, free residuals near `9.85e-11`, equilibrium near `1.39e-9`
and energy errors below `2e-14`. The two runtimes were 4427.657 s and
4378.777 s. These values are descriptive for that workload and environment,
not a general performance promise.

## Regression checks

Targeted domain checks: `336 passed, 11 skipped, 2 warnings`.
MPI/PETSc and governance checks: `30 passed`.
Small/medium performance sanity: `24 passed in 10.05 s`.
Full suite: `2147 passed, 3 failed, 184 skipped, 2 warnings`.

The three retained full-suite failures are:

- `tests/unit/test_contact_finite_sliding.py::test_finite_sliding_diagnostics_reach_common_newton_result`
- `tests/unit/test_geometric_nonlinear_public.py::test_public_geometric_nonlinear_rejects_distributed_loads`
- `tests/unit/test_nonlinear_benchmark.py::test_nonlinear_benchmark_paths_execute_bounded_profiles[finite_sliding]`

They reproduce the F4 baseline and remain outside the officially supported
bounded release matrix. They were not hidden with skips or xfails.

The current checks retain the MPI collective guard, structured MPIAIJ
preallocation guard, finite-output checks, dispatch/maturity guards, invalid
input checks and F4 release guards. The representative preallocation record
reports zero post-remediation mallocs and identical matrix/solution results;
its before/after performance numbers are not generalized beyond that case.

## Applicability and performance policy

Changes since the heavy evidence are limited to phase telemetry, structured
MPIAIJ preallocation and compatibility/evidence hardening. There is no source
change from F4 through F6, and no assembler change after the C3 evidence source.
Therefore the active 5M, 1M, 3M and C3 records remain valid regression
references for this commit. A new heavy replay would repeat qualification
rather than test a changed numerical path.

The only allowed performance interpretation is for the exact recorded workload,
hardware, PETSc/MPI image, backend, preconditioner and configuration. No
universal speedup, hardware-independent scaling, GPU, multi-node, nonlinear or
mixed-mesh claim is made.

## Findings and limitations

- P0: 0.
- P1: 0.
- P2: 1 retained non-blocking finding, the three pre-existing experimental or
  stale nonlinear full-suite failures.
- P3: 2 deferred findings: optional environments were not freshly exercised by
  the host audit, and no new heavy replay was needed.

F6 closes with `PASS_WITH_LIMITATIONS`. The current commit is technically ready
for the separate Owner R0 decision, but F6 does not start R0, publish artifacts,
change maturity or alter historical evidence.

Machine-readable record: `qualification/0_2_7/f6_numerical_performance_regression_audit.json`.
