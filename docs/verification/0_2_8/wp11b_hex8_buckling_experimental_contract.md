---
doc_id: DOC-028-WP11B-CONTRACT-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# WP11B HEX8 buckling experimental-readiness contract

This contract is separate from WP06/WP06B. It does not rewrite their Euler or
mesh-convergence failures and does not change any WP06 tolerance.

## Experimental scope

The candidate scope is HEX8 linear eigenvalue buckling from a linear-elastic
prestress state, on valid bounded geometries, with explicitly tested boundary
conditions and the first positive instability factor/mode only. It is for
exploratory/research use.

The frozen benchmark is a rectangular solid cantilever block (`L=4.0`,
`b=1.2`, `h=1.0`) with all DOFs fixed on `x=0` and uniform nodal dead
compression on the `x=L` face (`P=1.0`). The material is homogeneous isotropic
linear elasticity (`E=1000`, `nu=0.3`). Levels are `(2,2,2)`, `(4,4,4)` and
`(6,6,6)` HEX8 cells.

## Frozen gates

Preload residual must be at most `1e-8`, geometric-stiffness symmetry at most
`1e-12`, and recomputed eigen residual at most `1e-7`. The critical factor must
be finite and positive; the associated mode must be finite, physically lateral
(`UZ` dominant in this weak-axis setup), and free of NaN/Inf.

Doubling `E` must double the critical factor within 5%; doubling preload `P`
must halve it within 5%. Doubling `L` must produce a finite positive factor
lower than the reference. A moderate geometry perturbation must remain finite
and within 10% of the level-4 reference. Two replay digests must match exactly.

Refinement is characterization, not a convergence-to-Euler gate. Factors,
adjacent changes, modes and residuals must be reported honestly; a non-stable
trend cannot be presented as general convergence.

## Explicit exclusions

Euler prediction, certification, production use, imperfections,
nonlinear/post-buckling, plasticity, arbitrary meshes, universal accuracy,
multi-mode or mixed-mesh buckling, HEX8R, SRI, B-bar and hourglass control are
outside this contract. An unavailable external oracle is recorded as such and
is never invented.
