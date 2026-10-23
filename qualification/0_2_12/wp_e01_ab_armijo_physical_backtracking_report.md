# WP-E01-AB â€” Physical Armijo Backtracking Verification Report

## Outcome

**The authorized campaign did not establish accepted reduced-step backtracking in the production nonlinear solver.** COLLECT accepted all 17 authorized nodes. The one supervised RUN completed with 16 passed and 1 failed. The failing case was blocked at the protected `NonlinearStaticSolver.solve` execution guard before solver setup or finite-element assembly. No retry or guard bypass was attempted.

| Status | Result |
|---|---|
| `PRODUCTION_ARMIJO_CERTIFICATE` | `NOT_VERIFIED` |
| `INCREMENTAL_NEWTON` | `VERIFIED_BOUNDED` (preserved AA scope only) |
| `NATIVE_FEM_VNV` | `NOT_RUN` |
| `GENERAL_SCIENTIFIC_QUALIFICATION` | `NOT_ACQUIRED` |
| `WP_E01_STATUS` | `OPEN` |
| `AUTHORITATIVE_INTEGRATION` | `PENDING` |
| `PUBLIC_RELEASE` | `NOT_AUTHORIZED` |

## Baseline and frozen execution identity

- Worktree: `C:\wpc01-frictionless-public-integration-wt\wp-e01-x`
- Branch: `codex/wp-e01-x-newton-test-remediation-20261021`
- Source HEAD at COLLECT and RUN: `134cfb8e161d16f83f4711029c425399cff1cf59`
- Origin: `https://github.com/emptiesvoid-cloud/QF_solver.git`
- Test module SHA-256: `973df15eb8fffb8a9fb3af7fcb0365485ce3c582147159556ea1ec2eac3f6e7e`
- Registry SHA-256: `8b9e1122c9c014a3e1b79a44320f12f8e9b0611b40535a82e07986b3b5e72c17`
- Static manifest SHA-256: `315d1886a3ec07567e0376127d204b79556de67d03d4b07a03ba4d2886d0d8f8`
- Collection guard SHA-256: `789019b0bc09941f3b897e007e07b6d8765479d1aa47d301c4e5907ed32fcb63`
- Supervisor SHA-256: `f644c6f75bad659d69dff15f33d6618029b5aec663fca17b4e1d106feff29063`
- Job Object helper SHA-256: `76e71e833280b92c2478ec8aed187a473bf5f4002e5983c2386f37b58e9bbe62`
- RUN runtime manifest SHA-256: `17f26f90260f1d574af2592fab4354714d533aa8fd9cd42b99dc133ebfafeea5`
- Archived RUN runtime manifest SHA-256: `17f26f90260f1d574af2592fab4354714d533aa8fd9cd42b99dc133ebfafeea5`
- Tracked runtime profile returned to non-runnable `PREPARATION_ONLY` after the single RUN; current profile SHA-256: `0ce544cc673b9e6ebe980f1429e5a8b554ac41d3b9ea8dec1385f3bb922677c8`
- Production solver, material, contact, and assembly sources were not modified.

## Chronology and containment

1. Independent source review was completed before collection at the frozen HEAD; it reported no P0/P1 findings. It was a read-only source/hash review, not runtime evidence.
2. COLLECT command: `C:/Python313/python.exe -m experiments.wp_e01uvw_newton_supervisor --phase collect`.
3. COLLECT result: `COLLECTION_ACCEPTED`; 17 exact authorized nodes, natural child exit 0, no test bodies run, automatic retry disabled.
4. RUN command: `C:/Python313/python.exe -m experiments.wp_e01uvw_newton_supervisor --phase run`.
5. RUN result: child exit 1 after pytest completed; 16 passed, 1 failed, 0 skipped, 0 xfailed, 0 xpassed, 0 interrupted. One RUN only.
6. Both phases read back a 256 MiB per-process and Job committed-memory cap, active-process limit 1, kill-on-close enabled, breakaway disabled, and 120-second parent wall deadline. The worker was assigned before resume. Post-exit active PID list was empty and cleanup status was `VERIFIED_WINDOWS_JOB_CLOSED`.
7. COLLECT peak committed memory: 75,427,840 bytes. RUN peak committed memory: 108,294,144 bytes. Neither phase timed out or exceeded limits. Both stderr logs were empty.

## Test results

Observed: **17 collected; 16 passed; 1 failed; 0 skipped; 0 xfailed; 0 xpassed**.

Passed nodes:
- `tests/unit/test_wp_e01uvw_newton.py::test_incremental_equilibrium_matches_independent_affine_hencky_reference[tet4]`
- `tests/unit/test_wp_e01uvw_newton.py::test_incremental_equilibrium_matches_independent_affine_hencky_reference[hex8]`
- `tests/unit/test_wp_e01uvw_newton.py::test_final_equilibrium_is_independent_of_admissible_load_partition[tet4]`
- `tests/unit/test_wp_e01uvw_newton.py::test_final_equilibrium_is_independent_of_admissible_load_partition[hex8]`
- `tests/unit/test_wp_e01uvw_newton.py::test_small_strain_solution_approaches_linear_hencky_limit`
- `tests/unit/test_wp_e01uvw_newton.py::test_unattainable_excessive_load_fails_without_fabricating_equilibrium`
- `tests/unit/test_wp_e01uvw_newton.py::test_failed_second_increment_preserves_last_accepted_equilibrium`
- `tests/unit/test_wp_e01uvw_newton.py::test_iteration_limit_refuses_increment_without_changing_accepted_state`
- `tests/unit/test_wp_e01uvw_newton.py::test_singular_reduced_tangent_refuses_and_preserves_initial_state`
- `tests/unit/test_wp_e01uvw_newton.py::test_residual_merit_backtracking_records_rejected_full_step`
- `tests/unit/test_wp_e01uvw_newton.py::test_invalid_trial_is_rejected_then_smaller_admissible_step_is_selected`
- `tests/unit/test_wp_e01uvw_newton.py::test_wrong_mesh_accepted_state_fails_closed`
- `tests/unit/test_wp_e01uvw_newton.py::test_same_mesh_non_equilibrium_state_is_not_accepted_as_restart`
- `tests/unit/test_wp_e01uvw_newton.py::test_load_step_count_and_order_are_bounded`
- `tests/unit/test_wp_e01uvw_newton.py::test_reduced_increment_embedding_has_zero_prescribed_components`
- `tests/unit/test_wp_e01uvw_newton.py::test_initial_state_must_be_in_free_space_equilibrium`

Failed node:
- `tests/unit/test_wp_e01uvw_newton.py::test_production_contact_newton_rejects_full_step_then_accepts_reduced_step`

The failure traceback is preserved in `20261021T202050Z/run/stdout.log`. It ends with `SolverExecutionBlockedError`: `native finite-element execution is forbidden at solveur.core.nonlinear.solver.NonlinearStaticSolver.solve in test/no-FEM mode`. The exception arose at the solver guard before FE setup, assembly, line search, or physical trial evaluation. Thus no AB Armijo probe sequence, accepted reduced step, merit record, or constitutive commit was observed. The desired `1 â†’ 0.5 â†’ 0.25` physical sequence remains the fixtureâ€™s historical expected behavior only; it was not reproduced in this execution.

## Interpretation and safety boundary

The failure is not evidence that the physical Armijo fixture or production Armijo mathematics is incorrect: the guarded call never entered the solver. It is also not a successful physical validation. The test runner deliberately enters pytest/test-no-FEM mode, while the production solver guard refuses the public/native FEM execution boundary. This is a real safety boundary. Changing environment flags, weakening the guard, or moving this test outside the reviewed supervisor would exceed this campaignâ€™s safe execution path; none was done.

The supervisor itself operated as configured. This campaign therefore resolves neither the production Armijo certificate nor the physical rejected-full-step/accepted-reduced-step objective. A separate, explicitly reviewed execution profile must reconcile the test-mode solver guard with the authorized physical production route while preserving Job Object containment, exact-node scope, and no-retry behavior.

## Comparison with WP-E01-AA

WP-E01-AA remains historical evidence: 16/16 PASS for its bounded incremental TET4/HEX8 and failure/rollback fixtures, and no accepted physical reduced-alpha Armijo step. WP-E01-AB adds a frozen physical-contact test node and safely attempts its production route, but the execution guard blocks it before solver setup. The AB suite result is 16/17, so it does not improve the Armijo evidence. No AA results were rerun as part of this report.

## Evidence SHA-256

Execution directory: `qualification/0_2_12/wp_e01_x_newton_execution_2026-10-21/20261021T202050Z/`. The supervisor-generated evidence indexes are preserved. Key file hashes:
- `collection_receipt.json` â€” `abff9ecac0d7dc9e8b93b9c42e2595c42ea68e92d25dbb9ec91e029c35f75a35`
- `collection_nodes.json` â€” `c26bd899c9ed0d658b5385e5b12e2b074d5792cc0404f8c3e0381e37b013ec1d`
- `collection_runtime_manifest.json` â€” `fee85ca1b0bb286471951fece0ce0d465c1724e46727ebd84c3182e460976754`
- `collect_evidence_hashes.json` â€” `b630cf7ba96c53129e2f65f3e14a99d4458eec1a739fb4f3b728e266bfa9f0fa`
- `preflight.json` â€” `d6a909f3442f5ab0d8918ab66c819bd16f91ad50cb0612e523765701cb56ef53`
- `run_preflight.json` â€” `8bbf06d8b6064e4fee7fe3740f0a59c97ede72f3b57bb64c011ccbceffb61a4e`
- `run_results.json` â€” `3a2848efb1c8f4f7e32dff4c43a021ef76843eb63cb347041e2487af788c530d`
- `run_summary.json` â€” `4cf721271a5c8b3a302dd667870f9f622e6b0154573a7233751182da035e8de9`
- `run/phase_result.json` â€” `5de7b9cdb247b993a284d91cec27a9c77a7923e4323c2badc2ef55f410289bec`
- `run/stdout.log` â€” `2afa54e7efe6fbcda06f4499e3cd8fa5f7adb44310943cfa30159e748d8f3c9f`
- `run/stderr.log` â€” `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- `run_evidence_hashes.json` â€” `c664cf21523c7a4f96f77bae5fc3075fd04b2717aa96e4171c578fcd4635e809`
- `run_runtime_manifest.json` â€” `17f26f90260f1d574af2592fab4354714d533aa8fd9cd42b99dc133ebfafeea5`

The full collection inventory is in `collection_nodes.json`; collection authorization is in `collection_receipt.json`; node outcomes and traceback are in `run_results.json`; Job Object phase evidence is in `collect/phase_result.json` and `run/phase_result.json`.

## Remaining scientific status

- `PRODUCTION_ARMIJO_CERTIFICATE=NOT_VERIFIED`
- `INCREMENTAL_NEWTON=VERIFIED_BOUNDED` only for the pre-existing AA-supported scope.
- `NATIVE_FEM_VNV=NOT_RUN`.
- `GENERAL_SCIENTIFIC_QUALIFICATION=NOT_ACQUIRED`.
- No numerical thresholds were changed; no production code was changed; there was no retry, merge, release, or scientific promotion.

## Next decision

Authorize a distinct, safety-reviewed execution design for this exact production Newton path. It must explicitly address the `test/no-FEM` guard without disabling mandatory protections or reclassifying the test silently. Only after that design is reviewed should a fresh executable identity, collection, and one-run authorization be considered. The current result must remain recorded as **16 PASS / 1 FAIL (execution guard blocked)**.
