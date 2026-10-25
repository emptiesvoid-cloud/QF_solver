# WP12 — Regression plan for inherited rotating machinery capabilities

**Plan status:** documentary preparation only
**Prepared:** 2026-10-25
**Static review base:** branch emptiesvoids-cloud/0.2.12, HEAD 8aa83f632643c389aed3b8c4e9223f8c422eee1a
**Execution status:** all proposed v0.2.12 checks are NOT_RUN
**Authorization:** no FEM or solver execution is authorized by this plan

## 1. Purpose and boundary

Prepare a bounded WP12 non-regression check for the v0.2.11 experimental rotating_modal and campbell routes that are present in the v0.2.12 source tree. The checks are intended to detect loss of inherited behavior, result compatibility, or fail-closed boundaries. They do not implement a new rotordynamics formulation, qualify general rotating machinery, or promote either route beyond EXPERIMENTAL.

WP11 remains CLOSED for its approved API/integration, result-contract, serialization, documented-compatibility, and refusal gate. The absence of new rotor numerical runs does not reopen WP11. This plan does not close WP12 or change its official OPEN status.

No solver, FEM, Campbell campaign, benchmark, or pytest test was run while preparing this document.

## 2. Evidence states: keep the identities separate

### 2.1 Historical v0.2.11 evidence — acquired for its recorded identities only

The frozen [WP05 gyroscopic contract](../0_2_11/wp05_gyroscopic_contract.json) and [WP05 report](../0_2_11/wp05_gyroscopic_report.md) record GYRO-01 through GYRO-04 as PASS for the declared beam/disk scope. The WP05 verification records identify source SHA f2690bcac8f1b5b34c6b01a6cf5a9e19ecb725a9.

The frozen [WP06 Campbell contract](../0_2_11/wp06_campbell_contract.json), [WP06 report](../0_2_11/wp06_campbell_report.md), [GYRO-05 record](../0_2_11/gyro_05_campbell_analytical.json), [GYRO-06 record](../0_2_11/gyro_06_beam2_convergence.json), and [v0.2.11 verification summary](../../docs/verification/0_2_11/README.md) record GYRO-05 and GYRO-06 as PASS within their frozen scopes. The structured WP06 records identify source SHA bf59bac3d38f19139a401ec8665b326e05917629. GYRO-06 is internal mesh-convergence evidence only. Its high-frequency pair remains ambiguous at 100 rad/s; that ambiguity is part of the evidence and must remain visible.

These are historical results for those source and fixture identities. They are not test results on the v0.2.12 review HEAD.

### 2.2 Static v0.2.12 inspection — performed at the review base

The implementation and public surfaces inspected are:

- src/solveur/core/analyses/rotation_config.py
- src/solveur/core/analyses/rotating_input_validator.py
- src/solveur/core/analyses/rotating_modal.py
- src/solveur/core/analyses/campbell.py
- src/solveur/core/analyses/modal_tracking.py
- src/solveur/core/router.py
- src/solveur/core/results.py
- src/solveur/io/schema_analysis.py
- src/solveur/post/campbell.py
- src/solveur/api/public.py
- src/solveur/cli/standard.py

The v0.2.11 WP05 rotating-modal implementation and its associated unit tests are present. The WP06 tracking modules were added with Campbell. Comparing the current WP06 source identity to bf59bac3d38f19139a401ec8665b326e05917629 found a later, non-numerical provenance-path change in campbell.py, introduced by commit 5231d83 (“Fix Campbell provenance lookup in installed wheel”), together with test_implementation_hash_paths_support_installed_wheel_layout. The future run must therefore exercise the current v0.2.12 files and capture their hashes; the historical WP06 result cannot stand in for that check.

The current capability index and mechanics guides already identify both routes as EXPERIMENTAL and describe their inherited boundaries. The v0.2.12 WP11 traceability matrix records the rotor result DTOs and complex serialization as an inventory/API concern with no solver run. It is not a WP12 numerical non-regression result.

### 2.3 v0.2.12 checks to run later — all NOT_RUN

The nodeids below are present in the reviewed tree and are proposed for a future, separately authorized WP12 run. Run each explicit nodeid as its own bounded invocation. A pass on one fixture is evidence for that node and contract scope only.

| Coverage | Exact existing pytest nodeids |
|---|---|
| GYRO-01 zero-speed spectrum and eigenspaces | tests/unit/test_rotating_modal_cases.py::test_gyro01_zero_speed_matches_modal_frequencies_multiplicity_and_subspaces |
| GYRO-02 disk blocks, assembly map, skew-work and frame covariance | tests/unit/test_rotating_disk_gyro.py::test_disk_mass_and_unit_speed_gyro_blocks_match_contract; tests/unit/test_rotating_disk_gyro.py::test_assembled_gyro_uses_same_global_dof_map_and_has_zero_quadratic_work; tests/unit/test_rotating_disk_gyro.py::test_disk_mass_and_gyro_are_covariant_under_global_frame_rotation; tests/unit/test_rotating_disk_gyro.py::test_gyro_assembly_rejects_unknown_discrete_entity |
| GYRO-03 analytical oracle at the nine frozen signed speeds | tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[0.0]; tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[5.0]; tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[-5.0]; tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[25.0]; tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[-25.0]; tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[50.0]; tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[-50.0]; tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[100.0]; tests/unit/test_rotating_qep.py::test_gyro03_independent_disk_oracle_and_qep_residual[-100.0] |
| GYRO-04 signed-speed behavior and splitting | tests/unit/test_rotating_qep.py::test_gyro04_signed_spin_reverses_pencil_term_but_preserves_unordered_frequencies; tests/unit/test_rotating_qep.py::test_gyro04_splitting_increases_with_absolute_signed_spin |
| QEP scale invariance and fail-closed invariants | tests/unit/test_rotating_qep.py::test_qep_physical_spectrum_is_invariant_to_frozen_coordinate_length_scale; tests/unit/test_rotating_qep.py::test_qep_rejects_non_skew_gyro_and_non_positive_mass |
| QEP complex result serialization | tests/unit/test_rotating_qep.py::test_rotating_modal_complex_serialization_round_trip_preserves_all_roots |
| Complex MAC and phase/order invariance | tests/unit/test_modal_tracking.py::test_complex_mac_is_invariant_to_complex_phase_and_nonzero_scaling; tests/unit/test_modal_tracking.py::test_complex_mac_orthogonal_and_conjugate_behavior_is_explicit; tests/unit/test_modal_tracking.py::test_tracking_is_invariant_to_eigenpair_order_phase_and_scaling |
| Degenerate subspaces, lineage and ambiguity | tests/unit/test_modal_tracking.py::test_degenerate_cluster_split_records_parent_child_lineage; tests/unit/test_modal_tracking.py::test_degenerate_basis_rotation_is_reported_as_cluster_ambiguity; tests/unit/test_modal_tracking.py::test_competing_source_modes_make_the_global_assignment_ambiguous |
| Campbell contract, current provenance path, output and route | tests/unit/test_campbell.py::test_implementation_hash_paths_support_installed_wheel_layout; tests/unit/test_campbell.py::test_campbell_requires_frozen_qep_and_tracking_contracts; tests/unit/test_campbell.py::test_campbell_fails_closed_if_requested_mode_count_is_unavailable; tests/unit/test_campbell.py::test_campbell_sweep_reuses_one_model_and_serializes_complex_source_results; tests/unit/test_campbell.py::test_campbell_is_exposed_through_model_schema_and_analysis_router |
| Rotating-modal maturity, input and route refusals | tests/unit/test_rotating_modal_preflight.py::test_valid_bounded_model_is_explicitly_experimental; tests/unit/test_rotating_modal_preflight.py::test_rotation_config_normalizes_axis_and_requires_explicit_rpm_conversion; tests/unit/test_rotating_modal_preflight.py::test_rejects_non_beam_mixed_and_non_circular_sections; tests/unit/test_rotating_modal_preflight.py::test_duplicate_generic_mass_and_unsupported_discrete_are_rejected; tests/unit/test_rotating_modal_preflight.py::test_rotating_disk_is_rejected_by_classic_modal_route; tests/unit/test_rotating_modal_preflight.py::test_rotating_disk_json_model_round_trip_is_explicit; tests/unit/test_rotating_modal_preflight.py::test_router_returns_separate_experimental_rotating_modal_result |
| Public JSON API load/solve/save compatibility | tests/integration/test_rotating_modal_public_api.py::test_public_json_load_solve_and_save_support_experimental_rotating_modal |

Two additional existing tests are parameterized in the source: test_route_rejects_out_of_scope_inputs_before_assembly in tests/unit/test_rotating_modal_preflight.py and test_campbell_rejects_implicit_or_invalid_speed_grids in tests/unit/test_campbell.py. Their parameter cases cover non-collinearity/axis/load/disks and undersized, duplicate, non-finite, or descending speed lists. Before authorizing any of those cases, record the collected parameter-expanded nodeids in the execution manifest; no guessed wildcard nodeid is accepted.

### 2.4 Coverage gaps identified statically

- No current pytest node reproduces the full GYRO-06 4/8/16/32-element by 0/100/250 rad/s sequence. The checked-in scripts/run_wp06_verification.py writes the historical v0.2.11 evidence paths; do not rerun it in place. A WP12 replay would need an Owner-approved runner that writes a new, separately identified v0.2.12 record.
- No current pytest node reproduces the complete GYRO-05 analytical Campbell oracle at all nine frozen speeds. Existing tracking tests cover phase/order invariance, degeneracy and synthetic ambiguity, while the route test uses only 0/10/25 rad/s. The historical verification script writes the frozen v0.2.11 GYRO-05 and GYRO-06 records, so both full-case replays need a separate, approved runner and new output destinations.
- No rotor-specific CLI regression node was found. src/solveur/cli/standard.py uses the generic model/solve route, but the existing CLI tests do not establish Campbell or rotating-modal CLI compatibility. WP12 must either add a bounded CLI fixture/test or record that the capability is API-only if that is the supported contract. Do not claim CLI regression from the API test.
- The Campbell unit test checks a small explicit 0/10/25 rad/s sweep. The preserved 100 rad/s historical ambiguity is not thereby replayed on the current HEAD. If replayed, it must preserve AMBIGUOUS/gap data and must not force a branch association.
- The existing integration API smoke test performs a solve. All listed solve/QEP tests are numerical executions, even where pytest classifies them as unit tests.

## 3. Modules and behavior to cover

The route-level checks should jointly cover:

1. RotationConfig parsing, signed speed, global axis convention and explicit RPM conversion.
2. Rotating-modal preflight before matrix assembly; BEAM2/disk ownership and unsupported-input refusals.
3. Construction and invariants of M, K, and unit-speed skew G; dense QEP roots, residuals, mass normalization and complex modes.
4. RotatingModalResult and CampbellResult, their complex to_dict() representation, root reconstruction, branch samples, source-result hashes, and explicit maturity/status fields.
5. Campbell's fixed-structure sweep, fixed reduced K/M/G identity, explicit ordered speed input, global complex-MAC assignment, degeneracy lineage, gaps, and ambiguity.
6. Model schema, AnalysisRouter, public JSON load_model/solve_model/save_result, and the generic CLI path only after the CLI contract and fixture are explicit.

Do not use the generic result DTO boundary to infer a universal complex schema or load_result() contract. WP11's accepted heterogeneous DTOs and route-specific versioned schemas remain authoritative.

## 4. Frozen historical oracles and tolerances

Use only values already frozen in the v0.2.11 contracts. Do not tune thresholds to the new output.

| Check | Frozen oracle / limit |
|---|---|
| Matrix and QEP invariants | Relative M/K symmetry and G skew checks 1e-12; positive-definite mass via Cholesky; mass-normalization error 1e-10; general QEP relative residual 1e-8; GYRO-03 analytical residual and relative frequency error 1e-10; conservative growth ratio and conjugate-pair mismatch 1e-8; maximum generalized eigenvalue condition number 1e12. |
| GYRO-01 | Zero-speed frequency relative error 1e-8; modal assurance and degenerate-subspace minimum singular value at least 0.99999999; frozen cluster frequency-gap threshold 1e-8. |
| Campbell tracking | Complex MAC minimum admissibility 0.8; normalized frequency-distance maximum 0.25; ambiguity margin below 0.05 is AMBIGUOUS; degenerate cluster relative gap 1e-8; subspace minimum singular value 0.99999999. |
| GYRO-05 | Analytical frequencies at [-100,-50,-25,-5,0,5,25,50,100] rad/s, relative frequency error at most 1e-10, QEP residual at most 1e-10, phase/order invariance, degenerate lineage, and preserved controlled ambiguity. |
| GYRO-06 | 4/8/16/32 beam elements at [0,100,250] rad/s; QEP residual at most 1e-8; 16-to-32-element retained-branch relative frequency delta at most 0.005; adjacent-mesh complex MAC at least 0.8 for unambiguous correspondence. Compare only common explicitly retained tracked branches. |

The exact definitions and any additional fields remain in the [frozen WP05 contract](../0_2_11/wp05_gyroscopic_contract.json) and [frozen WP06 contract](../0_2_11/wp06_campbell_contract.json). A detected ambiguity is an acceptable recorded outcome when required by the oracle; silently forcing an edge is not.

## 5. Refusal and out-of-scope controls

The authorized regression should verify accepted legacy inputs and expected refusals without broadening the model. Check the existing validators against the original contracts for:

- non-BEAM2 or mixed models; branched, curved, non-collinear shafts; non-circular sections; missing or variable inferred axis;
- eccentric, off-node, non-axisymmetric, duplicate generic-mass disks; unsupported discrete entities, constraints or transformations;
- nonzero damping, prestress/static loads, speed-dependent structural or bearing properties, centrifugal stress-stiffening, variable speed within a single solve, distributed shaft gyro, contact/rubbing, nonlinear rotor response, and unbalance/forced response;
- implicit/generated/adaptively refined Campbell grids, non-finite or unordered speeds, unsupported tracking/QEP policy, and unavailable requested mode count;
- sparse, PETSc, SLEPc, MPI, or other unsupported QEP backends.

The original contracts remain the authority for each refusal. Where the existing pytest suite has no exact named case for a listed exclusion, record a WP12 coverage gap and obtain Owner approval for a new, separately named negative test; do not describe static code inspection as an executed refusal test.

## 6. Provenance and physical identity requirements

Before any WP12 execution, freeze a separate Owner-approved manifest that includes:

- target branch, exact commit and Git tree; clean/dirty state; Python and dependency versions; platform and numerical-library/thread settings;
- each exact nodeid, its source-file hash, allowed attempt count, timeout/memory/CPU budget, command, and expected artifact destination;
- model/fixture bytes and digest; mesh/connectivity, material/section data, disk mass/inertias/node/axis, supports, signed speed list, requested modes, and all route settings;
- the structural and reduced M/K/G identity hashes where produced; for a Campbell sweep, prove the physical operators and DOF map stay invariant while only the explicitly supplied signed spin speed changes;
- output/result JSON hashes, run status, QEP residuals, mode-selection and branch-lineage records, all ambiguity/gap fields, source-result hashes, stdout/stderr digests, and a reviewed manifest receipt.

Historical v0.2.11 source SHAs and records must remain labelled as historical. A current run must report its own v0.2.12 commit/tree and current test/source hashes. Do not copy a historical PASS status into a current run record.

## 7. Authorization and execution controls

This plan grants no execution authority. Before running a solver-backed test or mesh campaign, the Owner must approve a WP12 execution manifest with exact scope, input/source identities, nodeids, attempts and resource limits. Repository execution policy currently does not register rotor nodeids in the autonomous FEM runner. Direct pytest has no equivalent campaign budget/source-origin record. Therefore execution also requires an approved runner/registry path that enforces the manifest; do not bypass it with a raw pytest command.

The GYRO-06 replay must write to a new v0.2.12 evidence location and leave every frozen v0.2.11 file byte-identical. The manifest must explicitly forbid overwrite and retries beyond its approved attempt count. An unexpected failure, environment mismatch, missing result, or changed model identity is retained as such and escalated; it is not retried or reclassified without a new decision.

## 8. Acceptance conditions for a bounded non-regression result

WP12 may record inherited-route non-regression only when all authorized checks have:

1. run on the exact approved clean source/tree and fixture identities with accepted receipts;
2. reproduced the frozen analytical, algebraic, residual, tracking and ambiguity oracles within their original limits;
3. preserved the EXPERIMENTAL maturity, complex output fields, branch lineage, source/result hashes, missing samples and the 100 rad/s ambiguity where that case is replayed;
4. demonstrated intended JSON/API compatibility and either a tested supported CLI path or an explicit API-only compatibility boundary;
5. retained each required unsupported-input rejection and all original failure/ambiguity statuses, with no silent filtering or relaxed thresholds;
6. preserved the historical v0.2.11 artifacts and made no solver, equation, constitutive, numerical-policy or qualification-status change.

Passing this bounded plan is not general rotordynamics qualification, physical validation, publication authorization, or automatic WP12 closure. WP12 remains OPEN until a separate Owner gate decision reviews the full WP12 scope and evidence.

## 9. Cost, exclusions and residual risks

- The historical GYRO-05 analytical speed set entails nine small dense QEP solves plus synthetic tracking/oracle checks.
- GYRO-06 entails 12 dense QEP solves (four mesh levels by three speeds), followed by retained-branch convergence and ambiguity comparisons. Dense cost grows rapidly with mesh size; the manifest must set measured resource ceilings before execution. No wall-time estimate is inferred here.
- The selected API smoke test and Campbell route tests also perform actual solves. Do not count them as serializer-only checks.
- This plan excludes performance characterization beyond the bounded execution budget, external rotor correlation, experimental/modal validation on physical machinery, forced response, bearing models, general damping, distributed gyro, nonlinear rotor physics, sparse QEP, and general qualification.
- Residual publication risks include the absence of a current-HEAD GYRO-06 replay, no rotor-specific CLI regression node, no external physical validation, and the preserved Campbell branch ambiguity. These remain visible and are not resolved by the historical PASS records.
