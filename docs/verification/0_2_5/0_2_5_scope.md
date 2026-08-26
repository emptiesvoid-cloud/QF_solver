---
doc_id: DOC-NL-025-002
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 scope

## Product intent

Unify material nonlinearity, geometric nonlinearity, stability, path following
and contact around one inspectable nonlinear structural mechanics engine. The
release is evidence-driven: code presence is not qualification.

## MUST

| Scope | Required release claim |
|---|---|
| 0.2.4 J2 debt | multi-element, mesh/load-step convergence, energy, rollback and stronger tangent evidence |
| Common nonlinear contracts | one global residual/tangent, convergence, increment transaction and diagnostics model |
| Geometric nonlinear core | objective Total-Lagrangian or Owner-approved equivalent for TET4 and HEX8 |
| Stability | sparse linearized buckling factors/modes with analytical and external evidence |
| Path following | one sparse arc-length method for a bounded class of limit-point problems |
| Frictionless contact | finite-sliding opening/closure/recontact integrated into common Newton and rollback |
| Couplings | J2 + geometric and geometric + contact, subject to approved stress/strain measures |
| Robust failures | classified failures, no false convergence, state-safe rollback |
| Regression | full 0.2.4 linear and nonlinear release scope remains green |
| V&V | analytical, numerical, mesh/load-step and bounded external correlation evidence |

## SHOULD

| Scope | Condition |
|---|---|
| TET10 and HEX20 large deformation | only after low-order objectivity and tangent gates close |
| Augmented Lagrangian contact | only if penalty/active-set sensitivity blocks acceptable contact evidence |
| J2 + geometric + contact | only after both pairwise coupled gates close |
| Multiple external solvers | when comparable formulations and tools are available |
| Targeted optimization | only for measured hotspots with numerical non-regression |

## COULD

- Coulomb friction with stick/slip state and dissipation evidence.
- Additional arc-length controls after the primary method is verified.
- Additional nonlinear performance optimizations.

COULD items are excluded from release completeness unless the Owner explicitly
promotes them before implementation and assigns new mandatory evidence.

## Explicitly out of scope

- WEDGE, PYRAMID or any other new element family.
- Hyperelasticity, damage, fracture, creep, viscoplasticity or thermoplasticity.
- Generalized self-contact, cohesive, thermal or advanced mortar contact.
- Explicit nonlinear dynamics, multiphysics, CFD, thermal analysis or GUI work.
- General HPC/PETSc redesign.
- A physical-validation claim based only on numerical code-to-code correlation.

## Qualification vocabulary

| State | Meaning |
|---|---|
| `implemented` | code exists; no evidence claim |
| `PASS_INTERNAL` | defined internal verification passed on a traced SHA |
| `OBSERVED_INTERNAL` | local working-tree evidence observed during implementation; not final-SHA controlled evidence |
| `PASS_EXTERNAL_CORRELATION_BOUNDED` | reproducible external numerical correlation passed in the stated envelope |
| `owner_accepted_experimental_bounded_use` | Owner accepts use only within documented limits |
| `qualified` | all mandatory release requirements, evidence and Owner decision are closed |

## Release claim boundary

The default proposed claim is **experimental bounded nonlinear structural
mechanics**. It must list element, material, kinematic, load-path and contact
limits. No claim covers arbitrary finite-strain plasticity, arbitrary contact,
snap-back or friction unless its corresponding gate is explicitly closed.
