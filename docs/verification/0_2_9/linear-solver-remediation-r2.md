---
doc_id: DOC-029-LINEAR-SOLVER-REMEDIATION-R2-001
revision: 1.0
status: hold
applicable_version: 0.2.9-development
---

# Linear-solver remediation R2

R2 is a SciPy-local production-infrastructure remediation. It does not change
the mechanics formulation, element formulation, tolerance of the WP04
qualification campaign, maturity, or WP04 point accounting. The controlled
machine-readable evidence is
`qualification/0_2_9/wp04_linear_solver_r2.json`; candidate inputs and
per-candidate outputs are in
`qualification/0_2_9/wp04_linear_solver_r2_candidates/`.

## Preserved history and frozen contract

The R1 strict residual campaign remains immutable as
`INITIAL_STRICT_RESIDUAL_CAMPAIGN = FAIL_PRESERVED`. Its direct reference
reported raw relative residual `7.512615895580403e-10`, MINRES+Jacobi
reported `1.3406784179211412e-05`, and CG+Jacobi reported
`2.5521445752242036e-09` against the original `1e-10` gate. R2 does not
retroactively change those results.

The R2 contract was frozen before the candidate runs:

- solution relative difference versus direct `<= 1e-8`;
- normwise backward error `eta_inf <= 1e-10`;
- physical observable differences `<= 1e-8`;
- finite solution and solver-reported convergence required;
- raw relative residual retained as a diagnostic only;
- repeated numerical outcome required;
- CG `rtol` sweep `1e-10, 1e-11, 1e-12, 1e-13`;
- MINRES `rtol` sweep `1e-10, 1e-11, 1e-12`;
- GMRES restart `50`, ILU-A `(drop_tol=1e-4, fill_factor=10)` and ILU-B
  `(drop_tol=1e-5, fill_factor=10)`.

The backward-error diagnostic is

```text
eta_inf = ||A x - b||inf /
          max(||A||inf ||x||inf + ||b||inf, 1e-14)
```

The adapter measures the reduced CSR matrix symmetry defect and selects CG
only when the caller explicitly sets `assume_spd=True`; otherwise a symmetric
matrix uses MINRES and a nonsymmetric matrix uses GMRES. ILU is restricted to
GMRES. Direct fallback remains explicit and is disabled in the qualification
candidate runs.

## Owner-aborted C2-M3 record

The prior C2-M3 process record remains
`ABORTED_BY_OWNER_FOR_LINEAR_SOLVER_REMEDIATION`, with PID `25932`, CPU
`29,775.578 s`, wall `21,584.007 s`, RSS `10.46 GiB`, private memory
`14.58 GiB`, and 24 threads. The py-spy sample was approximately 98–100% in
`scipy.sparse.linalg.spsolve`/SuperLU. The stale external runner state is
documented as an interrupted status-write artifact; it is not a resource,
numeric, or timeout classification.

## Stage B — C2-M1 zero-state reduced matrix

The frozen matrix has 27,744 free DOFs, 1,151,694 nonzeros, CSR shape
27,744 x 27,744, and measured symmetry defect `0.0`. The following results
are the separate-process runs recorded in the raw JSON files.

| candidate | result | raw residual | eta_inf | solution delta vs direct | iterations | total s |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| direct | PASS | 7.5126158956e-10 | 6.5429841378e-16 | 0 | 1 | 4.6859 |
| CG+Jacobi, 1e-10 | PASS_R2_EQUIVALENCE | 2.5521445752e-09 | 2.4345593095e-15 | 1.2631369341e-11 | 1939 | 4.0123 |
| CG+Jacobi, 1e-11 | PASS_R2_EQUIVALENCE | 2.5610214776e-09 | 2.3913202488e-15 | 1.2631294695e-11 | 1998 | 4.0908 |
| CG+Jacobi, 1e-12 | PASS_R2_EQUIVALENCE | 2.5613919004e-09 | 2.3414123504e-15 | 1.2631451590e-11 | 2201 | 4.5157 |
| CG+Jacobi, 1e-13 | PASS_R2_EQUIVALENCE | 2.5602456346e-09 | 2.3416928751e-15 | 1.2631457498e-11 | 2315 | 4.6645 |
| MINRES+Jacobi, 1e-10 | FAIL_R2_EQUIVALENCE | 1.3406784179e-05 | 4.7295146466e-12 | 3.3888324301e-07 | 1604 | 3.4907 |
| MINRES+Jacobi, 1e-11 | PASS_R2_EQUIVALENCE | 2.3550875337e-06 | 1.7486487560e-12 | 3.5379998868e-09 | 1629 | 3.5900 |
| MINRES+Jacobi, 1e-12 | PASS_R2_EQUIVALENCE | 1.9347586285e-06 | 1.7040516750e-12 | 5.3054586712e-11 | 1654 | 3.6559 |
| GMRES+ILU-A | SOLVER_FAILURE | not available | not available | not available | 10000 | 188.0161 |
| GMRES+ILU-B | SOLVER_FAILURE | not available | not available | not available | 10000 | 196.6878 |

The CG sweep demonstrates that the original raw residual is conditioning
sensitive: tightening `rtol` does not reduce the measured raw residual, while
the solution delta and normwise backward error remain very small. GMRES+ILU-A
and B both reached the deterministic iteration limit (`info=10000`) and are
not accepted candidates. ILU setup private memory was approximately 165.1 MB
and 170.2 MB for A/B, with peak private memory approximately 187.8 MB and
194.2 MB; the setup and solve memory are recorded separately in the candidate
JSON.

An independent second CG+Jacobi `rtol=1e-10` process reproduced the core
diagnostics exactly: 1,939 Krylov iterations, raw residual
`2.5521445752242036e-09`, `eta_inf = 2.4345593094701063e-15`, and solution
delta `1.263136934125695e-11`. Wall time is intentionally not part of the
deterministic identity.

CG+Jacobi at `rtol=1e-10` was selected for the permitted Stage-C test because
it was the first numerically accepted candidate under the frozen ordering
(correctness, robustness, memory, wall time). This selection did not imply
that Stage C would pass.

## Stage C — frozen WP04 C2-M1 nonlinear case

The direct reference completed all 12 accepted increments and 145 Newton
iterations. Its telemetry recorded 133 linear-solve events, no fallbacks, and
647.0571 s of linear-solve time. The run took 758.9268 s, with peak RSS
736,813,056 bytes and peak private memory 711,041,024 bytes. Final observables
were:

- tip displacement `-0.18795714735201677`;
- strain energy `4.693669347230475`;
- representative `sigma_xx` `2837.843915881305`;
- force equilibrium relative error `3.552085348027768e-14`;
- moment equilibrium relative error `4.505940522377961e-15`;
- minimum `det(F)` `0.992927047661092`;
- maximum principal stretch `1.0089023457744155`;
- maximum Green–Lagrange norm `0.009423514082040636`;
- accepted load factors `1/12, 2/12, ..., 1`.
The selected CG+Jacobi candidate did not complete Stage C. It emitted 53
telemetry events, including 48 Newton iteration events, 45 linear-solve
events, 83,100 aggregate Krylov iterations, and no direct fallbacks. At load
step 4, Newton iteration 12, the adapter rejected the correction under the
frozen scale-aware contract: true raw relative residual
`9.6806965019717e-05` and `eta_inf = 1.0895221524409612e-05`, versus the
`1e-10` backward-error limit. The process took 218.2437 s, with peak RSS
626,094,080 bytes and peak private memory 605,446,144 bytes. The failure
diagnostics identify the backend as `scipy.sparse.linalg.cg`; no direct
fallback was used.

This is a failed iterative nonlinear validation, not a WP04 qualification
run. It does not establish a scalable candidate, and no C2-M2 or C2-M3 run
was started. The direct successful M1 result is retained as a reference only;
the failed CG path is not used to alter WP04 evidence.

## Governance and next step

The adapter and telemetry are production-source changes, but they are limited
to numerical infrastructure and diagnostics:

```text
PRODUCTION_SOURCE_CHANGED = YES
MECHANICS_FORMULATION_CHANGED = NO
ELEMENT_FORMULATION_CHANGED = NO
MATURITY_CHANGED = NO
```

WP04 remains `HOLD`, G04-10 remains
`UNRESOLVED_LINEAR_SOLVER_REMEDIATION`, WP04 points remain `0/12`, and the
validated total remains `29/100`. The full repository suite was not run.
Owner review is required before any WP04 M2/C2 resume. A future R3 decision
may evaluate PETSc/AMG; R2 intentionally adds no external dependency.
