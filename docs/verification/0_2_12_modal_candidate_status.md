# QF Solver 0.2.12 candidate — modal status and CI evidence

Status date: 2026-11-06. This note classifies candidate maturity and records
existing evidence. It does not change a tolerance, residual, oracle, solver
result, historical record, or Owner decision.

## Candidate maturity

The classical modal route in candidate 0.2.12 is EXPERIMENTAL. The residual
certification is bounded. A case exceeding a dimension, stored-term, or
aggregate-work limit is INCONCLUSIVE under the default strict policy. The
solver does not make that result a certified usable basis. An explicit
allow_inconclusive option may expose a computed candidate for controlled
compatibility use, but its status stays INCONCLUSIVE and derived responses
are not certified evidence. FAIL remains a failure.

For an individual case, PASS means only that its declared criterion was
demonstrated; PASS_CERTIFIED applies only to the bounded residual criterion.
INCONCLUSIVE means the available evidence cannot decide the criterion. NOT_RUN
means the check was not executed. These scientific statuses are separate from
GitHub Actions conclusions: a failing CI test remains a failed CI test, and
an INCONCLUSIVE scientific result is not CI PASS.

## Existing modal CI failures

The historical run [#42090387548](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/42090387548)
tested source 8c83eb9a521c9d35520cbd357f8e09475e758374, not the clean
integration candidate. Its modal-related failures were certification-budget
refusals. The diagnostic records nine modal nodeids:

- tests/unit/test_code_aster_mitc3_dynamic.py::test_mitc3_dynamic_qf_model_has_same_resultant_and_tip_mean_probe
- tests/unit/test_mitc4_modal_external.py::test_same_mesh_modal_comparison_accepts_identical_external_modes
- tests/unit/test_modal_basis_damping.py::test_prepared_modal_basis_supports_each_wp00_family[HEX20]
- tests/unit/test_modal_newmark.py::test_modal_newmark_integrates_each_wp00_family_in_bounded_full_basis[HEX20]
- tests/unit/test_modal_newmark.py::test_wp07_uniform_base_acceleration_integrates_each_wp00_family[HEX20]
- tests/unit/test_reduced_harmonic.py::test_new_method_runs_on_each_bounded_element_family[HEX20]
- tests/unit/test_wp10_final_modal.py::test_final_runner_preserves_explicit_external_skip
- tests/unit/test_wp10_wedge6_modal.py::test_distorted_modal_case_and_refinement_are_reported_without_monotonic_claim
- tests/integration/test_hex20_workflow.py::test_hex20_uses_common_static_modal_newmark_and_harmonic_paths

On that historical source, the scientific modal status for these certification
cases is INCONCLUSIVE; the corresponding CI tests failed because their
assertions require a usable certified result. The underlying certification
limits were 128 DDL, 1,024 combined stored K+M terms, and 65,536 estimated work
units. These cases are not new measurements on the clean integration commit.

## HEX20 campaign result

The historical
tests/unit/test_hex20_campaign.py::test_hex20_internal_campaign_covers_analysis_j2_and_three_model_comparison
reported an aggregate FAIL where its test expected PASS_INTERNAL. The modal
subcheck was not certified within the bounded validator. The overall FAIL is
preserved. Any independent failing subcheck remains FAIL and is not covered by
the experimental classification of the modal route.

The reporting change exposes modal_certification and does not promote
INCONCLUSIVE or FAIL. The synthetic status-reporting checks previously
recorded as passing are not a replacement for running the actual HEX20
campaign.

## Candidate test state

The clean integration commit
e81c7241f6ea8aa8948a84113b1a5f05926120c2 had no remote CI run as of the time
this note was prepared. The Tet4 package/CLI test
tests/integration/test_packaging.py::test_solver_cli_module_check_mesh_and_solve_run
passed locally once on that commit; this is not modal validation. Actual
modal FEM tests and the actual HEX20 campaign were NOT_RUN on that clean
commit. Their next CI status must be read from the run associated with the
PR merge SHA and must remain distinct from their scientific status.

## WP12 boundary

WP12 remains closed only as
WP12_CLOSED_BOUNDED_FOR_0_2_12_ALPHA for its 17 MUST dispositions; 39 SHOULD
and 6 DEFERRED remain. This is not general solver qualification or a scientific
replay on the release head. Preserve the TET4-L3 energy FAIL, both HEX8-SRI
FAILs with post-correction global validation NOT_ACQUIRED, and the HEX20
QUAD8 R4 FAIL with corrective FEM validation NOT_ACQUIRED. No status here
promotes those results.
