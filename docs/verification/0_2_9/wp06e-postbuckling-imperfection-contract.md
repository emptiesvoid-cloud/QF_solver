---
doc_id: DOC-029-WP06E-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
review_date: ""
---

# WP06-E — postbuckling, imperfection and bifurcation claim contract

## Status and boundary

This is a Phase-0 preparation artifact. It freezes a prospective, bounded
qualification contract and awards no formal point. WP06-E remains 0/1, WP06
remains 0/8 and the validated total remains 29/100.

The preparation baseline is `791758d9bdaecb1c41e5f38ad70aa3e4bae124f5` on
`0.2.9-wp06-prep`. No structural postbuckling solve, buckling eigenvalue
campaign, reference-solver run, external-solver run, heavy solve or full
suite was executed for this artifact. No production mechanics changed.

The contract is intentionally narrower than the words “postbuckling” or
“bifurcation” might suggest. The maximum future claim is:

> QF Solver 0.2.9 demonstrates bounded imperfection-seeded nonlinear
> continuation on the selected TET4 benchmark.

This is not a claim of general postbuckling, automatic bifurcation detection,
branch switching, uniqueness, stability, industrial robustness, or coverage
of other elements/routes.

## Source-grounded inventory

The following statuses are based on the implementation at the preparation
baseline, not on documentation alone.

| Capability | Status | Source-grounded finding |
|---|---|---|
| Linear buckling eigenvalue extraction | IMPLEMENTED_RESEARCH | `src/solveur/verification/tet4_total_lagrangian_buckling.py:TotalLagrangianBucklingCampaign` calls `smallest_tangent_eigenpair` from `total_lagrangian_structural.py` and brackets the smallest tangent eigenvalue sign change. |
| Geometric tangent / eigenmode construction | IMPLEMENTED_RESEARCH | The buckling campaign assembles a TET4 initial tangent plus a geometric-tangent rate and returns an `eigsh` mode. |
| Mode normalization | PARTIAL | `eigsh` supplies an implicit Euclidean normalization on free DOFs; constrained entries are zero. There is no frozen physical amplitude, sign convention, rigid-body projection contract or nodal interpolation API. |
| Explicit modified-coordinate imperfection | IMPLEMENTED_RESEARCH | `TotalLagrangianPostbucklingCampaign` adds `amplitude * (1 - cos(0.5*pi*x/L))` to `nodes[:, 2]`. |
| Eigenmode-scaled nodal imperfection | DISCONNECTED | A mode is extracted for plotting, but no production path maps it into initial coordinates for continuation. |
| User-defined imperfection field | MISSING | No generic public field route was found in the audited path. |
| Mesh-generation offset | MISSING | No separate mesh-generator imperfection contract was found. |
| Continuation from imperfect geometry | IMPLEMENTED_RESEARCH | `trace_sparse_arc_length` accepts an assembly built from perturbed coordinates; the postbuckling campaign uses this path. |
| Limit-point tracking | PARTIAL | The common arc-length and research paths can record load-factor turns, but this contract does not promote them to a general postbuckling detector. |
| Bifurcation detection | MISSING/NOT_QUALIFIED | The buckling study detects a tangent eigenvalue sign change in its own research campaign; no detector is connected to the continuation closure to identify a branch point. |
| Branch switching | MISSING/NOT_QUALIFIED | No branch-selection or primary-to-secondary branch API is present. |
| Symmetry-breaking path following | NOT_QUALIFIED | An explicit imperfection selects a path, but no symmetry-breaking invariant or branch-identity proof is implemented. |
| Imperfection provenance | PARTIAL | The research campaign records ratio/amplitude and a buckling-summary digest, but a future qualified case must bind case, contract and source digests. |
| Postbuckling restart | PARTIAL_RESEARCH | Arc-length checkpoint/restart and rollback exist in the broader nonlinear stack; imperfection/branch state is not a qualified WP06-E payload. |

Relevant implementation and test locations are:

- `src/solveur/verification/tet4_total_lagrangian_postbuckling.py`,
  `TotalLagrangianPostbucklingCampaign`;
- `src/solveur/verification/tet4_total_lagrangian_buckling.py`,
  `TotalLagrangianBucklingCampaign`;
- `src/solveur/verification/total_lagrangian_structural.py`,
  `trace_sparse_arc_length` and `smallest_tangent_eigenpair`;
- `src/solveur/verification/robustness_arc_length_extended.py`, the small
  common-driver FE snap-through path used by WP06-D;
- `tests/unit/test_tet4_tl_postbuckling.py`, lightweight research-path guards;
- `tests/verification/test_tet4_tl_postbuckling_vnv.py`, an optional benchmark
  test that is not a Phase-0 result.

The buckling mode is currently plotted after arbitrary visual amplification;
that display scale is not a physical imperfection amplitude and is not used
as qualification evidence.

## Claim separations

These terms remain distinct in the evidence schema and in Owner review:

- **LIMIT_POINT_TRACKING**: continuation through `d(lambda)/ds` reversal on
  one equilibrium path;
- **BIFURCATION_DETECTION**: identifying a branch point from tangent or
  eigenstructure;
- **BRANCH_SWITCHING**: deliberate transition from a primary to a secondary
  branch;
- **IMPERFECTION_SEEDED_POSTBUCKLING**: a declared perturbed geometry follows
  one selected continuation path.

Evidence for one term cannot silently close another. The selected future case
is the last term only; limit-point observations may be secondary diagnostics.
Bifurcation detection and branch switching remain `NOT_QUALIFIED`.

## Selected bounded benchmark

The future Phase-1 case is the existing straight-sided TET4 cantilever-like
column with a prescribed geometric imperfection. It is selected because the
repository already has an explicit coordinate perturbation and a sparse
arc-length path, while the case remains small and mechanically interpretable.

| Item | Frozen preparation value |
|---|---|
| Benchmark ID | `WP06E-TET4-IMPERFECT-COLUMN-001` |
| Route | `nonlinear_static`, research `arc_length` method |
| Element/formulation | straight-sided TET4, total-Lagrangian StVK elastic |
| Geometry | `L=4.0`, `H=0.5`, `D=0.5`, global Cartesian coordinates |
| Material | isotropic StVK, `E=1.0e6`, `nu=0.30` |
| Support | all displacement DOFs fixed on the `x=0` face |
| Load | conservative axial dead-load vector on the `x=L` tip-node set, with the existing campaign mapping retained for Phase-1 review |
| Contact/plasticity/dynamics | excluded |
| Search/parallelism | no contact; serial sparse direct path only |
| Primary imperfection | explicit modified reference coordinates, `Z_imperfect = Z0 + alpha*(1-cos(0.5*pi*X/L))` |
| Primary amplitude | `alpha/L = 0.005`, hence `alpha=0.020` in the declared units |
| Amplitude sweep | not part of qualification; existing research ratios are historical context only |
| Branch policy | follow the deterministic path selected by the frozen continuation orientation; no branch switching |

The selected amplitude is frozen before any Phase-1 result. It is not chosen
after observing a response. The perturbation is zero on the clamped `x=0`
face and reaches `alpha` at the free end. Coordinates are modified before
assembly and remain the reference coordinates for the TET4 total-Lagrangian
calculation.

### Mode-based boundary

`MODE_BASED_IMPERFECTION = NOT_QUALIFIED` for this contract. The available
eigenmode has no qualified physical normalization, sign convention, rigid-body
removal, or interpolation-to-coordinate route. The explicit coordinate field
above is therefore the only primary imperfection input. A future mode-based
claim would require a separate contract and evidence for:

- selected eigenmode and source eigenproblem;
- physical normalization and sign;
- rigid-body/null-space removal;
- nodal interpolation and coordinate frame;
- amplitude and mode-dimension validation;
- replay and provenance of the mode data.

## Physics and execution policies

The **physics contract** is frozen here: geometry, material, TET4
total-Lagrangian StVK formulation, fixed support, dead load, explicit
imperfection, primary amplitude, route scope, observables and envelope.

The **execution policy** is not frozen to a new WP06-specific tolerance. The
future run must bind the Owner-approved governing 0.2.9 policy after the
integration train, including Newton convergence, any floor-aware secondary
criterion, linear backend, line search, load-step/retry and arc-length
termination/orientation settings. The current status is
`PENDING_GOVERNING_BRANCH_INTEGRATION`.

The existing research helper has its own sparse arc-length controls. Those
controls explain the available prototype but do not create a public policy
claim for WP06-E.

## Required future observations

Each accepted and rejected continuation step must retain, where applicable:

- step number and accepted/rejected status;
- monitor displacement and full selected displacement vector;
- load factor and accepted load-factor history;
- support reaction/resultant and moment when applicable;
- strain energy when available;
- imperfection amplitude, case-definition digest and reference-coordinate
  digest;
- arc-length radius and constraint residual;
- mechanical residual and Newton iteration count;
- non-finite/envelope guards, including `det(F)`, principal stretches and
  `||E_GL||_F`;
- terminal classification and failure reason.

If a mode input is ever attempted, mode index, source eigenvalue, normalization,
sign and amplitude must be recorded. Missing or non-finite required values are
fail-closed; they are not replaced by zero or an implicit PASS.

## Envelope and prospective thresholds

The following limits are frozen for Owner review before Phase-1 execution:

| Gate | Candidate limit |
|---|---:|
| reference monitor displacement | 5% |
| reference load factor | 5% |
| reference reaction | 5% |
| reference strain energy | 7% |
| replay scalar/vector values | relative `1e-12`, absolute floor `1e-14` |
| force equilibrium, where applicable | `1e-8` relative |
| moment equilibrium, where applicable | `1e-8` relative |

Relative comparisons use a declared physical scale and a floor, not a
result-driven denominator. Missing/non-finite observables fail closed.

The governing TL-StVK envelope inherited from WP04 is mandatory:

- `det(F) >= 0.20`;
- principal stretches within `[0.75, 1.30]`;
- `||E_GL||_F <= 0.30`.

A benchmark or continuation segment requiring a violation is outside this
contract, regardless of whether the solver returns a numerical path.

## Reference plan

No reference result is produced in Phase 0. The preferred independent
reference is an `INDEPENDENT_IMPERFECT_TET4_ENERGY_PATH`: a separately written
reduced or small-FE implementation of the same TET4 StVK energy, explicit
coordinate perturbation, BCs, load mapping and path observables. It must not
call QF production continuation, residual/tangent assembly, or TET4
geometric-nonlinear helpers.

An external solver may supplement this only if exact formulation and load
mapping are demonstrated. Euler or a reduced analytical model is a sanity
reference, not an automatic acceptance oracle for the 3D TET4 path. The
reference must bind its own implementation digest, case-definition digest and
contract revision. A mismatch is `REFERENCE_MISMATCH`, not a relaxed PASS.

The comparison uses the normalized cumulative accepted-path arc measure at
predeclared stations, with piecewise-linear interpolation only between
accepted states. It must not cherry-pick different stations for different
results. No branch-identity or branch-switch equivalence is claimed.

## Replay and failure controls

One lightweight primary-case replay is required in Phase 1. The two runs must
match within relative `1e-12` and absolute `1e-14` for final state and
accepted path values, including load-factor and radius histories, accepted /
rejected-step history, orientation decisions, Newton counts when required by
the governing policy, and terminal classification. A binary state hash is not
required by this contract.

Prospective negative controls are safety evidence only and cannot award the
structural point:

| Case | Expected classification |
|---|---|
| zero or invalid imperfection | `IMPERFECTION_INPUT_FAILURE` or typed invalid-input result |
| non-finite amplitude | `IMPERFECTION_INPUT_FAILURE` |
| wrong mode dimension | `MODE_INPUT_FAILURE` |
| mode normalization failure | `MODE_INPUT_FAILURE` |
| unsupported element/path | `UNSUPPORTED_EXPLICIT` |
| unsupported branch switch | `BRANCH_SWITCHING_UNSUPPORTED` |
| unsupported bifurcation detection | `BIFURCATION_DETECTION_UNSUPPORTED` |
| envelope violation | `ENVELOPE_VIOLATION` |
| non-finite continuation state | `NONFINITE_STATE` |
| reference provenance mismatch | `REFERENCE_MISMATCH` |
| replay mismatch | `REPLAY_MISMATCH` |

No failure may be silently retried with altered physics. A typed failure may
be best-effort reported, but it is not a qualified success.

## Dependencies and gating

| Dependency | Preparation status | Phase-1 consequence |
|---|---|---|
| WP04 governing geometric-nonlinear policy | required | bind exact policy identity before execution |
| WP05 high-order geometric nonlinear | informative only | no transitive TET4 qualification; high-order remains separate |
| WP06-D structural limit-point evidence | contract available, formal evidence pending | execute WP06-E only after D structural evidence and integration |
| existing buckling route | research evidence available | mode extraction is not sufficient for mode-based imperfection |
| WP15 telemetry | useful, not required to freeze the physics contract | record telemetry when integrated, without changing mechanics |

Allowed before WP04 closure/integration: source audit, contract/docs,
case-definition and imperfection construction checks, schema/provenance tests,
and tiny algebraic validation. Structural continuation, eigenvalue campaign,
reference execution and heavy resource use remain blocked until the governing
branch is integrated and Owner authorizes Phase 1. WP06-D formal structural
evidence is also required before this WP06-E run.

## Governance and point boundary

WP06-E candidate exit evidence must include a valid source SHA and clean
status, case and contract digests, exact governing policy identity, finite
accepted path, envelope checks, replay, independent reference comparison and
negative-control records. The closure report must preserve the separate
statuses for limit-point tracking, bifurcation detection, branch switching
and imperfection-seeded continuation.

This preparation does not alter WP06-A/B/C/D points or the maturity registry:

- WP06-E formal points: `0/1`;
- WP06 total: `0/8`;
- validated total: `29/100`;
- no public general postbuckling, bifurcation or branch-switching claim.

