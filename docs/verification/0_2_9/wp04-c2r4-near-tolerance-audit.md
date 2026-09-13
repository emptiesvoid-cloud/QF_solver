# WP04-C2R4 — near-tolerance stagnation and protocol audit

**Audit SHA:** `0b947bb6c1c684f71f2f7b5ab32ad8b9f9afbcc8`  
**Scope:** C2-M2 only; no M3, M4, PETSc/AMG, threshold change, or maturity change.

## Route consistency

The original WP04-C2 route calls `_newton_dead_load` without robustness
options. `solve_full_newton` consequently enables its existing compatibility
line search. The R2B direct and MINRES M1 routes likewise use the default
enabled setting and recorded the same alpha trajectory. C2R3 instead passed
the explicit experimental `line_search="off"` override.

This is `PROTOCOL_DRIFT`, not a reinterpretation of historical evidence.
C2R3 is retained unchanged as a valid diagnostic run, but it is not directly
comparable with the original C2 line-search route as qualification evidence.

## Residual contract

For load factor `lambda`, the unified Newton engine records

`relative_residual = ||(lambda F_ext - F_int(u))_free||_2 /
max(||(lambda F_ext)_free||_2, force_scale, 1.0)`.

The C2 route does not supply `force_scale`; the denominator is therefore the
larger of the target free-load norm and one. The numerator has force units and
the reported value is dimensionless. Early incremental residuals are O(1e-1)
because the previously accepted displacement equilibrates the preceding load
factor, not the next target factor. Near convergence the same normalized
unbalanced force is O(1e-10).

## Exact C2R3 replay and same-state forensics

The frozen C2R3 configuration (M2, MINRES/Jacobi, `rtol=1e-11`,
`atol=1e-14`, 10,000 iterations, fallback off, line search off, Newton
tolerance `1e-10`, 12 target intervals) reproduced `CONVERGENCE_STAGNATION`
at step 3, Newton iteration 11, load factor 0.25. The reported residual was
`1.1303927985055497e-10`, exactly matching C2R3.

One reduced 90,000 x 90,000 system with 3,835,710 nonzeros was captured
outside Git at
`C:\Users\fari\AppData\Local\Temp\qf_solver_029_c2r4_forensics\c2_m2_stagnation_step3.npz`
(27,324,848 bytes, SHA-256
`8c690567cc1307796fe5384d9c464e7eafd8b12a4dd96ebcaf98d9abfd43d85e`).
It contains the accepted pre-step displacement, plateau trial displacement,
reduced tangent, rhs, load factor and DOF maps, without serializing arbitrary
objects.

| correction on the exact plateau state | correction norm | eta-infinity | nonlinear residual after isolated correction |
| --- | ---: | ---: | ---: |
| MINRES/Jacobi, rtol 1e-11 | 1.38186197362739e-15 | 5.35038263131594e-13 | 1.16582683590919e-10 |
| MINRES/Jacobi, rtol 1e-12 | 1.38186196369975e-15 | 4.51549464378308e-13 | 1.16582682076569e-10 |
| direct SuperLU | 1.381861963439e-15 | 1.07752718802466e-15 | 1.16582682076569e-10 |

Five reassemblies of the untouched plateau state returned the same normalized
residual (`min = max = 1.1303927985055497e-10`; spread zero). The direct
correction is only `3.24802865160447e-16` relative to the trial displacement.
At the actual 0.25 load factor, force and moment balance are
`3.299667940206007e-14` and `8.554221404645066e-16`, respectively. Thus the
same-state evidence classifies this boundary as
`NONLINEAR_RESIDUAL_NUMERICAL_FLOOR`: direct precision does not reduce the
residual below the frozen criterion. No tolerance was changed.

## Canonical-line-search comparison

The Owner-authorized, M2-only protocol correction kept MINRES/Jacobi,
all linear and Newton tolerances, 12 target factors and fallback-off status
unchanged; it changed only line search to `existing`.

It accepted steps 1–3; step 3 converged at
`9.360621054518423e-11`. It then terminated at step 4, iteration 26 with
`LINE_SEARCH_FAILURE` and residual `1.0411047989090212e-10`. The line-search
trajectory is therefore different, but it does not complete M2 and is not
qualification evidence. It demonstrates that the C2R3 off-route stagnation
cannot be used alone to decide the canonical C2 protocol.

## Diagnostic and memory hygiene

The stale hard-coded `scipy.sparse.linalg.spsolve` label on Full-Newton
terminal diagnostics has been fixed without changing solve behavior. Terminal
diagnostics now identify the configured adapter backend; the focused regression
covers MINRES stagnation specifically.

Historical C2R3 memory values are preserved. C2R4 defines:

- `peak_rss_process`: maximum process RSS sampled by the independent monitor
  and telemetry samples.
- `peak_private_or_uss_process`: corresponding psutil USS/private maximum.
- `telemetry_sample_peak_rss`: maximum per-Newton telemetry RSS only.
- `telemetry_sample_peak_private`: maximum per-Newton telemetry private/USS
  only.

Windows `PrivateMemorySize` and psutil USS are not interchangeable; neither
historical field was overwritten.

## Decision

WP04 remains `HOLD`, G04-10 remains `UNRESOLVED`, points remain `0/12`, and
the validated roadmap remains `29/100`. No C2-M3 rerun, M4 run, PETSc work,
mechanics formulation change, element formulation change, or maturity change
occurred. Owner review is required before deciding whether a qualification
protocol correction or a tolerance/termination-policy decision is authorized.

Machine-readable results: `qualification/0_2_9/c2r4/near_tolerance_audit_result.json`.
