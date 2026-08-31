---
doc_id: DOC-027-008
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 WEDGE6 Plan

This is a plan only. WEDGE6 is not implemented by the foundation commit.

## Design gate

WP07 cannot start until WP03, WP05 and WP06 are reviewed. The Solver/Owner
review must explicitly accept the formulation and the observable contract
before source changes begin.

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

## Implementation sequence after GO

1. isolated shape/Jacobian and patch checks;
2. element stiffness and mass checks, if mass is in the approved scope;
3. assembly and boundary-face/load vertical slice;
4. Gmsh import and maintained example;
5. reaction/equilibrium and stress/post-processing checks;
6. invalid-input and deterministic-replay checks;
7. only then modal or external work.

## Explicit non-goals

WEDGE15, PYRAMID5, mixed-mesh support, geometric nonlinearity, J2,
friction/contact, post-buckling and broad production claims are not implied by
WEDGE6 static implementation.
