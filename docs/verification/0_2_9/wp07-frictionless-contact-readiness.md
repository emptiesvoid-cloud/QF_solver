---
doc_id: DOC-029-WP07-A-READINESS-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.9 — WP07-A frictionless-contact readiness audit

This document is a preparation-only audit. It records the implementation
seams, exact bounded algorithms, historical evidence and gaps that must be
reviewed before a WP07 campaign. It awards no points, changes no maturity
record and does not qualify a new contact combination.

Audit source: `2c52bf8196a7d47d14ce1784290580160de26590`
Machine-readable companion: [`wp07_frictionless_contact_readiness.json`](../../../qualification/0_2_9/wp07_frictionless_contact_readiness.json)

## Status and bounded interpretation

The repository contains more than one frictionless-contact enforcement path.
They are reported separately because an active-set constraint solve is not
automatically equivalent to a penalty contribution in the common Newton
assembly.

| Route | Current implementation | Readiness classification | Honest maximum claim |
| --- | --- | --- | --- |
| `linear_static` | Direct sparse active-set solve with Lagrange multiplier rows | IMPLEMENTED_BOUNDED | Small-displacement node-to-triangle contact for the tested, declared direct route |
| `nonlinear_static` | Frictionless penalty contribution in common residual/tangent assembly | IMPLEMENTED_BOUNDED | Experimental/bounded static or quasi-static penalty scope with explicit controls |
| `geometric_nonlinear_static` | Penalty contribution composed with total-Lagrangian assembly and common full Newton driver | PARTIAL / RESEARCH | Bounded research composition only; no general finite-kinematic contact claim |
| `modal`, `linear_buckling`, `transient_dynamic`, `harmonic_response` | Rejected by contact validation or route scope | UNSUPPORTED_EXPLICIT | Not applicable to this bounded WP07 claim |

WP07 remains `PREPARATION_ONLY`, `0/10` points, and `29/100` validated total.

## Exact algorithm inventory

### Geometry, pair type and search

The input entity is `FrictionlessContact` in
`src/solveur/contact/entities.py`. The bounded pair is one slave node against
one ordered triangular master face, or an explicitly supplied triangulated
master surface. A declared slave patch is expanded into independent
node-to-faceted-surface contributions; it is not mortar or
surface-to-surface contact.

`face_geometry` computes a unit normal from the ordered triangle, the signed
normal gap and barycentric projection. The default policy requires an exact
projection inside a compatible face. An outside projection fails closed.
Closest-point clamping is opt-in and belongs only to the bounded updated
finite-sliding branch. Face selection is deterministic: compatible faces are
ordered by absolute gap and then face index.

The default `initial` search freezes the selected face and normal. The
`updated` search recomputes trial geometry and repeats bounded frozen-contact
solves until the face and displacement change stabilize. This is an
implemented, bounded experimental search, not a general contact search.

### `linear_static` path

`LinearStaticSolver` validates the model, assembles the structural stiffness
and invokes `FrictionlessActiveSetSolver` when contacts are present. The
active-set path forms a reduced structural system augmented with one contact
constraint row per active pair and solves it through
`scipy.sparse.linalg.spsolve`. The multiplier is mapped to a non-negative
compressive pressure. Contacts are activated on negative gap and tensile
active contacts are removed. A singular base or saddle system is converted to
an explicit numerical-convergence failure.

This is a route-native active-set/Lagrange enforcement path. It does not use
the ordinary linear backend selection and it does not expose a Newton tangent.

### Nonlinear penalty paths

`assemble_penalty_contact` is called from the common nonlinear assembly and,
for geometric nonlinear statics, through `_PenaltyContactAssembly`. For a
penetrating contact it adds

`f_contact = penalty * min(g, 0) * c`

and the rank-one tangent `penalty * c ⊗ c`. Open contacts contribute zero.
The common nonlinear driver owns residual evaluation, Newton correction,
accepted material/continuation state and rollback. The frictionless penalty
contribution is stateless: contact geometry and force are recomputed from the
current trial displacement and no active face/history is committed as
`NonlinearState.contact_state`.

The separate frictional regularized Coulomb route is implemented in the
contact package but is outside this frictionless WP07 audit and remains
unqualified.

## Route traces and compatibility with the common nonlinear core

| Concern | `linear_static` active-set | Nonlinear penalty | WP07 readiness |
| --- | --- | --- | --- |
| Residual | Constraint/saddle solve in `contact/solver.py` | Common assembly contribution | PARTIAL / READY_TO_REUSE respectively |
| Tangent | Contact constraint rows, no Newton tangent | Consistent penalty rank-one contribution | SEPARATE LEGACY PATH / READY_TO_REUSE |
| State transaction | Local to one solve | Material/continuation transaction; contact itself stateless | PARTIAL |
| Rejected increment | No common mutable transaction | Common `NonlinearStateTransaction` rollback | PARTIAL |
| Updated search | Separate fixed-point loop | Bounded geometry recomputation in contact assembly | PARTIAL ADAPTER |
| Checkpoint/restart | No contact checkpoint path | Topology can say `stateless`; no active-face/contact-history digest | PARTIAL / GAP |
| Line search | Not applicable | Geometric penalty can participate in common driver | READY for declared route only |

The architecture debt is explicit in
`qualification/0_2_9/architecture_decisions.json`:
`DEBT-029-03` records contact active-set/friction state and updated-search
loops outside the common nonlinear transaction/diagnostics boundary;
`DEBT-029-04` records the absence of an explicit contact-state checkpoint
schema, digest and restart contract.

## Validation and failure handling

The input schema and `MeshValidator` reject invalid contact pairs, degenerate
faces, non-finite geometry, invalid numerical parameters, frictional requests
on the common penalty route, MPC/RBE combinations and unsupported analysis
routes. Route-native failures include:

| Failure class | Current behavior | Readiness status |
| --- | --- | --- |
| Invalid pair/geometry | `InputValidationError` before solve | IMPLEMENTED |
| Unsupported route/combination | Compatibility or mesh validation rejection | IMPLEMENTED_BOUNDED |
| Singular contact base/saddle system | `NumericalConvergenceError` with linear-solver failure reason | IMPLEMENTED |
| Non-finite displacement/contact trial | Explicit input or `NAN_DETECTED` failure | IMPLEMENTED |
| Active-set/updated-search non-convergence | `CONTACT_UPDATE_FAILURE` | IMPLEMENTED_BOUNDED |
| Excessive penalty penetration | `CONTACT_PENETRATION_EXCESSIVE` | IMPLEMENTED_BOUNDED |

The explicit codes are useful, but there is no single cross-route contact
convergence envelope or requirement that every route expose identical Python
exceptions. That is a WP07 qualification/architecture gap, not a reason to
rename the existing route-native failures.

## State, rollback and contamination risk

The common nonlinear driver opens a detached trial state and commits material
and continuation updates only after convergence. Rejected increments verify
the accepted composite digest. For frictionless penalty contact this is safe
for the stateless contribution: a rejected trial does not carry a contact
history into the next trial.

The boundary is not universal. The active-set and updated-search loops own
local active faces, multipliers, gaps and search history. These are diagnostics
or local solve data, not a common accepted contact state. Checkpoint topology
labels frictionless contact as `stateless`, but no active-face/search digest is
persisted. Stateful friction is explicitly separate and out of scope.

Therefore the current risk is LOW for the stateless penalty contribution in
the common driver and MEDIUM for future active-set/updated-search integration.
No claim of restart equivalence or transactional contact history is made here.

## Equilibrium, moment and energy audit

`LinearStaticSolver` computes residual/internal force, reactions, constraint
forces, vector force and moment balance and records raw values in the audit.
`_apply_contact_moment_transport` keeps the raw global-origin moment visible
and applies a reference-position correction for a tangential contact force.
That correction is an audit/reference correction, not a change to contact
mechanics. A frictionless normal-only contact has no tangential contact force,
so the correction is zero for the present WP07 scope.

Penalty contact energy is derivable as `0.5 * penalty * penetration^2` and the
historical v3 contract independently checked branchwise work. This is not a
universal runtime energy field across active-set and penalty enforcement, and
the old v1/v2 failures remain preserved as failures.

## Historical evidence and current tests

| Evidence | Level | What it proves | What it does not prove |
| --- | --- | --- | --- |
| `qualification/0_2_8/wp13_07_contact_bounded_contract.json` | HISTORICAL FAIL | Bounded TET4 penalty contract and failure cases; v1 energy gate failed | 0.2.9 qualification or general contact |
| `qualification/0_2_8/wp13_07_contact_bounded_v2_contract.json` | HISTORICAL FAIL | Corrected branchwise energy contract; campaign still failed | Current maturity |
| `qualification/0_2_8/wp13_07_contact_bounded_v3/wp13_07_contact_v3_evidence.json` | PASS bounded | Two exact replays, finite residuals, penalty sensitivity and fail-closed cases in declared TET4 scope | Active-set equivalence, surface contact, friction, dynamics, MPI or general nonlinear material |
| `qualification/0_2_8/wp13_07d_contact_capability_record.json` | Owner-approved experimental bounded | Separate capability and explicit exclusions | Promotion of the 46 combination registry or WP07 closeout |
| `qualification/reviews/contact_v1_linear_static_bounded_2026-07-29.json` | Historical Owner bounded | Earlier linear-static review and external/internal record | A new 0.2.9 campaign |
| Contact unit tests | Targeted | Geometry, KKT, penalty tangent, updated search and invalid-input behavior | Structural qualification, external correlation or performance |

The existing contact unit set was run in this audit:

`tests/unit/test_frictionless_contact.py` +
`tests/unit/test_nonlinear_contact_composition.py` +
`tests/unit/test_contact_finite_sliding.py` → **40 passed**.

The structural TET4 campaign and Code_Aster campaign were not run under the
no-heavy-solve policy. Historical evidence was reused at its original level;
it was not requalified.

## Primary gaps

1. Active-set and updated-search contact state is not owned by the common
   accepted/trial transaction.
2. There is no explicit contact active-face/search checkpoint and restart
   compatibility contract.
3. Contact convergence and diagnostics remain route-native rather than a
   single cross-route envelope.
4. A new 0.2.9 external campaign is absent; historical Code_Aster evidence is
   not automatically comparable to both enforcement branches.
5. Surface-to-surface, friction, self-contact, impact, dynamic, modal,
   buckling, harmonic, MPI and performance claims are outside scope or
   explicitly unsupported.

## Proposed bounded WP07 scope

The maximum honest claim for a future WP07 qualification is:

* frictionless node-to-triangle contact;
* `linear_static` direct sparse active-set cases in small displacement;
* `nonlinear_static` frictionless penalty composition with explicit
  `contact_mode='penalty'` and declared search/penetration controls;
* `geometric_nonlinear_static` only as research/experimental bounded
  composition;
* declared tested meshes, geometries, load paths and penalty values only.

Explicit exclusions are friction, surface-to-surface/mortar/augmented
Lagrangian, self-contact, impact, modal/buckling/dynamic/harmonic contact,
MPI/distributed contact and universal penalty/convergence claims.

## Prospective V&V plan — Owner review required

No cases below were executed. They are the minimum future categories, not
retroactive evidence:

| Case | Purpose |
| --- | --- |
| Open contact | Positive analytical gap and zero normal contact force |
| Single active contact | Gap, complementarity/KKT and force equilibrium |
| Deformable master/multiple contacts | Action-reaction, vector force/moment balance and deterministic face selection |
| Open-close-reopen path | No ghost force/energy and accepted load-history consistency |
| Three-level mesh characterization | Declared displacement/reaction/penetration/equilibrium variation |
| Deterministic replay | Same arrays/diagnostics within predeclared tolerance and same failure code |
| Adversarial failures | Invalid geometry, singular system, unsupported combination, nonfinite state and update failure |
| Transaction boundary | Rejected/retried increment with accepted-state and contact/search digest |
| External comparison | Code_Aster only where the exact active-set or penalty formulation is comparable |

Candidate thresholds are `OWNER_REVIEW_REQUIRED`, not frozen by this audit:
gap/complementarity `<=1e-10`, force and moment vector relative error
`<=1e-8`, replay relative tolerance `<=1e-12` with absolute floor `1e-14`,
and a candidate final mesh variation `<=3%`. Missing/nonfinite observables
must fail closed; no artificial monotonicity or universal threshold is claimed.

## Proposed WP07 decomposition (10 points, none awarded)

| Package | Scope | Points |
| --- | --- | ---: |
| WP07-A | Readiness, exact formulation and state audit | 1 |
| WP07-B | Common residual/tangent and state-transaction adapter | 3 |
| WP07-C | Geometry/search/active-set unit and invariant V&V | 2 |
| WP07-D | Linear-static structural V&V and compatible external correlation | 2 |
| WP07-E | Nonlinear search, restart/rollback/replay and Owner closure | 2 |
| **Total** |  | **10** |

## Governance and next step

No production source, contact mechanics, route behavior or maturity record was
changed. The 0.2.8 contact documents remain immutable historical records. The
next authorized step is Owner review of this bounded scope and formulation
boundary before implementation or any heavy qualification campaign.
