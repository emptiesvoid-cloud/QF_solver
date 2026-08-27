---
doc_id: DOC-NL-025-005
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 requirements matrix

## Tolerance governance

Existing 0.2.4 tolerances remain lower bounds on rigor. New numeric targets must
be derived from an analytical solution, external-reference uncertainty, mesh or
load-step asymptote, or baseline repeatability before implementation. A target
cannot be relaxed after observing a failure without an Owner-reviewed technical
justification. `TBD-G00` means freeze during WP0, not choose after implementation.

## Requirements

| ID | Requirement | Formula / contract | Implementation target | Planned proof | Evidence | Gate |
|---|---|---|---|---|---|---|
| 025-REQ-001 | Preserve published 0.2.4 behavior | numerical/API baseline | all existing paths | complete 0.2.4 suite and snapshots | baseline manifest | G00, G11 |
| 025-REQ-002 | Classify maturity truthfully | qualification vocabulary | registry/docs | audit classification consistency | audit report | G00, G12 |
| 025-REQ-003 | J2 works on real multi-element meshes | global equilibrium + local return mapping | common nonlinear assembler | four-family meshed benchmark | J2 mesh pack | G01 |
| 025-REQ-004 | J2 solution converges in mesh/load step | asymptotic response | benchmark suite | coarse/medium/fine/refined and step sweep | convergence plots/tables | G01 |
| 025-REQ-005 | Cyclic J2 follows implemented hardening law | yield function and history | constitutive/state core | load/unload/reload/reversal cycles | path histories | G01 |
| 025-REQ-006 | Energy is accountable | `Wext = Ue + Dp + imbalance` | results/post-processing | energy history and dissipation sign | energy report | G01 |
| 025-REQ-007 | Failed increments preserve committed state | transactional invariant | state/increment controller | forced fail, rollback, cutback, retry | state digests | G01, G09 |
| 025-REQ-008 | J2 algorithmic tangent is consistent | `C_alg = d sigma / d epsilon` | constitutive core | FD sweep over states/paths/step sizes | tangent report | G01 |
| 025-REQ-009 | One common Full Newton drives mandatory paths | common residual/tangent loop | nonlinear driver | architecture tests and coupled runs | driver trace | G02, G05, G06 |
| 025-REQ-010 | Geometric kinematics are objective | rigid rotation produces no spurious strain/stress | kinematics/TL elements | rigid-body rotations and frame invariance | objectivity report | G02 |
| 025-REQ-011 | Geometric tangent is consistent | `K = dR/du` | nonlinear element contribution | element/global FD tangent | tangent report | G02 |
| 025-REQ-012 | Material and geometric tangents assemble sparsely | `K = Kmat + Kgeo` | global assembler | sparse type/nnz/memory contracts | assembly metrics | G02, G08 |
| 025-REQ-013 | TET4 and HEX8 large-deformation core is verified | approved measure pair | TL/corotational elements | patch, distortion, cantilever, mesh study | geometric V&V pack | G02 |
| 025-REQ-013A | High-order geometric paths reuse the common kernel without promotion by implementation alone | same kinematics/state/residual/tangent contract | TET10/HEX20 TL adapter | bounded residual, determinant, energy and state-recovery smoke | high-order geometric evidence | G02 (research) |
| 025-REQ-014 | Buckling uses a generalized sparse eigenproblem | `(K + lambda Kg) phi = 0` | eigen backend | Euler + external benchmark | buckling pack | G03 |
| 025-REQ-015 | Buckling diagnostics expose factor/mode/backend | structured result contract | analysis/results | API/serialization tests | result sample | G03 |
| 025-REQ-016 | Arc-length follows the intended branch | equilibrium + continuation constraint | continuation controller | shallow arch/limit point | path plots | G04 |
| 025-REQ-017 | Arc-length remains sparse and restartable | no dense global correction | backend/checkpoint | matrix guard + restart equivalence | allocation/restart report | G04, G08 |
| 025-REQ-018 | Frictionless contact contributes to common residual/tangent | `R += Rc`, `K += Kc` | contact contribution | isolated/contact-global tangent tests | contact pack | G05 |
| 025-REQ-019 | Contact supports bounded open/close/recontact and opt-in finite-sliding projection | gap/active-state contract | search/state/controller | path, clamped-projection and sliding tests | state/penetration histories | G05 |
| 025-REQ-020 | Contact rollback is exact | common transaction invariant | contact state | forced failed increment | state digests | G05, G09 |
| 025-REQ-021 | Penetration/enforcement sensitivity is bounded | contact consistency | contact controls | penalty/mesh/load-step sweep as applicable | sensitivity report | G05 |
| 025-REQ-022 | J2 + geometry uses an approved finite-kinematic model | explicit measure transformation | coupled elements/material | tangent, energy and external curves | coupling decision/evidence | G06 |
| 025-REQ-023 | Geometry + contact is solved by the common driver | combined residual/tangent | assembler/driver | coupled benchmark and limit recovery | coupling report | G06 |
| 025-REQ-024 | Coupled paths recover uncoupled limits | contribution disabling invariants | coupled core | A/B limit tests | comparison tables | G06 |
| 025-REQ-025 | Optional friction is objective and dissipative | Coulomb/stick-slip contract | contact friction | frame rotation and cyclic sliding | friction pack | G07 |
| 025-REQ-026 | Nonlinear costs are measured reproducibly | timing/memory protocol | benchmark utilities | repeated profile by component | performance report | G08 |
| 025-REQ-027 | HEX20 cost is explained | component cost decomposition | element/assembler profile | integration/constitutive/assembly/copy profile | HEX20 report | G08 |
| 025-REQ-028 | Every planned failure is structured | failure enum + diagnostic payload | driver/results | adversarial matrix | failure report | G09 |
| 025-REQ-029 | No important failure is reported converged | explicit convergence invariant | all nonlinear drivers | injected faults | failure report | G09 |
| 025-REQ-030 | Mandatory capabilities have bounded external correlation | comparable full histories | external campaign | Code_Aster/CalculiX/Abaqus where available | correlation pack | G10 |
| 025-REQ-031 | Correlation is not mislabeled physical validation | terminology contract | documentation/evidence | document audit | audit record | G10, G12 |
| 025-REQ-032 | Full linear/nonlinear regression remains green | release gate contract | CI/readiness | complete candidate-SHA campaign | CI/evidence manifest | G11 |
| 025-REQ-033 | Packaging and docs are reproducible | wheel/sdist/docs/smoke | release workflow | clean build/install/doc generation | artifact digests | G11, G12 |
| 025-REQ-034 | Final evidence matches candidate SHA | provenance contract | manifests/reviews | SHA and digest consistency audit | release report | G12 |
| 025-REQ-035 | Publication is Owner-controlled | no automatic publish decision | workflow/docs | workflow contract inspection | Owner decision | G12 |
| 025-REQ-036 | Trial transactions detect committed-state mutation | committed digest invariant | material/contact state transactions | adversarial in-place mutation | `STATE_CORRUPTION` diagnostics and state-transaction tests | G01, G09 |

Current bounded evidence for `025-REQ-014` is recorded in
`tests/unit/test_linear_buckling.py` and
`results/vnv_0_2_5/robustness_high_order_latest/euler_buckling/summary.json`.
The public path now attempts the sparse generalized problem
`K phi = lambda (-Kg) phi` with `eigsh` when `-Kg` is positive definite. When
the geometric tangent makes that generalized mass indefinite, it first
brackets the loss of positive definiteness with sparse tangent eigenvalues and
then uses shift-invert `eigs(K, M=-Kg)` around that bracket; if ARPACK returns
a complex or invalid pair, the diagnosed `bracketed_sparse_eigenvalue`
fallback is retained. The evidence covers a TET4 total-Lagrangian
clamped-free column on two structured levels and high-order internal research
rows, and remains `PASS_INTERNAL_RESEARCH`; it does not satisfy the external
or post-buckling portions of the requirement by itself.

Current bounded evidence for `025-REQ-019` is recorded by `VV-056` and
`VV-071`. It covers updated node-to-triangle penalty contact and an opt-in
closest-point projection when the slave leaves the current triangle. It does
not satisfy a general surface-to-surface, continuous large-sliding or
frictional-contact claim.

The local tangent portion of `025-REQ-018` is additionally exercised by the
fixed-active centered finite-difference check in `VV-018` through
`run_contact_tangent_fd_benchmark`. It sweeps three perturbation sizes across
all global displacement directions and records the maximum relative derivative
error. This is a smooth local contact verification only; it does not cover the
active-set kink, continuous sliding, or external correlation.

The retry path for `025-REQ-016`, `025-REQ-017`, `025-REQ-028` and
`025-REQ-029` now records bounded arc-length rejection telemetry through
`VV-072`: the attempted radius, cutback radius, typed failure reason,
failure diagnostics and rollback-before-retry flag are serialized alongside
the existing load-control rejection log. This improves observability without
changing the continuation algorithm or closing `G04`/`G09`.

## Acceptance table template

Each benchmark instantiates this table before its implementation changes begin.

| Requirement | Metric | Target | Warning | Reject | Justification source |
|---|---|---|---|---|---|
| Example | named physical/numerical metric | frozen before change | investigation band | gate remains OPEN | analytical/reference/baseline provenance |

## G01 controlled acceptance treatment

The following criteria are inherited from existing tests or the existing
Code_Aster runner. They are not relaxed for this campaign. Metrics without a
pre-frozen release band remain evidence for Owner review and do not close
`025-G01` by implication.

| Requirement | Metric | Target | Warning | Reject | Justification source |
|---|---|---|---|---|---|
| 025-REQ-008 | algorithmic tangent FD relative error | `< 1e-6` | `1e-7` to `<1e-6` | `>=1e-6` | existing constitutive V&V test contract |
| 025-REQ-006 | relative work-energy imbalance | `< 1e-6` | `1e-7` to `<1e-6` | `>=1e-6` | existing multi-element energy test contract |
| 025-REQ-006 | plastic dissipation | `D_p >= 0` | none | `D_p < 0` | J2 dissipation invariant in existing campaign |
| 025-REQ-003 | global residual/work contract | existing four-family test limits | diagnostic | failed existing test | existing multi-element V&V tests |
| 025-REQ-007 | committed-state transaction | exact digest preservation on rollback | none | digest mutation or false convergence | state transaction contract |
| 025-REQ-030 | Code_Aster comparable history error | `<= 5e-3` | none | `>5e-3` or non-comparable | existing external runner, 64 checks |
| 025-REQ-004 | mesh/load-step trends | Owner-approved bounded observation; no universal claim | observed trend only | failed/non-finite trend or no Owner decision | G01 qualification report and Owner decision record |
| 025-REQ-007 | rollback/reference difference | Owner-approved bounded observation; diagnostic only | no universal band | failed reference or no Owner decision | G01 qualification report and Owner decision record |
