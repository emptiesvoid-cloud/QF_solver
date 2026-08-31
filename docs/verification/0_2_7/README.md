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

This directory is the controlled planning pack for the `0.2.7a0` development
cycle. It is a foundation, not a release claim and not a record of executed
V&V. WP01 release truth and provenance is `PASS`; WP02-WP14 remain
`NOT_STARTED`.

## Baseline and status

| Item | Value |
| --- | --- |
| Target version | `0.2.7a0` |
| Theme | Prismatic solid interoperability and numerical robustness |
| Authoritative starting point | `e839373b6aef291a93292186d7553ba5cd12af55` |
| Starting branch | `main` at the recorded baseline |
| Foundation branch | Dedicated 0.2.7 foundation branch |
| Numerical source changed by this pack | No |
| WEDGE6 implemented by this pack | No |
| Release/tag/PyPI action | None |

The `0.2.6a0` qualification remains a historical tagged baseline. Its gate
records and evidence are not rewritten by this plan. The `0.2.7a0` records
below describe proposed work and must not be read as executed evidence.

## Direction

The cycle prioritizes a controlled prismatic-solid path and better numerical
diagnostics. It deliberately avoids a broad physics expansion. The proposed
sequence is:

1. establish release truth, provenance and a capability registry that can
   express element/analysis/material/route combinations;
2. add additive compatibility descriptors and a declarative V&V harness;
3. preflight independent C3D6/PENTA6 oracles before any WEDGE6 implementation;
4. define mesh-quality and distortion policies;
5. implement and qualify a WEDGE6 static vertical slice, then its modal path;
6. close existing J2 V&V gaps and characterize larger models;
7. keep stretch research work separate from the bounded release path.

## Work package map

The detailed plan, dependencies and STOP/GO criteria are in
[`0_2_7_master_plan.md`](0_2_7_master_plan.md). The current status is tracked
in [`0_2_7_progress_tracker.md`](0_2_7_progress_tracker.md).

| WP | Focus | Initial status |
| --- | --- | --- |
| WP01 | Release truth and provenance | `PASS` |
| WP02 | Capability registry v2 | `NOT_STARTED` |
| WP03 | Element descriptors and compatibility preflight | `NOT_STARTED` |
| WP04 | Additive declarative V&V harness | `NOT_STARTED` |
| WP05 | C3D6/PENTA6 external-oracle preflight | `NOT_STARTED` |
| WP06 | Mesh quality and distortion contract | `NOT_STARTED` |
| WP07 | WEDGE6 kernel, plan and design review | `NOT_STARTED` |
| WP08 | WEDGE6 static vertical slice | `NOT_STARTED` |
| WP09 | WEDGE6 robustness and external V&V | `NOT_STARTED` |
| WP10 | WEDGE6 modal qualification | `NOT_STARTED` |
| WP11 | Existing capability maturity and J2 gaps | `NOT_STARTED` |
| WP12 | Large-scale and 1M-DOF readiness | `NOT_STARTED` |
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

## Controlled documents

- [`0_2_7_master_plan.md`](0_2_7_master_plan.md)
- [`0_2_7_gate_matrix.md`](0_2_7_gate_matrix.md)
- [`0_2_7_progress_tracker.md`](0_2_7_progress_tracker.md)
- [`0_2_7_test_policy.md`](0_2_7_test_policy.md)
- [`0_2_7_vnv_strategy.md`](0_2_7_vnv_strategy.md)
- [`0_2_7_external_oracle_plan.md`](0_2_7_external_oracle_plan.md)
- [`0_2_7_wedge6_plan.md`](0_2_7_wedge6_plan.md)
- [`0_2_7_mesh_quality_plan.md`](0_2_7_mesh_quality_plan.md)
- [`0_2_7_j2_gap_closure.md`](0_2_7_j2_gap_closure.md)
- [`0_2_7_1m_dof_plan.md`](0_2_7_1m_dof_plan.md)
- [`0_2_7_risk_register.md`](0_2_7_risk_register.md)
- [`0_2_7_owner_decision_log.md`](0_2_7_owner_decision_log.md)
- [`0_2_7_release_criteria.md`](0_2_7_release_criteria.md)
- [`0_2_7_release_workflow_audit.md`](0_2_7_release_workflow_audit.md)

## Foundation boundary

This pack does not implement WEDGE6, WEDGE15, PYRAMID5, HEX8R or any new
formulation. It does not change the 0.2.6 Owner decisions for TL, Arc-Length,
J2, buckling, contact, performance or external correlations. A later work
package may stop before implementation if the formulation, oracle, quality or
provenance contract cannot be made reproducible.
