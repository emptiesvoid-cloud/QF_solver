---
title: "WP09 PYRAMID5 feasibility gate"
status: "FEASIBLE_CONTINUE"
scope: "internal bounded linear-static feasibility only"
---

# WP09 PYRAMID5 feasibility gate

WP09 evaluates whether a five-node linear pyramid can be integrated into the
existing solid-element architecture without claiming a released public
capability. The frozen [formulation](wp09_pyramid5_formulation.md) and
[predeclared contract](../../../qualification/0_2_8/wp09_pyramid5_contract.json)
use collapsed reference coordinates and never evaluate derivatives at the
coordinate singularity at the apex.

The executable [evidence](../../../qualification/0_2_8/wp09_pyramid5_vnv.json)
and [decision matrix](../../../qualification/0_2_8/wp09_pyramid5_matrix.json)
record passing Kronecker, partition-of-unity, derivative-sum, affine,
Jacobian, rank, rigid-body, stiffness-symmetry and mass-conservation checks.
Regular and bounded distorted geometries, invalid geometry rejection, a
manufactured affine patch, body and face loads, post-processing, Gmsh type-7
import, and a conforming HEX8/PYRAMID5/TET4 transition also pass. Two full
replays have identical evidence digests.

## Decision and boundaries

The technical decision is `FEASIBLE_CONTINUE`, not a maturity promotion.
PYRAMID5 is absent from the public compatibility descriptor and from the
46-combination element-analysis qualification registry; public solve dispatch
therefore remains fail-closed for this family. This internal kernel supports
only bounded small-strain, linear-isotropic, linear-static feasibility cases
with conforming nodal interfaces and geometries passing the declared Jacobian
checks.

No coherent PYRAMID5 h-refinement campaign or external-solver correlation has
been completed. Modal, Newmark, harmonic, nonlinear, contact, nonconforming
interfaces, higher-order pyramids, SRI, large-model performance and production
release claims are out of scope. WP07 and WP08 remain limited to their
TET4/WEDGE6/HEX8 workflows and are not extended by this record.
