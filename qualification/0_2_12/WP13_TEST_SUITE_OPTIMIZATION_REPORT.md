# WP13 test suite optimization and rationalization

**Status:** WP13 P0 remains PARTIAL_OR_BLOCKED.  
**Release decision:** No release, publication, tag, merge to main, or quality-criteria change is authorized or performed.  
**Release base:** ab137051d920d7fa9aae9a3012a48b2b26e2198b  
**PR #114 documentation head:** a29abce0a1b7a3d36ca846240ec63d72b651a848  
**Run 3 code/test source:** f00bbb9c23769f984a12c2dda37802382ffc5414  
**Evidence run:** GitHub Actions 41225195330  
**Inventory:** WP13_TEST_SUITE_INVENTORY.csv, 4,175 static pytest candidates in 705 files.

## 1. Scope and evidence boundary

This report uses the completed run 3 logs and exact-node local measurements already acquired. It does not rerun a full suite or a FEM test. Run 3 is the only corrected complete Linux result; the Windows jobs timed out. The earlier 17-failure run and its test/policy classifications remain in WP13_P0_TEST_PERFORMANCE_AND_CI_OPTIMIZATION_REPORT.md. A final local process inventory found no active pytest, Python solver, or package-smoke process; the latest quality workflows are completed, not queued or running.

The inventory is a static AST inventory of module-level test functions and test methods on classes, not a pytest collection manifest. It does not expand dynamic parametrization, plugin-generated cases, fixture behavior, or exact workflow keyword exclusions. The file records this limitation per row. CI collected 4,858 items per cell, of which 4,708 were selected (4,676 passed and 32 skipped; 150 deselected). The static 4,175 function candidates therefore must not be read as the exact collected or selected test count.

Per-node CPU, memory, assertion oracle, coverage, and exact duration were not emitted by the CI workflow. Aggregate Linux branch coverage was 84.75%; the two declared P0 modules passed at 100% and 92.16%. No per-node coverage can be reconstructed from those artifacts.

## 2. Dominant observed CI costs

The following are the 20 largest elapsed spans attributable to test-file progress records in Ubuntu/Python 3.13, ordered by elapsed span. These are **file-level wall proxies**, not per-node durations. Each span includes test execution and may include setup or collection. The logs have no node-level timestamps, CPU, or RSS. Function names and static function counts are available in the linked inventory.

| Rank | Test file | Static test functions | File wall proxy (s) | Interpretation |
|---:|---|---:|---:|---|
| 1 | tests/unit/test_release_readiness.py | 4 | 2413.651 | Repeated whole-repository readiness and scanner calls. |
| 2 | tests/integration/test_release_readiness_pipeline.py | 1 | 1229.360 | One end-to-end call scans the current worktree and archive. |
| 3 | tests/unit/test_public_release_audit.py | 9 | 1226.984 | Whole-source and current Git archive checks dominate this module. |
| 4 | tests/unit/test_wp_e01_j2_corotational_global.py | 2 | 504.639 | Global assembly/Newton mechanics test; standard-suite classification needs review. |
| 5 | tests/unit/test_nonlinear_multielement.py | 31 | 337.249 | Several campaign, nonlinear, buckling, arc-length, and contact scenarios. |
| 6 | tests/unit/test_public_document_audit.py | 2 | 309.638 | Current public-document audit is repeated for two assertions. |
| 7 | tests/integration/test_contact_verification_cli.py | 1 | 152.604 | One API/CLI test executes contact verification campaigns. |
| 8 | tests/unit/test_contact_documentation_assets.py | 1 | 73.006 | Before PR #115, documentation generation ran three numerical contact campaigns. |
| 9 | tests/unit/test_corotational_j2_corrected.py | 31 | 71.366 | Multiple mechanics and finite-difference tests. |
| 10 | tests/integration/test_examples.py | 6 | 61.737 | Example workflows; requires per-node classification. |
| 11 | tests/unit/test_wp_e01_j2_coro_phase8.py | 3 | 58.202 | E01-associated tests; classify their solve/assembly scope before CI placement. |
| 12 | tests/unit/test_architecture_rules.py | 5 | 56.963 | Repository-wide architecture/source checks. |
| 13 | tests/unit/test_wp12_diverse_models.py | 13 | 51.157 | Diverse-model and solver checks; classify by exact node. |
| 14 | tests/unit/test_nonlinear_performance.py | 1 | 40.334 | Bounded nonlinear performance campaign. |
| 15 | tests/unit/test_hex20_campaign.py | 1 | 34.971 | Campaign-oriented numerical test. |
| 16 | tests/integration/test_api_and_cli.py | 21 | 34.153 | API/CLI paths include several solves. |
| 17 | tests/unit/test_frictional_contact_family_survey.py | 4 | 33.064 | Contact-family mechanics and survey cases. |
| 18 | tests/integration/test_large_model.py | 27 | 19.461 | Mixed API, readiness, conversion, and solver cases. |
| 19 | tests/integration/test_vnv_cli.py | 5 | 18.570 | V&V command workflows. |
| 20 | tests/unit/test_total_lagrangian_j2.py | 12 | 18.557 | Finite-kinematic and tangent checks. |

The same three release-audit modules also dominate Ubuntu/Python 3.10: 2,724.601 s for test_release_readiness.py, 1,375.480 s for test_public_release_audit.py, and 1,366.752 s for test_release_readiness_pipeline.py. The exact file-level spans differ slightly by Python version.

### Cost cause

Source inspection confirms that the expensive tests repeatedly invoke repository-wide audits:

- release_readiness calls audit_public_release, audit_release_archive, and audit_git_history_paths;
- audit_public_release enumerates Git-tracked public files and reads/scans their contents;
- audit_release_archive creates and scans a Git tar archive;
- the unit and integration tests invoke those read-only checks against the real checkout more than once;
- public_document_audit also invokes the current public-release audit.

This is repeated repository I/O and archive scanning, not solver algorithm time. The distinct scanner contracts remain asserted. Separate PR #116 (stacked on PR #114) prepares a test-only reduction: readiness-composition tests inject explicit scanner reports instead of re-running source/archive scans; the current-root history check remains real once; the integration test continues to read real Git worktree state; and the two public-document assertions share one read-only report through a module fixture. The full public-source and archive scanners remain exercised by their dedicated current-repository tests. No product-level cache or oracle removal is proposed. PR #116 is not yet integrated into the candidate, so its CI saving is not measured.

Other high-cost files contain numerical or campaign-shaped tests. Their module durations do not identify which individual nodes dominate. Do not move or suppress a numerical oracle solely based on a module wall time.

## 3. Windows stall after 602 passed

Run 3 Windows/Python 3.10 and 3.13 both reached 602 passed, 5 skipped, and 150 deselected before the 180-minute cancellation. Both logs show the progress line for tests/unit/test_development_autonomous_policy.py at 12%, then a late burst of dots and a KeyboardInterrupt stack in pathlib. The logs omit verbose node reporting and full traceback. They provide no CPU, RSS, exact active nodeid, or per-test timeout.

The exact in-flight node is therefore **unresolved**. A static count of dots can suggest a candidate near test_wp12_runner_selects_scope_mandate_without_launching[rotor], but quiet progress output is buffered and does not prove that identity. That exact synthetic node passed its prior isolated local Windows run in 0.74 s; this does not reproduce or rule out a hosted-runner interaction. The traceback in pathlib suggests filesystem/path work but does not establish the cause.

Classification: repeated Windows runner/test-process stall; no assertion failure was recorded in run 3. Treat the completed Windows matrix as BLOCKED and Windows coverage as NOT_ACQUIRED. Do not report a product defect or a fixed stall without a verbose hosted reproduction. The next diagnostic should be a short Windows-only run of one exact candidate node at a time, with verbose nodeids, full traceback, per-node duration and a hard job timeout. Do not repeat the whole suite for this purpose.

## 4. Contact documentation test correction

The old node tests/unit/test_contact_documentation_assets.py::test_contact_publisher_includes_the_structural_friction_evidence invoked three campaigns, including two structural TET4 refinement campaigns. Run 3 file-level spans were 68.897 s on Ubuntu/Python 3.10, 73.006 s on Ubuntu/Python 3.13, 56.033 s on Windows/Python 3.10, and 75.330 s on Windows/Python 3.13. Its previous bounded local run measured 41.10 s pytest call, 39.438 s CPU, and 476.4 MiB peak RSS. This was a documentation-wiring test that unexpectedly included FEM, outside its intended test category.

PR #115 separates those responsibilities. The replacement test monkeypatches all three campaign run methods, copies a checked-in fixture image through the publisher outputs, and verifies campaign routing, generated files, and copied assets. It cannot enter a solver because every campaign run method is replaced. The exact replacement node passed locally: 1 passed, 0.03 s pytest call; Ruff passed and git diff --check passed. The prior and current calls were measured on the same local Windows/CPython 3.13.1 environment: 41.10 s to 0.03 s, a 99.93% reduction in that test-call measurement. The new run's CPU and RSS were not measured. No post-change CI timing exists, so a CI saving is not claimed. Contact campaign numerical tests and their oracles remain unchanged.

## 5. Redundancy analysis

A normalized AST-body scan found 16 groups of identical test function bodies: 15 groups spanning versioned WP08 M1/M2/M3 runner test modules and one group spanning the G09 lot 1 and lot 2 test files. These are candidates for manual review only. The versioned modules import different runner revisions and the G09 modules represent separate lot scopes. Identical syntax does not establish identical target behavior or defect detection. No group is a proven duplicate, so no test has been deleted or consolidated.

The inventory CSV marks the corresponding rows with an exact-body group ID and a warning to compare target imports. Filename similarity and shared source lines are not treated as redundancy proof.

## 6. Test classes and proposed three-level CI

| Level | Proposed contents | Evidence / constraints |
|---|---|---|
| A — FAST_PR | Ruff, mypy, compileall, quick CLI/API checks, fast serialization and governance contract tests, changed-file unit tests. | Candidate set only. Must be explicit nodeids or reviewed markers. Does not replace release coverage or the full standard suite. |
| B — RELEASE_GATE | Complete permitted standard suite on the reference environment; global branch coverage >=80%; existing P0 module gates >=90%; targeted compatibility and installed-package checks on the declared OS/Python cells. | The existing four-cell full-suite obligation remains NOT_ACQUIRED on Windows. A selected compatibility subset is not equivalent to full-suite coverage. No workflow or threshold change is applied here. |
| C — SCIENTIFIC_VV | FEM campaigns, convergence studies, benchmarks, qualification and certificate evidence under exact frozen manifests, budgets, ledgers, controller scope, and Owner authorization. | Keep separate from routine PR tests. The standard suite currently includes some campaign-shaped or solve-bearing tests that require node-level classification; do not silently relabel a completed run as controlled V&V. |

Keep the existing observed Linux coverage result: global branch coverage 84.75%; P0 modules 100.00% and 92.16%. Do not reduce thresholds or infer per-node coverage. Full four-platform coverage remains incomplete.

## 7. Results before and after

| Indicator | Before / recorded run 3 | After optimization | Status |
|---|---|---|---|
| Static pytest candidates | 4,175 definitions across 705 files | Same candidates; contact node behavior separated | Inventory is static and does not expand dynamic parametrization. |
| Selected Linux tests | 4,676 passed, 32 skipped, 150 deselected per cell | No full rerun | No suite-level test-count change measured. |
| Ubuntu/Python 3.13 suite duration | 7,120.37 s | Not measured | No full-suite speedup claim. |
| Global branch coverage | 84.75% | Not remeasured | Existing Linux result retained; thresholds unchanged. |
| P0 module branch coverage | 100.00%, 92.16% | Not remeasured | Existing Linux result retained. |
| Contact docs test call | 41.10 s before; 39.438 CPU s; 476.4 MiB peak RSS | 0.03 s call after; CPU/RSS unavailable | Same local Windows/Python 3.13.1; 99.93% call-time reduction, in PR #115 only. |
| Readiness/audit repeated calls | Ubuntu/Python 3.13 module proxies: 2413.651 s unit + 1229.360 s integration; 1226.984 s public-release audit module | Targeted composition nodes pass with repository source/archive scanners stubbed; no CI rerun | PR #116 preserves the dedicated real scanner tests; suite-level saving not measured. |
| Windows full standard suite | 602 passed before 180-minute cancellation in each Python cell | Not rerun | BLOCKED / coverage NOT_ACQUIRED. |
| Exact body duplicate groups | Not inventoried | 16 groups found; none proven redundant | No deletion or consolidation. |
| Distinct oracle count / mutation detection | Not available | Not measured | Requires a separate, bounded oracle inventory and representative mutation plan. |

The measured 0.03 s contact test is a local test-call measurement, not a whole-job or CI comparison. The historical run 3 file proxies imply approximately 56–75 s per complete matrix cell was associated with the old module, but no post-change hosted result exists.

## 8. Corrective actions and integration

| Action | Result |
|---|---|
| Separate documentation asset wiring from numerical contact campaigns | Implemented in PR #115; exact node and Ruff passed locally. |
| Record complete static candidate inventory and cost evidence | Added WP13_TEST_SUITE_INVENTORY.csv and this report to PR #114. |
| Identify exact Windows in-flight node | Not acquired from current logs. No root-cause fix claimed. |
| Remove or merge presumed duplicate tests | Not justified; 16 AST matches target versioned modules/lots. |
| Reduce repeated full-repository audit work | Test-only change prepared in PR #116, stacked on #114; exact targeted nodes pass and Ruff passes. No CI timing after change. |
| Correct initial targeted test failure | The assertion compared raw history status with its normalized readiness-gate status. Corrected the mapping and preserved the first failure log in PR #116; exact rerun passed. |
| Reorganize CI | Proposal only; no workflow configuration changed and no acceptance gate reduced. |

Do not rerun the four-cell suite until the confirmed test-scope correction is integrated and the Windows stall is diagnosed or an Owner decision changes the required matrix. A focused Windows diagnostic must use exact nodeids and a short bound. A later reference run should enable pytest per-node durations and preserve JUnit/job logs; this should be part of a planned full reference run, not a reason by itself to start another two-hour job.

## 9. Remaining limitations and next Owner decision

P0 remains PARTIAL_OR_BLOCKED. Linux standard and coverage gates passed at the recorded source identity; Windows full-suite and coverage gates are BLOCKED/NOT_ACQUIRED. No complete test inventory with exact collected parameter IDs, per-node coverage, CPU, or memory exists. No mutation-based check has measured regression detection. The CI architecture remains a proposal, not an adopted release policy.

The next Owner decision is one consolidated choice: authorize a bounded, hosted Windows diagnostic of the exact candidate node and immediate following nodeids, one test function per process with a 120-second per-node cap and a 15-minute aggregate cap, or retain the Windows P0 gate as BLOCKED pending a later diagnostic window. The run would be governance/synthetic-only and would not invoke FEM or modify scientific ledgers.

## 10. Evidence references

- Run 3: https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41225195330
- Run 2 (17 failures, corrected classifications in the earlier report): https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41210713065
- Previous performance and CI triage: WP13_P0_TEST_PERFORMANCE_AND_CI_OPTIMIZATION_REPORT.md
- Complete static inventory: WP13_TEST_SUITE_INVENTORY.csv
- Contact test separation: [PR #115](https://github.com/emptiesvoid-cloud/QF_solver/pull/115), open and not integrated.
- Release-audit test cost reduction: [PR #116](https://github.com/emptiesvoid-cloud/QF_solver/pull/116), stacked on #114 and not integrated.
- Run 3 logs and SHA-256 digests are recorded in the previous performance report; no log or historical scientific ledger was rewritten.