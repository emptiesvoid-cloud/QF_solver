---
doc_id: DOC-029-WP07-C-CONTACT-IDENTITIES-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.9 — WP07-C contact identities and open/close V&V

This is a lightweight mathematical V&V candidate for the already bounded
frictionless contact formulations. It does not qualify a new contact
combination, award formal points or change maturity.

Machine-readable evidence: [`wp07c_contact_identities.json`](../../../qualification/0_2_9/wp07c_contact_identities.json)
WP07-A contract: [`wp07a-contact-formulation-contract.md`](wp07a-contact-formulation-contract.md)
WP07-B contract: [`wp07b-contact-evaluation-restart.md`](wp07b-contact-evaluation-restart.md)

Source snapshot: `9ebad4a4ace79e0c4882bbf1636e45a5a3f6d563`
Owner status: `WP07-C_IMPLEMENTATION_CANDIDATE`
WP07-C formal points: `0/2`
WP07 total points: `0/10`
Validated total: `29/100`

## Bounded scope

The penalty identities apply only to
`NONLINEAR_PENALTY_INITIAL_SEARCH`: frictionless node-to-triangle contact,
initial/fixed face and normal, and the existing penalty contribution. The
active-set identities apply only to
`LINEAR_ACTIVE_SET_INITIAL_SEARCH`: linear static, small displacement,
frictionless node-to-triangle contact and the existing serial direct sparse
active-set route.

`UPDATED_SEARCH_FINITE_SLIDING` is not included in these claims. It remains
`RESEARCH_ONLY`, with an `APPROXIMATE_GEOMETRIC_CONTACT_TANGENT`, no energy
claim and `UNQUALIFIED_RESTART` status.

## Frozen identities and policies

For the fixed-normal penalty fixture, the signed gap and relative-gap vector
are

`g(u) = g0 + c · u`.

The declared piecewise response is:

* active (`g < 0`): `f_c = k * g * c` and `K_c = k * c ⊗ c`;
* open (`g >= 0`): `f_c = 0` and `K_c = 0`.

The contact potential is
`U_c = 0.5 * k * min(g, 0)^2`. The finite-difference energy-gradient
threshold is `1e-7` relative, away from the activation switch.

The central finite-difference tangent thresholds, frozen before execution,
are:

* Frobenius relative error `<= 1e-6`;
* maximum nonzero-column relative error `<= 5e-6`;
* symmetry relative error `<= 1e-12`.

Open-force normalization is `norm(f_c) / max(k, 1)` for this algebraic
fixture and must be `<= 1e-12`. Replay uses relative tolerance `1e-12` with
absolute floor `1e-14`.

For active-set checks the declared case scales are `L_char = 0.1`,
`F_char = ||F_external||` (`20` for the open case and `200` for the closed
case), and `P_char = max(|p|, 1)`. The frozen metrics are:

* closed gap: `abs(g) / L_char <= 1e-10`;
* wrong-sign pressure: `max(-p / P_char, 0) <= 1e-12`;
* complementarity: `abs(g*p) / (L_char*P_char) <= 1e-10`;
* open contact force: `norm(f_contact) / F_char <= 1e-12`;
* force and moment equilibrium: existing scale-aware audit fields `<= 1e-8`.

All checked observables must be finite. The activation boundary is
nonsmooth by contract; differentiability at `g = 0` is not claimed.

## Results

The tests use one straight-sided, single-master-triangle fixture and one
small direct active-set fixture. No mesh refinement, external solver,
MPI/PETSc run or large structural campaign was executed.

| Check | Observed result | Frozen limit | Status |
| --- | ---: | ---: | --- |
| open penalty force normalized | `0.0` | `1e-12` | PASS |
| active force identity | exact within `1e-12` absolute | `1e-12` | PASS |
| energy-gradient relative error | `1.5192447540e-10` | `1e-7` | PASS |
| tangent Frobenius relative error | `1.5743360214e-11` | `1e-6` | PASS |
| tangent maximum-column error | `3.2741809265e-11` | `5e-6` | PASS |
| tangent symmetry relative error | `0.0` | `1e-12` | PASS |
| active-set force equilibrium | `1.4210854715e-16` | `1e-8` | PASS |
| active-set moment equilibrium | `2.8421709430e-16` | `1e-8` | PASS |

The activation cases use `g = +1e-6` (open), `g = -1e-6` (active) and
`g = 0` (implementation-defined boundary, observed open). The open → close
→ deeper penetration → unload → reopen sequence produced no ghost force;
re-evaluation of both the reopened and closed states was deterministic.

The active-set open case had no reaction. The closed case had `p = 100`, a
zero normalized gap, zero wrong-sign pressure and zero normalized
complementarity. A repeated identical model/load reproduced active status,
pressure and displacement exactly.

## Governance and tests

The evidence is test-level candidate evidence only. It does not promote
updated search, finite sliding, friction, dynamics, impact, self-contact or a
general industrial contact claim. No contact formula, penalty value,
activation criterion, normal/search policy, active-set algorithm, Newton or
line-search policy changed.

Targeted tests:

* `tests/unit/test_wp07c_contact_identities.py` — 11 checks;
* WP07-B restart/evaluation regressions;
* existing frictionless-contact and nonlinear-contact regressions.

The WP07-C candidate is `PASS_CANDIDATE_PENDING_OWNER_REVIEW`. Formal points
remain `0/2` and validated total remains `29/100`.
