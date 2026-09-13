---
doc_id: DOC-029-WP07-A-CONTRACT-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.9 — WP07-A contact formulation contract R1

This is the Owner-correction contract companion to the WP07 readiness audit.
It freezes a prospective bounded scope before any WP07 mechanical campaign.
It is not a qualification result and awards no points.

Machine-readable contract: [`wp07a_contact_formulation_contract.json`](../../../qualification/0_2_9/wp07a_contact_formulation_contract.json)
Readiness audit: [`wp07-frictionless-contact-readiness.md`](wp07-frictionless-contact-readiness.md)

Owner disposition: `APPROVED_WITH_CORRECTIONS`
Revision: `OWNER_CORRECTION_R1`
Source snapshot: `2c52bf8196a7d47d14ce1784290580160de26590`

WP07 remains preparation-only (`0/10` points; validated total `29/100`). No
solver, formulation or maturity record is changed by this contract.

## Three regimes must remain separate

The word “frictionless contact” is not a single qualification claim in this
repository. The following regimes have different enforcement and state
semantics.

### A — `LINEAR_ACTIVE_SET_INITIAL_SEARCH`

* `linear_static`, small displacement, serial direct sparse execution;
* node-to-triangle unilateral normal contact;
* ordered master-face normal and initial/fixed face geometry;
* active-set/Lagrange multiplier enforcement through an augmented reduced
  system;
* local active-set multipliers and iteration history are not a common Newton
  transaction.

### B — `NONLINEAR_PENALTY_INITIAL_SEARCH`

* common nonlinear Newton path where the route admits penalty contact;
* frictionless node-to-triangle contact with initial/fixed face and normal;
* `f_contact = k * min(g(u), 0) * c` and local piecewise tangent
  `Kc = k * c ⊗ c`;
* finite penetration is an observable and may be valid under the penalty
  method; zero penetration is not an acceptance requirement;
* frictionless penalty contact is pure/stateless from the trial displacement;
  material and continuation state remain transaction-owned by the common
  driver.

### C — `UPDATED_SEARCH_FINITE_SLIDING`

* facet, normal and projection depend on trial displacement;
* bounded research path only, not part of the baseline qualified-scope
  candidate;
* the implemented rank-one penalty term does not by itself prove all geometry
  derivatives;
* classification is `APPROXIMATE_GEOMETRIC_CONTACT_TANGENT` unless a later
  proof establishes a consistent geometric tangent;
* no energy claim is made without a separate proof.

These regimes must not be collapsed into a generic “consistent contact” label.

## Scope candidate for future Owner freeze

The bounded candidate is limited to:

1. `linear_static` + A + frictionless node-to-triangle + small displacement +
   serial direct sparse;
2. static/quasi-static nonlinear + B + frictionless node-to-triangle + common
   Newton residual/tangent + serial execution.

Claims are restricted to declared and tested geometry, load path, mesh,
parameter and supported-material combinations. The candidate excludes general
surface-to-surface contact, arbitrary large sliding, finite-sliding and updated
normal qualification, friction, dynamics/impact, MPI, self-contact, mortar,
augmented Lagrangian, modal/buckling contact and general industrial contact.

## Scale-aware unilateral checks

There is no single universal dimensional `gap <= 1e-10` rule.

Each case must predeclare positive scales:

* `L_char`: characteristic geometry length;
* `F_char`: characteristic external-load/resultant norm;
* `P_char`: characteristic contact-pressure scale when a multiplier is
  reported.

For A, candidate dimensionless checks are:

| Quantity | Definition |
| --- | --- |
| Closed gap | `abs(g) / L_char` |
| Pressure sign | `max(-p / P_char, 0)` |
| Complementarity | `abs(g*p) / (L_char*P_char)` |
| Open-contact force | `norm(f_contact) / F_char` |

Candidate thresholds are respectively `1e-10`, `1e-12`, `1e-10` and `1e-12`,
all `OWNER_REVIEW_REQUIRED`. The active/open classification itself remains
unilateral and must be checked separately.

For B, finite penetration is allowed. Candidate checks compare normalized
penetration with an independent reference when available, contact-force error,
vector force/moment equilibrium, and penalty energy only when the fixed-normal
potential is mathematically applicable. Candidate thresholds are `1e-8` for
these normalized quantities and require Owner approval before execution.

## Tangent and energy policy

For fixed-normal penalty contact, the potential candidate is

`U_contact = 0.5 * k * min(g(u), 0)^2`.

Away from activation switching, its gradient must be compared with the runtime
contact force, and a central finite-difference test must compare the runtime
force with `k * c ⊗ c`. Perturbation size and scale are frozen before the test.

For active-set contact, no penalty potential is claimed. For updated search,
neither a consistent geometric tangent nor an energy identity is claimed until
the geometry-dependent derivatives and switching policy are independently
proven.

## State semantics

For frictionless penalty, contact evaluation is `PURE_STATELESS_FROM_TRIAL_U`:
same trial displacement, model and parameters must reproduce force, tangent and
diagnostics. Rollback therefore means restoring the accepted displacement and
re-evaluating without contamination; it does not invent a contact history.

For active-set and updated-search routes, distinguish:

* physical state: displacement and derived contact response;
* algorithmic state: active set, selected face, multiplier and search iterate;
* diagnostic state: gaps, pressures, face/normal and search history.

The active-set/restart contract is not yet implemented in the common
transaction/checkpoint boundary. This remains a qualification and
architecture gap, not a reason to broaden the scope.

## Prospective V&V — not executed

| Group | Minimum cases |
| --- | --- |
| Active-set | open zero force; prescribed closure; scale-aware complementarity; vector force/moment equilibrium; active-set stability |
| Penalty | open zero force; analytical 1-DOF compression; force/potential gradient; fixed-normal tangent FD; equilibrium; open-close; rollback/re-evaluation |
| Shared | replay; three-level refinement characterization; structural benchmark; formulation-compatible external/reference comparison |

No result-driven threshold tuning is allowed. Unsupported combinations,
non-finite values and missing required observables must fail closed.

## Point split and governance

| Package | Candidate scope | Points |
| --- | --- | ---: |
| WP07-A | Contract/formulation freeze | 1 |
| WP07-B | Unified contact evaluation + rollback/restart semantics | 2 |
| WP07-C | Contact identities/tangent/open-close V&V | 2 |
| WP07-D | Structural + compatible external V&V | 3 |
| WP07-E | Refinement/replay/Owner closure | 2 |
| **Total** |  | **10** |

This R1 freezes a candidate contract only. The next step is Owner freeze of
WP07-A, followed by separately authorized implementation and qualification.
