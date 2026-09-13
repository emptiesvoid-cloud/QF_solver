---
doc_id: DOC-029-WP07-B-CONTACT-EVALUATION-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.9 — WP07-B contact evaluation and restart semantics

This document records the bounded WP07-B implementation candidate. It does
not qualify a new contact combination, award points or change maturity.

Machine-readable contract: [`wp07b_contact_evaluation_restart.json`](../../../qualification/0_2_9/wp07b_contact_evaluation_restart.json)
WP07-A contract: [`wp07a-contact-formulation-contract.md`](wp07a-contact-formulation-contract.md)

Source snapshot: `1b400e20685f80d4508d93a31abeca2caee129fe`
Owner status: `WP07-B_IMPLEMENTATION_CANDIDATE`
WP07-B formal points: `0/2`
Validated total: `29/100`

## Bounded scope

WP07-B hardens only the already-existing fixed-normal frictionless penalty
evaluation. The numerical force and tangent assembly remains in
`solveur.contact.solver.assemble_penalty_contact`.

* `NONLINEAR_PENALTY_INITIAL_SEARCH` is a node-to-triangle, frictionless,
  initial/fixed-face and fixed-normal contribution to a supported common
  Newton route. Finite penetration is an observable; it is not silently
  replaced by zero.
* `LINEAR_ACTIVE_SET_INITIAL_SEARCH` remains a separate Lagrange/active-set
  route. Its active set, multipliers and iteration history are local to the
  solve.
* `UPDATED_SEARCH_FINITE_SLIDING` remains research-only. Its facet, normal and
  projection depend on trial displacement and it has no qualified restart or
  consistent-geometric-tangent claim.

## ContactEvaluation

`ContactEvaluation` wraps the legacy `(internal_force, tangent, details)`
return without copying large numerical arrays. It validates finite force,
tangent entries and diagnostic payloads and exposes the legacy details as well
as additive stable names:

| Stable name | Meaning |
| --- | --- |
| `contact_active_count` | Number of active penalty contributions |
| `contact_minimum_gap` | Minimum signed gap over evaluated contacts |
| `contact_maximum_penetration` | Maximum `max(-gap, 0)` |
| `contact_force_norm` | Norm of the assembled contact internal force |
| `contact_tangent_nnz` | Nonzero count of the contact tangent |
| `contact_search_mode` | `initial` or `updated` route setting |

Existing keys such as `active_contacts`, `gaps`, `master_face_indices`,
`maximum_penetration` and `tangent_nnz` remain available. The wrapper does not
alter force, tangent, activation, penalty value, Newton or line-search
behavior. The common nonlinear assembly continues to use

`R_global = R_internal + R_contact - F_external`
`K_global = K_internal + K_contact`.

## Pure evaluation and rollback

For a fixed model, DOF map, parameter set and trial `u`, evaluation is
deterministic and does not mutate persistent contact state. The bounded
rollback proof is:

1. evaluate accepted `u0`;
2. evaluate a discarded trial `u1`;
3. restore/re-evaluate `u0`;
4. compare force, tangent, active contacts, gaps, selected faces and stable
   diagnostics.

Penalty contact is `PURE_STATELESS_FROM_TRIAL_U`; there is no independent
committed `ContactStateTransaction`. Existing nonlinear material and
continuation transactions remain owned by the common driver.

## Configuration digest and restart metadata

`contact_configuration_digest` hashes a canonical semantic payload containing:

* schema/contract version and analysis type/method;
* ordered contact entries, names, slave nodes/patch nodes;
* ordered master nodes/faces;
* gap tolerance, friction coefficient and tangential stiffness;
* contact mode, search mode, finite-sliding setting;
* penalty value and relevant contact iteration/tolerance parameters.

The digest uses deterministic typed serialization and never hashes Python
object identities. Nodal coordinates are intentionally excluded because the
surrounding model/checkpoint signature owns physical geometry.

`PenaltyContactRestartMetadata` records the contact digest, analysis/search
configuration, state semantics and an optional accepted-state digest. A
compatible restart requires restored accepted state, the same model/contact
parameters and a matching digest. Metadata mismatch fails closed with
`InputValidationError`; it is never treated as a compatible restart.

Active-set mid-solve restart remains `UNSUPPORTED`. Updated-search restart is
`UNQUALIFIED_RESTART`; recomputation may be deterministic for a trial, but no
qualification claim is made.

## Failure and compatibility policy

Existing `CONTACT_PENETRATION_EXCESSIVE`, `CONTACT_UPDATE_FAILURE` and input
validation errors remain route-native. No numerical failure is remapped to a
generic contact exception. Legacy diagnostics are preserved and the stable
aliases are additive.

## Targeted verification

The WP07-B test set covers same-trial determinism, discarded-trial
re-evaluation, digest determinism and sensitivity, compatible/incompatible
restart metadata, explicit active-set/updated-search restart boundaries,
legacy diagnostic preservation and evaluation-wrapper numerical identity.
The existing contact/nonlinear tests remain part of the targeted regression.
No structural campaign, external solver, MPI/PETSc run or full suite is part
of this work package.

No production mechanics formulation, penalty value, activation criterion,
Newton policy, line-search policy or maturity record was changed.
