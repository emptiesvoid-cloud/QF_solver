---
doc_id: DOC-029-WP05-AB-IDENTITIES-001
revision: 0.1
status: owner_review_required
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP05-A/B — TET10 and HEX20 high-order TL identity V&V

**Campaign status:** `FORMAL_PASS_AFTER_GOVERNING_INTEGRATION`

**Formal WP05-A points:** `1/1`

**Formal WP05-B points:** `1/1`

**WP05 total:** `2/5`

**Validated release total:** `45/100`
**Source tested:** `1acd25e33fa0750a2189426e71b112117779365c`

This record is the bounded WP05-A/B prequalification campaign requested after
the [WP05 preparation audit](wp05-high-order-geometric-readiness.md).  It
records identity evidence only.  It does not close WP05-A or WP05-B, change
the capability registry maturity, or override the Owner-approved governance
blocker: formal WP05 qualification remains pending WP04 closure.

## Bounded scope

The tested domain is one homogeneous high-order family at a time, one
isotropic three-dimensional `SolidMaterial`, straight-sided valid reference
geometry, Green--Lagrange kinematics, Saint-Venant--Kirchhoff elasticity, and
nodal dead loads for the public geometric-static smoke.  The public route is
`geometric_nonlinear_static`; no contact, plasticity, distributed load, mixed
mesh, mixed material, external solver, or maturity claim is included.

The route is the existing path:

```text
solve_model
  -> AnalysisRouter.solve
  -> GeometricNonlinearStaticSolver
  -> build_total_lagrangian_assembly
  -> TotalLagrangianHighOrderAssembly
  -> TotalLagrangianJ2Tet10Element / TotalLagrangianJ2Hex20Element
  -> shared Green-Lagrange/StVK kernel
```

The historical `J2` class name is retained by the implementation, but this
bounded identity campaign uses the elastic `SolidMaterial` response.  No
production source or element formulation was changed.

## Frozen protocol and oracles

The following criteria were frozen before the identity tests ran:

| Identity | Criterion |
|---|---:|
| Objectivity, scaled energy | `<= 1e-12` |
| Objectivity, scaled internal-force norm | `<= 1e-11` |
| Affine patch, relative error | `<= 1e-10` |
| Affine patch, absolute error | `<= 1e-12` |
| Energy gradient | `<= 1e-7` relative |
| Tangent, full sampled Frobenius discrepancy | `<= 1e-6` relative |
| Tangent, maximum selected column discrepancy | `<= 5e-6` relative |
| Tangent symmetry | `<= 1e-12` relative |
| Small-displacement linear-limit displacement | `<= 1e-4` relative |
| Small-displacement linear-limit reaction | `<= 1e-4` relative |

The central-difference step is prospective and common to both families:
`h = eps**(1/3) * max(1, ||u||_inf)`, which evaluates to
`6.055454452393339e-06` for the declared affine fixture.  It was not selected
from an observed error.

The affine oracle is independent of the production response call:

```text
E_GL = 0.5 * (F.T @ F - I)
strain = [E11, E22, E33, 2 E12, 2 E23, 2 E13]
stress = C_isotropic @ strain
energy_density = 0.5 * strain @ stress
```

The frozen nontrivial deformation is

```text
F = [[1.04, 0.03, 0.00],
     [0.00, 0.98, 0.02],
     [0.00, 0.00, 1.01]]
```

Objectivity uses two proper finite Rodrigues rotations, not an infinitesimal
rotation: angles `0.20` and `-0.47` radians about axes `(0,0,1)` and
`(1,2,3)`.  The canonical material has `E=1`, so the declared unit scaling is
`max(E*reference_volume, 1) = 1` for both force/energy assertions.

## WP05-A — TET10 results

| Check | Result | Measured value | Frozen limit |
|---|---|---:|---:|
| Objectivity, maximum scaled energy over two rotations | `PASS` | `1.3565042920465786e-33` | `1e-12` |
| Objectivity, maximum scaled force norm | `PASS` | `4.5982901859622505e-17` | `1e-11` |
| Affine Green--Lagrange strain | `PASS` | `8.446007818039625e-17` relative | `1e-10` |
| Affine second-Piola stress | `PASS` | `1.3752230241763959e-16` relative | `1e-10` |
| Affine energy | `PASS` | `2.2926875000000042e-04` | reference `2.2926875000000040e-04` |
| Affine energy relative error | `PASS` | `1.18223937244555e-16` | `1e-10` |
| Internal force = energy gradient | `PASS` | `4.697706350207602e-09` relative | `1e-7` |
| Tangent finite-difference Frobenius | `PASS` | `2.43364613829268e-10` relative | `1e-6` |
| Tangent maximum sampled column | `PASS` | `3.2308277341215453e-10` relative | `5e-6` |
| Tangent symmetry | `PASS` | `0.0` | `1e-12` |
| Small-limit displacement | `PASS` | `9.454881526882126e-06` relative | `1e-4` |
| Small-limit reaction | `PASS` | `8.064907277828423e-06` relative | `1e-4` |

The tangent difference uses all 30 columns for the Frobenius value and
explicitly samples both corner DOFs `[0,1,2]` and midside DOFs `[12,13,14]`
for the maximum-column criterion.

The Gmsh-to-internal ordering regression passed.  A deliberately orientation-
reversed Gmsh TET10 cell was repaired to internal connectivity
`(0,1,2,3,4,5,6,7,8,9)` with one recorded orientation repair.  The expected
last-edge remap is therefore exercised as `(0,1,2,3,4,5,6,7,9,8)` at the
import boundary; no remap was changed.

**TET10 status:** `PASS_CANDIDATE_PENDING_WP04` for the tested identity scope;
not formally closed.

## WP05-B — HEX20 results

| Check | Result | Measured value | Frozen limit |
|---|---|---:|---:|
| Objectivity, maximum scaled energy over two rotations | `PASS` | `1.706667497213657e-32` | `1e-12` |
| Objectivity, maximum scaled force norm | `PASS` | `9.991149900296587e-17` | `1e-11` |
| Affine Green--Lagrange strain | `PASS` | `1.4957846974277547e-16` relative | `1e-10` |
| Affine second-Piola stress | `PASS` | `1.819774560246784e-16` relative | `1e-10` |
| Affine energy | `PASS` | `1.3756125000000024e-03` | reference `1.3756125000000024e-03` |
| Affine energy relative error | `PASS` | `0.0` | `1e-10` |
| Internal force = energy gradient | `PASS` | `9.310246079067896e-10` relative | `1e-7` |
| Tangent finite-difference Frobenius | `PASS` | `6.549800660920467e-11` relative | `1e-6` |
| Tangent maximum sampled column | `PASS` | `8.389251707149347e-11` relative | `5e-6` |
| Tangent symmetry | `PASS` | `0.0` | `1e-12` |
| Small-limit displacement | `PASS` | `1.9428760466840632e-07` relative | `1e-4` |
| Small-limit reaction | `PASS` | `2.69184150689822e-08` relative | `1e-4` |
| Integration-point Jacobians | `PASS` | `det(J)=0.125` at all 27 points | finite and positive |

The tangent difference uses all 60 columns and samples both corner DOFs
`[0,1,2]` and midside DOFs `[24,25,26]`.  HEX20 retains full 3 x 3 x 3
27-point Gauss integration.  No reduced-integration or hourglass claim is
made.

**HEX20 status:** `PASS_CANDIDATE_PENDING_WP04` for the tested identity scope;
not formally closed.

## Quadrature sensitivity and quality controls

For the straight-sided TET10 affine fixture, the current default Hammer-4
rule and the explicit diagnostic Code_Aster-5 rule gave a relative energy
difference of `3.546718117336649e-16`.  The rules remain distinct (4 versus 5
points), and the default was not changed based on this result.  The result is
only a bounded straight-geometry sensitivity observation.

The following negative controls passed with deterministic explicit rejection:

| Family | Control | Expected behavior | Result |
|---|---|---|---|
| TET10 | inverted reference orientation | reject with invalid reference orientation/volume | `PASS` |
| TET10 | non-finite reference coordinate | reject finite-node validation | `PASS` |
| HEX20 | nonpositive integration-point Jacobian | reject with invalid HEX20 Jacobian | `PASS` |
| HEX20 | non-finite reference coordinate | reject finite-node validation | `PASS` |

The future issue `CURVED_TET10_NONLINEAR_QUADRATURE_VV` remains open.  The
linear TET10 path has a curved-geometry sampled/lattice-quality strategy, but
the high-order TL path uses the selected nonlinear rule and does not inherit
that linear diagnostic automatically.  No curved-TET10 TL claim is made.

## Targeted validation

The new controlled fixtures and baseline tests report:

```text
python -m pytest -q \
  tests/verification/test_wp05a_tet10_high_order_identity.py \
  tests/verification/test_wp05b_hex20_high_order_identity.py

15 passed
```

Existing TET10/HEX20 unit tests, the public geometric-nonlinear high-order
route test, and relevant importer/order tests were also retained in the
validation set.  The new fixture helpers pass Ruff, mypy with the runtime
Python version (`--python-version 3.13`), and `compileall`.

No full test suite was run.  No external solver was invoked.  No numerical
threshold was retuned after observing a result.

## Formal decision boundary

The two families have finite, reproducible identity evidence for this exact
bounded fixture and pass every frozen check.  This supports
formal bounded identity closure for WP05-A/B. Remaining qualification
work includes high-order structural/refinement evidence, curved/distorted
geometry behavior, independent Owner policy adoption, and any externally
comparable evidence that the Owner later requires.  TET10/HEX20 code
availability, identity PASS, and this candidate record do not generalize to
all materials, loads, meshes, or nonlinear regimes.

**Next step:** Owner review before WP05-C/D structural execution. This result
does not award the three structural/cross-family points.
