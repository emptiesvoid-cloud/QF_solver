---
doc_id: DOC-027-021
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# WEDGE6 formulation contract

This is the T1-R pre-WP07 contract. It fixes the mathematical vocabulary and
the verification obligations without implementing a WEDGE6 kernel or creating
an active capability.

## Reference element

The natural domain is `r >= 0`, `s >= 0`, `r + s <= 1`, `-1 <= t <= 1`.
Nodes 1-3 form the lower triangle at `t=-1`; nodes 4-6 form the upper
triangle at `t=+1`. The shape functions are:

```text
N1 = 0.5 (1-t) (1-r-s)    N2 = 0.5 (1-t) r    N3 = 0.5 (1-t) s
N4 = 0.5 (1+t) (1-r-s)    N5 = 0.5 (1+t) r    N6 = 0.5 (1+t) s
```

Their derivatives, identities, and the physical mapping are recorded in
`qualification/0_2_7/wedge6_formulation_contract.json`. In particular,
`x=sum(Ni*x_i)`, `J=dx/d(r,s,t)`, `grad_x(Ni)=J^-T grad_ref(Ni)`, and the
orientation contract is `det(J)>0` at all declared validity controls.

The signed volume is the reference integral of `det(J)`. The future 3-D
small-strain matrix uses engineering shear order
`(xx, yy, zz, xy, yz, xz)`. Stress recovery must state its measure and sample
location; extrapolation is never implicit.

## Integration contract

The WP07 starting candidate is a six-point product rule: degree-2, three-point
triangle quadrature times two-point Gauss quadrature through the thickness.
A Duffy-transformed Gauss 5x5 triangle rule times four-point thickness rule is
the independent 100-point verification reference. This is a predeclared
candidate, not a production approval. Reduced or selective integration is
not qualified by T1-R.

The rule must be compared on affine and distorted positive-Jacobian prisms for
constant strain, stiffness rank, energy and sensitivity. The two integration
points reported for the external C3D6 deck are an external fact, not a QF
integration prescription.

## Ordering and faces

The asymmetric fixture in
`qualification/0_2_7/wedge6_mapping_fixture.json` prevents a permutation from
passing by geometric symmetry. The reference face cycles are:

| Face | Nodes | Outward direction |
| --- | --- | --- |
| TRI bottom | 1, 3, 2 | negative `t` |
| TRI top | 4, 5, 6 | positive `t` |
| QUAD side 1-2 | 1, 2, 5, 4 | negative `s` |
| QUAD side 2-3 | 2, 3, 6, 5 | positive `r+s` |
| QUAD side 3-1 | 3, 1, 4, 6 | negative `r` |

No automatic node or normal repair is allowed. Each adapter must record any
permutation and verify positive Jacobian, coordinates, normal, area,
uniform-pressure resultant and resultant moment.

## Quality, stiffness and mass

For linear WEDGE6, the validity certificate reduces `det(J)` to three
quadratics in `t`: at fixed `t`, the determinant is affine over the reference
triangle, so its minimum is at one of the three triangle vertices. Each
quadratic is checked at `t=-1`, `t=+1` and any interior stationary point. The
minimum is compared with a machine-epsilon-scaled determinant magnitude; this
is a roundoff guard, not a qualification cutoff. Volume quadrature points,
face centroids and the prism interior centroid remain additional diagnostics.
Degenerate, inverted, non-finite or unresolved orientations fail closed.
Distortion and conditioning remain diagnostics without a universal cutoff.

WP07 must predeclare tests for symmetry, rank, six rigid-body modes, affine
constant strain, tension, compression, shear, bending, distortion, energy and
replay. The consistent-mass formula and modal checks are specified for WP10
only; no static evidence promotes a modal route.

## External comparison

The primary future observables are displacement, total reaction and strain
energy. Stress is comparable only with the same measure, point, frame and
sign convention. The external tolerance candidates are recorded as
`PROPOSED_OWNER_REVIEW` in the JSON contract and are not derived from any
observed QF result. The current CalculiX/Code_Aster artifacts remain deck
validation only because WEDGE6 is not implemented.

T1-R does not add `WEDGE6` to the registry and does not authorize WP08 or
later numerical work. WP07 remains a separate formulation/Owner gate.
