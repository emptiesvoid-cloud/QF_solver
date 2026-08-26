---
doc_id: DOC-NL-025-007
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 V&V plan

## Terminology

**Verification** asks whether the equations and algorithms are implemented
correctly. **External correlation** compares independent numerical solvers under
matched assumptions. **Validation** requires evidence that the model represents
physical reality. This release plans verification and bounded external
correlation; it does not claim general physical validation.

## Evidence pyramid

### V0 - Formula and constitutive verification

- J2 elastic, yield, plastic, unloading/reloading, reversal, shear, hydrostatic
  and non-proportional paths.
- Consistent tangent FD over elastic, near-yield and plastic states with a
  perturbation-size study.
- Kinematic/stress-measure unit checks.
- Contact projection/gap/local tangent checks.
- State transaction and serialization invariants.

### V1 - Element verification

- Patch/constant-state tests.
- Rigid-body translations and rotations.
- Distorted TET4/TET10/HEX8/HEX20 where in scope.
- Internal force as energy derivative and tangent as `d f_int / d u`.
- Contact contribution tangent and active-state consistency.

### V2 - Global algorithm verification

- Multi-element J2 redistribution.
- Full Newton convergence histories and rate.
- Cutback/retry/rollback and restart equivalence.
- Arc-length branch control.
- Open/close/recontact and finite sliding.
- Pairwise coupled-limit recovery.

### V3 - Analytical/semi-analytical benchmarks

- Bilinear elastoplastic bar.
- Euler column.
- Large-rotation cantilever or other published interpretable reference.
- Reduced shallow-arch limit-point path, followed by a FEM benchmark before
  any release-gate closure.
- Simple contact pressure/reaction cases.

### V4 - Bounded external solver correlation

Use Code_Aster first, CalculiX where formulations are comparable and Abaqus only
when available. Match geometry, mesh, material, BC, history, increments and
post-processing. Compare complete curves and fields, not one endpoint.

### V5 - Adversarial, coupled and regression evidence

- Deliberately failed increments and solvers.
- Degenerate/invalid elements, NaN/Inf and singular tangent.
- Coupled J2/geometric/contact paths.
- Full 0.2.4 non-regression and package/documentation gates.

## Studies required by capability

| Capability | Mesh study | Load/continuation study | Energy | Tangent FD | External curve | Failure injection |
|---|---:|---:|---:|---:|---:|---:|
| J2 multi-element | yes | yes | yes | yes | yes | yes |
| Geometric nonlinear | yes | yes | yes | yes | yes | yes |
| Buckling | yes | eigensolver sensitivity | n/a | geometric stiffness checks | yes | yes |
| Arc-length | yes | radius/direction/restart | yes | global augmented system | yes | yes |
| Frictionless contact | yes | load/penalty/active-set | contact work | yes | yes | yes |
| Pairwise coupling | yes | yes | yes | yes | yes | yes |
| Friction optional | yes | cycle/penalty | dissipation | yes | yes | yes |

## Newton behavior study

For every differentiable mandatory benchmark, store `||R_i||`, correction norm,
energy criterion, linear-solver diagnostics and accepted increment size. Compare
consistent and intentionally approximate tangents only in a controlled study;
Modified Newton remains non-production. Near the solution, assess the observed
rate without assuming exact quadratic convergence in nonsmooth contact/active-set
transitions.

## Evidence integrity

Every artifact records candidate SHA, environment, dependencies, command,
random seed if any, mesh digest, input digest, external solver version, metrics,
threshold source and gate. Generated evidence is never edited by hand.
