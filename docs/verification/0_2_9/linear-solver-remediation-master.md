---
doc_id: DOC-029-020
revision: 0.1
status: controlled-evidence
applicable_version: 0.2.9-development
---

# Linear-solver remediation master record

This is a chronological technical index for the 0.2.9 WP04 linear-solver
remediation. It references the immutable R1/R2/R2B records, appends the
owner-authorized C2R3 overnight campaign, and records the recovered C2R6
campaign. It is not a maturity or release claim. The machine-readable
companion is
`qualification/0_2_9/linear_solver_remediation_master.json`.

## Historical C2R3 scope snapshot

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

The current recovered C2R6 status is recorded in section I below. It supersedes
the C2R3 snapshot for current campaign status only; the C2R3 observations and
raw artifacts remain immutable.

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

## H. C2R5 canonical M2 residual-precision audit

C2R5 is an Owner-authorized M2-only diagnostic at source SHA
`571b7f64450ec556e1f9a59ecc65826cf49675d5`. It corrected the C2R3 protocol
drift for this reproduction by using the canonical existing/enabled line
search, while retaining MINRES + Jacobi (`rtol=1e-11`, `atol=1e-14`,
`maxiter=10000`, fallback OFF), Newton tolerance `1e-10` and 12 target
increments. M3 and M4 were not run.

The canonical result reproduced three accepted steps and a step-4
`LINE_SEARCH_FAILURE` at Newton iteration 26, with residual
`1.0411047989090212e-10`. The run emitted 67 iteration events, had wall/CPU
times `1678.3279889000114 s` / `1741.671875 s`, and no linear-solver contract
failure. The one captured reduced system is retained outside Git at
`C:\Users\fari\AppData\Local\Temp\qf_solver_029_c2r5_forensics\c2_m2_canonical_step4_failure.npz`:
shape `90000 x 90000`, `3835710` nonzeros, `27394683` bytes, SHA-256
`f94e13d6a92c7ed6203a85f9be23d7fb7d23bf7552b8081393574472cb6b1b01`.

### Residual and cancellation evidence

The driver computes
`||(lambda*F_ext-F_int)_free||_2 / max(||(lambda*F_ext)_free||_2,
force_scale,1)`. C2 supplies no additional force scale, so the captured
step's denominator is 1.0 because its free target norm is
`0.6666666666666664`.

On free DOFs the target and internal force norms are
`0.6666666666666664` and `0.6666666666666998`; their imbalance is
`1.0411047989090212e-10`. The 2-norm and infinity-norm cancellation indicators
are `12806907957.1103` and `14255843879.227219`. Five repeated normal
reassemblies of the untouched trial were bitwise identical, with residual
min/max/mean `1.0411047989090212e-10` and spread zero. The accepted state
before step 4 has force/moment errors `1.324838322760566e-14` /
`4.172828174723821e-15`; the captured step-4 trial has
`2.4672319589855068e-14` / `2.4472628640241725e-15` against the corresponding
target load.

The local constitutive and kinematic calculations remained float64. Replacing
only the global sum of those local contributions gave:

| accumulation | normalized residual |
| --- | ---: |
| normal float64 | `1.0411047989090212e-10` |
| pairwise float64 | `1.0411048963249379e-10` |
| compensated/Kahan float64 | `1.0411048278985379e-10` |
| platform `longdouble` | `1.0411048047789044e-10` |

On the Windows environment, NumPy `longdouble` is an 8-byte float64 alias.
None of these methods materially lowers the floor. A per-DOF
`gamma_n*sum(abs(local))` diagnostic estimates `9.926818702066467e-13`, with
observed/estimated ratio `104.87799063886342`; this bound covers only the
local-contribution sum and does not prove a global-accumulation-only cause.

### Same-state and line-search evidence

Direct SuperLU, MINRES/Jacobi at `1e-11` and MINRES/Jacobi at `1e-12` all
produce machine-scale corrections (`8.108503804890719e-16`,
`8.10850383404193e-16`, `8.108503805815807e-16`) with relative correction
`~1.42954675e-16`. Their `eta_inf` values are
`1.148509118958703e-15`, `5.232341881338818e-13` and
`4.999305581031921e-13`. Applying each to an isolated copy yields the same
normal residual `1.1786672101386367e-10`; no correction materially improves
the physical imbalance.

The strict line search tested alphas
`1, 1/2, 1/4, 1/8, 1/16, 1/32, 1/64, 1/128, 1/256, 1/512, 1/1024,
1/2048, 1/4096, 1/8192, 1/16384`. The corresponding merits are, in order,
`1.1786672101386367e-10`, `1.087998092674283e-10`,
`1.0816636703227027e-10`, `1.0687095189798257e-10`,
`1.0608807344801181e-10`, `1.0537365372983584e-10`,
`1.0495728321429686e-10`, `1.0435852481068462e-10`,
`1.0430259234360327e-10`, `1.0429477685691295e-10`,
`1.041523504194613e-10`, `1.0416104471125124e-10`,
`1.0413191293026293e-10`, `1.0412069200871767e-10` and
`1.0411521045606017e-10`. The initial merit was
`1.0411047989090212e-10`; every tested merit was larger. The diagnostic
classification is therefore `LINE_SEARCH_TRUE_REJECTION`, with the overall
problem still classified as a numerical residual floor.

The C2R5 root classification is
`NONLINEAR_RESIDUAL_NUMERICAL_FLOOR`, mechanistically bounded by strong force
cancellation and float64 precision. It does not support an
`R6_ACCUMULATION_PRECISION_REMEDIATION` recommendation. A future
`R6_FLOOR_AWARE_TERMINATION_POLICY` is recommended for Owner review, but no
mixed criterion or threshold was implemented or frozen; the R2B M1 route was
not retroactively reclassified. The complete C2R5 record is
`docs/verification/0_2_9/wp04-c2r5-residual-precision-audit.md` and
`qualification/0_2_9/c2r5/residual_precision_audit.json`.

WP04 remains `HOLD`, G04-10 remains `UNRESOLVED`, points remain `0/12` and the
validated total remains `29/100`. Historical R1/R2/R2B/C2R3/C2R4 evidence is
unchanged; no M3/M4, PETSc/PyAMG or full-suite work was performed.

## I. C2R6 recovered floor-aware M2/M3 campaign

C2R6 is recovered here from the completed files under
`qualification/0_2_9/c2r6/`; this audit did not rerun M2 or M3. The campaign
source SHA was `2c52bf8196a7d47d14ce1784290580160de26590` on branch
`0.2.9-unified-nonlinear`. Both cases used the frozen MINRES/Jacobi route with
`rtol=1e-11`, `atol=1e-14`, `maxiter=10000`, direct fallback disabled,
existing/enabled line search, Newton tolerance `1e-10`, 12 increments, and
floor-aware termination enabled.

M2 (`48x24x24`, 165,888 TET4, 91,875 full DOFs) and M3 (`64x32x32`, 393,216
TET4, 212,355 full DOFs) both report `COMPLETED` with process-end reason
`COMPLETED`. Each has 12 accepted records, steps 1 through 12, load factors
from 1/12 through 1.0, matching declared/actual telemetry counts (313/313
and 288/288), no failure, no failing-system capture, and no direct fallback.
The recorded worker PIDs 57564 and 30220 are no longer running.

The result-level Newton totals are 300 and 275, and linear solves are 297 and
272. Nine of the 12 accepted steps in each case use
`CONVERGED_NUMERICAL_FLOOR`; the other three use `CONVERGED_RESIDUAL`. All
floor events satisfy the frozen conjunction when rechecked from the existing
records. Maximum linear backward error is `4.777962584217645e-12` for M2 and
`8.106166618904346e-12` for M3. The telemetry `SOLVE_COMPLETED` aggregate
Newton field is 288 and 263, exactly 12 below the result/per-step totals
because it excludes the floor-converged events. This is recorded as a
non-blocking bookkeeping discrepancy; no rerun was performed.

Recovered final observables are:

| Observable | M2 | M3 |
| --- | ---: | ---: |
| Tip displacement | -0.19685864781061374 | -0.2002482511318092 |
| Reaction resultant norm | 49.9999999999999 | 49.99999999999998 |
| Strain energy | 4.915487767084533 | 4.999939075668591 |
| Representative `sigma_xx` | 3002.540859194057 | 3068.972048649666 |
| Minimum `det(F)` | 0.9917813121785688 | 0.9909797199809931 |

The accepted load-factor paths are identical and both cases remain inside the
frozen deformation envelope. Applying the original frozen M2-to-M3 formula
`abs(fine-medium)/max(abs(fine),abs(medium),1e-12)` gives displacement
`0.01692700586415766` (limit 0.02), reaction
`1.563194018672221e-15` (limit 0.02), energy
`0.016890467524899724` (limit 0.02), and representative stress
`0.02164607184507869` (limit 0.10). All four pass.

The raw runner's top-level `G04-10: UNRESOLVED` is preserved as a historical
placeholder because that runner did not calculate the pair thresholds. The
derived controlled audit is
`qualification/0_2_9/c2r6/frozen_threshold_audit.json` and the companion
record is [the C2R6 recovered audit](wp04-c2r6-floor-aware-termination.md).
The derived decision is `PASS_CANDIDATE_PENDING_OWNER_REVIEW`; WP04 remains
`HOLD` at `0/12`, validated total remains `29/100`, and no maturity change is
claimed. M4, PETSc/PyAMG, and the full repository suite were not run.
