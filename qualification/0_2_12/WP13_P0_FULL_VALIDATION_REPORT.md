# WP13 P0 full validation report

**Status:** WP13_P0_PARTIAL_OR_BLOCKED — run 1 is complete but failed/incomplete; corrected candidate CI and installed-artifact solve smokes remain open.
**PR:** [#114 — Verify v0.2.12 release candidate artifacts](https://github.com/emptiesvoid-cloud/QF_solver/pull/114)
**Release baseline:** ab137051d920d7fa9aae9a3012a48b2b26e2198b
**Owner-specified initial PR head:** 57d011c9e228ffae642ff0e9b68098939c87e586
**PR head revalidated before current corrections:** 375872ec89699b23e5af23151feebc797bc5d94e

## 1. Candidate and execution identities

The first official P0 workflow ran on commit 3e2d5f07585b270bb1ac0157a911e94d59991735, tree 6f4372b7978b089c020c3c250f473bd2dd89d4ea, before the corrections now in the WP13 worktree. GitHub run [41201053221](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41201053221) used workflow_dispatch with extended WP14, engineering-campaign, and documentation jobs disabled. The run is complete and failed; no publish, tag, merge, or deployment occurred.

The historical v4 package contract remains QF-0212-WP13-SELECTED-CANDIDATE-20261031-04, source 60c202a75d20c6dea1df35aab591bd3832d12c58. v4 artifact results are retained in their report. The current P0 correction adds cryptography==48.0.0 to the selected requirements/baseline-standard.txt; that file is included in the sdist contract. Therefore v4 no longer identifies the selected sdist for the corrected candidate. A new contract and fresh builds are required before claiming installed-artifact results for the final candidate.

No solver source, numerical oracle, acceptance threshold, scientific input, WP12 proof, or ledger was changed. Corrections cover CI timeout/privacy-base handling, the locked standard-test dependency, synthetic fixtures/mocks, release-audit CLI root selection for fixture tests, the current prepublication metadata assertion, and WP13 reporting. Test source files bound by WP12 scientific contracts were restored unchanged.

## 2. Official CI matrix — run 1

| Environment | Exact Python | Standard test result | Other gates / verdict |
|---|---:|---|---|
| Ubuntu latest | 3.10.22 | FAIL — 4,646 passed, 72 failed, 32 skipped, 107 deselected; 4,197.98 s (1:09:57); global branch coverage 84.76% | Ruff, mypy, install, identity, and workflow privacy step passed; privacy step was an invalid self-comparison. P0 module coverage, compileall, quick verification, and artifact upload were skipped after the test failure. |
| Ubuntu latest | 3.13.17 | CANCELLED at the 90-minute job limit; 4,750 selected after 107 deselected, approximately 38% progress; no final counts or coverage | Install, identity, Ruff, mypy, and privacy step passed; downstream gates did not run. |
| Windows latest | 3.10.11 | Pytest emitted 602 passed, 5 skipped, 107 deselected in 5,292.57 s (1:28:12); the workflow job was then cancelled at its 90-minute limit | Ruff, mypy, install, identity, and privacy step passed; no completed P0 module coverage, compileall, quick verification, or coverage artifact. The test summary alone is not a workflow PASS. |
| Windows latest | 3.13.16 | Pytest emitted 602 passed, 5 skipped, 107 deselected in 5,334.88 s (1:28:54); the workflow job was then cancelled at its 90-minute limit | Ruff, mypy, install, identity, and privacy step passed; no completed P0 module coverage, compileall, quick verification, or coverage artifact. The test summary alone is not a workflow PASS. |

The first-run official selector was tests/unit tests/integration -m "not benchmark and not large and not evidence". Its 107 deselections are the pre-existing marker exclusions. The per-cell runtime and dependency versions are recorded in GitHub Actions logs. Full raw log and metadata are preserved outside the repository at E:\QFSolverAgents\wp13_p0_logs_41201053221; run.log SHA-256 is F95E5BB9E8BDF6B4233BAAA6D78DB6854EC7651CCD447A27D45500A823B4A5DC, and run.json SHA-256 is 4C3C9448E492EE02365E453634D26478ECC52A010EE0E46E3163BAEF3844017B.

The manual-dispatch privacy step compared the candidate to itself and is rejected as evidence. A direct run of python scripts/check_privacy_diff.py --base ab137051d920d7fa9aae9a3012a48b2b26e2198b passed locally. The workflow now requires that exact base as an explicit dispatch input. The standard matrix timeout is raised from 90 to 180 minutes; quality thresholds are unchanged.

## 3. Run 1 failures and dispositions

The original 72 failures remain visible in the preserved run and are not relabelled as passes.

| Failure group | Observed outcome | Disposition for corrected run |
|---|---|---|
| Missing cryptography in the locked test environment | 21 import failures in WP12 process-attestation and synthetic signature tests | Add the already-used pinned version 48.0.0 to the standard baseline; a local exact synthetic attestation test passed. This is a test dependency, not a solver runtime dependency. |
| Test doubles and synthetic Owner bindings | Three mocks rejected new keyword arguments; one synthetic decision did not bind its exact manifest digest | Update only mock signatures / synthetic decision fixture. Exact local tests passed. |
| Candidate document/version assertions | Two audit tests expected the 0.2.11 identifier; public-vocabulary scan included internal/archive sources | Update expected current audit identifier and limit the scanner to README and served docs/ inputs. Exact local checks passed; historical audit findings remain FAIL. |
| Synthetic WP12 runner tests | Windows-only absolute paths, suite-preloaded solver import, and an inventory entry without its fixture caused failures | Use host-native temporary paths, test import delta rather than global absence, and create the declared fake file. Exact local tests passed; no WP12 runner source, manifest, proof, or ledger changed. |
| WP12/VV3D and WP19 controlled nodes | Protected nodes failed closed without their registered controller, one WP12 S oracle produced a 6.16e-16 residual against exact zero, and one WP19 adversarial record-count assertion failed | Preserve observed results; do not change tolerances, evidence, or campaigns. Exact function families are excluded from the next P0 standard dispatch and remain outside P0 qualification. |
| WP12B HEX20 diagnostic and VV3D path fixture | HEX20 refused without QF_DEVELOPMENT_AUTONOMOUS; VV3D controller fixture used an unavailable Windows path | Exclude the controller-gated HEX20 node. Replace only the VV3D test fixture with a synthetic temporary source/ledger; its exact local test passed. No FEM ran in the fixture test. |
| RBE2 integration | Test ran its solve/API/CLI path, then failed because check_mesh returned PASS while the frozen test expects WARNING | Preserve the FAIL and the WP12-4-bound test file unchanged. Do not replay it under the generic matrix; exact node is excluded. |
| WPC02 AR approval and wrong-manifest guards | The Owner-approved protocol digest matches its historical protocol bytes, not the later current report; two wrong-digest tests lacked an external manifest | Preserve the decision, plan, protocol, and evidence. Bind the test to the immutable historical protocol commit; use a synthetic temporary manifest for M4/M5 refusal checks. Exact local nodes passed; no FEM ran. |
| Release-audit CLI and publication-phase checks | Two CLI subprocess tests rescanned the entire Git history/archive although they test CLI output behavior; the post-publication test targeted 0.2.11 after package metadata moved to 0.2.12 | Add `--root` with the same default and run the CLI wiring tests against a tiny temporary Git root. Keep separate whole-current-tree audit tests. Replace the stale post-publication assertion with candidate-state checks confirming 0.2.12 remains unreleased and 0.2.11 remains latest published. Exact local nodes passed. G03 remains FAIL_PRESERVED. |

The first generic CI dispatch also reached unmarked WP12/WP19 controlled nodes and the RBE2 integration before their boundaries were recognized. Their outcomes and original logs are preserved. The corrected workflow excludes the exact function families below; it does not alter or erase the first-run failures.

## 4. Corrections and targeted local checks

The corrected workflow keeps the standard release-audit tests and current-candidate publication-state test in the suite. Their command-line tests now use a tiny temporary Git repository while separate current-tree audit tests continue to exercise the real checkout. The explicit `-k` exclusions are limited to exact historical FEM/controlled-campaign nodes that cannot run under the registered WP12/WP19 authorization scopes in a generic matrix, plus the RBE2 integration test that performs an unregistered solve. Marker exclusions remain `benchmark`, `large`, `evidence`, `scientific_vv`, and `native_vv`; they do not change coverage thresholds, oracles, or qualification status. No policy-controlled FEM case is rerun by the corrected P0 matrix.

Exact `-k` exclusions in `.github/workflows/quality.yml`:

- `tests/integration/test_api_and_cli.py::test_rbe2_example_runs_through_api_cli_audit_and_vtu_export` — runs a structural solve without a WP13 package-smoke reservation.
- `tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables`, `tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation`, and `tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization` — WP12 scientific nodes requiring their registered exact runner and authorization.
- `tests/unit/test_wp12_s_quantitative_extraction.py::{test_wp12_s_modal_discrete_001,test_wp12_s_modal_2dof_001,test_wp12_s_dyn_sdof_001,test_wp12_s_modal_2dof_poly_001,test_wp12_s_stat_beam_uy_001,test_wp12_s_stat_beam_uz_001,test_wp12_s_fem_tet4_h_001}`, `tests/unit/test_wp12_vv3d_adaptive_prepared.py::{test_prepared_fem_case,test_prepared_adaptive_fem_case,test_prepared_archived_postprocess_case}`, and `tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12_hex20_affine_patch_archives_residual` — historical WP12 execution/campaign nodes not authorized for this WP13 run.
- `tests/unit/test_wp19_robustness_hex8.py::{test_wp19_adversarial_cases_fail_closed_and_replay,test_wp19_hex8_diagnostic_is_bounded_and_deterministic,test_wp19_replays_golden_set_without_rewriting_wp13_evidence}` — WP19 campaign/diagnostic nodes outside the P0 release-engineering scope.

The frozen WPC02 Owner approval hash assertion and WP12 static-manifest assertion are not excluded: their tests now verify the historical binding with immutable bytes and synthetic fixtures, without altering the recorded decisions or manifest.

Completed local non-FEM checks on the corrected worktree:

- Ruff across src/qf_solver, src/solveur, tests, and scripts: PASS.
- Progressive mypy on the four workflow files: PASS.
- compileall: PASS.
- Correct-base privacy additions check: PASS.
- YAML parse and CRLF-aware git diff --check: PASS.
- Exact synthetic tests for CLI mocks, local-VV refusal/binding, WP12 manifest parsing fixtures, WP12 controller refusal, WPC02 wrong-digest guards, the candidate metadata phase, release-audit CLI output paths, and the review-vocabulary scan: PASS.
- The initial WPC02 approval test compared its Owner-approved historical protocol digest to the later current report and failed. The approved digest matches the historical protocol bytes at ancestor commit `938668c16bc4d8b7a99616bd8af9904adf7f2136`; the current protocol remains different and unchanged. The corrected exact test verifies that historical binding and the current divergence, without changing the Owner decision or protocol.
- The static WP12 manifest portability test now uses a synthetic repository with fixed bytes and separately asserts the immutable real manifest's recorded C01 conflict and missing overlay. It passed locally on Windows Python 3.13; the original Ubuntu failure is preserved in run 1.

The corrected four-cell GitHub matrix has not yet run. Run 1 never completed the 90% P0 module coverage gate, compileall, or the two official quick-verification steps. No coverage gate PASS is claimed.

## 5. API, CLI, serialization, and artifacts

The earlier v4 report records 21 exact Windows Python 3.13.1 and four Windows Python 3.12 non-FEM API/serialization/CLI checks. Those remain valid for the unchanged solver source, but do not replace the final-candidate CI matrix.

V4 wheel/sdist installs and six non-solving check-mesh probes remain historical. Because the selected baseline lock changed, a new candidate-bound v5 contract, scope scan, reproducible wheel/sdist builds, clean installs, source-origin checks, CLI probes, and check-mesh probes are required. No artifact from v4 is relabelled as v5.

No package-installed static, modal, or dynamic structural solve has run. V4 check-mesh checks do not constitute mechanical solves. The current local-VV runner requires source-checkout imports and has no WP13 installed-package scope. No matching manifest, reservation, or Owner execution decision exists. The solve-smoke gate remains BLOCKED / NOT_RUN pending a compatible, synthetic-tested controller and one consolidated Owner decision covering exact artifacts, cases, oracles, budgets, and attempt limits.

## 6. Current gate verdicts

| Gate | Verdict at this revision |
|---|---|
| Ruff / progressive mypy | PASS locally and on all four first-run jobs; final corrected matrix pending. |
| Privacy additions | PASS with the explicit release baseline locally; first workflow result rejected as self-comparison; corrected workflow pending. |
| Full standard tests | FAIL / PARTIAL on run 1; corrected four-cell run pending. |
| Global branch coverage >=80% | PARTIAL — Ubuntu/Python 3.10 observed 84.76%; other cells lack complete results; corrected run pending. |
| P0 module branch coverage >=90% | NOT_RUN — downstream gate skipped/cancelled in run 1. |
| Compileall and official quick verification | NOT_RUN in the first workflow jobs. Local compileall passed; official matrix steps still required. |
| API/CLI/serialization | PASS, bounded for named non-FEM exact tests; RBE2 integration remains FAIL-preserved. |
| Wheel/sdist and installed non-solving checks | PASS, historical v4 only; v5 pending because selected lock input changed. |
| Installed-artifact static/modal/dynamic solves | BLOCKED / NOT_RUN; no FEM beyond the exact authorized CI tests. |
| Overall WP13 P0 | WP13_P0_PARTIAL_OR_BLOCKED; do not declare WP13_P0_VALIDATED. |

No publication, tag creation, merge to main, site synchronization, package upload, GitHub Release, or Zenodo deposit is authorized or performed.
