---
doc_id: DOC-029-006
revision: 0.2
status: controlled
applicable_version: 0.2.9-development
---

# 0.2.9 progress tracker

| Work package | Points | Status |
| --- | ---: | --- |
| WP00 | 4 | Closed |
| WP01 | 12 | **Closed** — Owner-approved unified nonlinear core |
| WP02 | 6 | **Closed** — 6/6; independent WP02-E audit `GO_WITH_LIMITATIONS` |
| WP03 | 7 | **Closed** — 7/7; independent WP03-E audit `GO_WITH_LIMITATIONS` |
| WP04 | 12 | **Closed — 12/12; independent WP04-F `GO_WITH_LIMITATIONS` audit** |
| WP15 | 2 | **Closed — 2/2; governing-branch telemetry integration validated** |
| WP16 | 0 | **Post-release operational step — external archive/Git LFS migration for large evidence** |
| WP05 | 5 | **Closed — 5/5, bounded with limitations; C/D structural qualification and E cross-family closure accepted** |
| WP06 | 8 | **Owner accepted A/B/C — 4/8 with limitations; D accepted as experimental bounded evidence only**; no formal D points; historical D failure preserved |
| WP07 | 10 | **Owner accepted — 10/10 with bounded limitations; A–E closed** |
| WP08 | 8 | **Closed — 8/8; Owner-approved with limitations** |
| WP09 | 8 | **Closed — Owner accepted 8/8; HEX8-only bounded corotational J2 with limitations** |
| WP10 | 6 | **Closed — Owner accepted 6/6; bounded TET4/HEX8/HEX20/TET10 coupled evidence with limitations** |
| WP11–WP14 | 12 | Not started |
| **Validated total (consolidated ledger)** | **84 / 100** | **Includes WP05 5/5, WP06 4/8, WP07 10/10, WP08 8/8, WP09 8/8 and WP10 6/6** |

## Current administrative closure

On 2026-09-22 the Owner accepted WP09 HEX8 R3 at 8/8 and WP10 at 6/6
within the explicitly bounded multi-family scope. WP10 covers the recorded
TET4, HEX8, HEX20 and TET10 evidence; it does not claim unrestricted
finite-strain behavior, frictional/finite-sliding contact, dynamics, MPI/PETSc,
or external-solver correlation. The TET10 M2 moment-balance value is retained
as an accepted limitation because no equilibrium threshold was frozen in the
R2 contract. The reconciled local machine ledger is therefore 84/100.
The governing push remains a separate publication step and does not change
the evidence or the decision.

The Owner-approved WP05-C/D/E integration adds 3 bounded points to the
58/100 pre-integration ledger, producing 61/100. WP07-D then added 3 points
(61→64 in the consolidated ledger), and WP07-E added 2 (64→66). The earlier
Owner-stated 61/100 after D used the 58/100 pre-WP05 baseline; the 3-point
difference is the already accepted local WP05-C/D/E award, not duplicated
credit. The governing branch is pushed at
`51e8d09c23a2f5ecaf61251cb308e025752b6d6b`. See the [WP05-C/D/E Owner
integration audit](wp05-cde-owner-integration.md) and [WP07 score-ledger
reconciliation](owner-decisions.md#wp07-d-and-wp07-e-closure-and-score-ledger-reconciliation).

## WP05 bounded closure

WP05-C TET10 H1/H2/H3, WP05-D HEX20 H1/H2/H3, and the evidence-only WP05-E
H3 cross-family comparison are accepted within their frozen benchmark and
observable scope. Historical WP05-D `FAIL_CLOSED` evidence remains preserved.
WP05-E uses the historical common `representative_sigma_xx`; the HEX20-only
clipped-window value is not substituted. The observed 5.2784% stress
agreement is not a general stress-field equivalence claim. Code_Aster or
another external-solver comparison is deferred to future V&V and remains
explicitly unclaimed. See the [WP05-C report](wp05-c-tet10-formal-requalification.md),
[WP05-D Owner review](wp05d-owner-validation-review.md), and [WP05-E closure](wp05-e-cross-family-closure.md).

WP07 is **OWNER-ACCEPTED — 10/10 WITH LIMITATIONS**. A/B/C remain formally
accepted; D R1 was awarded 3/3 after production/reference gates and authorized
replays passed; E R2 was awarded 2/2 after the fail-closed checker accepted
all six negative cases and the D evidence dependencies. D was not rerun for
E. The accepted scope remains bounded to the frozen routes and evidence;
updated-search and finite-sliding contact remain research-only. See the
[WP07-E Owner acceptance](wp07e-owner-acceptance-r2.md), [WP07-E closure
audit](wp07e-closure-owner-review-r2-final.md), and [WP07 integration
audit](wp07-integration-into-governing-branch.md).

The frozen roadmap declares 100 total points, and its listed package weights
sum to 100. No package weights were changed.

WP16 is an operational post-release step with zero qualification points. It
will publish or migrate large raw evidence outside ordinary Git history,
preserve SHA-256 manifests and restore reproducibility without changing any
solver result or qualification decision. The current WP09 raw archive is
`qualification/0_2_9/wp09_large_artifacts_archive_v1.json`.

WP06-A/B/C were revalidated against the current governing source with 118
focused continuation, rollback/restart and identity tests passing. The Owner
accepted A at 1/1, B at 1/1 with limitations, and C at 2/2 within its bounded
algebraic/toy scope. WP06 is now **4/8 officially** and the consolidated
ledger is **70/100**. The evidence remains limited to source/formulation
audit, state/restart behavior and algebraic/toy identities; it does not
qualify a structural postbuckling path. The Owner explicitly did **not**
authorize WP06-D R2 structural execution. Historical WP06-D1 M2
`FAIL_CLOSED` is preserved. See the [WP06-A/B/C revalidation package](wp06-abc-current-revalidation.md)
and [Owner decision record](wp06-abc-owner-decision.md).

The stale WP06-D R1 runner is now quarantined: it used the node-specific
control DOF rather than the frozen mean-crown monitor and targeted shared R1
output paths. Its command entry point is fail-closed; the historical raw
failure remains untouched. R2 execution is not ready: it still needs a frozen
current-source contract and exact Owner authorization. The safety regression
selection passed 145 tests; no structural solve was run. See the
[WP06-D R2 safety preparation](wp06d-r2-runner-safety-preparation.md).
The standalone R2 authorization helper has since been hardened to query Git
provenance directly and to constrain contracts, grants and output paths. A
current-source R2 contract draft and no-solve limit-point evaluator are now
available for Owner review. The strict-monotone q-continuity interpretation is
explicitly not frozen pending that review. No dedicated R2 runner or
independent reference implementation exists yet; D execution remains
unauthorized. See the [guard hardening audit](wp06d-r2-guard-hardening.md)
and [R2 contract/path-gate preparation](wp06d-r2-contract-path-gates.md).

## WP06-D bounded experimental decision

On 2026-09-19, the Owner accepted the local-axial M2/M3 campaign as
**experimental bounded continuation evidence**. M2 and M3 each completed 160
accepted states, the independent observable recomputation passed, and the
archival evidence replay passed. No limit point was detected, so WP06-D
remains **0/2 formal points** and WP06 remains **4/8**. This decision makes no
postbuckling, bifurcation, independent-path-solve, production-replay or full
three-dimensional mesh-convergence claim. WP06-E and WP06-F remain blocked for
formal closure. Historical WP06-D1 `FAIL_CLOSED` evidence is unchanged. See
the [bounded experimental Owner decision](wp06d-owner-bounded-experimental-decision.md)
and the [diagnostic requalification report](wp06d-local-axial-diagnostic-requalification.md).

## WP08 closure

The Owner has approved WP08-A through WP08-E at **8/8**. Together with the
accepted WP05 5/5 and WP07 10/10 closures, the consolidated total at that
checkpoint was **66/100**, before the subsequent WP06 A/B/C award. The reviewed evidence is the frozen
WP08 A–D closure, WP08-E accepted-state restart closure, and direct Owner
inspection package; see the [Owner approval](wp08-owner-approval.md),
[WP08-E closure report](wp08e-closure-report.md), and
[inspection record](../../../qualification/0_2_9/wp08_closure/wp08_owner_review_inspection.json).
Historical FAIL_CLOSED evidence and its execution SHAs remain preserved; this
decision neither reruns nor overwrites M1/M2/M3 evidence.

The approved claim is bounded to the serial/direct `linear_static`
frictional-contact route with small displacement, fixed initial search/face/
normal, and positive friction coefficient and tangential stiffness. It makes
no claim for frictional updated search, finite sliding, general nonlinear
friction, mid-Newton or general nonlinear restart, global pressure-coupled
tangent consistency, complete global energy decomposition, external-solver
correlation, MPI/PETSc, or dynamics.

WP01 is closed by the independent Owner decision recorded in
[the WP01 closure record](wp01-owner-closure.md), based on audit SHA
`6876d867cdd845195e8946b05329b0bc82937fdc`. The decision is
`GO_WITH_LIMITATIONS`, with G01/G05/G06/G07/G10 retaining their documented
bounded/research boundaries. Unified checkpoint persistence, frictional
contact migration and adaptive penalty-contact qualification remain future
work; inherited typing debt remains documented. At that historical checkpoint,
OD-029-01 was still OPEN and blocked WP09 only; it was subsequently closed by
the Owner decision recorded above. WP02 is closed by the independent audit; Owner review is
required before WP04 authorization.

## WP02 closure

WP02-A froze the prospective state, rollback and checkpoint contract at 0/6
points. WP02-B implemented the schema-v2 persistence foundation: one accepted
`NonlinearState` authority, deterministic typed serialization,
component/composite digest validation, topology checks, bounded schema-1
migration and atomic canonical writes. WP02-C migrated solver-level fixed and
adaptive restart ownership. WP02-D now routes the public arc-length restart
path through the accepted composite state while retaining its specialized
correction kernel. WP02-D1 remediates and verifies the caller-visible
material-state mirror after a path-dependent restart. The independent WP02-E
audit at `c4e02fbd2d1262f621f6c8d4f07ee2da89d885f5` found no in-scope production
blocker and closes WP02 at **6/6**, bringing the validated roadmap to
**22/100**. Its `GO_WITH_LIMITATIONS` result is bounded to supported
single-process fixed/adaptive/arc restart routes; it does not claim frictional
contact, distributed, nonlinear-dynamics or adaptive penalty-contact restart.
Owner review is required before the independent WP03-E closure audit.

## WP03-A contract phase

WP03-A freezes the Newton robustness and adaptive-control contract at
ecc09f0bae2dab867c12d7e471860887f6ef0548. It records the actual current
authority map, duplicate policy surfaces to consolidate, canonical stagnation
and line-search semantics, the failure/retry matrix and a 16-case baseline
campaign. No production source was changed during WP03-A, and no WP03 points
were awarded. WP03-B is recorded as a targeted implementation phase; its
historical evidence remains unchanged, including the pre-existing adaptive
rollback benchmark signature mismatch at that SHA.

The controlled records are [the robustness contract](wp03-robustness-contract.md),
[the architecture map](wp03-architecture-map.md), [the failure/retry
matrix](wp03-failure-retry-matrix.md), [the baseline campaign](wp03-baseline-campaign.md),
[the gate matrix](wp03-gate-matrix.md) and [the implementation
decomposition](wp03-implementation-plan.md).

## WP03-B implementation

WP03-B implements one formulation-neutral
`UnifiedNonlinearRobustnessController` for stagnation decisions and line-search
dispatch. `UnifiedNewtonEngine` consumes its deterministic diagnostics, while
the legacy helpers delegate without retaining a second reduction loop. The
public default is a four-sample `1e-10` residual plateau decision and strict
line search with a `1e-4` floor and 12 reductions. The historical direct-helper
defaults remain an explicit compatibility configuration and were not observed
to change the easy baseline outcomes. Targeted evidence is recorded in
[the WP03-B baseline](wp03-b-baseline.md) and [the WP03-B authority record](wp03-b-robustness-authority.md).

## WP03-C implementation

WP03-C is `ADAPTIVE_POLICY_AUTHORITY` at 0/7 points. A single
`UnifiedAdaptiveStepPolicy` now owns proposed increment, retry/cutback,
growth, shrink and terminal boundary decisions for both stateless adaptive
Full Newton and stateful material load control. Accepted physical state
continues to be owned by `UnifiedContinuationController` and
`NonlinearStateTransaction`. The B16 signature mismatch was resolved as a
stale verification fixture seam; no numerical source or formulation changed.

The controlled records are [the WP03-C baseline](wp03-c-baseline.md) and
[the WP03-C adaptive policy evidence](wp03-c-adaptive-policy.md). WP03-D now
records the common arc-length radius/retry policy in
[the WP03-D evidence](wp03-d-arc-radius-policy.md), including the
target-clipped retry-progress correction. Difficult-case improvement is not
yet demonstrated; Owner review is required before independent WP03-E.

## WP03-D implementation

WP03-D is `ARC_LENGTH_ROBUSTNESS_BOUNDARY` at 0/7 points. One
`UnifiedArcLengthRadiusPolicy` now owns arc-radius keep/grow/shrink, retry
classification, minimum-radius boundaries and deterministic diagnostics while
the augmented arc-length correction kernel and branch-selection mathematics
remain unchanged. The policy distinguishes carried `policy_radius` from the
target-clipped `effective_attempt_radius`; when the latter would repeat after
a nominal cutback, the next effective attempt is forced strictly smaller.
Rollback remains before radius policy evaluation, and checkpoint persistence
remains after physical acceptance. The start-SHA D-B01–D-B15 baseline and
targeted after-evidence are recorded in
`qualification/0_2_9/wp03_d_baseline.json` and
`qualification/0_2_9/wp03_d_arc_radius_policy.json`.

The focused WP03-D tests report `40 passed`. Existing WP03-B/C, WP02-D/D1 and
continuation/arc regressions remain green in the controlled targeted campaign.
The independent WP03-E audit independently closes G03-10 with the same-model
target-clipped retry challenge: repeated effective attempts drop from five to
one without changing the accepted physical solution. WP03 is therefore
**CLOSED at 7/7**, the roadmap is **29/100**, and the next step is Owner review
before WP04 authorization.

## WP03-E independent closure

The audit at `4ca71d549ea13460086f52670baa42c74d9ac1aa` reports one authority
each for stagnation, line search, adaptive step and arc radius. It found no
policy able to commit accepted state, no rollback leak, and no checkpoint
failure-induced physical retry. Easy pre-WP03 comparisons are exact for the
replayed core paths; targeted geometric/contact results remain bounded and
unchanged. The decision is `GO_WITH_LIMITATIONS`, retaining the documented
frictional-contact, adaptive-penalty-contact, distributed and dynamics scope
boundaries. See [the WP03-E closure record](wp03-e-independent-closure.md).

## WP04-A contract phase

WP04-A freezes a prospective two-family qualification contract for TET4 and
HEX8 only: homogeneous `isotropic_3d` Total-Lagrangian StVK solids, static
nodal dead loads, fixed displacement constraints and serial fixed/adaptive
load control. Objectivity, affine finite-deformation patch, force/energy,
tangent, accepted-path work refinement, small-load, equilibrium, mesh,
cross-family and deterministic replay gates are fixed before implementation.

The historical WP13-11 discovery record remains unchanged and remains
`RESEARCH_ONLY`: its 24-sample trapezoidal energy/work comparison missed its
discovery threshold and lacked public accepted-increment snapshots. The current
transaction/controller callback boundary was the authoritative accepted-state
provenance used by WP04-B, while WP04-A itself made no completion or maturity
claim. See [the WP04 contract](wp04-geometric-qualification-contract.md).

The contract is split into the [state/checkpoint contract](wp02-state-checkpoint-contract.md),
[compatibility matrix](wp02-compatibility-matrix.md),
[failure matrix](wp02-failure-matrix.md), [prospective gates](wp02-gate-matrix.md),
[implementation decomposition](wp02-implementation-plan.md), [WP02-B
schema-v2 evidence](wp02-b-schema-v2-foundation.md), [WP02-C fixed/adaptive
restart evidence](wp02-c-fixed-adaptive-restart.md), [WP02-D arc-length
restart evidence](wp02-d-arc-length-restart.md), [WP02-D1 material-state
ownership remediation](wp02-d1-material-state-alias.md) and the independent
[WP02-E closure audit](wp02-e-independent-closure.md).

## WP04-B mechanics identities

WP04-B is the targeted mechanics-identities phase at 0/12 points. The
qualification-only harness uses independent StVK formulas from the prescribed
deformation gradient and the existing accepted-state callback. At the expected
start SHA `2cd96b6695be1e90a8cc2dff81f6534774ab04d2`, its focused matrix reports
`43 passed` and records raw JSON/NPZ evidence in
`qualification/0_2_9/wp04_b_mechanics_identities.json` and
`qualification/0_2_9/wp04_b_raw.npz`.

Both TET4 and HEX8 pass the bounded objectivity, affine patch,
internal-force/energy-gradient, consistent-tangent/symmetry and accepted-path
work-refinement checks. G04-06, G04-07, G04-09, G04-10, G04-11 and G04-12 remain
pending for later structural qualification phases. Current maturity remains
`RESEARCH_ONLY`, historical WP13-11 evidence is unchanged, and no production
numerical source was modified. The next permitted action is Owner review before
WP04-C.

## WP04-C TET4 structural qualification — HOLD

WP04-C froze and executed a TET4-only structural cantilever campaign at
`48bfa83bc517e031cdab4876970a4f511f744e35`. It uses a Total-Lagrangian StVK
TET4 `4.0 x 0.5 x 0.5` cantilever with a mesh-independent distributed nodal
dead load, direct force/reaction and deformed-coordinate moment balance,
accepted-state load paths, and a stress sample away from clamp/load
singularities. Small-load linear convergence, force/moment equilibrium,
load-step stability, deterministic replay, deformation envelope, and explicit
failure behavior pass.

The frozen G04-10 mesh gate fails: M3 versus M2 changes are 16.40618103457515%
in loaded-face transverse displacement, 16.379509145773455% in strain energy,
and 24.310580151133324% in representative stress, versus frozen limits of 2%,
2%, and 10%. The convergence trend is monotone but insufficient. WP04 is
therefore **HOLD at 0/12**, the roadmap remains **29/100**, both element
families remain `RESEARCH_ONLY`, and no production numerical source was
changed. See [the WP04-C controlled record](wp04-c-tet4-structural-qualification.md).

Owner direction is required before changing the frozen campaign, re-scoping
WP04, or resuming qualification. WP04-D and subsequent work must not start
from this HOLD result.

## WP04-C1 TET4 mesh diagnosis

WP04-C1 preserves the WP04-C HOLD evidence in commit
`a5c3031f6b28b00476e328daff4845a741a5c161`, reproduces M1/M2/M3 exactly,
and extends the same benchmark with M4 nonlinear plus M4/M5 linear diagnostics.
The linear and nonlinear tip/energy refinement changes match closely; load
resultant/centroid, volume, orientation, and alternate body-diagonal checks
pass. The primary diagnosis is `SLOW_TET4_DISCRETIZATION_CONVERGENCE` with
medium confidence, with a pre-asymptotic original range. The stress sample has
bounded discrete-volume aliasing, but it cannot explain the independently
failing displacement and energy metrics. G04-10 remains
`FAIL_UNDER_REMEDIATION`, both families remain `RESEARCH_ONLY`, and the
roadmap remains 29/100. See [the WP04-C1 diagnosis](wp04-c1-tet4-mesh-diagnosis.md).

The recommended next action is Owner review of a separately frozen C2
finer-mesh requalification campaign; WP04-D remains unauthorized.

## WP04-C2 finer-mesh requalification

WP04-C2 froze the same benchmark at `715bdd655601508170d60c4715a53d658890bdb2`
with required meshes 32x16x16, 48x24x24 and 64x32x32. The unchanged direct
sparse route completed the first two linear levels but remained active on the
64-level preflight after at least 5,976 CPU seconds and approximately 5.42 GB
private memory; the run was interrupted. No nonlinear C2 result was started.
Therefore G04-10 is `UNRESOLVED_RESOURCE_LIMIT`, not PASS, WP04 remains 0/12,
and Owner direction is required. See [the WP04-C2 record](wp04-c2-tet4-requalification.md).

## Linear-solver remediation R1/R2

The owner-aborted C2-M3 process is preserved as
`ABORTED_BY_OWNER_FOR_LINEAR_SOLVER_REMEDIATION`; it is not classified as a
numeric, memory or timeout failure. R1 records the original strict Krylov
residual campaign as `FAIL_PRESERVED`. R2 adds a single nonlinear sparse-solver
adapter with direct/CG/MINRES/GMRES dispatch, Jacobi and GMRES-only ILU
preconditioning, scale-aware backward-error diagnostics, explicit fallback,
and opt-in JSONL telemetry. The frozen Stage-B C2-M1 matrix is symmetric
(`symmetry_defect = 0`): CG+Jacobi satisfies the new contract, while MINRES
and GMRES+ILU outcomes remain recorded rather than promoted. The selected
CG+Jacobi candidate then fails nonlinear Stage C at load step 4 with
`eta_inf = 1.0895221524409612e-05` versus the frozen `1e-10` limit; there is
therefore no validated iterative nonlinear backend and no M2 run. G04-10 is
`UNRESOLVED_LINEAR_SOLVER_REMEDIATION`, WP04 remains 0/12 and 29/100, and
current maturity remains `RESEARCH_ONLY`. See [the R2 evidence](linear-solver-remediation-r2.md).

## Linear-solver remediation R2B

R2B independently reproduces the CG failure at M1 load step 4, Newton
iteration 12 and captures the failing 27,744 x 27,744 reduced system outside
Git. Same-matrix forensics show a finite but inaccurate CG correction
(`solution delta = 0.1116795084`, `eta_inf = 1.0895221524e-05`), while
MINRES+Jacobi satisfies the frozen contract at `rtol=1e-11` and `1e-12`.
The lower spectral estimate did not converge, so SPD remains `NOT_PROVEN`.
The bounded full M1 MINRES check completes all 12 increments and 145 Newton
iterations with zero fallbacks; physical observables, accepted load factors
and line-search trajectory match the direct reference within the frozen
`1e-8` physical tolerance. WP04 remains HOLD and G04-10 remains unresolved;
no M2/M3 run or PETSc/PyAMG dependency was added. See the [R2B controlled
record](linear-solver-remediation-r2b.md) and
`qualification/0_2_9/wp04_linear_solver_r2b.json`.

## Linear-solver remediation master and C2R3 overnight campaign

The owner-authorized C2R3 campaign at
`20186a940ba39b03bf68ee52b8b6137c698c2a16` ran the frozen MINRES+Jacobi route
sequentially: M2 (`48 x 24 x 24`) in one child, followed by M3
(`64 x 32 x 32`) in a fresh child. M2 accepted two increments and terminated
with numerical `CONVERGENCE_STAGNATION` at step 3; M3 accepted three and
terminated with the same numerical classification at step 4. Both returned
control normally, so neither is classified as resource failure; M3 was not
skipped. No final M2/M3 pair exists for applying the G04-10 mesh thresholds,
and no failing linear-solver contract event required a new forensic matrix
capture. M4 was not run and no PETSc/AMG work was performed.

The detailed chronological record is [the linear-solver remediation master]
(linear-solver-remediation-master.md), with machine-readable evidence in
`qualification/0_2_9/linear_solver_remediation_master.json` and flushed raw
case telemetry/results in `qualification/0_2_9/c2r3/`. WP04 remains HOLD at
0/12, G04-10 remains unresolved, and Owner review is required before any
further M2/C2 resume or solver-policy change.

## WP04-C2R4 near-tolerance and protocol audit

C2R4 reproduced C2R3 M2's step-3 stagnation exactly under the frozen
line-search-off MINRES route. A single captured plateau system confirms that
direct SuperLU and tighter MINRES both yield a machine-scale correction and
remain above the frozen nonlinear tolerance; the result is a bounded
`NONLINEAR_RESIDUAL_NUMERICAL_FLOOR` diagnosis, not a linear-solver failure.
It also finds `PROTOCOL_DRIFT`: original C2 and R2B use the existing enabled
line search, whereas C2R3 explicitly disabled it. The M2-only canonical
line-search experiment accepts step 3, then ends at step 4 with
`LINE_SEARCH_FAILURE` near tolerance. G04-10 remains unresolved and no
qualification outcome changes. See [the C2R4 audit](wp04-c2r4-near-tolerance-audit.md).

## WP04-C2R5 residual precision audit

C2R5 reran only M2 with the canonical existing/enabled line search and the
frozen MINRES/Jacobi route. It reproduced three accepted steps followed by
step-4 `LINE_SEARCH_FAILURE` at Newton iteration 26 and residual
`1.0411047989090212e-10`. The exact failing state is captured outside Git.
Direct and tighter MINRES corrections are machine-scale; five repeated normal
reassemblies are bitwise identical; and pairwise, compensated and platform
`longdouble` accumulation remain at the same residual order. Force/internal
force cancellation is large while accepted/trial force and moment balance are
near machine scale. The bounded classification is
`NONLINEAR_RESIDUAL_NUMERICAL_FLOOR` with mechanism
`FORCE_CANCELLATION_AND_FLOAT64_PRECISION_LIMIT`. No threshold, convergence
policy, mechanics formulation or maturity status changed. A future
`R6_FLOOR_AWARE_TERMINATION_POLICY` is recommended for Owner review; it was
not implemented or frozen. M3/M4 and qualification reruns remain prohibited.
See [the C2R5 audit](wp04-c2r5-residual-precision-audit.md) and
`qualification/0_2_9/c2r5/residual_precision_audit.json`.

## WP04-C2R6 recovered M2/M3 campaign

The C2R6 M2 and M3 outputs were recovered from disk without rerunning either
solver process. Both cases completed under the frozen MINRES+Jacobi route with
`rtol=1e-11`, `atol=1e-14`, `maxiter=10000`, direct fallback disabled,
existing/enabled line search, Newton tolerance `1e-10`, 12 increments, and
floor-aware termination enabled. M2 (`48x24x24`) and M3 (`64x32x32`) each
contain 12 accepted records and complete matching JSONL telemetry; both ended
normally with no failure capture and zero fallback.

Each case has three primary and nine floor-aware convergences. All recorded
floor events satisfy the frozen conjunction, with maximum linear backward
errors `4.777962584217645e-12` (M2) and `8.106166618904346e-12` (M3). The
accepted load-factor paths are identical and both cases remain within the
frozen deformation envelope. Result/per-step Newton totals are 300 and 275;
the `SOLVE_COMPLETED` telemetry aggregate is lower by 12 in each case because
it excludes the floor-converged events. This existing bookkeeping discrepancy
is documented and does not indicate incomplete output.

Using the original frozen fine-versus-medium formula, the recovered deltas are
1.6927005864% for tip displacement, approximately zero for reaction,
1.6890467525% for energy, and 2.1646071845% for representative stress. All
four thresholds pass. The derived status is
`G04-10 = PASS_CANDIDATE_PENDING_OWNER_REVIEW`; WP04 remains HOLD at 0/12 and
the validated total remains 29/100. The raw runner record’s top-level
`UNRESOLVED` placeholder is preserved. See [the recovered C2R6 audit](wp04-c2r6-floor-aware-termination.md)
and `qualification/0_2_9/c2r6/frozen_threshold_audit.json`.

## WP04-D HEX8 structural qualification

WP04-D froze and executed the same bounded Total-Lagrangian StVK cantilever
contract for HEX8 at H1 `16x8x8`, H2 `24x12x12`, and H3 `32x16x16`. All three
required cases completed under the exact Owner-approved C2R6 route: 12 fixed
increments, canonical existing line search, MINRES+Jacobi with `rtol=1e-11`,
`atol=1e-14`, `maxiter=10000`, direct fallback disabled, and floor-aware
termination enabled. The consistent boundary-face load preserves resultant
`[0,-50,0]` and reference moment `[12.5,0,-200]`; no equal-share load was
used.

The frozen H2→H3 deltas are displacement `0.01999034019793022`, reaction
`9.224898992711293e-14`, energy `0.019943897062970836`, and representative
stress `0.046483239095767515`, all within the `2%/2%/2%/10%` limits. Maximum
force and moment equilibrium errors are `6.479137079435662e-14` and
`4.033649056229668e-15`; the deformation envelope passes with minimum
`det(F)=0.9924435183210853`, principal stretches
`[0.9907111439153957,1.0092228247131967]`, and maximum
`||E||_F=0.0095824348944902`. H1 replay has identical accepted-state digests,
load factors, classifications and recorded observables. H4 was not run
because H2→H3 passed, and G04-12 is limited to prepared machine-readable H3
inputs with no cross-family decision.

The H1 small-load support sequence was executed and its convergence trend is
retained. At multiplier `0.001`, displacement error is
`2.5607163831358572e-05`, while reaction error is
`2.7738177407149553e-04`, above the supporting `1e-4` limit. This explicit
support limitation is not used to alter the frozen G04-11 mesh decision and
requires review in the combined WP04 phase. See the [WP04-D record](wp04-d-hex8-structural-qualification.md),
`qualification/0_2_9/wp04d/hex8_campaign_result.json`, and
`qualification/0_2_9/wp04d/g04_11_audit.json`.

## WP04-E G04-12 cross-family closure

The evidence-only WP04-E audit compares the approved TET4 C2R6 M3 record with
the approved HEX8 H3 record. The physical geometry, homogeneous isotropic
StVK material, fixed face, physical load resultant and reference moment,
displacement/reaction/energy definitions, and the reference-volume weighted
stress region match. The family-specific discrete boundary-load
representations are disclosed; the governing resultant and first moment are
the frozen cross-family checks.

Using the frozen `abs(a-b)/max(abs(a),abs(b),1e-12)` metric, the displacement,
reaction, energy and representative-stress deltas are
`0.004566585385421973`, `7.105427357601005e-16`,
`0.004553762679948579` and `0.05163720669059609`. All four pass the frozen
`0.03/0.03/0.03/0.12` limits. The carried HEX8 H1 small-load reaction
support limitation remains explicit for WP04-F. Therefore the derived result
is `G04-12=PASS_PENDING_OWNER_REVIEW`; WP04 remains HOLD at 0/12 and 29/100.
See [the WP04-E record](wp04-e-g04-12-cross-family-closure.md) and
`qualification/0_2_9/wp04e/g04_12_cross_family_audit.json`.

## WP04-F independent final closure

The evidence-only WP04-F audit at
`70e1bf953c8e6f37b8070e78ca97e58b21499291` independently reconciles the
WP04-A/B/C/C1/C2/C2R6/D/E chain. The original WP04-C G04-10 failure remains
preserved at its original Git blob and is explicitly distinguished from the
authorized C2R6 requalification and final bounded pass. All twelve frozen
gates are `PASS` or `PASS_WITH_LIMITATION`: G04-06 carries the predeclared
HEX8 small-load reaction support limitation, and G04-09 carries the nonblocking
TET4 `SOLVE_COMPLETED` aggregate Newton undercount. No in-scope blocking
limitation was found.

The final decision is `GO_WITH_LIMITATIONS`: WP04 is **CLOSED at 12/12** and
the validated total is **41/100**. No structural solve, H4, PETSc or full
repository suite was run during the audit. The public maturity registry remains
unchanged pending Owner approval and sequential child-branch integration. See
[the WP04-F audit](wp04-f-final-closure-audit.md) and
`qualification/0_2_9/wp04f/wp04_final_closure_audit.json`.
