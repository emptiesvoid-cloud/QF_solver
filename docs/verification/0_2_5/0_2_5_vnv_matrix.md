---
doc_id: DOC-NL-025-008
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 V&V matrix

Rows marked `OBSERVED_INTERNAL` record exploratory evidence from the
incremental implementation. The G01 rows below are promoted to
`PASS_INTERNAL` only when the `g01_latest` manifest records the final clean
source SHA. `PASS_INTERNAL` or `PASS_EXTERNAL_CORRELATION_BOUNDED` describes
the evidence result; it does not by itself close a gate when an acceptance
band still requires Owner approval. `owner_accepted_experimental_bounded_use`
records an explicit Owner decision that accepts evidence only within the stated
domain. Element families marked SHOULD do not block release unless promoted.

| V&V ID | Scope | Model/path | Metrics | Reference | Status | Gate |
|---|---|---|---|---|---|---|
| VV-001 | J2 constitutive | elastic/yield/uniaxial | stress, alpha, tangent | analytical | PASS_INTERNAL | G01 |
| VV-002 | J2 constitutive | unload/reload/reversal cycles | full stress-strain path | analytical law | PASS_INTERNAL | G01 |
| VV-003 | J2 constitutive | shear/hydrostatic/non-proportional | yield, flow, PEEQ | invariants/independent calc | PASS_INTERNAL | G01 |
| VV-004 | J2 tangent | eight elastic/near-yield/plastic, cyclic and non-proportional states with FD-step sweep | max/RMS relative derivative error | centered FD | PASS_INTERNAL | G01 |
| VV-005 | state | true failed increment | state digests, retry result | small-step reference | PASS_INTERNAL | G01/G09 |
| VV-006 | J2 elements | common multi-element mesh, 4 families | F-u, reactions, VM, PEEQ, energy | converged mesh/external | PASS_INTERNAL | G01 |
| VV-007 | J2 load-step sensitivity | coarse/reference/refined on connected mesh | solution, PEEQ, dissipation and cost trends | step-sensitivity study | PASS_INTERNAL | G01 |
| VV-008 | objectivity | rigid translation/rotation and translation+rotation, four families | spurious strain/stress/force/energy, det(F) | exact invariant | PASS_INTERNAL | G02 |
| VV-009 | geometric element | TET4 TL | force/tangent/energy FD | numerical derivative | PASS_INTERNAL | G02 |
| VV-010 | geometric element | HEX8 | force/tangent/energy FD | numerical derivative | PASS_INTERNAL | G02 |
| VV-011 | geometric global | TET4/HEX8 large-rotation bounded dead-load path | load-displacement, reactions, energy, det(F), Newton residuals | internal bounded path; post-limit is G04 | owner_accepted_experimental_bounded_use | G02 |
| VV-012 | geometric distortion | TET4/HEX8 four-level pre-limit refinement | robustness, Jacobian, displacement, reaction, energy, stress/strain trends | bounded mesh-trend contract; Owner scope decision | owner_accepted_experimental_bounded_use | G02 |
| VV-013 | high-order geometric | TET10/HEX20 | common TL J2 residual/state/recovery smoke | numerical/external | OBSERVED_INTERNAL_RESEARCH | G02 |
| VV-014 | buckling | TET4 total-Lagrangian Euler column, four structured levels 16x4x4 -> 40x10x10 | critical factor, mode, Euler error, refinement change, bracket, det(F) | analytical Euler | PASS_INTERNAL | G03 |
| VV-015 | buckling | constrained 5-TET4 unit-block solid probe | critical factor, mode residual, mode normalization/MAC | Code_Aster 18.1.0 pinned execution | PASS_EXTERNAL_CORRELATION_BOUNDED | G03 |
| VV-016 | arc-length | reduced shallow-arch equilibrium `lambda = u - u^3` | lambda-u branch, limit point, equilibrium residual | analytical reduced-order reference | OBSERVED_INTERNAL_RESEARCH | G04 |
| VV-017 | arc-length | restart from intermediate checkpoint | endpoint displacement, load-factor continuation state | continuous arc-length run | OBSERVED_INTERNAL_RESEARCH | G04 |
| VV-018 | contact local | gap/projection/normal tangent | residual/tangent FD | analytical/FD | OBSERVED_INTERNAL_RESEARCH | G05 |
| VV-019 | contact global | block-plane open/close/recontact | reaction, gap, active set | analytical/external | PASS_EXTERNAL_CORRELATION_BOUNDED | G05 |
| VV-020 | contact sliding | bounded faceted/finite-sliding projection | path, penetration, reactions | internal bounded contract + compatible external contact histories | OBSERVED_INTERNAL_RESEARCH | G05/G10 |
| VV-021 | contact rollback | injected contact assembly failure with adaptive retry | rejection reason, retry increment, committed-step history | common transaction contract | OBSERVED_INTERNAL_RESEARCH | G05/G09 |
| VV-022 | coupled | J2 + geometry | F-u, VM, PEEQ, energy, tangent | approved model/external | BLOCKED OWNER DECISION | G06 |
| VV-023 | coupled | geometry + contact | load-gap-u, reactions, energy | external | PLANNED | G06/G10 |
| VV-024 | coupled SHOULD | J2 + geometry + contact | complete histories | external | PLANNED SHOULD | G06/G10 |
| VV-025 | friction optional | stick/slip/cycle | traction, slip, dissipation | analytical/external | PLANNED COULD | G07 |
| VV-026 | Newton | consistent tangent rate | residual histories, reduction ratios, observed-order estimates, iterations | expected local behavior | OBSERVED_INTERNAL | G01/G02/G06 |
| VV-027 | failures | full taxonomy matrix | reason, rollback, converged=false | contract | PASS_INTERNAL | G09 |
| VV-028 | regression | complete 0.2.4 + 0.2.5 suite | tests, skips, coverage, artifacts | frozen baseline | PLANNED | G11 |
| VV-029 | release | clean docs/build/smoke | hashes and imports | clean environment | PLANNED | G12 |
| VV-030 | J2 mesh refinement | regular block levels 1/2/4, four families | displacement, reactions, VM, PEEQ, energy, cost | internal trend study | PASS_INTERNAL | G01 |
| VV-031 | J2 cyclic path | load/unload/reversal/reload, four families | PEEQ, dissipation, residual, iterations | constitutive limitations | PASS_INTERNAL | G01 |
| VV-032 | Nonlinear phase timing | regular two-cell shared J2 TET4/HEX8 smoke | assembly, sparse linear solve, line-search wall time | reproducible benchmark telemetry | PASS_INTERNAL | G08 |
| VV-033 | J2 external multi-element | regular two-cell shared TET4/TET10/HEX8/HEX20 | UX, reaction, SXX, PEEQ histories | Code_Aster Docker | PASS_EXTERNAL_CORRELATION_BOUNDED | G01/G10 |
| VV-034 | J2 finite-kinematic candidate | TET4/TET10/HEX8/HEX20, `kinematics=total_lagrangian_j2` | objectivity, element tangent FD, residual and state recovery | internal research contract | OBSERVED_INTERNAL_RESEARCH | G02/G06 |
| VV-035 | Common contact contribution | TET4 + initial node-to-triangle penalty contact | sparse contact residual/tangent, unilateral activation, common Newton | internal research contract | OBSERVED_INTERNAL_RESEARCH | G05/G06 |
| VV-036 | J2 energy balance | connected two-element mesh, ten monotonic increments, four families | Wext, Ue, Dp, signed/relative imbalance, point dissipation | work-energy identity and non-negative dissipation | PASS_INTERNAL | G01 |
| VV-037 | J2 rollback adversarial | TET4 connected mesh, injected rejected trial, cutback/retry | state digest, clean displacement, retry log, final reference difference | fixed-step reference | PASS_INTERNAL | G01/G09 |
| VV-038 | Linear buckling bounded | homogeneous TET4/HEX8 preload with sparse generalized `eigsh(K, M=-Kg)` when positive definite, shift-invert `eigs` after a sparse bracket when indefinite, and diagnosed bracket fallback otherwise | critical factor, formulation, bracket/fallback reason, tangent nnz, preload residual, critical-mode residual | internal sparse contract | PASS_INTERNAL | G03 |
| VV-039 | Arc-length continuation | proportional nonlinear TET4 path to target factor | load-factor path, monotonicity, residual histories, endpoint comparison | fixed load-control path | OBSERVED_INTERNAL_RESEARCH | G04 |
| VV-040 | Common frictionless contact | TET4 penalty contact open/penetrating plus initial/updated common Newton | active set, sparse tangent, search mode, residual | unilateral contact contract | OBSERVED_INTERNAL_RESEARCH | G05/G06 |
| VV-041 | Coupled material/geometric path | connected two-element TET4 `total_lagrangian_j2` through common Newton | kinematics, residual history, PEEQ, iterations | common-driver contract | OBSERVED_INTERNAL_RESEARCH | G06 |
| VV-042 | Coupled geometric/contact path | connected two-element TET4 Total-Lagrangian plus initial penalty contact | contact mode, residual, displacement, iterations | common-driver contract | OBSERVED_INTERNAL_RESEARCH | G06 |
| VV-043 | Coupled triple path | connected two-element TET4 J2 + Total-Lagrangian + updated penalty contact | shared driver, residual/tangent path, contact search mode, PEEQ | common-driver contract | OBSERVED_INTERNAL_RESEARCH | G06 |
| VV-044 | Nonlinear path profiling | TET4 load-control, arc-length, contact and coupled paths | elapsed time, phase timings, DOF, Newton iterations, Python peak allocation, RSS when available | reproducible benchmark telemetry | PASS_INTERNAL | G08 |
| VV-045 | External unilateral contact oracle | scalar spring-supported point, compression and separation branches | QF/Code_Aster displacement, gap closure/opening, active-set branch | Code_Aster 18.1.0 Docker digest | PASS_EXTERNAL_CORRELATION_BOUNDED | G05/G10 |
| VV-046 | External TET4-TL buckling | four structured TET4 column levels | QF/CalculiX critical factor, Euler error, homogeneous stress patch | CalculiX 2.20 Docker campaign | PASS_EXTERNAL_CORRELATION_BOUNDED | G03/G10 |
| VV-070 | External solid-family buckling probe | shared one-cell TET4/TET10/HEX8/HEX20 decks, first factor | factor, relative difference, execution diagnostics | CalculiX 2.20 Docker campaign | BLOCKED_EXTERNAL_TOOL | G03/G10 |
| VV-071 | Bounded finite-sliding projection | common penalty path with updated search and slave projection outside the current triangle | clamped barycentrics, gap, active contact, sparse tangent and serialized projection mode | internal contact contract | OBSERVED_INTERNAL_RESEARCH | G05 |
| VV-047 | Contact recontact path | TET4 load path open/close/reopen/reclose | active-set sequence, gaps, residual per load step | common penalty driver | OBSERVED_INTERNAL_RESEARCH | G05/G09 |
| VV-053 | Contact penalty sensitivity | TET4 node-to-triangle penalty sweep `1e2..1e6` | convergence, penetration trend, contact tangent nnz, residual | local penalty asymptotic trend | OBSERVED_INTERNAL_RESEARCH | G05/G08 |
| VV-055 | Multi-face contact search | two-face planar master surface with two compatible slave positions | selected face index, face count, gap, active set | bounded geometry-search contract | OBSERVED_INTERNAL_RESEARCH | G05 |
| VV-056 | Updated-contact face crossing | two connected TET4 elements with tangential/normal load and two-face master surface | face sequence, switch count, gaps, residual history, common-driver status | bounded updated-search contract | OBSERVED_INTERNAL_RESEARCH | G05/G06 |
| VV-057 | Large-deflection geometric smoke | unit-block TET4/HEX8 transverse dead load | end-line angle, detF, strain energy, residual history | internal geometric research contract | PASS_INTERNAL_RESEARCH | G02 |
| VV-066 | Large-deflection mesh sensitivity | regular TET4/HEX8 block levels 1/2/3/4 at pre-limit load scale 0.2 | displacement, end-line angle, detF, energy, stress/strain, residual and Newton cost | bounded internal geometric mesh-trend contract | PASS_INTERNAL_RESEARCH | G02 |
| VV-067 | High-order geometric mesh sensitivity | regular TET10/HEX20 block levels 1/2 at load scale 0.25 | displacement, detF, energy, residual and Newton cost | internal low-load geometric mesh-trend contract | OBSERVED_INTERNAL_RESEARCH | G02 |
| VV-058 | Buckling mesh sensitivity | assembled homogeneous levels 1/2 on TET4/TET10/HEX8/HEX20 | critical factor, bracket, DDL, tangent nnz, preload residual, critical-mode residual, coarse/medium trend | internal sparse mesh-trend contract | OBSERVED_INTERNAL_RESEARCH | G03 |
| VV-059 | Multi-family J2/geometric coupling | connected two-element TET4/TET10/HEX8/HEX20 meshes | shared driver, kinematics, residual, iterations, PEEQ | internal common-driver contract | OBSERVED_INTERNAL_RESEARCH | G02/G06 |
| VV-060 | FEM arc-length path | imperfect TET4 total-Lagrangian cantilever, 24 sparse continuation steps | load-factor path, residual, detF, tip response | existing sparse FEM arc-length contract | OBSERVED_INTERNAL_RESEARCH | G04 |
| VV-061 | Nonlinear component profiling | regular two-cell J2 load-control, TET4/TET10/HEX8/HEX20 | element setup/kernel/scatter, sparse conversion, solve time, nnz, cache hits/misses, RSS/allocation observations | reproducible phase telemetry | PASS_INTERNAL | G08 |
| VV-062 | Multi-family J2/geometric/contact coupling | one regular block per TET4/TET10/HEX8/HEX20 with active small-strain J2 and updated penalty contact crossing from open to active | shared driver, active-step transition, initial/final gap, penetration, PEEQ, residual and Newton iterations | bounded common-driver contact contract | OBSERVED_INTERNAL_RESEARCH | G05/G06 |
| VV-063 | Finite-kinematic limit recovery | common small-load TET4/TET10/HEX8/HEX20 comparison between small-strain and `total_lagrangian_j2` | displacement recovery, residual, zero plastic strain | small-strain regime consistency | OBSERVED_INTERNAL_RESEARCH | G02/G06 |
| VV-064 | Finite-kinematic arc-length | common nonlinear driver on homogeneous TET4/TET10/HEX8/HEX20 `total_lagrangian_j2` paths to signed load factor 0.5 with bounded adaptive radius | load-factor path, final PEEQ, residual history, step count, radius controls and common-driver contract | internal bounded monotone continuation contract | OBSERVED_INTERNAL_RESEARCH | G04/G06 |
| VV-065 | Geometric/contact composition | Total-Lagrangian elastic TET4 plus fixed master patch through the common sparse penalty contribution | active contact, final gap, penetration, residual, detF, strain energy | bounded geometric/contact composition contract | OBSERVED_INTERNAL_RESEARCH | G02/G05/G06 |
| VV-048 | High-order geometric path | TET10/HEX20 common TL adapter | residual, detF, energy, state recovery and tangent contract | internal bounded research contract | OBSERVED_INTERNAL_RESEARCH | G02 |
| VV-049 | High-order linear buckling | homogeneous TET10/HEX20 preload and sparse generalized/fallback tangent path, including indefinite-mass shift-invert refinement | critical factor, formulation, fallback reason, bracket width, tangent nnz, preload residual | internal sparse research contract | OBSERVED_INTERNAL_RESEARCH | G03 |
| VV-050 | Path failure taxonomy | capped arc-length continuation and unbracketed buckling factor | reason, converged flag, solver diagnostics, no partial success | structured failure contract | PASS_INTERNAL | G09 |
| VV-051 | Multi-step rollback | injected failure after one accepted adaptive increment | committed prefix, cutback factor, retry path, final convergence | fixed-step/adaptive transaction contract | PASS_INTERNAL | G01/G09 |
| VV-054 | Contact penetration failure | configured penalty penetration limit exceeded on a trial | typed reason, converged=false, penetration diagnostics | failure contract | PASS_INTERNAL | G05/G09 |
| VV-068 | Contact penetration cutback/retry | regular multi-element TET4 contact guard with adaptive load control | typed guard failures, committed factors, retry log, final displacement/reaction/gap versus fine-step reference | fixed small-step reference | PASS_INTERNAL | G05/G09 |
| VV-052 | Arc-length limit point | reduced shallow-arch branch through the analytical turning point | branch turn, reference curve error, residual history | analytical reduced-order reference | OBSERVED_INTERNAL_RESEARCH | G04 |
| VV-069 | State transaction corruption guard | committed material/contact state mutated during a detached trial | typed `STATE_CORRUPTION`, before/after digests, no silent rollback | transaction invariant | PASS_INTERNAL | G01/G09 |
| VV-072 | Arc-length retry telemetry | injected failed continuation trial followed by radius cutback/retry | failure reason, failed radius, retry radius, failure diagnostics, rollback flag and retry result | common transaction and continuation contract | PASS_INTERNAL | G04/G09 |
| VV-073 | Non-finite correction classification | sparse correction NaN, +Inf, -Inf and mixed payload policy | deterministic reason, converged=false, structured Full Newton diagnostics | non-finite failure contract | PASS_INTERNAL | G09 |
| VV-074 | Common-driver FEM snap-through | two-element TET4 total-Lagrangian model with signed arc-length continuation through a load-factor turning point | signed load-factor path, control displacement, predictor/branch diagnostics, residual, det(F) | bounded internal branch-tracking contract | OBSERVED_INTERNAL_RESEARCH | G04 |
| VV-075 | Common-driver FEM arc-length restart | restart from the checkpoint immediately before the observed turning point | continuation suffix, restart metadata, endpoint displacement and state equality | continuous-run suffix comparison | OBSERVED_INTERNAL_RESEARCH | G04 |
| VV-076 | Common-driver FEM arc-length rollback | controlled Newton failure after two corrections near the turning point | failure classification, radius cutback, clean retry state, committed step history | common transaction/retry contract | OBSERVED_INTERNAL_RESEARCH | G04/G09 |
| VV-077 | Contact slave patch | two slave nodes against a two-face triangulated master surface | round-trip schema, active contacts, selected facets, sparse tangent | bounded node-patch contact contract | OBSERVED_INTERNAL_RESEARCH | G05 |
| VV-078 | Contact three-facet sliding | one slave node traversing three connected master facets | face sequence, facet switches, gap, active state, sparse tangent | bounded updated-search contract | OBSERVED_INTERNAL_RESEARCH | G05 |
| VV-079 | Contact updated normals | deformed master facet under updated finite-sliding search | finite unit normal, updated orientation, active contact | current-configuration geometry contract | OBSERVED_INTERNAL_RESEARCH | G05 |
| VV-080 | Contact facet-transition rollback | failed trial after a facet transition, followed by replay and retry | failure reason, committed facet, rollback facet, retry facet, deterministic force | common contact transaction contract | OBSERVED_INTERNAL_RESEARCH | G05/G09 |
| VV-081 | Geometric small-strain limit | elastic Total-Lagrangian versus small-strain static, TET4/TET10/HEX8/HEX20 at 1e-2/1e-3/1e-4 load factors | relative displacement error and positive det(F) trend | finite-kinematic limit consistency | PASS_INTERNAL | G02 |
| VV-082 | Geometric external correlation | TET4/HEX8, twelve-step Green-Lagrange Code_Aster ramp with initial state | full tip displacement, reactions, SIEF_ELGA stress and EPSI_ELGA strain histories | pinned Code_Aster 18.1 Docker image | PASS_EXTERNAL_CORRELATION_BOUNDED | G02/G10 |

`VV-033` uses the explicit QF parameter
`tet10_nonlinear_quadrature=code_aster_5` for TET10. This matches the five
`ELGA` values per `TETRA10` element exposed by the pinned Code_Aster run. The
legacy Hammer four-point rule remains the default for existing models. The
bounded external row is therefore convention-matched, but it does not alone
close G01/G10 because those gates also require energy, mesh, cyclic, rollback,
threshold and final-SHA evidence.

## G04 Owner audit outcome

The controlled G04 audit is archived under `results/vnv_0_2_5/g04_latest/`.
`VV-074`, `VV-075` and `VV-076` remain internal research evidence: the
common-driver FEM path crosses a signed load-factor turn, restart reproduces
the continuation suffix, and rollback records a radius cutback and clean retry.
The required arc-length mesh study is absent.

The historical monotone Code_Aster path was diagnosed as a configuration
mismatch, not a numerical deviation: it applied the opposite physical load and
used mean crown displacement instead of QF's apex control quantity. The
corrected pinned replay reproduces a single turning branch, with maximum
load-factor difference `4.8719e-07` when parameterized by apex displacement.
The detailed bounded diagnostic is `DOC-NL-025-030`.

These observations do not satisfy G04 closure. The external discrepancy is
resolved, but no exact published FEM reference and no required four-level
arc-length mesh study are available. No arc-length production claim is
promoted.

## Controlled G02 evidence

The dedicated controlled pack is archived under
`results/vnv_0_2_5/g02_latest/`. Its `summary.json`, `report.md`,
`gate_decision.json` and `evidence_manifest.json` record the same source SHA,
`dirty=false`, UTC timestamp, command, environment and SHA-256 digests. It
contains four-family objectivity, sparse tangent finite-difference, bounded
TET4/HEX8 large-rotation, four-level pre-limit mesh, four-family small-strain
limit and pinned Code_Aster TET4/HEX8 correlation evidence.

The numerical source pack deliberately reports `025-G02 = OPEN`: it is the
immutable pre-Owner evidence record. The Owner decision in
`0_2_5_g02_owner_review.md` closes G02 for the bounded elastic TET4/HEX8 scope
only, with `APPROVED_BOUNDED_REFINEMENT`. The Code_Aster correlation remains
bounded numerical code-to-code evidence, not physical validation. This decision
does not qualify `total_lagrangian_j2`, high-order plastic finite-kinematic
paths, post-limit load control, buckling, arc-length, contact or coupling, and
it does not alter G03-G06.

## Historical and exploratory evidence

The controlled G09 evidence is archived under
`results/vnv_0_2_5/g09_latest/`. Its manifest is authoritative for the exact
candidate SHA and reports `dirty=false`; the report contains 22 cases, all
passed. In particular, the correction path now distinguishes NaN from both
signs of Inf, and mixed arrays give `INF_DETECTED` deterministically when an
infinite value is present. This closure is limited to failure handling and
does not alter the status of functional gates.

The observed rows are backed by the following implementation and test
artifacts. They remain provisional until regenerated and attached to a final
release SHA:

- J2 constitutive, tangent and transaction paths:
  `tests/unit/test_nonlinear_constitutive_vv.py`,
  `tests/unit/test_robustness_tangent_fd.py`,
  `tests/unit/test_nonlinear_state_transaction_contract.py`;
- four-family connected mesh and load-step sensitivity:
  `tests/unit/test_nonlinear_multielement.py`,
  `tests/unit/test_nonlinear_load_step_sensitivity.py`;
- four-family mesh refinement and cyclic paths:
  `tests/unit/test_nonlinear_multielement.py`,
  `tests/unit/test_nonlinear_cyclic.py`,
  `src/solveur/verification/robustness_nonlinear_solids.py`;
- four-family energy balance:
  `tests/unit/test_nonlinear_multielement.py`,
  `src/solveur/verification/robustness_nonlinear_solids.py`;
- adversarial rollback and fixed-step comparison:
  `tests/unit/test_nonlinear_multielement.py`,
  `src/solveur/verification/robustness_nonlinear_solids.py`;
- bounded buckling, arc-length and common contact observations:
  `tests/unit/test_nonlinear_multielement.py`,
  `src/solveur/verification/robustness_nonlinear_solids.py`;
- finite-kinematic arc-length bounded four-family path with adaptive-radius
  contract:
  `tests/unit/test_nonlinear_multielement.py`,
  `tests/unit/test_total_lagrangian_j2.py`,
  `src/solveur/core/nonlinear.py`,
  `src/solveur/core/nonlinear_controls.py`,
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/finite_kinematic_arc_length.png`,
  `results/benchmark_0_2_5/arc_length_finite_kinematic_latest.json`;
- targeted performance replays for the bounded geometric, contact and coupled
  paths:
  `results/benchmark_0_2_5/geometric_static_all_families_latest.json`,
  `results/benchmark_0_2_5/contact_tet4_latest.json`,
  `results/benchmark_0_2_5/coupled_tet4_latest.json`; these are single-run
  dirty-worktree observations and remain non-qualifying for G02/G05/G06/G08;
- geometric Total-Lagrangian plus penalty contact composition:
  `tests/unit/test_nonlinear_multielement.py`,
  `src/solveur/core/geometric_nonlinear.py`,
  `src/solveur/mesh/contact_validation.py`,
  `src/solveur/verification/robustness_nonlinear_solids.py`;
- reduced shallow-arch arc-length branch-following evidence:
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`,
  `results/vnv_0_2_5/robustness_high_order_latest/shallow_arch_arc_length.png`;
- bounded analytical Euler buckling evidence:
  `results/vnv_0_2_5/robustness_high_order_latest/euler_buckling/summary.json`,
  `results/vnv_0_2_5/robustness_high_order_latest/euler_buckling/report.md`,
  `src/solveur/verification/tet4_total_lagrangian_buckling.py`;
- high-order geometric and buckling research observations:
  `tests/unit/test_geometric_nonlinear_public.py`,
  `tests/unit/test_linear_buckling.py`,
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_geometric_latest/summary.json`,
  `results/vnv_0_2_5/robustness_high_order_buckling_latest/summary.json`;
- large-deflection geometric smoke `VV-057`:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`;
- large-deflection mesh sensitivity `VV-066`:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`;
- high-order low-load mesh sensitivity `VV-067`:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`;
- assembled buckling mesh sensitivity `VV-058`:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`;
  the sparse buckling rows now also record the normalized critical-mode
  residual at the reported factor; this is a diagnostic, not a qualification
  threshold or a closure of `025-G03`.
- multi-family J2/geometric coupling `VV-059`:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`;
- FEM arc-length path `VV-060`:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`,
  `src/solveur/verification/total_lagrangian_structural.py`;
- component-level nonlinear profiling `VV-061`:
  `src/solveur/core/nonlinear_assembly.py`,
  `src/solveur/core/nonlinear_controls.py`,
  `scripts/benchmark_nonlinear_025.py`,
  `results/benchmark_0_2_5/nonlinear_load_control_component_profile_latest.json`;
- reusable nonlinear assembly-plan contract and replay extension of `VV-061`:
  `src/solveur/core/nonlinear_assembly.py`,
  `src/solveur/core/nonlinear.py`,
  `tests/unit/test_nonlinear_assembly_plan.py`,
  `results/benchmark_0_2_5/nonlinear_load_control_cache_latest.json`;
- Newton residual-rate characterization `VV-026`:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/verification/test_robustness_newton_rate_vnv.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`;
- four-family finite-kinematic contact composition `VV-062`:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`;
- finite-kinematic small-strain limit recovery `VV-063`:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`;
- aggregated adversarial failure contract `VV-027`, `VV-050`, `VV-051` and
  `VV-054`:
  `src/solveur/verification/nonlinear_failure_campaign.py`,
  `tests/unit/test_nonlinear_failure_campaign.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`;
- bounded coupling composition observations (J2/geometric/contact):
  `tests/unit/test_nonlinear_multielement.py`,
  `src/solveur/verification/robustness_nonlinear_solids.py`;
- repeated all-family performance characterization:
  `scripts/benchmark_nonlinear_025.py`,
  `results/benchmark_0_2_5/nonlinear_load_control_all_families_repeats2_latest.json`;
- bounded external unilateral contact oracle:
  `results/vnv_0_2_5/contact_code_aster_liaison_unil/summary.json`,
  `results/vnv_0_2_5/contact_code_aster_liaison_unil/report.md`,
  `tests/verification/test_code_aster_contact_vnv.py`;
- bounded external TET4-TL stress/buckling campaign:
  `results/vnv_0_2_5/calculix_tl_structural/summary.json`,
  `results/vnv_0_2_5/calculix_tl_structural/report.md`,
  `qualification/vnv/external/calculix_tl_structural/reference/summary.json`;
- external solid-family buckling probe `VV-070`:
  `src/solveur/verification/calculix_buckling_025.py`,
  `scripts/run_calculix_buckling_025.py`,
  `tests/unit/test_calculix_buckling_025.py`,
  `results/vnv_0_2_5/calculix_buckling_solid_families_mode1_recorded/summary.json`;
  the deck applies the fixed boundary set, requests only the first factor and
  bounds the Lanczos subspace to the free-equation count. The current
  CalculiX replay records relative differences of about 24.6 % (TET4), 45.1 %
  (TET10) and 13.4 % (HEX8), plus a native C3D20 execution stop. These are
  explicit external blockers, not PASS evidence and do not close G03/G10.
- common contact recontact path:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_contact_composition.py`,
  `tmp/vnv_0_2_5_recontact_latest/summary.json`;
- updated-contact face crossing `VV-056`:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_contact_composition.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`;
- bounded finite-sliding projection `VV-071`:
  `src/solveur/contact/entities.py`, `src/solveur/contact/solver.py`,
  `src/solveur/mesh/contact_validation.py`,
  `src/solveur/verification/robustness_nonlinear_solids.py` and
  `tests/unit/test_contact_finite_sliding.py`; the opt-in path is restricted
  to updated frictionless penalty contact, records a deterministic two-face
  clamped-projection crossing, and remains non-qualifying for a general
  surface-to-surface claim. The common Newton step now also exposes the
  finite-sliding flag, clamped-projection flags, closest distances and the
  exact/bounded projection mode in its serialized increment diagnostics;
- local penalty contact tangent finite-difference contract:
  `src/solveur/verification/robustness_nonlinear_solids.py`,
  `tests/unit/test_nonlinear_multielement.py`,
  `results/vnv_0_2_5/robustness_high_order_latest/summary.json`; the fixed-active
  node-to-triangle tangent is compared with centered finite differences over
  three perturbation sizes. The result remains internal research evidence and
  excludes active-set transitions;
- minimum-increment failure contract:
  `tests/unit/test_nonlinear_failure_campaign.py`,
  `src/solveur/verification/nonlinear_failure_campaign.py`;
- sparse backend failure classification:
  `tests/unit/test_nonlinear_failure_modes.py` verifies that a runtime failure
  from the sparse factorization backend is reported as `LINEAR_SOLVER_FAILURE`,
  distinct from `SINGULAR_TANGENT`;
- adversarial campaign aggregation:
  `tests/unit/test_nonlinear_failure_campaign.py` verifies the same typed
  backend failure in the campaign report, alongside the injected contact
  cutback/rollback case;
- contact assembly failure with adaptive cutback/retry:
  `tests/unit/test_nonlinear_failure_campaign.py`,
  `src/solveur/verification/nonlinear_failure_campaign.py`;
- real contact penetration guard cutback/retry `VV-068`:
  `tests/unit/test_nonlinear_failure_campaign.py`,
  `src/solveur/verification/nonlinear_failure_campaign.py`; the guarded
  multi-element TET4 result follows `[0.5, 0.75, 1.0]` after two typed
  penetration failures and matches an eight-step reference within the recorded
  displacement/reaction/gap limits;
- committed-state corruption guard `VV-069`:
  `src/solveur/core/material_state.py` checks a digest captured at
  `begin_trial()` before either commit or rollback, and raises a structured
  `STATE_CORRUPTION` error if the committed object was mutated in place;
  `tests/unit/test_nonlinear_state_transaction_contract.py` covers both the
  generic contact-style transaction and the material-state session;
- multi-step adaptive rollback after a previously committed increment:
  `tests/unit/test_nonlinear_failure_campaign.py`,
  `src/solveur/verification/nonlinear_failure_campaign.py`;
- arc-length checkpoint/restart contract:
  `tests/unit/test_nonlinear_checkpoint.py`,
  `src/solveur/core/nonlinear_checkpoint.py`,
  `src/solveur/io/nonlinear_checkpoint.py`;
- Total-Lagrangian objectivity/tangent:
  `tests/unit/test_total_lagrangian_hex8.py`,
  `tests/unit/test_geometric_nonlinear_public.py`;
- high-order Total-Lagrangian J2 integration and post-processing:
  `tests/unit/test_total_lagrangian_j2.py` covers TET10 and HEX20 through the
  common nonlinear driver, including residual, material state and
  integration-point recovery. The bounded finite-kinematic campaign now also
  records TET10 and HEX20 rows with rigid-rotation and tangent-FD checks. This
  is an internal research observation only. The controlled campaign replay is
  archived at `results/vnv_0_2_5/robustness_high_order_latest/summary.json` and
  remains non-qualifying for G02/G06.
- failure contracts and sparse continuation:
  `tests/unit/test_nonlinear_failure_modes.py`,
  `tests/unit/test_nonlinear_iteration_sparse.py`,
  `tests/unit/test_nonlinear_failure_campaign.py`,
  `src/solveur/verification/nonlinear_failure_campaign.py`;
- internal campaign runner:
  `src/solveur/verification/robustness_nonlinear_solids.py`.

## G03 controlled closure update

The earlier buckling observations in this document are historical and are
superseded for G03 by the final bounded evidence in
`results/vnv_0_2_5/g03_euler_final/` and
`results/vnv_0_2_5/g03_final/`. The current qualified source is
`85c75d06955976251dd54ad782f57f1eb5a7f8f4`; the source worktree was clean when
the evidence was generated. The corrected path isolates the initial-stress
geometric tangent from the material tangent. It passes the four-level Euler
study, the exact TET4 Code_Aster factor/mode probe and the buckling failure
contract. G03 is therefore `PASS` for its bounded TET4-first-instability
scope. TET10/HEX8/HEX20 external buckling, post-buckling and
imperfection-sensitive collapse remain research/unqualified, and CalculiX
remains a SHOULD comparison with retained negative high-order evidence.
