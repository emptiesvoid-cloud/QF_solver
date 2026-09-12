---
doc_id: DOC-029-020
revision: 0.1
status: controlled-evidence
applicable_version: 0.2.9-development
---

# Linear-solver remediation master record

This is a chronological technical index for the 0.2.9 WP04 linear-solver
remediation. It references the immutable R1/R2/R2B records and appends the
owner-authorized C2R3 overnight campaign. It is not a maturity or release
claim. The machine-readable companion is
`qualification/0_2_9/linear_solver_remediation_master.json`.

## Scope and decision

- Branch: `0.2.9-unified-nonlinear`
- C2R3 source SHA: `20186a940ba39b03bf68ee52b8b6137c698c2a16`
- Route for both cases: MINRES + Jacobi, `rtol=1e-11`, `atol=1e-14`,
  `maxiter=10000`, direct fallback OFF, 12 fixed increments, Newton tolerance
  `1e-10`, maximum 40 iterations, line search OFF.
- M2 and M3 were both run in separate child processes. Both terminated with a
  numerical `CONVERGENCE_STAGNATION`; neither was a memory/resource failure.
- Because both required cases did not converge, M2-to-M3 qualification deltas
  are not computable and G04-10 remains `UNRESOLVED`.
- WP04 remains HOLD at 0/12 and the validated total remains 29/100. M4 was not
  run, PETSc/AMG was not evaluated, and the full repository suite was not run.

## A. Original direct route

The original nonlinear path dispatched every reduced Newton tangent to
`scipy.sparse.linalg.spsolve` / SuperLU. Sparse factorization was rebuilt for
each Newton solve, with fill-in and factorization cost retained as the large-
mesh bottleneck. A non-invasive py-spy profile sampled approximately
98–100% of main-thread time inside `spsolve`/SuperLU.

The earlier M3 process was explicitly owner-aborted for remediation:

| field | value |
| --- | --- |
| PID | 25932 |
| CPU | 29,775.578 s |
| wall | 21,584.007 s |
| RSS | 10.46 GiB |
| private | 14.58 GiB |
| threads | 24 |
| classification | `ABORTED_BY_OWNER_FOR_LINEAR_SOLVER_REMEDIATION` |
| reason | `OWNER_ABORT_FOR_LINEAR_SOLVER_REMEDIATION` |

The stale external runner state `RUNNING` is not authoritative; the durable
owner-abort record is preserved in the existing C2 evidence.

## B. R1 — adapter and telemetry foundation

R1 added one nonlinear sparse-solver adapter, opt-in JSONL telemetry, DIRECT,
CG, MINRES and GMRES dispatch, NONE/JACOBI preconditioning and explicit direct
fallback. The initial strict raw-residual campaign remains immutable and is
recorded as `FAIL_PRESERVED`:

- direct raw relative residual: `7.512615895580403e-10`
- MINRES + Jacobi: `1.3406784179211412e-05` — initial FAIL
- CG + Jacobi: `2.5521445752242036e-09` — initial FAIL

The raw residual was retained as a diagnostic rather than silently replacing
the original result.

## C. R2 — scale-aware local contract

R2 froze a new contract using solution difference to DIRECT, normwise backward
error and physical observables:

- solution relative difference versus DIRECT `<= 1e-8`
- `eta_inf <= 1e-10`
- physical observable relative difference `<= 1e-8`
- finite result and deterministic repeated outcome required
- raw residual recorded, but not required to be lower than the direct baseline

The diagnostic CG sweep on the C2-M1 zero-state matrix was:

| rtol | raw residual | eta_inf | solution delta | iterations | seconds |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1e-10 | 2.5521445752242036e-09 | 2.4345593094701063e-15 | 1.263136934125695e-11 | 1939 | 4.012283799995203 |
| 1e-11 | 2.561021477606342e-09 | 2.3913202487804604e-15 | 1.2631294695351825e-11 | 1998 | 4.090833400026895 |
| 1e-12 | 2.5613919004247475e-09 | 2.341412350361331e-15 | 1.2631451590474693e-11 | 2201 | 4.515720400027931 |
| 1e-13 | 2.560245634602514e-09 | 2.3416928750841772e-15 | 1.2631457497865784e-11 | 2315 | 4.664493599964771 |

The MINRES sweep was:

| rtol | raw residual | eta_inf | solution delta | iterations | seconds | status |
| ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1e-10 | 1.3406784179211412e-05 | 4.729514646552805e-12 | 3.3888324301384204e-07 | 1604 | 3.4907299000187777 | initial R2 FAIL |
| 1e-11 | 2.355087533668818e-06 | 1.7486487560006215e-12 | 3.5379998868403373e-09 | 1629 | 3.5899714999832213 | recorded |
| 1e-12 | 1.934758628543101e-06 | 1.7040516750321025e-12 | 5.305458671225802e-11 | 1654 | 3.6559333999757655 | recorded |

The two bounded GMRES + ILU candidates (restart 50, fill factor 10) both hit
the 10,000-iteration limit. ILU-A used drop tolerance `1e-4`, setup time
`2.5424168999888934 s`, setup private bytes `165068800`, setup RSS bytes
`185712640`, and total time `188.01606980001088 s`. ILU-B used drop tolerance
`1e-5`, setup time `2.458274300035555 s`, setup private bytes `170192896`,
setup RSS bytes `191053824`, and total time `196.68780940002762 s`. Neither was
promoted.

## D. R2 Stage-C CG failure

On nonlinear C2-M1, CG + Jacobi with `rtol=1e-10` failed at load step 4,
Newton iteration 12, with `eta_inf≈1.0895221524409612e-05` and no direct
fallback. This is a genuine nonlinear correction failure, not a qualification
promotion.

## E. R2B failing-tangent forensics

R2B captured the exact CG-failing reduced tangent outside Git:

- shape: `27744 x 27744`
- nnz: `1,151,694`
- symmetry defect: `6.538813369795086e-17`
- `lambda_max=1329687.869479092`
- lower spectral estimate: not estimated; ARPACK did not converge
- SPD: `NOT_PROVEN`

Same-matrix results were:

| solver | eta_inf | solution delta versus DIRECT | iterations |
| --- | ---: | ---: | ---: |
| DIRECT | 5.351464074942563e-16 | 0.0 | 1 |
| CG + Jacobi, 1e-10 | 1.0895221524409612e-05 | 0.11167950837977482 | 334 |
| MINRES + Jacobi, 1e-11 | 5.539586978844418e-13 | 1.2292890785125705e-09 | 1731 |
| MINRES + Jacobi, 1e-12 | 3.4532323474136956e-13 | 3.008417667805209e-11 | 1787 |

The full nonlinear M1 MINRES check at `rtol=1e-11` completed all 12 increments,
145 Newton iterations and 133 linear solves with zero fallback. Its maximum
`eta_inf` was `2.3445324728241484e-12`; direct-equivalent physical observables
were obtained. Wall time was `618.9505746 s` versus the direct `758.9268 s`,
an observed ratio of `1.22615x`. Peak RSS was `632733696` bytes versus direct
`736813056`; peak private was `608567296` versus `711041024`. This is bounded
M1 evidence, not a general scalability claim.

## F. C2R3 overnight M2/M3

The owner-authorized orchestrator ran M2 and, after M2 returned, launched M3
in a new process with identical settings. Raw files are retained in
`qualification/0_2_9/c2r3/`.

### M2

M2 is the `48 x 24 x 24` mesh with 30,625 nodes, 165,888 TET4 elements and
91,875 full DOFs. The largest observed reduced tangent was `90000 x 90000`
with 3,835,710 nonzeros. The child started at
`2026-09-12T21:09:07.058546+00:00` and returned at
`2026-09-12T21:14:54.931569+00:00`.

It accepted load factors `1/12` and `2/12`, then terminated at load step 3
with `CONVERGENCE_STAGNATION`. It completed 18 observed Newton iterations and
16 MINRES solves. Total MINRES iterations were 40,843 (min 2,394, median
2,602, p95 2,620.25, max 2,624). Total linear-solve time was
`308.4431667999015 s`; maximum `eta_inf` was
`5.401027300872594e-12`. No fallback was used. No linear-solver contract
failure occurred, so no new failing-system binary was required. M2 wall time
was `347.8730394000304 s`, CPU time `358.1875 s`; telemetry-observed peak RSS
was `710877184` bytes and peak private/USS was `685223936` bytes.

No final converged displacement, energy or stress observable exists for M2;
M2-to-M3 qualification deltas are therefore not reported.

### M3

M3 is the `64 x 32 x 32` mesh with 70,785 nodes, 393,216 TET4 elements and
212,355 full DOFs. The largest observed reduced tangent was `209088 x 209088`
with 9,031,086 nonzeros. The fresh child started at
`2026-09-12T21:14:55.930112+00:00` and returned at
`2026-09-12T21:39:27.811917+00:00`.

It accepted load factors `1/12`, `2/12` and `3/12`, then terminated at load
step 4 with `CONVERGENCE_STAGNATION`. It completed 20 observed Newton
iterations and 17 MINRES solves. Total MINRES iterations were 57,156 (min
3,167, median 3,371, p95 3,483, max 3,527). Total linear-solve time was
`1366.0570388998603 s`; maximum `eta_inf` was
`6.620529972813195e-12`. No fallback was used. No linear-solver contract
failure occurred, so no new failing-system binary was required. M3 wall time
was `1471.8818355999538 s`, CPU time `1530.734375 s`; telemetry-observed peak
RSS was `1490403328` bytes and peak private/USS was `1466814464` bytes. A
separate live process sample observed a transient working set of `3216179200`
bytes and process-private value of `3944767488` bytes during allocation; these
are supplementary observations, not a platform durability guarantee.

No final converged M3 displacement, energy or stress observable exists.

### C2R3 decision

Both processes were responsive and returned normally. `RESOURCE_LIMITED=NO`
and `RESOURCE_FAILURE_PROVEN=NO` for this campaign. Both cases are numerical
failures under the frozen route, not resource failures. Since the pair did not
converge, the original M2-to-M3 displacement/energy/stress thresholds cannot
be applied. G04-10 remains `UNRESOLVED`; no M2/M3 qualification pass is
claimed.

## G. Targeted validation and tooling history

The following are separate historical campaigns and may overlap. They must
not be summed into one synthetic total:

| campaign | reported result |
| --- | --- |
| initial remediation | 54 passed; 48 passed; 48 passed |
| R2 | 21 passed; 41 passed; 27 passed; 34 passed; 15 passed; 43 passed; 6 passed |
| combined R2 scoped run | 187 passed |
| R2B | 83 targeted tests passed; 104 geometric/checkpoint tests passed |
| R1/R2/R2B tooling | Ruff PASS; compileall PASS; qualification JSON validation PASS; MkDocs strict PASS |
| mypy | 0 new diagnostics; 2 inherited diagnostics remain in `linear.py` |

C2R3 itself was an overnight numerical campaign, not a replacement for the
targeted regression counts above. Its raw telemetry is JSONL and immediately
flushed; `m2_result.json` and `m3_result.json` contain the structured terminal
metrics.

## Lessons and governance boundary

- DIRECT/SuperLU remains the correctness reference but scales poorly on large
  nonlinear runs because repeated sparse LU factorization and fill-in dominate.
- CG + Jacobi is excellent on the zero-state M1 matrix but produced an invalid
  nonlinear correction at step 4; it is not promoted.
- GMRES + ILU was not viable in the tested local configurations; both bounded
  candidates hit the iteration limit and are not promoted.
- MINRES + Jacobi passed the exact CG-failing tangent and full nonlinear M1;
  it is the current bounded local candidate, but C2R3 shows that the frozen
  M2/M3 nonlinear route still reaches stagnation before qualification closure.
- SPD is `NOT_PROVEN`; no indefiniteness claim is made.
- PETSc/AMG was not evaluated in this remediation.
- No frictional, distributed, nonlinear-dynamics or general scalability claim
  is made. Maturity remains unchanged.

WP04 remains `HOLD`, G04-10 remains unresolved, and the next step is Owner
review before any further WP04 M2/C2 resume or other solver-policy change.
