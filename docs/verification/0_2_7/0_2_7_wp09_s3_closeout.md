---
doc_id: DOC-027-WP09-S3-CLOSEOUT-001
revision: 1.0
status: controlled_candidate
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# WP09 WEDGE6 Static-Linear Closeout

This closeout consolidates the existing WEDGE6 static-linear evidence after S3. It does not rerun a heavy benchmark or rewrite historical evidence.

The controlled internal corpus contains 22 cases: 18 positive passes and 4 expected fail-closed outcomes for inverted geometry, wrong node ordering, malformed Gmsh input and singular boundary conditions. It covers affine tension/compression, shear, bending, TRI3/QUAD4 pressure, prescribed displacement, multi-element behavior, bounded distortion/refinement, rigid transforms, scale invariance, finite outputs and deterministic replay.

The controlled external corpus contains 12 Code_Aster 18.1.0 PENTA6 cases with bounded PASS outcomes for displacement, total reaction and strain energy. Its tolerance policy remains `OWNER_REVIEW_REQUIRED`; this is not a maturity promotion. CalculiX C3D6 remains `NOT_COMPARABLE` because its controlled integration route differs from QF WEDGE6 `TRI3_X_GAUSS2`.

WEDGE6 remains `EXPERIMENTAL`. No claim is made for modal, dynamics, nonlinear, J2, TL, contact, buckling, mixed meshes or arbitrary distortion. Stress comparison remains excluded unless the measure, point, frame and convention are equivalent.

The machine-readable source of truth is `qualification/0_2_7/wp09_s3_closeout.json`.
