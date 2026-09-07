---
doc_id: DOC-028-WP09-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP09 — PYRAMID5 formulation gate

This note fixes the formulation considered by WP09 before any kernel or V&V
implementation. It is a feasibility record, not a production qualification or
a change to the 0.2.7 capability set.

## Selected formulation

WP09 evaluates the conventional five-node displacement pyramid obtained by a
collapsed-coordinate map. Let `(r, s, t)` lie in
`[-1, 1] × [-1, 1] × [0, 1]`, with physical reference coordinates
`(x, y, z) = ((1-t) r, (1-t) s, t)`. The base nodes are ordered
counter-clockwise as `0, 1, 2, 3`; node `4` is the apex. The five shape
functions are

```text
N0 = (1-t)(1-r)(1-s)/4     N1 = (1-t)(1+r)(1-s)/4
N2 = (1-t)(1+r)(1+s)/4     N3 = (1-t)(1-r)(1+s)/4
N4 = t
```

Their reference derivatives are used directly for the isoparametric Jacobian
and the small-strain `B` matrix. This is the lowest-order nodal pyramid used
by the Gmsh/PYRAMID5 topology. The coordinate domain and base/apex ordering
are consistent with the PYRAMID5 reference descriptions in
[libMesh](https://mooseframework.inl.gov/docs/doxygen/libmesh/classlibMesh_1_1Pyramid5.html)
and with [Gmsh type 7 and its node-ordering contract](https://gmsh.info/doc/texinfo/gmsh.html#Node-ordering).

For broader pyramidal approximation theory, rational pyramid spaces are
necessary to retain compatible traces across hybrid meshes; see
[Bergot, Cohen and Duruflé](https://arxiv.org/abs/math/0610206) and the
[numerical-integration discussion](https://arxiv.org/abs/1003.0495).
WP09 does not claim that this five-node displacement space has the properties
of a higher-order compatible pyramid family.

## Apex behavior and bounded geometry

At `t = 1` every `(r, s)` represents the apex. The nodal values are
unambiguous there, but reference derivatives and the collapsed-coordinate
Jacobian are not a valid evaluation point. This is a known limitation of
isoparametric PYRAMID5 mappings; [Axom documents the corresponding near-apex
Jacobian singularity](https://axom.readthedocs.io/en/feature-white238-inlet_variant_containers/doxygen/html/classaxom_1_1mint_1_1Lagrange_3_01mint_1_1PYRAMID_01_4.html).

Therefore WP09 never evaluates derivatives or quadrature at the apex. The
candidate scope is restricted to a convex planar QUAD4 base, a non-coplanar
apex, and positive sampled Jacobians over the predeclared production and
reference rules. Distorted, flattened, folded or inverted pyramids outside
that sampled domain are explicitly rejected; this is not an arbitrary-shape
robustness claim.

## Quadrature

The selected production rule is a tensor product of three Gauss--Legendre
points in each collapsed base coordinate and four points in `t`, mapped to
`[0, 1]`. The geometric factor is retained in `det(J)`; no apex point is used.
The reference rule is `5 × 5 × 6` Gauss--Legendre points. The latter is a V&V
comparison rule only. Both stiffness and consistent translational mass use the
same production mapping, so no reduced integration or hourglass control is
introduced.

## Predeclared gates

The machine-readable contract
[`wp09_pyramid5_contract.json`](../../../qualification/0_2_8/wp09_pyramid5_contract.json)
fixes all gates before execution. In particular, the regular and bounded
distorted cases must have exactly six rigid-body null modes and rank `9` of
`15`; production/reference relative stiffness error is bounded by `1e-5`; and
the affine, load-balance, mass and replay gates are frozen there. A failure is
a WP09 feasibility result, not a reason to retune a tolerance.

## Deliberate exclusions

WP09 excludes PYRAMID13, nonlinear material/kinematics, SRI, stabilization,
hourglass control, modal/dynamic routes, nonconforming interfaces, hanging
nodes, MPC/RBE transitions and any general HEX/TET transition-mesh claim. A
conforming HEX8/PYRAMID5/TET4 patch, if implemented, is a separate static
feasibility check and does not alter the WP07 or WP08 qualified workflows.
