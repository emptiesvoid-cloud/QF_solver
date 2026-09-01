---
doc_id: DOC-027-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.7a0 Foundation

**Prismatic solid interoperability and numerical robustness.**

This directory is the controlled evidence pack for the `0.2.7a0` development
cycle. It is not a release claim. WP01 release truth and provenance is `PASS`; WP02 is `PASS` for the
capability-registry control; WP03 is `PASS` for the descriptor/preflight
control; WP04 is `PASS` for the additive V&V harness; WP05 is `PASS` for the
external deck preflight only; WP06 is `PASS` for an additive mesh-quality
diagnostic contract; WP07 is `PASS` for the experimental elemental WEDGE6
kernel and its targeted V&V; WP10 is `PASS_WITH_LIMITATIONS` with modal maturity
`QUALIFIED_BOUNDED` within its declared scope; WP12 is `PASS_WITH_LIMITATIONS` for bounded large-scale
readiness evidence; WP11 is `PASS_WITH_LIMITATIONS` with Owner review required,
while WP13-WP14 remain `NOT_STARTED`.

## Baseline and status

| Item | Value |
| --- | --- |
| Target version | `0.2.7a0` |
| Theme | Prismatic solid interoperability and numerical robustness |
| Authoritative starting point | `e839373b6aef291a93292186d7553ba5cd12af55` |
| Starting branch | `main` at the recorded baseline |
| Foundation branch | Dedicated 0.2.7 foundation branch |
| Numerical source changed by this pack | No |
| WEDGE6 implemented by this pack | Technical elemental kernel only |
| Release/tag/PyPI action | None |

The `0.2.6a0` qualification remains a historical tagged baseline. Its gate
records and evidence are not rewritten by this plan. The `0.2.7a0` records
below distinguish executed WP01-WP07 evidence from the later proposed work.

## Direction

The cycle prioritizes a controlled prismatic-solid path and better numerical
diagnostics. It deliberately avoids a broad physics expansion. The proposed
sequence is:

1. establish release truth, provenance and a capability registry that can
   express element/analysis/material/route combinations;
2. add additive compatibility descriptors and a declarative V&V harness;
3. preflight independent C3D6/PENTA6 oracles before WEDGE6 implementation
   (completed in WP05);
4. define mesh-quality and distortion policies;
5. implement the WEDGE6 elemental kernel (WP07), then qualify a static vertical slice and modal path;
6. close existing J2 V&V gaps and characterize larger models;
7. keep stretch research work separate from the bounded release path.

## Work package map

The detailed plan, dependencies and STOP/GO criteria are in
[`0_2_7_master_plan.md`](0_2_7_master_plan.md). The current status is tracked
in [`0_2_7_progress_tracker.md`](0_2_7_progress_tracker.md).

| WP | Focus | Initial status |
| --- | --- | --- |
| WP01 | Release truth and provenance | `PASS` |
| WP02 | Capability registry v2 | `PASS` |
| WP03 | Element descriptors and compatibility preflight | `PASS` |
| WP04 | Additive declarative V&V harness | `PASS` |
| WP05 | C3D6/PENTA6 external-oracle preflight | `PASS` |
| WP06 | Mesh quality and distortion contract | `PASS` |
| WP07 | WEDGE6 kernel and elemental V&V | `PASS` (`EXPERIMENTAL`) |
| WP08 | WEDGE6 static vertical slice | `PASS` (`EXPERIMENTAL`) |
| WP09 | WEDGE6 robustness and external V&V | `PASS_WITH_LIMITATIONS` (`EXPERIMENTAL`) |
| WP10 | WEDGE6 modal qualification | `PASS_WITH_LIMITATIONS` (`QUALIFIED_BOUNDED`, bounded) |
| WP11 | Existing capability maturity and J2 gaps | `PASS_WITH_LIMITATIONS` (Owner review required) |
| WP12 | Large-scale and 1M-DOF readiness | `PASS_WITH_LIMITATIONS` |
| WP13 | Research/stretch candidates | `NOT_STARTED` |
| WP14 | Documentation, regression and Owner release review | `NOT_STARTED` |

## Reading rules

`SUPPORTED` means that an implementation path is available. `TESTED` means
that a case was executed. `VERIFIED` means that an oracle or invariant was
checked. `QUALIFIED_BOUNDED` requires a recorded Owner decision for a declared
scope. `EXPERIMENTAL` and `NOT_QUALIFIED` are valid outcomes and are never
promoted by test count alone.

The pack uses `PROPOSED_OWNER_REVIEW` whenever a numerical threshold is not
already justified by an existing controlled policy. No threshold is silently
invented from a future result. External-tool unavailability is recorded as an
explicit skip or limitation, never as `PASS`.

## Machine-readable records

- [`qualification/0_2_7/gates.json`](../../../qualification/0_2_7/gates.json)
- [`qualification/0_2_7/requirements.json`](../../../qualification/0_2_7/requirements.json)
- [`qualification/0_2_7/progress.json`](../../../qualification/0_2_7/progress.json)
- [`qualification/0_2_7/manifest.json`](../../../qualification/0_2_7/manifest.json)
- [`qualification/0_2_7/release_truth.json`](../../../qualification/0_2_7/release_truth.json)
- [`qualification/0_2_7/release_workflow_audit.json`](../../../qualification/0_2_7/release_workflow_audit.json)
- [`qualification/0_2_7/capability_registry_v2.json`](../../../qualification/0_2_7/capability_registry_v2.json) (source of truth)
- [`qualification/0_2_7/registry_migration.json`](../../../qualification/0_2_7/registry_migration.json)
- [`qualification/0_2_7/wp03_state.json`](../../../qualification/0_2_7/wp03_state.json)
- [`qualification/0_2_7/wp05_state.json`](../../../qualification/0_2_7/wp05_state.json)
- [`qualification/0_2_7/external_oracles/wedge6/contract.json`](../../../qualification/0_2_7/external_oracles/wedge6/contract.json)
- [`qualification/0_2_7/external_oracles/wedge6/preflight_evidence.json`](../../../qualification/0_2_7/external_oracles/wedge6/preflight_evidence.json)
- [`qualification/0_2_7/wp12_state.json`](../../../qualification/0_2_7/wp12_state.json)
- [`qualification/0_2_7/wp12_scaling_evidence.json`](../../../qualification/0_2_7/wp12_scaling_evidence.json)
- [`qualification/0_2_7/wp12_assembly_probe_300k.json`](../../../qualification/0_2_7/wp12_assembly_probe_300k.json)
- [`qualification/0_2_7/wp10_state.json`](../../../qualification/0_2_7/wp10_state.json)
- [`qualification/0_2_7/vnv_v2/wp10_cases.json`](../../../qualification/0_2_7/vnv_v2/wp10_cases.json)
- [`qualification/0_2_7/vnv_v2/wp10_evidence.json`](../../../qualification/0_2_7/vnv_v2/wp10_evidence.json)
- [`qualification/0_2_7/wp10_final_state.json`](../../../qualification/0_2_7/wp10_final_state.json)
- [`qualification/0_2_7/vnv_v2/wp10_final_cases.json`](../../../qualification/0_2_7/vnv_v2/wp10_final_cases.json)
- [`qualification/0_2_7/vnv_v2/wp10_final_evidence.json`](../../../qualification/0_2_7/vnv_v2/wp10_final_evidence.json)
- [`qualification/0_2_7/external_oracles/wedge6/results/wp10_code_aster_modal.json`](../../../qualification/0_2_7/external_oracles/wedge6/results/wp10_code_aster_modal.json)

## Controlled documents

- [`0_2_7_master_plan.md`](0_2_7_master_plan.md)
- [`0_2_7_gate_matrix.md`](0_2_7_gate_matrix.md)
- [`0_2_7_progress_tracker.md`](0_2_7_progress_tracker.md)
- [`0_2_7_test_policy.md`](0_2_7_test_policy.md)
- [`0_2_7_vnv_strategy.md`](0_2_7_vnv_strategy.md)
- [`0_2_7_external_oracle_plan.md`](0_2_7_external_oracle_plan.md)
- [`0_2_7_wedge6_plan.md`](0_2_7_wedge6_plan.md)
- [`0_2_7_mesh_quality_plan.md`](0_2_7_mesh_quality_plan.md)
- [`0_2_7_mesh_quality_contract.md`](0_2_7_mesh_quality_contract.md)
- [`0_2_7_j2_gap_closure.md`](0_2_7_j2_gap_closure.md)
- [`0_2_7_1m_dof_plan.md`](0_2_7_1m_dof_plan.md)
- [`0_2_7_risk_register.md`](0_2_7_risk_register.md)
- [`0_2_7_owner_decision_log.md`](0_2_7_owner_decision_log.md)
- [`0_2_7_release_criteria.md`](0_2_7_release_criteria.md)
- [`0_2_7_release_workflow_audit.md`](0_2_7_release_workflow_audit.md)
- [`0_2_7_capability_matrix.md`](0_2_7_capability_matrix.md) (generated view)
- [`0_2_7_element_descriptor_preflight.md`](0_2_7_element_descriptor_preflight.md)
- [`0_2_7_vnv_harness_v2.md`](0_2_7_vnv_harness_v2.md)
- [`0_2_7_wedge6_external_review.md`](0_2_7_wedge6_external_review.md)
- [`0_2_7_large_scale_readiness.md`](0_2_7_large_scale_readiness.md)
- [`0_2_7_wedge6_modal.md`](0_2_7_wedge6_modal.md)

## Foundation boundary

WP03 installs technical descriptors and a fail-closed compatibility preflight
on top of the source-controlled combination registry. WP07 adds only the
authorized WEDGE6 elemental kernel; it does not implement
WEDGE15, PYRAMID5, HEX8R or any new
formulation. It does not change the 0.2.6 Owner decisions for TL, Arc-Length,
J2, buckling, contact, performance or external correlations. A later work
package must complete the static/import/load/post contracts before making a
user-facing static WEDGE6 claim. The static WEDGE6 registry maturity remains
`EXPERIMENTAL`; the separate modal combination is `QUALIFIED_BOUNDED` only
within its final declared scope.

WP10 adds a separate modal route using consistent translational mass and the
common modal solver. Its first-three-mode refinement and four same-mesh
Code_Aster frequency/MAC cases support a bounded modal qualification; it does
not transfer the static WP07-WP09 evidence or qualify other dynamic routes.

WP12 is a bounded readiness study, not a general scalability guarantee. Its
current evidence is limited to the generated structured TET4 linear-static
route and the recorded environment; Owner closeout remains pending.
