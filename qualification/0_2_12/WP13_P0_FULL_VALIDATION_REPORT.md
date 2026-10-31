# WP13 P0 full validation report

**Status:** WP13_P0_PARTIAL_OR_BLOCKED — run 2 has Linux test failures and pending Windows jobs; installed-artifact solve smokes remain open.
**PR:** [#114 — Verify v0.2.12 release candidate artifacts](https://github.com/emptiesvoid-cloud/QF_solver/pull/114)
**Release baseline:** ab137051d920d7fa9aae9a3012a48b2b26e2198b
**Owner-specified initial PR head:** 57d011c9e228ffae642ff0e9b68098939c87e586
**PR head revalidated before current corrections:** 375872ec89699b23e5af23151feebc797bc5d94e

## 1. Candidate and execution identities

The first official P0 workflow ran on commit 3e2d5f07585b270bb1ac0157a911e94d59991735, tree 6f4372b7978b089c020c3c250f473bd2dd89d4ea, before the corrections now in the WP13 worktree. GitHub run [41201053221](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41201053221) used workflow_dispatch with extended WP14, engineering-campaign, and documentation jobs disabled. The run is complete and failed; no publish, tag, merge, or deployment occurred.

The corrected run and v6 packages bind to source/workflow commit
`2865587a44f9e461a0b4e4286c912c17e4f04be5`. The current PR head when this
report was prepared was `d6a49a279b4d8ce548e4d6ed1f48e8cad6f20e23`; its tree
adds only three WP13 build-contract/provenance JSON files after the tested
commit. A direct tree comparison confirms solver sources, tests, workflow,
examples, packaging files and selected requirements are identical. The report
updates in this change are documentation-only and are not represented as a
new CI execution or package build.

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

The RBE2 assertion predates the later rank-aware behavior: the test was added
at `a051da38`, while `d07fdf72e` added MPC/RBE-aware suppression of legacy raw
support warnings after the constrained-rank check. The checker and this test
file are byte-identical between the release baseline and the v6 workflow
source. The observed `PASS` versus expected `WARNING` is therefore a preserved
expectation mismatch in the release candidate, not a WP13 code change. The
test remains bound to its existing WP12-4 evidence and is not edited or
replayed; its integration coverage stays `FAIL_PRESERVED`.

## 4. Corrections and targeted local checks

The corrected workflow keeps the standard release-audit tests and current-candidate publication-state test in the suite. Their command-line tests now use a tiny temporary Git repository while separate current-tree audit tests continue to exercise the real checkout. The explicit `-k` exclusions are limited to exact historical FEM/controlled-campaign nodes that cannot run under the registered WP12/WP19 authorization scopes in a generic matrix, plus the RBE2 integration test that performs an unregistered solve. Marker exclusions remain `benchmark`, `large`, `evidence`, `scientific_vv`, and `native_vv`; they do not change coverage thresholds, oracles, or qualification status. No policy-controlled FEM case is rerun by the corrected P0 matrix.

Exact `-k` exclusions in `.github/workflows/quality.yml`:

- `tests/integration/test_api_and_cli.py::test_rbe2_example_runs_through_api_cli_audit_and_vtu_export` — runs a structural solve without a WP13 package-smoke reservation.
- `tests/unit/test_modal_newmark.py::test_wp12_newmark_fixed_time_state_refinement_residual_and_energy_observables`, `tests/unit/test_reduced_harmonic.py::test_wp12_harmonic_sweep_separates_full_basis_route_error_from_truncation`, and `tests/unit/test_wp07_uniform_base_acceleration.py::test_wp12_base_acceleration_complex_sweep_checks_frames_sign_and_serialization` — WP12 scientific nodes requiring their registered exact runner and authorization.
- `tests/unit/test_wp12_s_quantitative_extraction.py::{test_wp12_s_modal_discrete_001,test_wp12_s_modal_2dof_001,test_wp12_s_dyn_sdof_001,test_wp12_s_modal_2dof_poly_001,test_wp12_s_stat_beam_uy_001,test_wp12_s_stat_beam_uz_001,test_wp12_s_fem_tet4_h_001}`, `tests/unit/test_wp12_vv3d_adaptive_prepared.py::{test_prepared_fem_case,test_prepared_adaptive_fem_case,test_prepared_archived_postprocess_case}`, and `tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12b_hex20_affine_patch_archives_residual` — historical WP12 execution/campaign nodes not authorized for this WP13 run.
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

Corrected official run 2 has run on all four cells, but its full suite is incomplete: both Ubuntu cells recorded the same 17 test-fixture/platform/scope failures and both Windows cells remain active. Ubuntu's global branch-coverage gate passed at 84.75%; P0 module coverage, compileall and quick verification were skipped after test failures. Run 1 also never reached those downstream gates. Run 3 is required after the targeted fixes below; no P0 module-coverage or official quick-verification PASS is claimed.

## 5. API, CLI, serialization, and artifacts

The earlier v4 report records 21 exact Windows Python 3.13.1 and four Windows Python 3.12 non-FEM API/serialization/CLI checks. Those remain valid for the unchanged solver source, but do not replace the final-candidate CI matrix.

V4 wheel/sdist installs remain historical. The selected standard-test lock changed, so the final candidate was rebuilt and checked under v6; v6 artifacts and fresh installs are detailed in section 7 and the linked artifact report. No v4 artifact is relabelled as v6.

No package-installed static, modal, or dynamic structural solve has run. V4 check-mesh checks do not constitute mechanical solves. The bounded WP13 installed-package controller and exact manifest are now prepared; the persisted and synthetic preflights passed without FEM or a real reservation. The actual attempt ledger is absent. The solve-smoke gate remains BLOCKED / NOT_RUN pending one consolidated Owner decision bound to the exact controller, manifest, preflight reports and six attempt pairs.

## 6. Current gate verdicts

| Gate | Verdict at this revision |
|---|---|
| Ruff / progressive mypy | PASS — all four run-2 cells; full standard suite outcome is tracked separately. |
| Privacy additions | PASS — all four run-2 cells use explicit release base `ab137051d920d7fa9aae9a3012a48b2b26e2198b`. |
| Full standard tests | PARTIAL / FAIL — both Ubuntu cells failed with the same 17 cases; both Windows cells remain active at report time. Run 1 failures remain preserved. |
| Global branch coverage >=80% | PASS on Ubuntu/Python 3.10 and 3.13 at 84.75%; Windows coverage and final matrix result pending. |
| P0 module branch coverage >=90% | NOT_RUN on Ubuntu because the test step failed; Windows result pending. No gate PASS claimed. |
| Compileall and official quick verification | NOT_RUN in the two failed Ubuntu jobs; Windows result pending. Local compileall passed. |
| API/CLI/serialization | PASS for named non-FEM exact checks; targeted fixture corrections pass locally; RBE2 integration remains FAIL-preserved. |
| Wheel/sdist and installed non-solving checks | PASS — v6 two-run candidate builds, normalized sdist, fresh wheel/sdist installs, CLI probes and six check-mesh checks. |
| Installed-artifact static/modal/dynamic solves | BLOCKED / NOT_RUN — exact Owner approval required. The controller, manifest and no-FEM preflights are prepared; the real attempt ledger is absent and no solve from the selected wheel or sdist has run. The first generic CI run did execute a source-checkout RBE2 integration solve before failing its frozen status assertion; that node is excluded from run 2 and has not been replayed. |
| Overall WP13 P0 | WP13_P0_PARTIAL_OR_BLOCKED; do not declare WP13_P0_VALIDATED. |

No publication, tag creation, merge to main, site synchronization, package upload, GitHub Release, or Zenodo deposit is authorized or performed.

## 7. Candidate artifact verification — v6

This update supersedes the v4/v5-pending artifact status above. The exact v6
source is `2865587a44f9e461a0b4e4286c912c17e4f04be5`, bound by contract
`QF-0212-WP13-SELECTED-CANDIDATE-20261031-06` (SHA-256
`f33a72b182439774828f8e604d6ab234bbf206c697c0f1082d7bc0ef81003db9`). The
PR/report execution HEAD was `d6a49a279b4d8ce548e4d6ed1f48e8cad6f20e23`;
selected package inputs and build tools remained identical to the contract's
source commit.

Two independent Windows Python 3.13.1 builds passed selected-content scans:
585 wheel files and 593 sdist files, no findings. The wheel was byte-identical
at 1,689,662 bytes (SHA-256
`ae5211136a2eab912cdb73222937a84b1cec75f7af0a425f1162b288b39c287a`). Raw
sdists differed; normalized outputs were identical at 1,294,049 bytes (SHA-256
`183bc4448d4a83c5e24d9c8b0d7f15e9e2cca37b63b25646d9ec030220611fde`). Twine
7.0.0 passed for both runs' wheel and raw sdist, and both normalized sdists.

The exact run-2 wheel and raw sdist were installed separately from local paths
into fresh Python 3.13.1 Windows venvs with dependency resolution. Both imports
resolved to the installed `site-packages`, verified 501 installed source
files, and passed CLI version/help. The intentional `verify-all` refusal
returned exit 2 and created no report. All six installed `check-mesh` probes
(TET4, BEAM2, MITC4 for each artifact) passed. These checks do not assemble or
solve a structural model. Complete identities and external log/report hashes
are in [`WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md`](WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md).

The v4 and v6 source diff confirms the solver package, examples, packaging
metadata and package manifest are unchanged; only the selected standard-test
lock changed. The v6 artifact checks therefore retain the prior solver/input
identity while verifying the actual new wheel and sdist. G03 remains
`FAIL_PRESERVED`.

## 8. Corrected official CI matrix — run 2, partial

Manual workflow run
[41210713065](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41210713065)
is bound to `2865587a44f9e461a0b4e4286c912c17e4f04be5`, with the explicit
release privacy base `ab137051d920d7fa9aae9a3012a48b2b26e2198b` and extended
jobs disabled. Both Ubuntu cells completed the standard test step with the
same 17 failures; both Windows cells remain active. Setup, locked install,
identity capture, Ruff, privacy additions and progressive mypy passed in all
four cells before their test results.

| Environment | Exact Python | Standard suite | Coverage and downstream gates |
|---|---:|---|---|
| Ubuntu 26.04 | 3.10.22 | FAIL — 4,659 passed, 17 failed, 32 skipped, 149 deselected; 7,354.84 s (2:02:34) | Global branch coverage 84.75% (80% gate passed); P0 module gate, compileall, quick verification and artifact upload skipped after test failures. |
| Ubuntu 26.04 | 3.13.17 | FAIL — 4,659 passed, 17 failed, 32 skipped, 149 deselected; 7,627.12 s (2:07:07) | Global branch coverage 84.75% (80% gate passed); P0 module gate, compileall, quick verification and artifact upload skipped after test failures. |
| Windows latest | 3.10 | IN_PROGRESS | No final counts, coverage or downstream gate results yet. |
| Windows latest | 3.13 | IN_PROGRESS | No final counts, coverage or downstream gate results yet. |

The 17 Linux failures are classified as 14 Windows suspended-process
attestor cases, two synthetic WP12 runner fixture defects, and one
controller-gated WP12B HEX20 node that escaped the `-k` exclusion because the
expression omitted the `b` in the actual function name. The HEX20 node failed
closed before solver execution. Attestor cases used only the fixed fake child;
no solver or FEM ran. There is no numerical solver failure in this set.

The next candidate has a narrow test/workflow correction: non-Windows runs
assert the attestor's documented `DENY_EXECUTION` refusal, while the Windows
child-result classifications remain enabled on both Windows matrix cells;
the runner fixture builds its junit path with the host-native `Path` API and
clears preloaded `solveur` modules before inserting its fake; and the exact
HEX20 controller-gated node is excluded under its real name. No WP12 runner
implementation, contract, manifest, result, proof, ledger, solver source or
threshold changes. Each affected test function passed individually on local
Windows Python 3.13.1, as did Ruff, compilation for the two changed test files,
and `git diff --check`. Those local checks do not replace the official run.

The two raw Ubuntu job logs are retained outside the repository:
`E:\QFSolverAgents\wp13_p0_logs_41210713065\ubuntu_py310_job_logs.txt`
(SHA-256 `CBCFE01B2913B952BDE7C20D357EABB7B9AE84687764770DFF76E158A1DA9C30`)
and `E:\QFSolverAgents\wp13_p0_logs_41210713065\ubuntu_py313_job_logs.txt`
(SHA-256 `A95C46AA5D9B8701DE79279711D5AE1BC3583CA445ABA8EB2F6D6F275EEB9067`).
They contain the exact runner image, Python patch, full `pip freeze`, pytest
counts, coverage summary and original failure traces. The two Windows cells
were still running at this report revision; no final four-cell verdict is
claimed.

The package-installed static, modal and dynamic solves remain `BLOCKED /
NOT_RUN` pending Owner approval. The controller, exact manifest and synthetic
preflight are now prepared; no actual reservation or solve exists. The six
exact proposed cases, inputs, oracles and budgets remain in
[`WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md`](WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md).
Overall status remains `WP13_P0_PARTIAL_OR_BLOCKED`.

## 9. Package-smoke controller and no-FEM preflights

The installed-artifact controller is pinned at SHA-256
`16df6eba0f902c332cace9e9a5624d1b8b59c3e051bfcc4063782123cc9a7f2f`; its v1
manifest SHA-256 is
`dea2c6f6d72bbd7303f23b6cff6b9809be471513dffa639990d13313dee9086b`. The
selected v6 wheel, raw sdist, dependency-install reports, Windows Python
3.13.1 environments, six installed inputs, three independent-oracle sources,
and controlled thread variables passed the persisted no-FEM preflight. The
preflight report SHA-256 is
`f2fb9a13986ab3d9ec95d91f645da973657ab02ae4f6ee261cfb5a50511ab610`.

The synthetic fixed-child route passed with stdout marker
`WP13_SYNTHETIC_NO_FEM_ROUTE_PASS`, exit 0, and no FEM. Its report SHA-256 is
`2eac9b8eeb1635695f907ea4db977f0b223ac991667d786554d8ca8ed3addf6c`; its
append-only ledger SHA-256 is
`5cb540211b529db1fbef1e55a5a303d8cd623e3695a8791cfbdecbd106c2639c`. That
ledger contains only the synthetic reservation and terminal record. The real
attempt ledger at
`E:\QFSolverAgents\evidence\wp13_p0_package_smokes_20261031_run1\attempt_ledger.jsonl`
does not exist.

One earlier preflight failed closed at controller commit `3202161` with
`WinError 267` because the runner used the evidence directory as subprocess
working directory before creating it. It created no files, made no
reservation, and ran no FEM. The correction, captured output and classification
are preserved in
[`WP13_P0_PACKAGE_SMOKE_PREFLIGHT_ATTEMPT_1.md`](WP13_P0_PACKAGE_SMOKE_PREFLIGHT_ATTEMPT_1.md).


## 10. Corrected official CI run 3 and performance triage — 2026-10-31

The corrected official workflow
[41225195330](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41225195330)
used PR #114 HEAD f00bbb9c23769f984a12c2dda37802382ffc5414. This run supersedes
the run-2 in-progress descriptions above for its own cells; run-2 failures
remain unchanged historical evidence.

| Environment | Pytest result | Coverage / later gates |
|---|---|---|
| Ubuntu / Python 3.10.22 | 4,676 passed, 32 skipped, 150 deselected, 4 warnings; 7,537.95 s | Global branch coverage 84.75%; P0 module coverage, compileall, official quick verification and artifact upload PASS. |
| Ubuntu / Python 3.13.17 | 4,676 passed, 32 skipped, 150 deselected, 4 warnings; 7,120.37 s | Global branch coverage 84.75%; P0 module coverage, compileall, official quick verification and artifact upload PASS. |
| Windows / Python 3.10.11 | 602 passed, 5 skipped, 150 deselected before cancellation; 10,681.97 s | Reached the 180-minute job limit in tests/branch coverage. No coverage artifact or downstream gate result. |
| Windows / Python 3.13.16 | 602 passed, 5 skipped, 150 deselected before cancellation; 10,724.65 s | Reached the 180-minute job limit in tests/branch coverage. No coverage artifact or downstream gate result. |

All four jobs passed setup, identity, Ruff, privacy additions and progressive
mypy. The Windows logs stop at 12% while reporting the governance-policy
module and a pathlib traceback. The exact in-flight nodeid is not present in
the logs; no test has been attributed to the stall by inference. The same
stopping point appeared in the prior run. Windows complete-suite and coverage
gates remain BLOCKED / NOT_ACQUIRED.

The Linux fixes resolve all 17 run-2 failures in the corrected matrix without
changing solver behavior, scientific oracle thresholds or ledgers. Fourteen
platform-specific attestation tests now assert the existing fail-closed
DENY_EXECUTION behavior on non-Windows; two synthetic fixture defects were
corrected; the exact controller-gated HEX20 node remains excluded and NOT_RUN
in generic CI.

The local bounded profile, the single contact-documentation node that
unexpectedly executed real structural FEM, its temporary-output-only result,
the full selected-node timing table, source-scan observation, and CI
recommendation are documented in
[WP13_P0_TEST_PERFORMANCE_AND_CI_OPTIMIZATION_REPORT.md](WP13_P0_TEST_PERFORMANCE_AND_CI_OPTIMIZATION_REPORT.md).
That contact-node execution is disclosed as a scope deviation, not qualification
evidence. No further FEM, package solve, benchmark or full-suite rerun was
performed for this triage.

| Gate | Current verdict |
|---|---|
| Linux Python 3.10 and 3.13 permitted full suite | PASS |
| Linux global and P0 branch coverage | PASS |
| Windows Python 3.10 and 3.13 full suite / coverage | BLOCKED / NOT_ACQUIRED |
| Package-installed static, modal and dynamic solves | NOT_RUN; separate exact authorization required |
| Old four-cell full-suite obligation | NOT_ACQUIRED |
| Overall WP13 P0 | WP13_P0_PARTIAL_OR_BLOCKED; not validated |

No publication, tag, merge to main, site deployment or release artifact was
created.
