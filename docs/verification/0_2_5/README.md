---
doc_id: DOC-NL-025-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 planning pack

## Executive summary

QF Solver 0.2.4a0 provides a common small-strain J2 constitutive contract,
material-state transactions and a bounded Full Newton path for TET4, TET10,
HEX8 and HEX20. The 0.2.5 working tree now also contains a bounded,
two-cell Code_Aster correlation with matched displacement, reaction, stress and
PEEQ histories for all four families. Multi-element plastic redistribution,
cyclic paths, energy balance and adversarial cutback still have internal V&V
debt beyond that correlation.

The current geometric-nonlinear TET4/HEX8 Total-Lagrangian path, the contact
solvers and the small-strain nonlinear driver use separate global iteration and
state management paths. A bounded sparse linear-buckling route now exists for
TET4/HEX8, but it is not a unified production analysis. The working tree also
contains a sparse arc-length correction helper, but branch following remains
unqualified.

Version 0.2.5a0 therefore targets a unified nonlinear structural mechanics
infrastructure, not an accumulation of new element types. Work proceeds one
gate at a time: close 0.2.4 V&V debt, unify geometric nonlinearity, verify
buckling and path following, integrate frictionless contact, then prove coupled
behavior. Friction is optional and cannot block the core release.

Implementation has started incrementally under the controlled status record
[`0_2_5_implementation_status.md`](0_2_5_implementation_status.md). Controlled
evidence closes G01, G02, G03, G05, G08 and G09 only within their documented bounded
domains. In particular, G02 accepts the elastic Total-Lagrangian TET4/HEX8
pre-limit scope; it does not promote finite-kinematic J2, high-order geometric
paths, post-limit response, contact or coupling.

The current robustness campaign also records provisional internal evidence for
bounded TET4/HEX8 buckling factors, proportional arc-length continuation to a
unit load factor, a reduced shallow-arch branch crossing an analytical limit
point, unilateral sparse penalty-contact activation, and an
adversarial `MIN_INCREMENT_REACHED` failure. It also records a bounded TET4
composition smoke for J2, Total-Lagrangian geometry and initial/updated
frictionless penalty contact through the same Newton driver. These observations
are useful for the next work packages. The bounded G05 contact contract is now
closed; G04 and G06 remain open, while general surface-to-surface contact,
friction and unrestricted large sliding remain outside the qualified claim.

G06 is intentionally deferred: its implementation is `CODE_COMPLETE /
EXPERIMENTAL`, but its qualification remains `OPEN` because finite-kinematic
J2 is still research and the required external coupled correlations are not
comparable or complete. The 0.2.5 contract is unchanged.

The post-release roadmap is deliberately narrow. `0.2.6` targets maturity,
V&V, robustness, benchmarks and scalability/performance. `0.2.7` targets an
approved finite-strain J2 formulation and G06 requalification with coherent
measures, state transactions and independent Code_Aster evidence. Neither
roadmap entry promotes a claim in 0.2.5.

## Audited baseline

| Item | Current state | Evidence / implementation | 0.2.5 consequence |
|---|---|---|---|
| Published baseline | `v0.2.4a0`, SHA `e368c0ce00874c16ff1e8fa9158ea0a8cd2dd745` | successful release workflow, wheel/sdist and smoke installation | use as immutable numerical baseline |
| J2 small-strain | bounded experimental use | `materials/solid.py`, constitutive and robustness tests | close multi-element and path-dependent V&V debt first |
| Material state | common committed/trial session | `core/material_state.py` | profile deep copies and reuse for every nonlinear subsystem |
| Full Newton | qualified within 0.2.4 bounded scope | `core/nonlinear.py` | sole production Newton strategy initially |
| Modified Newton | implemented, not production-qualified | `core/nonlinear.py` | remain locked outside qualified scope |
| Arc-length | sparse correction, existing FEM TET4 path, restart smoke and reduced shallow-arch limit-point path observed | `core/nonlinear.py`, `core/nonlinear_checkpoint.py`, `verification/total_lagrangian_structural.py`, robustness campaign | unify the FEM branch with the common driver, verify snap-through/post-buckling and external correlation as WP4 |
| Geometric nonlinearity | research TET4/HEX8 Total Lagrangian with bounded large-deflection smoke | `core/geometric_nonlinear.py`, `elements/solid/*total_lagrangian*`, robustness campaign | merge contracts, mesh/external evidence and plastic large-rotation qualification after audit |
| Buckling/post-buckling | bounded research TET4/TET10/HEX8/HEX20 linear-buckling route; assembled coarse/medium mesh sensitivity; bounded TET4 Euler reference now recorded | `core/buckling.py`, `tet4_total_lagrangian_buckling.py`, robustness campaign | add external/high-order correlation, true multi-family mesh convergence and post-buckling evidence |
| Normal contact | bounded common penalty path with initial/updated geometry modes, open/close/recontact, multi-face search, opt-in clamped finite-sliding projection, penalty sensitivity and bounded Code_Aster histories | `contact/solver.py`, `core/nonlinear_assembly.py`, `g05_latest` evidence | general surface-to-surface, friction and unrestricted large sliding remain outside scope |
| Coupled nonlinear path | bounded connected two-element TET4 J2 + geometry + penalty-contact composition, four-family J2/geometric and updated-contact replay through common Newton, independent coupled tangent FD, bounded geometry/contact mesh replay, and a deformable TET4 Green-Lagrange contact comparison | `results/vnv_0_2_5/g06_latest/`, `g06_diagnostic/summary.json`, `g06_geometry_contact_mesh/summary.json`, `g06_geometry_contact_code_aster/tet4_green_lagrange/comparison.json`, `tests/unit/test_nonlinear_multielement.py` | internal research evidence only; Code_Aster J2+geometry MUST remains convention-limited/non-convergent for TET10/HEX20, and the contact comparison remains open because the mapped reaction history differs by up to 76.7% and does not use an identical multiplier observable |
| Friction | experimental separate path | friction tests and contact solver | optional WP7 after frictionless gate |
| External J2 correlation | `PASS_EXTERNAL_CORRELATION_BOUNDED` | Code_Aster affine and regular two-cell campaigns; TET10 uses explicit `code_aster_5` comparison quadrature | broader external cells and final-SHA evidence remain required |
| 0.2.4 gate record | published release, but local gate JSON retains pre-release SHA placeholders | `qualification/reviews/qf_solver_0_2_4a0_gate_status.json` | repair provenance in WP0 without rewriting historical numerical evidence |

## Current architecture map

```text
AnalysisRouter
|-- nonlinear_static
|   `-- NonlinearStaticSolver
|       |-- small-strain element nonlinear contract
|       |-- ConstitutiveModel / J2
|       |-- MaterialStateSession
|       `-- linear backend
|-- geometric_nonlinear_static
|   `-- GeometricNonlinearStaticSolver
|       `-- TotalLagrangianTet4Assembly / StVK
`-- linear_static with contact
    `-- FrictionlessActiveSetSolver
        `-- independent active-set / friction iteration
```

The three branches do not yet share one residual assembly, one tangent
assembly, one increment transaction or one convergence diagnostic contract.

## 0.2.4 debt carried into WP1

1. Multi-element J2 mesh convergence across TET4/TET10/HEX8/HEX20.
2. Cyclic loading within the exact isotropic-hardening limitations.
3. External work, recoverable elastic energy and plastic dissipation balance.
4. A real failed Newton increment followed by rollback, cutback and retry.
5. Tangent finite-difference robustness near yield and on non-proportional paths.
6. Broader external correlations beyond the bounded regular two-cell history.
7. Investigation of PEEQ differences across formulations and HEX20 cost.
8. Final-SHA provenance cleanup for the published 0.2.4 gate record.

## Pack contents

- [Scope](0_2_5_scope.md)
- [Target architecture](0_2_5_architecture.md)
- [Work packages and dependencies](0_2_5_work_packages.md)
- [Requirements matrix](0_2_5_requirements.md)
- [Formula inventory](0_2_5_formula_inventory.md)
- [V&V plan](0_2_5_vnv_plan.md)
- [V&V matrix](0_2_5_vnv_matrix.md)
- [Benchmark plan](0_2_5_benchmark_plan.md)
- [External correlation matrix](0_2_5_external_correlation_matrix.md)
- [Performance plan](0_2_5_performance_plan.md)
- [Failure-mode plan](0_2_5_failure_mode_plan.md)
- [Risk register](0_2_5_risk_register.md)
- [Gate matrix](0_2_5_gate_matrix.md)
- [Known limitations](0_2_5_known_limitations.md)
- [Release-readiness template](0_2_5_release_readiness.md)
- [Owner Review template](0_2_5_owner_review_template.md)
- [G02 Owner decision](0_2_5_g02_owner_review.md)
- [Objective-mode execution plan](0_2_5_objective_execution_plan.md)

The repeatable local readiness chain is
`scripts/release_readiness_pipeline_025.py`. It is dry-run by default and
never tags, pushes or uploads artifacts.

## Planning status

G01, G02, G03, G05, G08, G09 and G11 are closed only by their controlled
evidence and recorded replay decisions. G04 and G06 remain `OPEN`; G10 is
`BLOCKED` by the mandatory external cells of G04/G06, and G12 remains `OPEN`
until aggregate readiness and Owner closure. Optional friction gate G07 is
`NOT_IN_RELEASE_SCOPE` until an explicit Owner promotion. A planning document
never closes an implementation, V&V, correlation or release gate.
