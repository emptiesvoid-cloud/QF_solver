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
[`WP07 contract`](../../../qualification/0_2_8/wp07_mixed_static_contract.json);
the executable machine-readable result is the
[`WP07 evidence`](../../../qualification/0_2_8/wp07_mixed_static_vnv.json);
and the candidate matrix is the
[`WP07 matrix`](../../../qualification/0_2_8/wp07_mixed_static_matrix.json).

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

WP07 technical result: **`QUALIFIED_BOUNDED_CANDIDATE`**. This is a
technical candidate only. The 46-combination source registry remains
unchanged at `32 QUALIFIED_BOUNDED`, `13 EXPERIMENTAL` and one
`NOT_QUALIFIED`, namely `COMB-HEX8-linear_buckling`. WEDGE6 static remains a
separate route. No public qualification, maturity relabel or claim expansion
is applied by WP07.

The separate Owner decision must either approve this exact bounded scope,
approve it with further limitations, or reject it. WP08 is not started by
this record.
