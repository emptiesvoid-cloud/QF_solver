---
doc_id: DOC-029-006
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# 0.2.9 progress tracker

| Work package | Points | Status |
| --- | ---: | --- |
| WP00 | 4 | Closed |
| WP01 | 12 | **Closed** — Owner-approved unified nonlinear core |
| WP02 | 6 | **Closed** — 6/6; independent WP02-E audit `GO_WITH_LIMITATIONS` |
| WP03 | 7 | **Closed** — 7/7; independent WP03-E audit `GO_WITH_LIMITATIONS` |
| WP04 | 12 | **HOLD — TET4 mesh convergence diagnosed** — 0/12; G04-10 remains failed |
| WP05–WP08 | 31 | Not started |
| WP09 | 8 | Blocked by OD-029-01 |
| WP10–WP14 | 20 | Not started |
| **Validated total** | **29 / 100** | **WP00 4/4 + WP01 12/12 + WP02 6/6 + WP03 7/7; WP04 remains unawarded** |

WP01 is closed by the independent Owner decision recorded in
[the WP01 closure record](wp01-owner-closure.md), based on audit SHA
`6876d867cdd845195e8946b05329b0bc82937fdc`. The decision is
`GO_WITH_LIMITATIONS`, with G01/G05/G06/G07/G10 retaining their documented
bounded/research boundaries. Unified checkpoint persistence, frictional
contact migration and adaptive penalty-contact qualification remain future
work; inherited typing debt remains documented. OD-029-01 stays OPEN and
blocks WP09 only. WP02 is closed by the independent audit; Owner review is
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
WP04, or considering any numerical remediation. WP04-D and subsequent work
must not start from this HOLD result.

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
