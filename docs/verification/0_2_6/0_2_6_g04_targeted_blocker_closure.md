# 026-G04 targeted blocker closure

This artifact records the internal blocker closure executed from source SHA
`171bc93803690fb70b8831f17db81f60f4401ea6`. It does not close G04 and does
not alter the maturity of any element or analysis route.

## Analytical declarations

The 20 already configured analytical cases remain PASS. The 30 previously
declared but unconfigured analytical records were reviewed individually and
classified `NOT_APPLICABLE` under `TOL-026-ANALYTICAL-001`: the available
`constrained_free_dof` oracle requires a one-element isotropic continuum model
with one free-node UX load. Multi-element meshes, mixed-constraint static
models, shells, BEAM2, and orthotropic material cases do not satisfy those
preconditions. No missing oracle was converted into PASS.

## New mesh policy evidence

`qualification/0_2_6/g04_mesh_refinement_study.json` declares the observable
`q` (mean end-face UX), dimensional `q_ref = F_total*L/(E*A)`, four compatible
HEX8 levels, and `G04-POL-003` before execution. The measured q values are:

| level | q (m) |
|---:|---:|
| 1 | 4.333333333333333e-09 |
| 2 | 4.486791757449624e-09 |
| 4 | 4.551780487472014e-09 |
| 8 | 4.571463783673658e-09 |

The final adjacent change is `0.004133492202345242`, hence PASS against the
Owner threshold `<= 0.01`. The dimensional reference is recorded as a scale;
the study does not claim an exact three-dimensional end-effect solution.

## Invalid inputs and route boundaries

Six dedicated cases reject deterministically on two executions: invalid
connectivity, incomplete material, insufficient supports, incoherent active
DOF, degenerate TET4 geometry, and non-positive BEAM2 area. All are expected
failures with explicit stable error classes/messages. The prior RBE2-plus-spring
case has no DISCRETE element, so `RBE2 = DIAGNOSTIC_ONLY` and
`DISCRETE = NOT_APPLICABLE`.

Code_Aster and CalculiX are both `SKIPPED_UNAVAILABLE`; no external PASS is
claimed. Therefore the resulting proposal is `PASS_WITH_LIMITATIONS`, with
official G04 closeout still deferred to Owner review.
