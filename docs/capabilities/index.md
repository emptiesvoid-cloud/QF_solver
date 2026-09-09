---
doc_id: DOC-CAPABILITY-028-001
revision: 1.0
status: controlled
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# QF Solver 0.2.8 capability index

**Current development state:** `0.2.8` / release preparation
**Publication status:** `NOT_PUBLISHED_YET`

This page is the public orientation index for the 0.2.8 candidate. It links to
the authoritative element-analysis registry and to the separate mixed-workflow,
capability and research records. It does not merge those records and it does
not create a new maturity decision.

## How to read this index

The active source of truth for the 46 element-analysis combinations is the
[consolidated registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/consolidated_registry.json):

| Registry | `QUALIFIED_BOUNDED` | `EXPERIMENTAL` | `NOT_QUALIFIED` | Total |
| --- | ---: | ---: | ---: | ---: |
| Element-analysis combinations | 32 | 14 | 0 | 46 |

Mixed workflows and separate capabilities are deliberately outside those 46
records. Their status applies only to the linked scope, evidence and
limitations.

## Element-analysis registry

- [Elements and route boundaries](../elements/index.md)
- [Analyses map](../analyses/index.md)
- [Consolidated machine-readable registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/consolidated_registry.json)
- [Known limitations](../etat/limites.md)

The registry remains the only authority for the 46 element-analysis maturity
counts. This index must not be used to infer a broader element or analysis
qualification.

## Mixed workflows

| Workflow | Status | Authoritative record or evidence |
| --- | --- | --- |
| Connected conforming mixed static | `QUALIFIED_BOUNDED` | [WP07 Owner record](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp07_owner_gate_final.json) |
| Connected conforming mixed modal | `QUALIFIED_BOUNDED` | [WP08B Owner record](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp08b_owner_gate_final.json) |
| Translational MPC mixed static | `QUALIFIED_BOUNDED` | [WP13-03D delivery](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_03d_mixed_mpc_owner_delivery.json) |
| Multi-material mixed static | `QUALIFIED_BOUNDED` | [WP13-04D delivery](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_04d_multimaterial_owner_delivery.json) |
| Mixed Newmark linear dynamics | `EXPERIMENTAL_BOUNDED` | [WP13-02D delivery](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02d_mixed_dynamics_delivery.json) |
| Mixed harmonic linear response | `EXPERIMENTAL_BOUNDED` | [WP13-02D delivery](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_02d_mixed_dynamics_delivery.json) |
| Distributed mixed PETSc/MPI runtime | `NOT_VALIDATED` | [0.2.8 verification history](../verification/0_2_8/README.md) |

The distributed mixed PETSc/MPI route is architecture evidence only. Its
runtime physical and partition gates failed; the partial two-rank result is
not a public qualification claim.

## Separate experimental capabilities

| Capability | Status | Authoritative record |
| --- | --- | --- |
| Bounded Abaqus/CalculiX `.inp` importer | `EXPERIMENTAL_BOUNDED` | [WP13-05 capability record](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_05_inp_import_capability_record.json) |
| Family-aware mixed HDF5 result storage | `EXPERIMENTAL_BOUNDED` | [WP13-06D capability record](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_06d_mixed_hdf5_capability_record.json) |
| Frictionless penalty node-to-triangle contact | `EXPERIMENTAL_BOUNDED` | [WP13-07D capability record](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_07d_contact_capability_record.json) |
| HEX8 selective reduced integration | `EXPERIMENTAL_BOUNDED` | [WP10 Owner record](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp10_hex8_sri_owner_gate_final.json) |

These capabilities remain opt-in or route-specific. They do not promote any
element-analysis combination in the 46-record registry.

## Internal and research routes

| Route | Status | Reference |
| --- | --- | --- |
| PYRAMID5 | `INTERNAL / RESEARCH_ONLY` | [WP13-10 maturation evidence](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_10_pyramid5_maturation/wp13_10_pyramid5_maturation_evidence.json) |
| Geometric nonlinear discovery | `RESEARCH_ONLY` | [WP13-11 evidence](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_11_geometric_nonlinear_discovery/manifest.json) |
| High-order mixed-interface feasibility | `RESEARCH_ONLY` | [WP13-09 evidence](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/wp13_09_high_order_interface_feasibility/wp13_09_feasibility_evidence.json) |

These entries are visible for traceability only. They are not stable public
solver capabilities and must not be used as production or qualification claims.

## Public entry points

- [V&V and evidence model](../verification/evidence-and-maturity.md)
- [0.2.8 What's New](../whats-new/0.2.8.md)
- [Installation](../getting-started/installation.md)
- [API stability](../reference/api_stability.md)
- [Known limitations](../etat/limites.md)
- [Historical 0.2.7 verification](../verification/0_2_7/README.md)
