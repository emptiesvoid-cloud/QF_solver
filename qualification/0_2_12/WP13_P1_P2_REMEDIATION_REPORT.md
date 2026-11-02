# QF Solver 0.2.12 P1/P2 Remediation Report

## Audit identity and scope

- Repository and target branch: `emptiesvoid-cloud/QF_solver`, `emptiesvoids-cloud/0.2.12`.
- Audited source commit: `d31614f59341d175d8e2daade92daf7d8149d199`.
- Audited source tree: `d11b456a045955efb9563acf43b031bd77fab2ae`.
- Findings register SHA-256: `213b4502e7e3b93a783425c209c388a38e2efd7ead1cd6f9b8c663b8ac83e504`.
- Remediation roadmap SHA-256: `0e32b322111891a648fb3b14faffa037097d9403b70b4068ecb1af8cf61b37bd`.
- Corrective branch is based directly on the audited commit; the P1 spring rejection is retained unchanged from its prior commit.

The register and roadmap identify DA-002 through DA-005 as the four demonstrated P2 code defects. The remaining DA-006/DA-007 entries are proof limitations, not newly demonstrated code defects. DA-H01 and DA-H02 remain hypotheses.

## P2 disposition

| Finding | Status | Correction and evidence | Limits |
| --- | --- | --- | --- |
| DA-002 — contact residual reported as zero | FIXED | Contact solver metadata now emits `residual_norm: null`, `relative_residual_norm: null`, and `residual_status: NOT_COMPUTABLE`. Synthetic JSON serialization test passes. | Contact numerical behavior was not rerun; this change only corrects the meaning of reported metadata. Consumers must handle unavailable residuals. |
| DA-003 — TET4/HEX20 thresholds depend on length units | FIXED | TET4 volume and HEX20 Jacobian checks now use a dimensionless signed determinant normalized by the local matrix 2-norm, retaining the `1e-14` relative shape threshold. Tests accept scales `1e-5`, `1`, and `1e5`; inverted and degenerate cases remain rejected. | Direct element geometry/kernel checks only; no global FEM solution or qualification was run. |
| DA-004 — non-finite nodal loads pass mesh validation | FIXED | The common mesh validation boundary rejects non-finite nodal values with an indexed error. NaN and both infinities are covered. A finite load on a fixed DOF remains reportable as a reaction in a synthetic audit and serializes as strict JSON. | The synthetic reaction record checks unchanged reporting/serialization logic, not a solved structural response. |
| DA-005 — unit-floor residuals and unchecked residual limits | FIXED | Linear, harmonic, and Newmark residual ratios no longer use a unit-sized denominator floor. Configured failure limits must be finite positive scalars and are checked before route work. The default limits and their configured values were not changed. A `1e-12` right-hand side with zero solution reports relative residual `1`, and the existing `1e-7` gate rejects it. | Algebraic and route-input tests only. Full harmonic/dynamic FEM compatibility was not rerun under this mandate. |

## P1 retained

The prior P1 fix remains unchanged: `geometric_nonlinear_static` and `linear_buckling` reject discrete springs before mesh validation or assembly. Its original targeted tests remain in the branch. This remediation did not add spring support.

## Targeted tests and checks

All listed pytest invocations selected one exact test-function nodeid per process. Parameterized cases are reported by pytest as individual cases.

| Test nodeid | Result |
| --- | --- |
| `tests/unit/test_da002_contact_residual_metadata.py::test_contact_solver_metadata_serializes_unmeasured_residuals_as_null` | PASS, 1 |
| `tests/unit/test_tet4_element.py::test_tet4_geometry_acceptance_is_independent_of_length_units` | PASS, 3 |
| `tests/unit/test_tet4_element.py::test_tet4_rejects_inverted_or_degenerate_element` | PASS, 1 |
| `tests/unit/test_hex20_element.py::test_hex20_geometry_acceptance_is_independent_of_length_units` | PASS, 3 |
| `tests/unit/test_hex20_element.py::test_hex20_geometry_still_rejects_degenerate_and_inverted_elements` | PASS, 1 |
| `tests/unit/test_da004_nodal_load_validation.py::test_mesh_validator_rejects_nonfinite_nodal_load_values` | PASS, 3 |
| `tests/unit/test_da004_nodal_load_validation.py::test_finite_nodal_load_on_fixed_dof_remains_reportable_and_json_serializable` | PASS, 1 |
| `tests/unit/test_da005_residual_contracts.py::test_residual_failure_tolerances_must_be_finite_positive_scalars` | PASS, 7 |
| `tests/unit/test_da005_residual_contracts.py::test_relative_linear_residual_is_not_hidden_by_unit_floor` | PASS, 1 |
| `tests/unit/test_da005_residual_contracts.py::test_relative_residual_defines_exact_zero_reference` | PASS, 1 |
| `tests/unit/test_da005_residual_contracts.py::test_analysis_routes_reject_nonfinite_residual_limits_before_mesh_work` | PASS, 3 |
| `tests/unit/test_backend_coverage_margin.py::test_linear_solver_reports_bad_residual_and_nonfinite_solution` | PASS, 1 |
| `tests/unit/test_backend_coverage_margin.py::test_direct_refinement_is_opt_in_and_keeps_the_same_residual_gate` | PASS, 1 |
| `tests/unit/test_backend_coverage_margin.py::test_linear_solver_supports_complex_frequency_systems` | PASS, 1 |

Ruff checks passed for all changed Python sources and tests. Python compilation and `git diff --check` passed. No full suite, controlled FEM campaign, CI matrix, or WP13 v7 smoke was run.

One initial run of the synthetic fixed-DOF serialization test queried reaction rows from the compact summary audit, which intentionally omits those rows. The test fixture now requests values detail and passes; this was a test-fixture correction, not a solver failure.

## Points retained as open

These entries remain open exactly as limitations or hypotheses; no code change here promotes them to defects or closes them:

- DA-006: full-repository confidentiality gate G03 remains `FAIL_PRESERVED`; archive selection does not purge Git history.
- DA-007: independent legal review remains `NOT_ACQUIRED`.
- DA-H01: positivity of the HEX Jacobian between sampled integration points remains an unverified hypothesis.
- DA-H02: interpretation of the buckling critical factor for non-unit preloads remains an unverified hypothesis.

They are preserved as release-review items and were not relabeled PASS.

## Package and v7 evidence impact

The v7 wheel, normalized sdist, contracts, hashes, and six smoke records remain historical and unchanged. This remediation modifies distributed solver sources and therefore produces a different source/package identity. Any later candidate requires a new artifact contract, builds, hashes, and applicable installed-package verification. The v7 smoke results do not cover these changes. No rebuild or scientific rerun is claimed here.

## Verdict

**`REMEDIATION_READY_FOR_REVIEW`** — the four demonstrated P2 code defects have minimal corrections and targeted non-campaign tests. Independent review is still needed, and the open proof limitations and hypotheses remain outside this code remediation. This verdict does not approve integration, qualification, tagging, or publication.
