---
doc_id: DOC-029-WP06-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
review_date: ""
---

# QF Solver 0.2.9 — WP06 Arc-Length and Postbuckling Readiness

## Audit scope and disposition

This document is a Phase 0, read-only architecture and readiness audit for
WP06. It records what is present at source revision
03166e98a9a0b8cc7978c7ad2a370e441aefdc1e and what would be needed for a
bounded qualification. It does not record a new numerical result, does not
award WP06 points, and does not promote any public capability claim.

The preparation branch is 0.2.9-wp06-prep. The source baseline is the
0.2.9-unified-nonlinear branch at the revision above. No production mechanics,
formulation, convergence policy, or maturity state is changed by this audit.
No structural postbuckling solve, external solver run, MPI/PETSc run, or full
test suite is authorized in Phase 0.

The overall conclusion is:

- arc-length continuation is implemented on the nonlinear_static route with a
  dedicated predictor/corrector and adaptive-radius path;
- accepted-state transaction, rollback, and continuation checkpointing are
  materially reusable;
- the arc-length loop remains a specialized path rather than an invocation of
  the common Newton engine;
- limit-point and small research snap-through demonstrations exist, but they
  are not a general structural or postbuckling qualification;
- bifurcation detection, branch switching, and snap-back qualification are
  not present;
- the next safe action is Owner review and contract freeze, followed only
  after governing nonlinear-policy integration by the smallest predeclared
  qualification ladder.

## Current implementation inventory

| Component | Source location | Observed role | Status |
|---|---|---|---|
| Public nonlinear route | src/solveur/core/nonlinear/solver.py, NonlinearStaticSolver.solve | Dispatches method=arc_length and owns the surrounding checkpoint session | IMPLEMENTED |
| Arc-length driver | src/solveur/core/nonlinear/arc_length.py, NonlinearArcLengthMixin._solve_arc_length | Continuation loop, accepted history, checkpoint save, terminal classification | IMPLEMENTED_BOUNDED |
| Arc-length step | src/solveur/core/nonlinear/arc_length.py, _solve_arc_length_step | Spherical predictor/corrector, residual and constraint convergence, branch sign | SPECIALIZED_IMPLEMENTATION |
| Radius policy | src/solveur/core/nonlinear/controls.py, ArcLengthControls; src/solveur/core/nonlinear/driver.py, UnifiedArcLengthRadiusPolicy | Fixed/adaptive radius, target clipping, shrink/grow and minimum-radius handling | IMPLEMENTED_BOUNDED |
| Augmented correction kernel | src/solveur/core/nonlinear/iteration.py, solve_arc_length_correction | Sparse augmented Newton correction with one additional constraint row | IMPLEMENTED_BOUNDED |
| Common assembly seam | src/solveur/core/nonlinear/driver.py, ContributionResponse, compose_contribution_responses, canonical_residual; common assembly called by solver.py | Combines internal, material, geometric and applicable contact contributions | REUSABLE |
| Common Newton engine | src/solveur/core/nonlinear/driver.py, UnifiedNewtonEngine | Authoritative fixed-load-control Newton lifecycle | NOT_USED_BY_ARC_PATH |
| Continuation transaction | src/solveur/core/nonlinear/driver.py, UnifiedContinuationController | Accepted/trial ownership, commit, rollback and accepted-digest verification | REUSABLE_BOUNDED |
| Nonlinear state | src/solveur/core/nonlinear/state.py, NonlinearState and NonlinearStateTransaction | Displacement, load factor, material/contact slots, continuation payload and digests | REUSABLE_BOUNDED |
| Checkpoint | src/solveur/core/nonlinear/checkpoint.py, NonlinearCheckpointV2 and NonlinearCheckpointSession | Accepted-only state and continuation persistence; save occurs after physical acceptance | REUSABLE_BOUNDED |
| Public geometric route | src/solveur/core/analyses/geometric_nonlinear.py | Separate finite-kinematic full-Newton route | ARC_LENGTH_NOT_EXPOSED_AS_THIS_ROUTE |
| Verification research paths | src/solveur/verification/robustness_arc_length.py, robustness_arc_length_extended.py, total_lagrangian_structural.py, tet4_total_lagrangian_postbuckling.py | Reduced, minimal-FEM, restart/rollback and imperfection-seeded research evidence | RESEARCH_ONLY |
| Legacy compatibility name | src/solveur/core/nonlinear_arc_length.py | Compatibility alias/wrapper around current implementation | COMPATIBILITY_ONLY |

The route boundary is important: the public geometric_nonlinear_static
settings currently expose Newton-Raphson, whereas the public
nonlinear_static solver can select arc_length, including the supported
finite-kinematic configurations validated by its own scope checks. This does
not make every geometric route arc-length-qualified.

## Governing equations and algorithm trace

### Residual

The continuation equilibrium residual is:

    R(u, lambda) = lambda * F_ext - F_internal(u)

where F_internal is the assembled internal contribution returned by the
common assembly seam. The repository's unified nonlinear contract describes
the corresponding composition as external load factor times external load
minus internal and applicable contact contribution. No sign convention is
changed or inferred beyond those source contracts.

In each correction iteration, the implementation evaluates the assembled
internal vector and tangent, computes the residual on free degrees of
freedom, and tracks a residual reference. The reported convergence quantity
also includes the normalized spherical-constraint residual.

### Constraint

For the accepted step relative to the previous accepted state, the
implemented spherical constraint is:

    g(Delta-u, Delta-lambda) =
        Delta-u^T Delta-u
        + (load-scale * Delta-lambda)^2
        - radius^2

The source names the displacement increment delta_u_step, the load-factor
increment delta_lambda, and the scale load_scale. The implementation reports
the constraint residual in the step diagnostics.

### Predictor

The predictor solves the free structural tangent system against the external
load direction:

    K_ff * predictor = F_ext,ff

The predictor is normalized together with the load scale and the current
radius. Its sign is selected from the previous displacement/load-factor
direction when one exists. The initial radius is derived from the predictor
norm and the declared load-step count unless an explicit radius is supplied.

### Corrector

The correction solves a sparse augmented Newton system. In the source's
notation the free block is:

    [ K_ff                    -F_ext,ff                         ]
    [ 2 * Delta-u^T             2 * load-scale^2 * Delta-lambda ]

with right-hand side:

    [ R_ff ]
    [ -g   ]

The implementation constructs this matrix as a sparse CSC matrix and calls
SciPy sparse direct spsolve. Matrix-rank warnings, invalid shapes, solver
errors, and non-finite correction vectors become the route's
ARC_LENGTH_FAILURE numerical failure reason. The correction kernel is
deliberately not relabeled as Crisfield, Riks, or another named algorithm
without a separate equivalence proof.

### Root and branch selection

There is no quadratic-root enumeration API. The current root/branch decision
is an orientation sign: it uses the alignment of the previous displacement
direction with the predictor, with the scaled load-factor direction as a
tie-breaker. This preserves a continuation branch and permits a load-factor
turn when the controls allow it. It is not a bifurcation detector and does
not provide automatic branch switching.

## Unified-core compatibility

| Concern | Current observation | Readiness |
|---|---|---|
| Residual and tangent composition | Arc steps call the common internal/tangent assembly seam; the correction is then formed by the specialized arc loop | REUSABLE, but not a complete common execution graph |
| Accepted/trial ownership | UnifiedContinuationController wraps a NonlinearStateTransaction and verifies the accepted digest during rollback | COMPATIBLE_BOUNDED |
| Common Newton lifecycle | UnifiedNewtonEngine is the fixed-load-control engine and is not called by _solve_arc_length_step | GAP |
| Line search | The arc correction path does not use the ordinary load-control line-search lifecycle | GAP / ROUTE-SPECIFIC |
| Radius decision | UnifiedArcLengthRadiusPolicy is the single bounded radius-policy authority | REUSABLE_BOUNDED |
| Failure taxonomy | Typed reasons exist, but several arc predictor/corrector/constraint failures collapse to ARC_LENGTH_FAILURE | PARTIAL |
| Telemetry | NonlinearStep and existing nonlinear telemetry carry residual, iteration, load and timing information; the generic WP15 event core is not yet the arc producer in this baseline | PARTIAL |
| Contact/material state | Material state is carried and committed. Current frictionless stateless contact can be represented as topology metadata; no general stateful-contact restart claim is made | PARTIAL |

The key architectural gap is not lack of an accepted-state transaction. It is
that arc-length owns a specialized nonlinear loop with its own predictor,
corrector, convergence combination and branch logic. A future convergence
qualification must therefore bind the exact governing policy and source
revision rather than infer compatibility from the existence of common
assembly utilities.

## State, rollback and restart semantics

The accepted NonlinearState contains displacement, load factor, material state,
contact-state slot, continuation state, and accepted-increment metadata. The
arc path records the following continuation values when applicable:

- accepted_step
- load_factor
- radius
- maximum_radius
- load_scale
- previous_du
- previous_dlambda
- target load factor and stop mode
- load-factor-turning permission
- optional control degree of freedom

The transaction sequence is bounded and auditable:

1. begin a detached trial from the accepted state;
2. evaluate one continuation step;
3. on acceptance, update trial continuation/material data and commit;
4. record the accepted digest and update caller-visible displacement/material
   state;
5. save a checkpoint only after physical acceptance;
6. on failure, rollback before the radius policy decides whether a retry is
   possible.

Rollback tests already cover preservation of displacement, material state,
load factor, previous direction and radius behavior. Checkpoint tests cover
accepted-only persistence, continuation values, restart determinism, adaptive
radius/rejection behavior, v1-to-v2 boundaries, and checkpoint failure
semantics.

The remaining boundary is explicit:

- a stateless frictionless contact response is recomputed from the restored
  accepted displacement and topology metadata;
- stateful friction history is not a qualified arc-length restart payload;
- there is no qualified branch-switching or bifurcation state;
- append/restart compatibility does not imply cross-process or MPI sequence
  ordering;
- a failed physical arc step is ARC_LENGTH_FAILURE, while a post-acceptance
  checkpoint write failure is CHECKPOINT_FAILURE and must not turn a
  physically accepted step into a radius rollback.

### Rollback gaps to close later

The future WP06 evidence must still demonstrate, on a declared structural
benchmark, that a rejected continuation attempt leaves the complete accepted
state and continuation path unchanged, and that restart at a declared point
reproduces the suffix of the path. It must also state whether any benchmark
uses material or contact state. This is a qualification obligation, not an
assumption derived from the existence of the transaction class.

## Augmented system and backend boundary

For n_free free displacement unknowns, the correction system has dimension
n_free + 1. Its matrix is generally non-symmetric because the top-right
load-direction block and bottom-left displacement-gradient block are not
transposes with the same scaling. It is therefore not expected to be SPD;
indefinite/poorly scaled behavior is possible near a limit point.

The current backend split is:

- predictor: the configured nonlinear linear-solver adapter may receive the
  selected linear_method;
- augmented correction: SciPy sparse direct spsolve is called directly by
  solve_arc_length_correction;
- no qualification exists for CG, MINRES, GMRES, PETSc KSP, iterative
  preconditioning, augmented-system conditioning, or large distributed
  continuation.

Required future backend evidence is therefore limited first to the direct
serial path. Any iterative or PETSc continuation path needs its own
compatibility, symmetry/conditioning, convergence, and replay evidence.

## Capability assessment

| Capability | Current assessment | Maximum honest Phase-0 claim |
|---|---|---|
| Limit-point tracking | PARTIAL_INTERNAL_RESEARCH | Turning behavior is exercised by reduced and minimal internal research paths; no general structural qualification |
| Snap-through | PARTIAL_RESEARCH_ONLY | A scalar shallow-arch identity and a minimal common-driver FEM path exist; no public general snap-through claim |
| Snap-back | UNPROVEN | No bounded evidence or branch policy sufficient for a claim |
| Bifurcation detection | MISSING | No eigenmode/bifurcation detector is connected to continuation closure |
| Branch switching | MISSING | No qualified branch-selection or branch-switching API |
| Imperfection-seeded postbuckling | PARTIAL_RESEARCH_ONLY | TET4 verification campaign perturbs coordinates and traces a research path; no external validation, branch guarantee, or general element claim |
| Adaptive radius | IMPLEMENTED_BOUNDED | Deterministic fixed/adaptive radius decisions, target clipping, rejection shrink and accepted growth are implemented and unit-tested |
| Failure classification | PARTIAL | Typed nonlinear reasons exist; arc-specific predictor/corrector/constraint detail remains aggregated in ARC_LENGTH_FAILURE |
| Telemetry readiness | PARTIAL | Step diagnostics and legacy telemetry are usable; a generic arc-specific WP15 event contract is not yet bound to this baseline |

The research paths include a reduced scalar lambda = u - u^3 limit-point
example, a separate sparse TET4 trace, a minimal common-driver FEM
snap-through path, restart/rollback demonstrations, and an imperfection-seeded
TET4 postbuckling study. They return research classifications and explicitly
exclude claims of external, industrial, uniqueness, stability, contact, or
general postbuckling qualification.

## Existing tests and qualification evidence

### Unit and regression inventory

The following existing focused suites are relevant and should be reused
without interpreting their existence as a new WP06 qualification:

- tests/unit/test_wp01_d_continuation.py: accepted/rejected arc-step
  ownership, rollback, turning point baseline, adaptive radius, replay
  digest, checkpoint ordering and unified-controller use.
- tests/unit/test_wp02_d_arc_length_restart.py: 28 focused restart and
  checkpoint tests, including continuation fields, rejected-trial
  persistence, adaptive radius/rejection restart, v1 migration boundaries,
  failure semantics and deterministic suffix behavior.
- tests/unit/test_wp02_d1_arc_length_material_state.py: material-state
  restart, rejected-increment isolation, accepted-state publication and
  elastic-regression boundaries.
- tests/unit/test_wp03_d_arc_radius_policy.py: the unified radius policy,
  fixed/adaptive growth and shrink, target clipping, rollback ordering,
  rejection/checkpoint behavior, deterministic mapping and policy authority.
- tests/unit/test_tet4_tl_postbuckling.py: small unit-level sparse
  arc-length/postbuckling checks and controlled-summary guards; it does not
  replace a structural campaign.
- tests/verification/test_tet4_tl_postbuckling_vnv.py: a benchmark-marked
  campaign test; it is intentionally not executed in this preparation phase.

Historical evidence is kept at its historical level. In particular,
qualification/0_2_6/g07_b1_arc_length_evidence.json and
g07_b3_gap_resolution_evidence.json are partial/blocked 0.2.6 G07 records,
not 0.2.9 WP06 closure evidence. The 0.2.9 WP02/WP03 continuation artifacts
are implementation and focused-restart evidence, not automatic structural
qualification.

### Current qualification level

The current level is EXPERIMENTAL_BOUNDED / internal research readiness. No
WP06 formal points are awarded. A future structural claim requires a
predeclared benchmark, governing-policy binding, replay, rollback, equilibrium
and reference evidence.

## Proposed qualification benchmark ladder

The ladder is intentionally incremental and avoids a route-by-element
Cartesian product.

| Stage | Purpose | Minimum evidence | Cost class | Gate |
|---|---|---|---|---|
| A — algebraic turning identity | Verify constraint, predictor orientation, load-factor turn, finite residual and deterministic replay on lambda = u - u^3 | Raw state/history, constraint residual, turning indicator, replay | TINY | WP06-C support only |
| B — reduced shallow arch / von Mises truss | Connect the continuation semantics to a mechanically interpretable limit point and an independently reducible reference | Displacement/load path, limit point, equilibrium, radius/rejection history, independent reduced reference | LIGHT to MODERATE | WP06-D candidate |
| C — common-driver structural limit point | Use a declared production FE model, initially low-order TET4, with fixed direct sparse correction and predeclared mesh/path/replay criteria | Multi-level path, equilibrium, finite state/detF where relevant, turning point, reference and restart suffix | MODERATE to HEAVY | WP06-D formal |
| D — imperfection-seeded postbuckling | Evaluate a deliberately declared imperfection and postcritical path after branch policy exists | Imperfection provenance, path continuity, branch/turning behavior, mesh/reference evidence, restart and failure controls | HEAVY | WP06-E candidate |
| E — high-order or other route extension | Reuse only after WP05/high-order and route governance provide independent evidence | Separate element/formulation contract and V&V; no transitive promotion from TET4 | HEAVY | Future release / WP05-linked |

Every future structural stage must predeclare observables including load
factor, selected displacement, residual, arc constraint, accepted/rejected
steps, radius, equilibrium, energy when meaningful, determinant/kinematic
guards where relevant, and replay/reference comparisons. A turning point in a
reduced model is not a qualification of the production FE route.

## Proposed WP06 decomposition — 8 points

This is an Owner candidate split only; all formal points remain zero.

| Sub-WP | Weight | Exit evidence | Dependencies |
|---|---:|---|---|
| WP06-A — formulation and route contract | 1 | Exact residual/constraint/predictor/corrector/root-selection contract, route boundary and public-claim exclusions | Existing source audit; Owner review |
| WP06-B — continuation state, rollback and checkpoint | 1 | Accepted/trial digest, rejected-step isolation, restart metadata and suffix replay on the declared path | WP01–03 foundations; governing integration |
| WP06-C — identity, radius and backend V&V | 2 | Constraint/predictor/corrector checks, radius-policy behavior, direct augmented-backend diagnostics and finite failure taxonomy | WP03 radius authority; policy binding |
| WP06-D — structural limit-point qualification | 2 | Predeclared FE benchmark, mesh/path observables, equilibrium, replay and independent reference | WP04 governing nonlinear policy; WP06-A/B/C |
| WP06-E — bounded imperfection/postbuckling qualification | 1 | Only if a branch/imperfection contract is available; explicit exclusions if not | WP06-D; branch policy; adequate resources |
| WP06-F — reference, evidence aggregation and Owner closure | 1 | Machine-readable gate matrix, provenance, limitations and final bounded claim | All applicable sub-WPs and integration train |

The split deliberately puts more weight on the identities/backend and
structural qualification than on an unproven industrial postbuckling claim.
No partial point is implied by a research-only result.

## Dependencies and execution gates

### Work allowed before WP04 closes

- source and test audit;
- this documentation and machine-readable contract;
- small schema/provenance helpers;
- unit tests of algebraic constraint/radius/state behavior;
- reuse of existing focused continuation tests;
- a tiny algebraic stage-A replay only if it is operationally harmless and
  separately classified as research evidence.

### Work blocked until WP04/WP05 and integration

- production structural limit-point or postbuckling campaigns;
- heavy FE mesh/path studies;
- external Code_Aster/CalculiX or other reference runs;
- high-order TET10/HEX20 continuation claims;
- stateful friction/contact continuation claims;
- any public maturity promotion or release claim.

WP04 must supply the governing 0.2.9 nonlinear execution policy, including the
accepted convergence/floor behavior and its source identity. WP05 is a
dependency for any high-order claim, not a reason to promote high-order
continuation transitively. The eventual integration train must bind the exact
policy and revalidate the affected targeted tests before structural execution.

## Failure and telemetry readiness

The current nonlinear failure enumeration includes
MAX_ITERATIONS, MIN_INCREMENT_REACHED, LINEAR_SOLVER_FAILURE,
SINGULAR_TANGENT, NAN_DETECTED, INF_DETECTED, MATERIAL_UPDATE_FAILURE,
INVALID_ELEMENT, STATE_CORRUPTION, LINE_SEARCH_FAILURE,
CONVERGENCE_STAGNATION, CONTACT_UPDATE_FAILURE,
CONTACT_PENETRATION_EXCESSIVE, ARC_LENGTH_FAILURE, CHECKPOINT_FAILURE, and
BUCKLING_FAILURE.

For WP06, failure evidence must preserve the original classification and
distinguish at least:

- predictor/initial-radius failure;
- augmented correction singularity or non-finite correction;
- constraint non-convergence;
- physical residual non-convergence;
- minimum-radius termination;
- rollback failure;
- checkpoint failure after acceptance.

The current umbrella ARC_LENGTH_FAILURE is acceptable as an implementation
boundary for the readiness audit, but is not sufficient by itself for a
high-confidence industrial qualification report.

Existing step diagnostics contain residual, iteration, load increment,
timings, contact diagnostics and arc-specific metadata such as radius,
control displacement, predictor sign, branch direction, direction alignment
and constraint residual. This is useful evidence input. A future WP15 generic
event sink may consume it, but WP06 does not claim that generic monitoring is
already integrated in every route.

## Public claim boundary

The maximum honest claim from this Phase-0 audit is:

> QF Solver 0.2.9 contains an experimental, bounded arc-length continuation
> implementation on the nonlinear_static route, with deterministic radius
> policy and accepted-state rollback/checkpoint foundations, plus internal
> research demonstrations of turning behavior on reduced and minimal FEM
> paths.

The following claims are explicitly out of scope:

- general-purpose or industrial postbuckling;
- universal limit-point, snap-through or snap-back robustness;
- bifurcation detection or automatic branch switching;
- external validation;
- stateful frictional-contact restart;
- MPI/PETSc/distributed continuation qualification;
- high-order element continuation qualification by transitivity;
- a separate geometric_nonlinear_static arc-length capability;
- any maturity or release promotion from preparation artifacts.

## Phase-0 validation policy and status

No structural or external solve is recorded here. The allowed validation is
limited to focused existing continuation/restart/radius unit tests, source
compilation, JSON parsing, targeted static checks, and controlled-document
metadata validation. Full-suite execution is intentionally skipped by policy.
Any inherited static-analysis or documentation-registry drift is reported
separately and is not converted into a WP06 qualification result.

Current governance values:

- WP06 points: 0/8
- validated total: 29/100
- production mechanics changed: NO
- maturity changed: NO
- heavy solve run: NO
- structural postbuckling run: NO
- external solver run: NO
- full test suite run: NO

The next action is Owner readiness review and sub-WP contract freeze. No
qualification campaign should start until that review and the WP04 governing
policy/integration train are complete.
