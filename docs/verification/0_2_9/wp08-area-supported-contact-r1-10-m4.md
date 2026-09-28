---
doc_id: "DOC-MARKDOWN-8A99184B4663EB77"
revision: "0.1"
status: "controlled_evidence"
applicable_version: "0.2.9"
reviewer: ""
approver: ""
---
# WP08 area-supported contact — prospective R1.10 M4 diagnostic

## Purpose and authority

This is a prospective, diagnostic-only extension of the R1.10 contact study.
Owner authorization covers exactly one M4 run at parent-cell resolution
16×8×8, with the existing stick and slip targets executed sequentially.
M1/M2/M3 evidence is reused read-only and must pass hash/provenance checks
before M4 starts. A failed case is preserved; there is no retry or parameter
tuning.

This is not formal WP08 qualification, a replay, an independent global FEM
reference, an external-solver correlation, or a score award. No mesh
convergence threshold has been frozen; M3→M4 differences are descriptive and
cannot be called a pass or fail for convergence.

## Frozen benchmark

- Element family: linear TET4, six tetrahedra per parent voxel.
- M4 parent cells: 16×8×8; 6,144 TET4 elements.
- Body: 1,377 nodes and 4,131 body DOFs. Four fixed master metadata nodes
  bring the model to 1,381 nodes / 4,143 total DOFs.
- Contact patch: 81 slave nodes and 128 triangular faces, area 0.5 m².
- Material: isotropic linear elastic, E=1.0 MPa, ν=0.30.
- Geometry: 2.0 m × 1.0 m × 0.5 m, with the existing 0.5 mm initial gap.
- Boundary conditions: body face x=0 fixed in UX/UY/UZ; master fixed.
- Contact: the existing fixed initial-search node-to-triangle route,
  friction coefficient μ=0.30, area-supported tangential stiffness density
  κ=2,666,700 N/m³, no area redistribution.
- Targets: normal resultant 1,000 N; tangential resultant 150 N (stick) or
  450 N (slip), applied using the existing eight load factors.
- Integrated tangential stiffness κA=1,333,350 N/m.
- Solver/backend, friction/contact mechanics, tolerances, iteration limits,
  fallback policy, loads, and physical parameters are unchanged from R1.10.

The generated preflight must confirm positive element volumes, full
projection of slave nodes inside the master patch, contact support rank 2,
and the expected patch area and integrated stiffness before freezing.

## Execution order and gates

1. Re-verify all six R1.10 M1/M2/M3 primary cases, manifests, process exit
   codes, source bundle and hashes. Do not rerun them.
2. Run M4/stick_target in one child process.
3. Run M4/slip_target only if stick passes its frozen diagnostic gates.
4. Stop after any process or gate failure; preserve all artifacts.

Each M4 case must have finite serialized observables, solver convergence,
eight accepted load steps, active-support affine rank 2, and the expected
terminal stick/slip state. The run records process identity, UTC times,
command, exit code, telemetry and hashes. Fallback count is not claimed if
the result schema does not expose it.

## Interpretation

The report compares M3 and M4 on common body nodes and reports displacement,
normal/tangential contact resultants, active area and state distribution.
These are observations only: no threshold was frozen, and no result may be
promoted to formal qualification or a general mesh-convergence claim.

The solver policy digest is context only; the runner does not claim that the
governing policy was enforced. Raw case outputs stay local; compact contract,
binding, manifests and final report are retained as review evidence.
