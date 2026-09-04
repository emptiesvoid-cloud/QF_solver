---
doc_id: DOC-027-001
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# QF Solver 0.2.7 verification

This page is the readable entry point to the 0.2.7 evidence pack. It separates
the active public conclusion from the internal qualification trace. Historical
records are preserved unchanged and are labelled as historical in their own
documents.

## Public conclusion

The 0.2.7 qualification is complete for its declared, bounded scope. The
evidence supports the following summary:

| Area | Public conclusion |
| --- | --- |
| Solid elements | TET4, TET10, HEX8 and HEX20 have bounded recorded routes. |
| Small-strain J2 | `QUALIFIED_BOUNDED` for TET4, TET10, HEX8 and HEX20 within the active constitutive scope. |
| WEDGE6 static | `EXPERIMENTAL`, limited to the recorded small-strain elastic workflow. |
| WEDGE6 modal | `QUALIFIED_BOUNDED`, limited to the homogeneous isotropic first-three-mode consistent-mass scope. |
| Large models | 1M, 3M and 5M evidence is bounded to the recorded structured TET4 PETSc/MPI route; 10M remains a bounded C3 result. |
| External correlation | Code_Aster is bounded to comparable recorded cases. CalculiX is `NOT_COMPARABLE` where observables or conventions do not match. |
| Release state | Stable source release `0.2.7` at tag `v0.2.7`; limitations remain part of the claim. |

No result here is a universal certification, hardware-independent scaling law or
general physical validation.

## Evidence navigation

- [Capability matrix](0_2_7_capability_matrix.md)
- [Large-model evidence](0_2_7_large_scale_readiness.md)
- [Qualification campaign records](0_2_7_gate_matrix.md)
- [Release audit records](0_2_7_release_workflow_audit.md)
- [WEDGE6 static boundary](0_2_7_wedge6_static_vertical_slice.md)
- [WEDGE6 modal boundary](0_2_7_wedge6_modal.md)
- [S3 expanded validation](0_2_7_s3_expanded_validation.md)
- [WEDGE6 robustness and external V&V](0_2_7_wedge6_robustness_external_vnv.md)

Machine-readable records are indexed by
[`qualification/0_2_7/manifest.json`](../../../qualification/0_2_7/manifest.json),
[`capability_registry_v2.json`](../../../qualification/0_2_7/capability_registry_v2.json)
and [`release_truth.json`](../../../qualification/0_2_7/release_truth.json).

## Known limitations

- WEDGE6 static remains experimental; static and modal maturity are not
  interchangeable.
- WEDGE15, PYRAMID5, generalized mixed meshes, HEX8R, SRI and B-bar production
  routes are deferred or not supported.
- Finite-kinematic J2, generalized nonlinear, frictional contact and
  finite-sliding production routes are not qualified.
- 5M Gold and deeper 10M scaling analysis are deferred.
- Optional PETSc/MPI routes are bounded by the recorded environment. Untested
  Python versions and operating systems are not claimed as verified.

## Internal qualification traceability

Historical pre-closure views may retain `46/50` or `96/100`; these scores are
preserved for traceability and do not override the active conclusion above.

The detailed work-package, gate and audit records are retained for provenance.
They are implementation and governance history, not user-facing capability
labels. The main records are:

- [qualification gates](0_2_7_gate_matrix.md)
- [progress history](0_2_7_progress_tracker.md)
- [release readiness record](0_2_7_r0_release_readiness.md)
- [test-quality audit](0_2_7_f4_unit_test_quality_audit.md)
- [packaging audit](0_2_7_f5_packaging_compatibility_audit.md)
- [numerical regression audit](0_2_7_f6_numerical_performance_regression_audit.md)
- [master plan and risk register](0_2_7_master_plan.md)

The remaining controlled records are available from this evidence index:

- [1M plan](0_2_7_1m_dof_plan.md)
- [element descriptor preflight](0_2_7_element_descriptor_preflight.md)
- [external oracle plan](0_2_7_external_oracle_plan.md)
- [J2 gap closure](0_2_7_j2_gap_closure.md)
- [large-scale readiness](0_2_7_large_scale_readiness.md)
- [LU2 maturity](0_2_7_lu2_wp07_maturity.md)
- [LU2 scope decisions](0_2_7_lu2_wp08_decisions.md)
- [mesh quality contract](0_2_7_mesh_quality_contract.md)
- [mesh quality plan](0_2_7_mesh_quality_plan.md)
- [owner decision log](0_2_7_owner_decision_log.md)
- [release criteria](0_2_7_release_criteria.md)
- [release workflow audit](0_2_7_release_workflow_audit.md)
- [risk register](0_2_7_risk_register.md)
- [assembly telemetry](0_2_7_s1_assembly_telemetry.md)
- [test policy](0_2_7_test_policy.md)
- [V&V harness](0_2_7_vnv_harness_v2.md)
- [V&V strategy](0_2_7_vnv_strategy.md)
- [WEDGE6 external review](0_2_7_wedge6_external_review.md)
- [WEDGE6 formulation contract](0_2_7_wedge6_formulation_contract.md)
- [WEDGE6 kernel](0_2_7_wedge6_kernel.md)
- [WEDGE6 plan](0_2_7_wedge6_plan.md)
- [WEDGE6 static slice](0_2_7_wedge6_static_vertical_slice.md)
- [observatory](0_2_7_wp01_observatory.md)
- [configuration freeze](0_2_7_wp02_configuration_freeze.md)
- [3M compute](0_2_7_wp03_3m_gold_compute.md)
- [5M Bronze](0_2_7_wp04_5m_bronze.md)
- [5M forensic audit](0_2_7_wp04_forensic_audit.md)
- [execution contract](0_2_7_wp06_execution_contract.md)
- [S3 closeout](0_2_7_wp09_s3_closeout.md)
- [J2 closeout](0_2_7_wp11_j2_closure.md)
- [golden baseline](0_2_7_wp13_golden_baseline.md)
- [large-scale contract](0_2_7_wp14_large_scale_contract.md)
- [matrix-free study](0_2_7_wp15_matrix_free.md)
- [1M qualification record](0_2_7_wp16_1m_qualification.md)
- [final PETSc path](0_2_7_wp17_final.md)
- [solver stack](0_2_7_wp17_solver_stack.md)
- [PETSc remediation](0_2_7_wp17r_petsc_remediation.md)
- [3M ladder](0_2_7_wp18_3m_ladder.md)
- [HEX8 robustness](0_2_7_wp19_robustness_hex8.md)
- [J2 closeout](0_2_7_wp20_j2_closeout.md)
- [F1 architecture audit](0_2_7_f1_architecture_audit.md)
- [F2 bug hunt](0_2_7_f2_bug_hunt.md)
- [F3 public claims audit](0_2_7_f3_public_claim_audit.md)
- [F4 test-quality audit](0_2_7_f4_unit_test_quality_audit.md)
- [F5 packaging audit](0_2_7_f5_packaging_compatibility_audit.md)
- [F6 regression audit](0_2_7_f6_numerical_performance_regression_audit.md)
- [WEDGE6 robustness](0_2_7_wedge6_robustness_external_vnv.md)
- [WEDGE6 modal](0_2_7_wedge6_modal.md)
- [S3 validation matrix](0_2_7_s3_expanded_validation.md)
- [step freeze record](0_2_7_step1_release_freeze.md)
- [release manifest](../../../qualification/0_2_7/manifest.json)
- [gate records](../../../qualification/0_2_7/gates.json)
- [release truth](../../../qualification/0_2_7/release_truth.json)
- [S3 evidence](../../../qualification/0_2_7/s3_validation_matrix.json)
- [F6 evidence](../../../qualification/0_2_7/f6_numerical_performance_regression_audit.json)

References to earlier prerelease versions, intermediate scores and planned
work packages in this traceability area describe the state at that time. They
do not override the active 0.2.7 conclusion above.
