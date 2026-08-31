---
doc_id: DOC-027-008
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 WEDGE6 Plan and WP07 Boundary

T1-R prepared the formulation, mapping, quality and V&V contracts. Terra High
authorized WP07 at T1-R4, and the six-node elemental kernel is now implemented
with `EXPERIMENTAL` public maturity. The current evidence is recorded in
`0_2_7_wedge6_kernel.md` and `qualification/0_2_7/wp07_state.json`.

## Design gate

WP07 could start only after WP03, WP05 and WP06 were reviewed. The Terra High
T1-R4 review accepted the formulation and observable contract for this
elemental implementation. WP08 remains the separate static workflow gate.

## T1-R controlled inputs

- `qualification/0_2_7/wedge6_formulation_contract.json`
- `qualification/0_2_7/wedge6_mapping_fixture.json`
- `qualification/0_2_7/wp07_prerequisites.json`

The first three inputs are retained pre-WP07 contracts and historical
authorization records. The active implementation contract is
`wedge6_formulation_contract.json`; executed evidence is stored separately.

## Required design decisions

- six-node prism topology, local node order and orientation;
- shape functions and derivatives, including the physical Jacobian;
- quadrature order and any reduced/selective integration decision;
- face maps for TRI3 and QUAD4, outward-normal convention and boundary
  extraction;
- load distribution for nodal, face traction and body-force inputs;
- material/stress sampling and recovery/post-processing convention;
- positive-volume/orientation and distortion diagnostics;
- static route entry point and explicit unsupported analysis behavior;
- same-mesh or controlled-mesh mapping for C3D6/PENTA6 correlation;
- mixed-mesh policy. A mixed TET/WEDGE/HEX mesh is not supported merely
  because each individual element exists.

## WP07 implementation boundary

1. isolated shape/Jacobian and patch checks;
2. elemental stiffness and strain/stress recovery checks;
3. invalid-input and deterministic-replay checks;
4. comparison of production and reference quadrature.

Assembly, boundary-face/load support, Gmsh import, reactions, modal/dynamic
routes and external correlation remain later gates and are not implied by the
WP07 PASS.

## Explicit non-goals

WEDGE15, PYRAMID5, mixed-mesh support, geometric nonlinearity, J2,
friction/contact, post-buckling and broad production claims are not implied by
WEDGE6 static implementation.
