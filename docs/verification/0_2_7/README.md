---
doc_id: DOC-027-001
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.7a0 Foundation and Level-Up

**Reproducible large-model solving and numerical trust.**

This directory is the controlled evidence pack for the `0.2.7a0` development
cycle. It is not a release claim. WP01 release truth and provenance is `PASS`; WP02 is `PASS` for the
capability-registry control; WP03 is `PASS` for the descriptor/preflight
control; WP04 is `PASS` for the additive V&V harness; WP05 is `PASS` for the
external deck preflight only; WP06 is `PASS` for an additive mesh-quality
diagnostic contract; WP07 is `PASS` for the experimental elemental WEDGE6
kernel and its targeted V&V; WP10 is `PASS_WITH_LIMITATIONS` with modal maturity
`QUALIFIED_BOUNDED` within its declared scope; WP12 is `PASS_WITH_LIMITATIONS` for bounded large-scale
readiness evidence; WP11 is `PASS_WITH_LIMITATIONS` with its Owner review
closed by the WP20 bounded J2 decision, while the foundation WP01-WP12
evidence remains preserved. The official
Level-Up portfolio is `CLOSED / ACCEPT_WITH_CONSOLIDATION`; WP13 is `PASS` on
its controlled golden-baseline evidence and WP14 is `PASS` on its frozen
execution contract; WP15 is `PASS_WITH_LIMITATIONS` on controlled subscale
evidence, WP16 is `PASS` on the official PETSc 1M retry, WP17 is
`PASS_WITH_LIMITATIONS` after its PETSc/MPI closure, and WP18 is
`PASS_WITH_LIMITATIONS` after its Bronze/Silver ladder; WP19 is
`PASS_WITH_LIMITATIONS` on bounded adversarial and HEX8 diagnostic evidence;
WP20 is `PASS_WITH_LIMITATIONS` for the existing bounded small-strain J2
scope. WP21 is `PASS_WITH_LIMITATIONS` for surgical compatibility and
release-truth cleanup; WP22 remains `PLANNED` for final Owner release action.

F4 is `PASS_WITH_LIMITATIONS`: the unit-test quality audit found no P0/P1
release blocker, strengthened critical negative-test exception contracts and
added guards for bounded maturity, evidence and skip policy. F5 is now
`PASS_WITH_LIMITATIONS`: clean wheel and sdist installs, public API/CLI smoke
tests and runtime resource checks pass on the directly verified Windows
environments; one packaging P1 was fixed. Python 3.10/3.13 Linux/Windows are
CI-declared, while Python 3.11, macOS and optional external runtimes remain
bounded limitations. No numerical source, historical evidence or maturity
was changed.

The historical Level-Up 1 machine-readable source is
`qualification/0_2_7/level_up_plan.json`. WP16's 1M-DOF requirement is
satisfied for its declared PETSc/TET4 scope; WP18 is mandatory and distinguishes Bronze model/preflight,
Silver full solve and Gold distributed/restart evidence. Silver has completed
two 3M solves on the declared route; Gold remains unattempted and unclaimed.
No record promotes capability maturity.

## Baseline and status

| Item | Value |
| --- | --- |
| Target version | `0.2.7a0` |
| Active theme | Reproducible Large-Model Solving and Numerical Trust |
| Historical foundation theme | Prismatic solid interoperability and numerical robustness |
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
| WP11 | Existing capability maturity and J2 gaps | `PASS_WITH_LIMITATIONS` (Owner-approved bounded scope) |
| WP12 | Large-scale and 1M-DOF readiness | `PASS_WITH_LIMITATIONS` |
| WP13 | Release truth and golden numerical baseline | `PASS` |
| WP14 | Large-scale execution contract | `PASS` |
| WP15 | Matrix-Free TET4 V2 / SPD / preconditioning | `PASS_WITH_LIMITATIONS` |
| WP16 | True 1M-DOF qualification | `PASS` (bounded PETSc/TET4 scope) |
| WP17 | PETSc/MPI and large sparse path | `PASS_WITH_LIMITATIONS` |
| WP18 | 3M DOF ladder Bronze/Silver/Gold | `PASS_WITH_LIMITATIONS` |
| WP19 | Adversarial robustness and HEX8 diagnostic | `PASS_WITH_LIMITATIONS` |
| WP20 | Residual J2 and external V&V closure | `PASS_WITH_LIMITATIONS` (bounded existing scope) |
| WP21 | Architecture, API and registry surgical cleanup | `PASS_WITH_LIMITATIONS` (broader redesign deferred) |
| WP22 | Final release qualification | `PLANNED` |
| Foundation WP13-WP14 proposal | Superseded by the Level-Up namespace | `PRESERVED_HISTORY` |

The active LU2 accounting is `46/50` and `96/100` globally. LU2-WP04 and
LU2-WP05 are now closed, while LU2-WP06, LU2-WP07 and LU2-WP08 are
closed as `PASS_WITH_LIMITATIONS`: mixed TET/WEDGE/HEX is deferred without an
end-to-end claim; WEDGE15 and PYRAMID5 are not supported; and HEX8R, SRI,
B-bar and hourglass control remain research/deferred. The detailed decision
record is [`0_2_7_lu2_wp08_decisions.md`](0_2_7_lu2_wp08_decisions.md), with
the machine-readable matrix at
[`lu2_wp08_decision_matrix.json`](../../../qualification/0_2_7/lu2_wp08_decision_matrix.json).

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
- [`qualification/0_2_7/wp21_state.json`](../../../qualification/0_2_7/wp21_state.json)
- [`qualification/0_2_7/wp21_final_release_truth.json`](../../../qualification/0_2_7/wp21_final_release_truth.json)
- [`qualification/0_2_7/wp21_public_document_audit.json`](../../../qualification/0_2_7/wp21_public_document_audit.json)
- [`qualification/0_2_7/f3_public_claim_audit.json`](../../../qualification/0_2_7/f3_public_claim_audit.json) (F3 claims source)
- [`0_2_7_f3_public_claim_audit.md`](0_2_7_f3_public_claim_audit.md) (F3 review view)
- [`qualification/0_2_7/golden/wp21_replay_evidence.json`](../../../qualification/0_2_7/golden/wp21_replay_evidence.json)
- [`qualification/0_2_7/release_workflow_audit.json`](../../../qualification/0_2_7/release_workflow_audit.json)
- [`qualification/0_2_7/capability_registry_v2.json`](../../../qualification/0_2_7/capability_registry_v2.json) (source of truth)
- [`qualification/0_2_7/lu2_wp08_decision_matrix.json`](../../../qualification/0_2_7/lu2_wp08_decision_matrix.json)
- [`qualification/0_2_7/lu2_wp08_state.json`](../../../qualification/0_2_7/lu2_wp08_state.json)
- [`qualification/0_2_7/registry_migration.json`](../../../qualification/0_2_7/registry_migration.json)

`progress.json` conserve un champ composite issu des anciennes vues; pour
l'etat courant LU2, utiliser `level_up_2_state.json` et
`level_up_2_index.json`. Cette distinction preserve la provenance sans
requalifier ni reecrire les snapshots historiques.
- [`qualification/0_2_7/wp03_state.json`](../../../qualification/0_2_7/wp03_state.json)
- [`qualification/0_2_7/wp05_state.json`](../../../qualification/0_2_7/wp05_state.json)
- [`qualification/0_2_7/external_oracles/wedge6/contract.json`](../../../qualification/0_2_7/external_oracles/wedge6/contract.json)
- [`qualification/0_2_7/external_oracles/wedge6/preflight_evidence.json`](../../../qualification/0_2_7/external_oracles/wedge6/preflight_evidence.json)
- [`qualification/0_2_7/wp12_state.json`](../../../qualification/0_2_7/wp12_state.json)
- [`qualification/0_2_7/wp12_scaling_evidence.json`](../../../qualification/0_2_7/wp12_scaling_evidence.json)
- [`qualification/0_2_7/wp12_assembly_probe_300k.json`](../../../qualification/0_2_7/wp12_assembly_probe_300k.json)
- [`qualification/0_2_7/wp16_runtime/wp16_retry_summary.json`](../../../qualification/0_2_7/wp16_runtime/wp16_retry_summary.json)
- [`qualification/0_2_7/wp16_runtime/wp16_retry_run1_raw.json`](../../../qualification/0_2_7/wp16_runtime/wp16_retry_run1_raw.json)
- [`qualification/0_2_7/wp16_runtime/wp16_retry_run2_raw.json`](../../../qualification/0_2_7/wp16_runtime/wp16_retry_run2_raw.json)
- [`qualification/0_2_7/wp16_runtime/wp16_retry_subscale_raw.json`](../../../qualification/0_2_7/wp16_runtime/wp16_retry_subscale_raw.json)
- [`qualification/0_2_7/wp18_runtime/wp18_summary.json`](../../../qualification/0_2_7/wp18_runtime/wp18_summary.json)
- [`qualification/0_2_7/wp18_state.json`](../../../qualification/0_2_7/wp18_state.json)
- [`qualification/0_2_7/wp19_state.json`](../../../qualification/0_2_7/wp19_state.json)
- [`qualification/0_2_7/wp19_cases.json`](../../../qualification/0_2_7/wp19_cases.json)
- [`qualification/0_2_7/wp19_runtime/wp19_robustness_summary.json`](../../../qualification/0_2_7/wp19_runtime/wp19_robustness_summary.json)
- [`qualification/0_2_7/wp19_runtime/wp19_robustness_evidence.json`](../../../qualification/0_2_7/wp19_runtime/wp19_robustness_evidence.json)
- [`qualification/0_2_7/wp19_runtime/wp19_hex8_diagnostic.json`](../../../qualification/0_2_7/wp19_runtime/wp19_hex8_diagnostic.json)
- [`qualification/0_2_7/wp19_runtime/wp19_golden_replay.json`](../../../qualification/0_2_7/wp19_runtime/wp19_golden_replay.json)
- [`0_2_7_wp18_3m_ladder.md`](0_2_7_wp18_3m_ladder.md)
- [`0_2_7_wp16_1m_qualification.md`](0_2_7_wp16_1m_qualification.md)
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
- [`0_2_7_wp19_robustness_hex8.md`](0_2_7_wp19_robustness_hex8.md)
- [`0_2_7_f2_bug_hunt.md`](0_2_7_f2_bug_hunt.md)

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

The active successor is Level-Up 2, installed from the qualified snapshot
`8f08bfb5a6d4dedcd24966f5474e8c12cbfa5bc3`. Its source, state and index are
`qualification/0_2_7/level_up_2_plan.json`,
`qualification/0_2_7/level_up_2_state.json` and
`qualification/0_2_7/level_up_2_index.json`. LU1 remains a preserved historical
record; LU2 is open at `46/50` (`96/100` globally). LU2-WP03 is closed as
`PASS_WITH_LIMITATIONS`, with `3M_GOLD_COMPUTE = PASS` for the controlled
structured TET4/PETSc route. LU2-WP04 and LU2-WP05 are closed as `PASS` for
the recorded 5M Bronze and two-replay Silver scope under the frozen route;
the machine-readable evidence is indexed in
`qualification/0_2_7/level_up_2_state.json`,
`qualification/0_2_7/lu2_wp04_state.json` and
`qualification/0_2_7/lu2_wp05_state.json`. These results do not create a
universal 5M, hardware-independent or non-TET4 claim. The active next gate is
LU2-WP09; the earlier owner-interrupted WP04 attempt remains preserved as
historical forensic evidence.

LU2-WP08 is closed as `PASS_WITH_LIMITATIONS` by
`qualification/0_2_7/lu2_wp08_decision_matrix.json`. Mixed TET/WEDGE/HEX is
deferred without an end-to-end claim; WEDGE15 and PYRAMID5 are not supported;
the existing HEX8 route remains bounded; and HEX8R, SRI, B-bar and hourglass
control remain research/deferred. No new element, formulation or active
capability was added.

For the active claim audit, see
[`qualification/0_2_7/f3_public_claim_audit.json`](../../../qualification/0_2_7/f3_public_claim_audit.json).
For the packaging/install audit, see
[`qualification/0_2_7/f5_packaging_compatibility_audit.json`](../../../qualification/0_2_7/f5_packaging_compatibility_audit.json)
and [`0_2_7_f5_packaging_compatibility_audit.md`](0_2_7_f5_packaging_compatibility_audit.md).
Runtime state and evidence heads take precedence over preserved historical
snapshots in this directory.

## F6 numerical and performance regression audit

F6 starts from clean source SHA
`f6cfde036f5866c15e688bce70be5ed21b493ff1` and closes as
`PASS_WITH_LIMITATIONS`. Targeted element, solver, BC/load/material,
post-processing, MPI/PETSc and governance checks passed. The full suite
completed with `2147 passed, 3 failed, 184 skipped, 2 warnings`; the three
failures reproduce the F4 baseline and remain in experimental or stale
nonlinear paths outside the supported release matrix.

No numerical source, tolerance, active baseline or maturity record changed.
The existing 1M, 3M and 5M replay evidence, representative structured AIJ
preallocation evidence and bounded C3 10M record remain applicable. F6 did
not rerun 5M or 10M because no relevant numerical source change occurred
during F3-F6. The controlled record is
[`qualification/0_2_7/f6_numerical_performance_regression_audit.json`](../../../qualification/0_2_7/f6_numerical_performance_regression_audit.json)
with the review view in
[`0_2_7_f6_numerical_performance_regression_audit.md`](0_2_7_f6_numerical_performance_regression_audit.md).

F6 is technically ready for the separate Owner R0 decision. It does not
start R0, publish artifacts, promote maturity or broaden any performance
claim beyond the recorded workload and environment.
