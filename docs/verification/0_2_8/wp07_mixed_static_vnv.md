---
doc_id: DOC-028-WP07-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP07 mixed linear-static V&V

WP07 audits one mixed workflow using `TET4 + WEDGE6 + HEX8`, starting from
`d7501fd144daf11a5f51eae5c04d664ebbcdc763`. It does not rewrite 0.2.7
evidence or any earlier 0.2.8 record. The frozen campaign contract is the
[`WP07 contract`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp07_mixed_static_contract.json);
the executable machine-readable result is the
[`WP07 evidence`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp07_mixed_static_vnv.json);
and the candidate matrix is the
[`WP07 matrix`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp07_mixed_static_matrix.json).

## Existing architecture audit

The element registry, `AssemblyPlan`/`GlobalAssembler`, shared-node DOF map,
solid material construction, load integration, reactions, stress/strain
recovery and result export were already family-generic. Gmsh already accepted
the three solid families. The demonstrated gap was the mixed-interface
contract: duplicate-node/nonconforming interfaces were not rejected
explicitly. WP07 adds only that validation and its failure-path coverage; no
element stiffness or global formulation is changed.

| Subsystem | WP07 classification |
| --- | --- |
| Element registry | `ALREADY_IMPLEMENTED` |
| Assembly plan / global assembler | `ALREADY_IMPLEMENTED` |
| Gmsh importer | `ALREADY_IMPLEMENTED_NEEDS_VNV` |
| Materials, DOF mapping, loads and boundary conditions | `ALREADY_IMPLEMENTED_NEEDS_VNV` |
| Reactions, recovery and results/export | `ALREADY_IMPLEMENTED_NEEDS_VNV` |
| Diagnostics | `PARTIAL_NEEDS_FIX` |
| Mixed-interface validation | `NEEDS_FIX` → fixed and tested |

## Candidate scope

The technical candidate is limited to `linear_static`, small-strain linear
elasticity, and the tested homogeneous `isotropic_3d` material route. It
covers conforming shared-node triangular `TET4-WEDGE6` faces,
quadrilateral `WEDGE6-HEX8` faces, and their tested three-family chain. The
tested load contract includes nodal, body-force, pressure and global surface
traction routes on supported faces.

The candidate does not qualify `TET10`, `HEX20`, `PYRAMID5`, hanging nodes,
MPC/RBE coupling, nonconforming interfaces, modal/dynamic/nonlinear/buckling
analysis, contact, arbitrary distortion or large mixed models. It is not a
public maturity promotion until a separate Owner gate approves it.

## Campaign gates

The predeclared tolerances are preserved in the contract and evidence. The
exact affine manufactured field is the primary analytical oracle for the
declared assembly and interface contract. The campaign verifies:

- affine displacement, strain, stress, energy, residuals, reactions and
  global force/moment balance;
- one global symmetric matrix, unique shared-node DOFs, rank and six
  unconstrained rigid-body modes;
- TET4-WEDGE6, WEDGE6-HEX8 and TET4-WEDGE6-HEX8 interfaces, including
  displacement continuity and opposing face resultants;
- nodal, body-force, pressure and surface-traction resultants;
- material routing, stress/strain recovery, JSON/VTU export and a dependency-
  neutral Gmsh mixed import/solve;
- three conforming-chain refinement levels;
- explicit rejection of unsupported families, invalid geometry/connectivity
  and nonconforming duplicate-node interfaces;
- two complete deterministic replays with identical evidence digests.

Every listed gate passes in the machine-readable evidence. No external
Code_Aster/CalculiX mixed-family correlation is claimed: no comparable
external result was available in this campaign. That limitation is part of
the bounded candidate scope and remains for Owner review.

## Technical decision and maturity boundary

WP07 technical result: **`QUALIFIED_BOUNDED_CANDIDATE`**. The separate final
[`WP07 Owner gate`](wp07_owner_gate_final.md), recorded in
[`wp07_owner_gate_final.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp07_owner_gate_final.json),
approves this candidate **`APPROVE_WITH_LIMITATIONS`** and records the mixed
workflow as **`QUALIFIED_BOUNDED`**. This status belongs to the dedicated
`mixed_workflow_qualification` record; it is not added as a new element/analyse
combination.

The 46-combination source registry remains unchanged at
`32 QUALIFIED_BOUNDED`, `13 EXPERIMENTAL` and one `NOT_QUALIFIED`, namely
`COMB-HEX8-linear_buckling`. WEDGE6 static remains a separate route.

The affine manufactured field and `K·u` load construction are sufficient for
the bounded assembly/interface/load contract, but the refinement sequence is
an affine-consistency check rather than an independent general accuracy
convergence study. No general mixed-mesh accuracy, arbitrary-load, external
solver or large-model claim is made.

## Owner-approved scope and limitations

The approved scope is `linear_static` only, with TET4/WEDGE6/HEX8, conforming
shared-node triangular and quadrilateral interfaces, small-strain homogeneous
isotropic elasticity, valid element geometries and the nodal, body-force,
pressure and surface-traction routes actually exercised by WP07. It covers
the tested pairwise interfaces and the tested three-family chain, including
the recorded continuity, DOF, equilibrium, energy, recovery and failure
contracts.

Modal/Newmark/harmonic, nonlinear, contact, hanging-node or MPC transitions,
TET10/HEX20 mixed, PYRAMID5, nonconforming interfaces, arbitrary mixed
topologies, large-model performance and general accuracy convergence remain
out of scope.

WP08 is not started by this record.
