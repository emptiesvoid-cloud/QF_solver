---
doc_id: DOC-027-022
revision: 1.0
status: controlled_evidence
applicable_version: 0.2.7a0
---

# WP07 WEDGE6 kernel evidence

WP07 implements the six-node, 18-DOF triangular-prism kernel authorized by the
Terra High T1-R4 review. The implementation is intentionally limited to an
elemental small-strain, homogeneous isotropic elastic route. It is technical
evidence, not a public qualification or a complete WEDGE6 workflow.

## Implemented contract

- Shape functions, natural derivatives and isoparametric mapping follow
  `qualification/0_2_7/wedge6_formulation_contract.json`.
- Physical gradients and the 3-D engineering-shear `B` matrix use
  `(xx, yy, zz, xy, yz, xz)` ordering.
- `TRI3_X_GAUSS2` is the six-point full-integration production rule.
- `DUFFY_GAUSS5_X_GAUSS4` is a 100-point independent reference rule used only
  for verification. Reduced or selective integration is not implemented.
- Elemental strain/stress recovery is reported at production integration
  points; stress extrapolation is not implicit.

## Geometry boundary

Before stiffness or recovery, WEDGE6 geometry is checked by the exact
triangular-vertex reduction from T1-R3. At each triangular reference vertex,
`det(J)(t)` is evaluated as a quadratic on `[-1, 1]`, including both endpoints
and every interior stationary point. The minimum is compared with a
machine-epsilon-scaled determinant guard. Quadrature and interior samples are
diagnostics only. Non-finite, coincident, inverted, degenerate or unresolved
orientation cases fail closed; no node-order auto-repair exists.

The Terra adversarial prism, which can pass sparse integration samples while
having an interior negative determinant, is recorded as
`EXPECTED_FAILURE_PASS` in the WP07 evidence artifact.

## Targeted V&V result

The declarative catalog is executed by `scripts/run_wedge6_wp07.py` through
the V&V v2 runner. The committed evidence records source SHA, input and result
digests, oracle/tolerance metadata, verdict, runtime and artifact class.

| Check | Result |
| --- | --- |
| shape identities and affine reproduction | `PASS` |
| Jacobian certificate and nominal geometry | `PASS` |
| Terra interior-inversion adversarial case | `EXPECTED_FAILURE_PASS` |
| elastic stiffness symmetry | `PASS` |
| free-element rank / rigid-body modes | rank `12`, modes `6` |
| constant strain, tension, compression, shear | `PASS` |
| bending-like finite energy | `PASS` |
| distorted positive-Jacobian prism | `PASS` |
| production/reference quadrature | `PASS` |
| deterministic harness replay | `PASS` |

## Maturity and deferred scope

The registry records `COMB-WEDGE6-linear_static` as technically supported and
verified but `EXPERIMENTAL` in qualification state. The descriptor/preflight
reports the route as `EXPERIMENTAL_ROUTE`; it does not create a public
qualified claim. Gmsh import, face loads, user-level assembly/reactions,
modal or dynamic routes, nonlinear materials, contact and external
correlation remain deferred to later work packages.

No TET4, TET10, HEX8 or HEX20 formulation was modified. Full regression is
not part of this WP07 targeted checkpoint.

## Provenance

- State: `qualification/0_2_7/wp07_state.json`
- Case catalog: `qualification/0_2_7/vnv_v2/wp07_cases.json`
- Evidence: `qualification/0_2_7/vnv_v2/wp07_evidence.json`
- Formulation contract: `qualification/0_2_7/wedge6_formulation_contract.json`
- Kernel: `src/solveur/elements/solid/wedge6.py`
