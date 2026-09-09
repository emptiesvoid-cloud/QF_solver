---
doc_id: DOC-028-WP08B-OWNER-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP08B — final Owner gate

This Owner gate audits commit
`35d2debbd414917ac31d2b2d945df1132737eae5` and applies only to the WP08B
mixed modal workflow. The machine-readable decision is recorded in
[`wp08b_owner_gate_final.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp08b_owner_gate_final.json).
The WP08 initial failure, the WP08B contract and the WP08B campaign evidence
remain unchanged. No numerical source, tolerance or 0.2.7 evidence is
changed.

## Decision

**`APPROVE_WITH_LIMITATIONS` — resulting workflow state: `QUALIFIED_BOUNDED`**

The decision is recorded in the separate
[`WP08B mixed-modal matrix`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp08b_mixed_modal_matrix.json)
as a `mixed_workflow_qualification` record. It does not create or relabel an
element-analysis combination in the 46-record
[`element-analysis registry`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_7/capability_registry_v2.json).

## Audit result

The WP08B root-cause audit correctly identifies the original failure as a
`MESH_TO_MESH_MAPPING_PROBLEM`: the WP08 refinement runner changed the
mechanical domain by retaining only the first WEDGE6/HEX8 segment above level
one, and the original shared-node MAC did not compare fields in one FE space
with one mass inner product. This explains the initial `0.1028` result without
changing its `0.5` gate.

The WP08B method is mathematically appropriate for the bounded comparison:
coarse fields are prolonged to the fine mesh with the containing element's
shape functions, extrapolation is rejected, and the MAC uses the fine global
consistent mass inner product after generalized-mass normalization. The full
MAC matrix is assigned globally, so the result is not obtained by forcing
mode `i` onto mode `i`.

The new contract was predeclared separately from WP08, with fixed gates of
mapped MAC `>= 0.85` and adjacent matched-frequency change `<= 10%`. The
first six frequencies are monotone across levels 1/2/4/8; the largest
adjacent change is `5.86%`; mapped MAC minima are `0.9751`, `0.9037` and
`0.9979`. Residuals, mass orthogonality, mass assembly/conservation,
conforming interface checks, failure paths and two deterministic replays pass.
The independent dense local-matrix scatter/eigensolve and analytical mass
conservation are sufficient for this bounded assembly claim. No external
industrial-solver correlation is claimed or required for this scope.

## Approved scope and limitations

The approved workflow is limited to:

- modal linear analysis only;
- the fixed-base `x=0` TET4/WEDGE6/HEX8 conforming chain tested by WP08B;
- shared-node triangular and quadrilateral interfaces;
- small-strain homogeneous isotropic elasticity;
- consistent translational finite-element mass;
- the first six positive modes;
- refinement levels 1, 2, 4 and 8;
- valid geometries within the already qualified elementary domains.

It does not qualify modal stress, lumped or concentrated mass, Newmark,
harmonic, nonlinear, contact, nonconforming or hanging-node/MPC/RBE
interfaces, TET10/HEX20, PYRAMID5, large-model performance or universal
all-frequency behavior. Pure-family controls remain diagnostics only.

## Registry reconciliation and integrity

The element-analysis registry remains at 46 records and is not modified by
this mixed-workflow decision. Its source counts remain `20 QUALIFIED_BOUNDED`,
`25 EXPERIMENTAL` and `1 NOT_QUALIFIED`; the cumulative 0.2.8 state after
WP06B remains `32 QUALIFIED_BOUNDED`, `13 EXPERIMENTAL` and one
`NOT_QUALIFIED`, exactly `COMB-HEX8-linear_buckling`. No WP08 gate is changed,
no WP08 evidence is rewritten, no 0.2.7 evidence is changed, and no numerical
source is changed.

WP09 is not started by this Owner gate.
