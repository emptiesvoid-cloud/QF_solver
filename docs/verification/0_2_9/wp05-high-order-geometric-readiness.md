---
doc_id: DOC-029-WP05-READINESS-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.9-development
reviewer: ""
approver: ""
---

# WP05 — High-order geometric-nonlinear readiness audit

**Status:** `PREPARATION_ONLY`

**Source baseline:** `2c52bf8196a7d47d14ce1784290580160de26590`

**Scope:** TET10 and HEX20 under the existing total-Lagrangian geometric-static route.
**Date:** 2026-09-13

This is an implementation and verification-readiness audit.  It does not
qualify, promote, or change the maturity of either high-order family.  The
current public route remains a bounded research capability, and no result in
this document is a replacement for the active WP04 TET4/HEX8 qualification.

## Boundaries and governance

WP05 is restricted to homogeneous, isotropic, three-dimensional solid models
with nodal dead loads on `geometric_nonlinear_static`.  The existing router
fails closed outside that bounded scope: mixed element families, multiple
materials, non-isotropic materials, and distributed loads are not silently
redirected to a high-order TL path.

`TET10` and `HEX20` have an implemented public dispatch path, but their
traceability labels are respectively
`tet10-total-lagrangian-structural-research` and
`hex20-total-lagrangian-structural-research`.  The capability registry's
owner-qualified elastic TL claim is bounded to TET4.  Therefore, code
availability is not a qualification claim.

WP04 currently has its own TET4/HEX8 contract and deliberately excludes
TET10/HEX20.  WP05 can develop isolated fixtures and harnesses before WP04
closes, because it shares the generic TL kernel rather than the active WP04
campaign artifacts.  Formal WP05 qualification remains blocked until both an
Owner-approved high-order contract exists and the governing geometric-static
baseline has been closed or superseded by an approved successor.  In
particular, no WP04 floor-aware termination policy may be copied into WP05
without an Owner decision.

## Route traceability

```text
solve_model
  -> AnalysisRouter.solve
  -> GeometricNonlinearStaticSolver.solve
  -> build_total_lagrangian_assembly
  -> TotalLagrangianHighOrderAssembly (TET10 or HEX20)
  -> TotalLagrangianJ2Tet10Element / TotalLagrangianJ2Hex20Element
  -> TotalLagrangianJ2Element shared kernel
  -> solve_full_newton or solve_adaptive_full_newton
```

The historical class name `TotalLagrangianJ2Element` is not a claim that the
high-order geometric route uses J2 plasticity.  With the accepted
`SolidMaterial`, the shared kernel evaluates Green--Lagrange strain with an
isotropic Saint-Venant--Kirchhoff elastic constitutive response.  At each
integration point it forms `F`, checks finite `det(F) > 1e-10`, evaluates
second Piola stress `S`, uses `P = F S` for the internal force, and builds a
combined material-plus-geometric tangent.  The assembled tangent is
symmetrized.  This implementation observation is not a formulation
qualification.

## Capability/readiness matrix

The first status describes implemented availability; the final column states
the verification state.  `SUPPORTED` never implies Owner qualification here.

| Capability | TET10 | HEX20 | Evidence and remaining verification gap |
|---|---|---|---|
| `LINEAR_STATIC` | `SUPPORTED` | `SUPPORTED` | Registered element paths and unit coverage exist; not a high-order TL proof. |
| `MODAL` / mass | `SUPPORTED` | `SUPPORTED` | Consistent mass is implemented (`tetra_duffy_rule(5)` / 27-point rule); no geometric-nonlinear modal claim. |
| `TOTAL_LAGRANGIAN` | `SUPPORTED` (research) | `SUPPORTED` (research) | Both dispatch to the common high-order TL assembly and kernel; direct identity V&V is missing. |
| `GEOMETRIC_NONLINEAR` | `SUPPORTED` (research) | `SUPPORTED` (research) | Public small dead-load smoke path succeeds; structural qualification is missing. |
| `INTERNAL_FORCE` | `SUPPORTED` | `SUPPORTED` | Shared `P = F S` integration is present; needs independent affine/energy checks. |
| `CONSISTENT_TANGENT` | `SUPPORTED` | `SUPPORTED` | Shared material and geometric blocks are present; high-order finite-difference evidence is missing. |
| `ENERGY` | `SUPPORTED` | `SUPPORTED` | `strain_energy` and integration-point fields exist; energy-gradient identity is unqualified. |
| `OBJECTIVITY` | `PARTIAL` | `PARTIAL` | One isolated rigid-rotation smoke was finite and near zero; formal fixture/oracle is missing. |
| `AFFINE_PATCH` | `PARTIAL` | `PARTIAL` | One affine smoke was finite and symmetric; analytical patch oracle is missing. |
| `SMALL_LINEAR_LIMIT` | `PARTIAL` | `PARTIAL` | Linear and TL routes exist; a controlled small-displacement equivalence test is missing. |
| `STRUCTURAL_CONVERGENCE` | `MISSING` | `MISSING` | No high-order TL mesh/refinement benchmark is qualified. |

## Element and integration audit

### TET10

`Tet10Element` uses four corner nodes followed by six edge nodes in its
documented internal ordering.  The Gmsh importer applies
`GMSH_TET10_TO_INTERNAL = (0, 1, 2, 3, 4, 5, 6, 7, 9, 8)` to reconcile the
last two Gmsh edge-node positions.  This mapping is a test target, not an
assumption to be changed in WP05.

The default high-order TL quadrature is the four-point Hammer rule (degree two
exact); an explicit five-point `code_aster_5` option integrates cubic fields
but includes a negative centroid weight.  The linear TET10 route switches to
a Duffy rule for curved geometry, while the high-order TL reference-data path
selects the configured nonlinear rule and validates the corner orientation
plus the selected integration points.  It does not perform the linear route's
full lattice-quality diagnostic.  This is a geometry-validation and
quadrature-sensitivity gap to test; it is not evidence of a formulation bug.

### HEX20

`Hex20Element` follows the conventional Gmsh incomplete second-order
hexahedron ordering: eight corners and twelve edge nodes.  Its TL path uses
full 3 x 3 x 3 Gauss integration (27 points, tensor-product degree five
exactness) and validates finite positive Jacobians at every integration point.
There is no reduced-integration HEX20 route, so there is no current WP05
hourglass claim to make.  Near-incompressible locking and distorted-geometry
behavior remain validation topics, not resolved properties.

## Existing evidence, executed smoke, and limitations

The following focused baseline tests were executed in the isolated Agent B
environment:

```text
python -m pytest -q tests/unit/test_tet10_element.py \
  tests/unit/test_hex20_element.py tests/unit/test_geometric_nonlinear_public.py \
  -k "not tet4 and not requires_six_increments and not rejects_distributed_loads"

27 passed, 4 deselected
```

The existing public geometric test exercises a one-element, six-increment,
nodal-dead-load TET10 and HEX20 solve and checks successful dispatch, research
scope, positive minimum `det(F)`, and positive strain energy.  It is a route
smoke, not a patch, tangent, objectivity, or convergence qualification.

An isolated, non-archived direct assembly smoke additionally applied one
affine deformation and one rigid rotation to a canonical straight-sided
element of each family.  Both force vectors and tangents were finite; the
assembled tangent symmetry defect was zero.  Rigid-rotation energy/force norms
were:

| Family | Rigid energy | Rigid force norm | Affine energy | Public-solve min `det(F)` |
|---|---:|---:|---:|---:|
| TET10 | `3.289446898492168e-32` | `3.855185596419919e-15` | `0.22926875000000047` | `0.9999993182476841` |
| HEX20 | `2.8149473805666008e-30` | `4.4740786613619486e-14` | `1.3756125000000026` | `0.9999999577683978` |

These measurements are recorded solely as readiness smoke evidence.  They do
not establish a tolerance, an independent oracle, material generality,
curved-mesh robustness, or a public maturity claim.

## WP04 identity reuse map

The shared kernel makes the following identities applicable, but WP04's
TET4/HEX8 thresholds cannot automatically become high-order qualification
thresholds.  Each item requires high-order fixtures and Owner adoption of the
policy before it can count toward WP05.

| Identity / policy | TET10 status | HEX20 status | Reason |
|---|---|---|---|
| Rigid-body objectivity | `FIXTURE_ONLY_REQUIRED` | `FIXTURE_ONLY_REQUIRED` | Same Green--Lagrange kernel; family-specific geometry/quadrature fixtures needed. |
| Affine constant-strain patch | `FIXTURE_ONLY_REQUIRED` | `FIXTURE_ONLY_REQUIRED` | Same constitutive path; independent analytical force/energy oracle needed. |
| Energy-gradient identity | `FIXTURE_ONLY_REQUIRED` | `FIXTURE_ONLY_REQUIRED` | Energy API exists; high-order DOF scaling and perturbation policy need approval. |
| Finite-difference tangent consistency | `FIXTURE_ONLY_REQUIRED` | `FIXTURE_ONLY_REQUIRED` | Combined tangent exists; family-specific columns/conditioning must be sampled. |
| Tangent symmetry | `FIXTURE_ONLY_REQUIRED` | `FIXTURE_ONLY_REQUIRED` | Assembly is symmetrized; the test must also ensure this does not hide FD inconsistency. |
| Small-displacement linear limit | `FIXTURE_ONLY_REQUIRED` | `FIXTURE_ONLY_REQUIRED` | Both routes exist, but no controlled high-order equivalence fixture exists. |
| Force/moment equilibrium | `FIXTURE_ONLY_REQUIRED` | `FIXTURE_ONLY_REQUIRED` | Requires a high-order structural fixture with declared reactions and moments. |
| Energy/work and mesh refinement | `FIXTURE_ONLY_REQUIRED` | `FIXTURE_ONLY_REQUIRED` | Requires new family-specific benchmark meshes and observables. |

## Proposed bounded WP05 sub-work packages

The proposed point split is exactly five points and is intentionally not
started by this audit.

| Sub-WP | Points | Bounded outcome |
|---|---:|---|
| WP05-A — TET10 identities and quadrature/orientation fixtures | 1 | Objectivity, affine patch, energy-gradient, selected FD-tangent and importer/orientation evidence. |
| WP05-B — HEX20 identities and integration/geometry fixtures | 1 | Same identities, full-integration geometry checks, and no reduced-integration/hourglass claim. |
| WP05-C — TET10 structural bounded benchmark | 1 | Nodal-dead-load cantilever/bending convergence, reactions, equilibrium, `det(F)`, and replay evidence. |
| WP05-D — HEX20 structural bounded benchmark | 1 | Equivalent HEX20-only structural evidence, including distortion-sensitive declared cases. |
| WP05-E — Cross-family comparison and Owner review | 1 | Compare declared observables only; issue a bounded/non-qualified disposition without generalizing across elements. |

`WP05_VALIDATION_POINTS = 0 / 5` at this preparation stage.  The release-wide
validated total remains `29 / 100`; no maturity, capability, or release status
changes here.

## Benchmark-design decision record

No benchmark is executed in this audit.  The following designs are proposals
to be frozen before any result is observed.

### A. High-order cantilever / small-to-moderate bending

Use the same rectangular three-dimensional domain for each family,
`L = 10`, `H = 1`, `W = 1`, clamped at `x = 0`.  Apply a prescribed set of
equivalent **nodal dead loads** to the `x = L` end nodes; do not substitute an
unsupported distributed-load route.  Use an isotropic elastic material and a
declared load sequence kept below inversion.

Candidate refinement levels are 4 x 1 x 1, 8 x 2 x 2, and 16 x 4 x 4 base
cells along `(L, H, W)`, converted independently into valid TET10 and HEX20
meshes.  Before execution declare: tip displacement, summed clamp reaction,
reaction moment, minimum integration-point `det(F)`, convergence history,
and strain-energy/work consistency.  Compare each family to its own
refinement sequence and to an analytical beam observable only within the
declared small-to-moderate regime.  Do not make a pointwise TET10-versus-HEX20
claim merely because the domain is shared.

### B. Curvature- and distortion-sensitive bending

Use a mapped quarter-cantilever with the same material, clamp, and end-node
dead-load convention.  Candidate levels are 4 x 1 x 1, 8 x 2 x 1, and
16 x 4 x 2 cells in (arc, radial, thickness) directions.  Freeze the mapping,
element conversion, and a geometry-quality observable before execution.
For TET10, compare the configured Hammer-4 and explicit Code_Aster-5
nonlinear quadrature only as a declared sensitivity study; do not select a
rule after seeing results.  For HEX20, retain full 27-point integration.  The
benchmark must classify any negative/near-zero Jacobian, `det(F)` violation,
or non-convergence as an explicit failure rather than silently lowering the
claim.

## Threshold and policy status

WP04-B provides technical references, not transferred qualification.  The
existing objectivity (`energy <= 1e-12`, force norm `<= 1e-11`), affine patch
(`relative <= 1e-10`, absolute `<= 1e-12`), and symmetry (`<= 1e-12`)
thresholds are candidates for `REUSE_WP04_THRESHOLD` after Owner adoption.
Energy-gradient and finite-difference-tangent bounds require
`NEW_JUSTIFICATION_REQUIRED` because high-order DOF counts, quadrature, and
conditioning differ.  Small-linear-limit, equilibrium/moment, energy-work,
mesh-convergence, distortion, and cross-family thresholds also require
`NEW_JUSTIFICATION_REQUIRED` with their observables frozen before execution.
No tolerance has been adjusted after observation.

## Readiness decision

* `WP05_IMPLEMENTATION_CAN_START_BEFORE_WP04_CLOSE = YES` — isolated fixtures,
  runners, and benchmark generation can proceed on this independent branch.
* `WP05_QUALIFICATION_BLOCKED_BY_WP04 = YES` — formal credit requires the
  Owner high-order contract and an approved governing geometric baseline.
* `PACKAGE_VERSION_OBSERVATION = EXPECTED_DEVELOPMENT_BASELINE` — the audited
  base declares package version `0.2.8` even though the work is planned for
  0.2.9; this audit makes no version-management defect claim.
* `NEXT_STEP = OWNER_REVIEW_OF_WP05_SCOPE_AND_POLICY` — no merge or promotion
  is authorized while Agent A's WP04-C2R6 campaign remains active.

## Explicit limitations

This audit does not establish high-order TL external correlation, large-strain
industrial robustness, contact, dynamics, J2 plasticity, mixed materials,
mixed element meshes, curved TET10 nonlinear-quadrature adequacy, stress
recovery accuracy, locking behavior, or any broad HEX20/TET10 maturity claim.
No full regression, large numerical campaign, formulation change, or external
solver execution was performed.
