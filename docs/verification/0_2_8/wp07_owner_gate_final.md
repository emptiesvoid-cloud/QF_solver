---
doc_id: DOC-028-WP07-OWNER-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 WP07 — final Owner gate

This Owner gate audits commit
`da310e8f3708c46d0a69a2980a2f47c4c7e9f4aa` and applies only to the WP07
mixed workflow. The machine-readable decision is recorded in
[`wp07_owner_gate_final.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp07_owner_gate_final.json).
The underlying contract and campaign evidence remain unchanged. No numerical
source, tolerance or 0.2.7 evidence is changed.

## Decision

| Mixed route | Owner decision | Resulting workflow state |
| --- | --- | --- |
| TET4 + WEDGE6 | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` |
| WEDGE6 + HEX8 | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` |
| TET4 + WEDGE6 + HEX8 | `APPROVE_WITH_LIMITATIONS` | `QUALIFIED_BOUNDED` |

The decision is recorded as a separate `mixed_workflow_qualification` record
in the [`WP07 matrix`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp07_mixed_static_matrix.json).
It does not create or relabel an element/analyse combination in the 46-record
[`element-analysis registry`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_7/capability_registry_v2.json).

## Audit result

The TET4/WEDGE6 triangular and WEDGE6/HEX8 quadrilateral interfaces use shared
nodes and one global DOF map. The campaign demonstrates zero displacement
discontinuity, unique element DOFs and opposing interface resultants at the
declared tolerance. The same checks pass for the three-family conforming
chain.

The affine field `u_x = alpha*x` is an exact analytical patch for the declared
assembly, interface, stress/strain recovery and equilibrium contract. The
equivalent loads are constructed as `K*u`; this is valid for that consistency
contract, but it is not an independent general mechanical benchmark.

The three refinement levels reproduce the affine field and preserve the
equilibrium/energy identities. This is therefore recorded as an affine
consistency refinement check, not as a general accuracy-convergence claim.
The absence of a comparable Code_Aster/CalculiX mixed-family result does not
block this narrowly bounded workflow record, but no external correlation is
claimed.

Loads, reactions, energy, stress/strain recovery, JSON/VTU export, Gmsh import,
invalid-input rejection and two deterministic replays pass within the
declared scope. The detected validation gap was fixed by explicit rejection of
duplicate-node/nonconforming mixed interfaces; no numerical bug or kernel
change was found.

## Approved scope and limitations

The approved workflow state is limited to:

- `linear_static` only;
- TET4, WEDGE6 and HEX8;
- conforming shared-node triangular and quadrilateral interfaces;
- small-strain homogeneous isotropic elasticity;
- valid element geometries in the tested domains;
- nodal, body-force, pressure and surface-traction routes exercised by WP07;
- the tested pairwise interfaces and three-family chain.

It does not qualify modal/Newmark/harmonic, nonlinear, contact, hanging-node
or MPC transitions, TET10/HEX20 mixed, PYRAMID5, nonconforming interfaces,
arbitrary mixed topologies, large-model performance or general accuracy
convergence. WEDGE6 static remains a distinct element-analysis route.

## Registry reconciliation and integrity

The element-analysis registry remains at 46 records. The cumulative state
after WP06B remains `32 QUALIFIED_BOUNDED`, `13 EXPERIMENTAL` and one
`NOT_QUALIFIED`, exactly `COMB-HEX8-linear_buckling`. WP07 does not change
those counts. No 0.2.7 evidence, prior WP01-WP06B record, numerical source or
predeclared tolerance is rewritten.

WP08 is not started by this Owner gate.
