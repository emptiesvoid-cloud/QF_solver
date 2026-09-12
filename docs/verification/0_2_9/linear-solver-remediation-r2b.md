---
doc_id: DOC-029-LINEAR-SOLVER-REMEDIATION-R2B-001
revision: 1.0
status: hold
applicable_version: 0.2.9-development
---

# Linear-solver remediation R2B

R2B is a bounded forensic follow-up to R2. It preserves the R1 strict
residual failure and does not authorize WP04 qualification, M2/M3 execution,
PETSc/PyAMG work or maturity promotion. Machine-readable evidence is in
`qualification/0_2_9/wp04_linear_solver_r2b.json`.

## Frozen scope and reproduction

The run started from `bee8cb606a975a8714947776be489e00af8fa623` on
`0.2.9-unified-nonlinear`, using the unchanged WP04 C2-M1 case: 32x16x16,
49,152 TET4 elements, 28,611 full DOFs, 12 load increments, tolerance
`1e-10`, CG+Jacobi `rtol=1e-10`, and direct fallback disabled.

The CG failure reproduced exactly at load step 4, Newton iteration 12:

```text
raw relative residual = 9.680696501971698e-05
eta_inf                = 1.0895221524409612e-05
krylov iterations     = 334
```

The failing CSR system was captured without changing the solve. The compressed
NPZ remains outside Git and is intentionally not committed:

```text
path   = C:/Users/fari/AppData/Local/Temp/qf_solver_029_r2b_forensics/wp04_m1_failing_system_step4_iter12.npz
sha256 = 97883531107a289ee43dd6dead45666090f4555e883bb49f6e621e97ab15e33a
size   = 7,966,755 bytes
shape  = 27,744 x 27,744
nnz    = 1,151,694
```

The accepted state before the failed trial had three accepted steps and
digest `e204f78d1df309bf92d03faa9b86db70828c3bf900e1f27c55d7c7b0e1bb2283`.

## Matrix forensics

The matrix was numerically symmetric but SPD was not inferred from its
diagonal:

| quantity | value |
| --- | ---: |
| symmetry defect | 6.538813369795086e-17 |
| diagonal min / max | 19305.548205844076 / 439711.0960886668 |
| negative diagonal entries | 0 |
| near-zero diagonal entries | 0 (threshold 4.397110960886668e-7) |
| norm 1 / norm infinity | 1480438.6248984546 / 1480438.6248984544 |
| rhs norm 2 / infinity | 1.0293403443721332e-10 / 3.5394644165446035e-12 |
| Jacobi diagonal absolute range | 19305.548205844076 .. 439711.0960886668 |
| Jacobi inverse absolute range | 2.2742205254660032e-6 .. 5.179858087103091e-5 |

An `eigsh` probe converged for the upper estimate
`lambda_max=1329687.869479092`, but did not converge for `lambda_min` within
2,000 iterations. Therefore `SPD_STATUS = NOT_PROVEN` and
`SPECTRAL_STATUS = PARTIAL_NOT_PROVEN`.

## Same-matrix shootout

The exact captured K/rhs produced these independent results. Diagnostic
shootout calls exposed the returned candidate for inspection; no direct
fallback was enabled.

| solver | result | raw residual | eta_inf | solution delta vs direct | iterations |
| --- | --- | ---: | ---: | ---: | ---: |
| direct / SuperLU | PASS | 3.1145843902e-15 | 5.3514640749e-16 | 0 | 1 |
| CG + Jacobi, 1e-10 | FAIL_R2_CONTRACT | 9.6806965020e-05 | 1.0895221524e-05 | 1.1167950838e-01 | 334 |
| MINRES + Jacobi, 1e-11 | PASS_R2_CONTRACT | 6.7569559510e-12 | 5.5395869788e-13 | 1.2292890785e-09 | 1731 |
| MINRES + Jacobi, 1e-12 | PASS_R2_CONTRACT | 3.9857862084e-12 | 3.4532323474e-13 | 3.0084176678e-11 | 1787 |

This establishes that the CG result is genuinely inaccurate on the failing
nonlinear tangent, while MINRES satisfies the frozen R2 equivalence contract.
It does not prove that the tangent is indefinite; the SPD status remains
unproven.

## Full nonlinear M1 MINRES check

Because MINRES passed the exact failing system, the bounded full M1 check was
run with MINRES+Jacobi `rtol=1e-11`, direct fallback disabled. It completed all
12 increments and 145 Newton iterations with 133 linear solves and zero
fallbacks. Every linear solve satisfied the backward-error gate; the maximum
observed `eta_inf` was `2.3445324728241484e-12`.

The accepted load-factor path and all 133 line-search alpha values matched the
direct M1 reference. Final physical observables were equivalent:

| observable | MINRES | relative difference vs direct |
| --- | ---: | ---: |
| tip displacement | -0.18795714735201677 | 0 |
| strain energy | 4.693669347230475 | 0 |
| representative sigma_xx | 2837.843915881297 | 2.724147343624811e-15 |
| reaction resultant norm | 50.00000000000004 | 1.1368683772161603e-15 |

Both paths satisfy the force/moment equilibrium checks and deformation
envelope. The MINRES run took `618.9505745999631 s`, with peak RSS
`632,733,696` bytes and peak private memory `608,567,296` bytes. It used
1,627–1,733 Krylov iterations per linear solve (median 1,631, p95 1,707,
total 218,189). The direct reference took `758.9268259999808 s`, with peak
RSS `736,813,056` and private memory `711,041,024` bytes. These are observed
M1 measurements, not a general scalability claim.

The final iterative displacement/composite digests are not binary-identical to
the direct run, as expected for a distinct correction kernel; physical
observables, accepted path and line-search trajectory are equivalent within
the frozen contract.

## Telemetry and governance

Telemetry was minimally extended with `linear_backward_error_eta_inf`; events
now expose load step, Newton iteration, method, Krylov iterations, raw
residual, backward error, solve time, memory, line-search alpha and status.
It remains opt-in, JSONL/callback based, immediately flushed, and does not
write full matrices or vectors. Observer failures remain isolated from the
numerical state.

```text
PRODUCTION_SOURCE_CHANGED = YES (diagnostic telemetry field only)
MECHANICS_FORMULATION_CHANGED = NO
ELEMENT_FORMULATION_CHANGED = NO
MATURITY_CHANGED = NO
WP04_STATUS = HOLD
G04-10 = UNRESOLVED_LINEAR_SOLVER_REMEDIATION
WP04_POINTS = 0/12
VALIDATED_TOTAL = 29/100
M2/M3 = NOT RUN
PETSc/PyAMG = NOT ADDED
FULL_TEST_SUITE_RUN = NO
```

R2B validates MINRES+Jacobi on the frozen nonlinear M1 case but does not close
the C2 finer-mesh qualification. Owner review is required before any M2/C2
resume; no PETSc/PyAMG route is authorized by this record.
