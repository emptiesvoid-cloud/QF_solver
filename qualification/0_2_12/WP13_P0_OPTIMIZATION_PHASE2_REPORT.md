# WP13 P0 optimization phase 2 report

**Status:** `WP13_P0_PARTIAL_OR_BLOCKED`.

**Release decision:** no release, tag, publication, merge into `main`, or full four-cell rerun was performed.

**Candidate branches:** PR #114 HEAD `32520eba0aacbce782c0b3cd660074ecf1b7f824`; PR #116 HEAD `368b3ef3e10b5df9e325f25bb62880a50ee24ac2`; release baseline `ab137051d920d7fa9aae9a3012a48b2b26e2198b`.

The measurements in this report use targeted, non-FEM tests. Raw local log files were retained outside the checkout; their sizes and SHA-256 identities are recorded in [the phase 2 evidence JSON](wp13_test_optimization_phase2_evidence.json). No coverage run followed these test-only changes, so the current P0 coverage and four-cell matrix remain `NOT_ACQUIRED`.

## 1. Windows stall after 602 passes

### Hosted evidence

GitHub Actions run [41225195330](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41225195330), job `124607776630` (Windows, Python 3.13), was cancelled at the 180-minute limit after 602 passed, 5 skipped and 150 deselected. Its log contains no active nodeid, stack trace, CPU or RSS measurement. It therefore does not establish a root cause.

The Owner-cited earlier run [41210713065](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41210713065) is a separate source identity, `2865587a44f9e461a0b4e4286c912c17e4f04be5`. Its Windows/Python 3.13 job `124564905544` ended cancelled after 602 passed, 5 skipped and 149 deselected in 10,723.80 s. The final log line contains no active nodeid, stack or traceback. The Ubuntu/Python 3.13 job `124564905530` completed with 4,659 passed, 17 failed, 32 skipped and 149 deselected in 7,627.12 s (84.75% coverage). No job from either run remains active.

The 17 Linux failures are classified from that run's short summary and tracebacks:

| Count | Failing tests | Cause and disposition in the candidate |
|---:|---|---|
| 14 | `tests/unit/test_wp12_process_attestation.py` | The attestation backend correctly returned `DENY_EXECUTION` with `SUSPENDED_WINDOWS_PROCESS_REQUIRED_FOR_ATTESTATION` on Linux before the Windows-child scenarios ran. The tests had expected post-launch statuses on a platform that cannot provide the required suspended Windows process. The candidate now asserts the fail-closed Linux refusal explicitly, while retaining the deeper child/receipt checks on Windows. The production attestation code and its denial policy are unchanged. |
| 1 | `test_pilot_v4_manifest_binds_separate_checkouts_and_stays_blocked` | The test constructed `--junitxml` with a hard-coded Windows separator. It now uses `Path` composition, preserving the exact argv/nodeid check on both platforms. |
| 1 | `test_provenance_plugin_accepts_pinned_inventory_superset_with_only_fake_module` | A previously imported checkout `solveur` module contaminated the synthetic fake-module fixture. The test now removes cached `solveur` modules before injecting the fake, leaving the pinned-inventory assertions intact. |
| 1 | `tests/unit/test_wp12b_hex20_affine_diagnostic.py::test_wp12b_hex20_affine_patch_archives_residual` | The standard-suite `-k` exclusion named the old `test_wp12_hex20_...` spelling and missed the actual `test_wp12b_hex20_...` node. The controller refused the run before assembly/solve because no registered diagnostic authorization was present. The candidate fixes the exclusion spelling; the diagnostic remains available only through its authorized scientific route. No FEM ran in the failed CI attempt. |

The three test fixes and corrected quality filter are present at PR #114 HEAD `32520eba0aacbce782c0b3cd660074ecf1b7f824`; the corresponding test and workflow blobs match run `41225195330` at `f00bbb9c23769f984a12c2dda37802382ffc5414`. The process-attestation production source is unchanged across these commits. On that subsequent Linux/Python 3.13 run, the standard suite completed with 4,676 passed, 32 skipped and 150 deselected in 7,120.37 s; the P0 module gate and quick verification also passed. This is historical executed evidence on the same relevant test/workflow blobs, not a new run for this report. The 17 failures were test-platform assumptions, a cross-platform path construction, fixture isolation and a stale selection spelling; none required weakening a security refusal or scientific oracle.

### Bounded local diagnostic

The quality-workflow filters selected 4,708 items in a local collect-only pass; the policy module began at selected item 556 and contributed 247 items. With 602 passes plus 5 skips, the next ordered item would be item 53 of that module:

`tests/unit/test_development_autonomous_policy.py::test_wp12_runner_selects_scope_mandate_without_launching[rotor]`

This is an order-based candidate, not a nodeid recorded by the cancelled hosted job. The module blob (`6603a639662bf79462d14bb87d8b9929d1c7adb2`) and quality workflow blob (`e1ebb19f35ea640812f3dd1e742b1be9a74dcaac`) match the run source at `f00bbb9c23769f984a12c2dda37802382ffc5414`.

On Windows 10 / CPython 3.13.1 / pytest 8.4.1, the exact node passed alone (1 passed in 1.32 s; test body 0.035 s), then passed again in a same-process prefix of the first 53 policy-module nodeids (53 passed in 8.66 s). The prefix was governance-only and used temporary test data. Peak sampled process-tree RSS was 135,376,896 bytes. The checkout stayed unchanged. No FEM, benchmark, campaign or scientific ledger write occurred.

**Conclusion:** `NOT_REPRODUCED_LOCALLY`; the hosted cause remains unproven. The test did not exhibit an isolated hang or an interaction within the first 52 preceding tests from this module.

A new manual workflow, `.github/workflows/wp13-windows-diagnostic.yml`, and its bounded runner are included in this PR. It uses Windows/Python 3.13 only, a 15-minute job cap, a 110-second in-test watchdog (under the 120-second limit), `pytest -vv`, per-node timestamps/resource snapshots, timeout trace output, and runner-temp logs. It collects the filtered module, runs the suspected node alone, then the first 53 nodes in one process. Its source and nodeid digests fail closed if the tested inputs change. The selected tests are synthetic/governance tests; output and basetemp remain outside the checkout.

The hosted workflow was **not dispatched**. GitHub exposes `workflow_dispatch` only when the workflow file exists on the default branch ([GitHub documentation](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions#onworkflow_dispatch)). This directive forbids a merge into `main`, so a hosted Windows reproduction remains blocked until an Owner-approved route makes the workflow available there.

## 2. PR #115 and PR #116

### PR #115 — contact documentation assets

PR #115 remains open at `00306cd4f6358947f329ded2f7450925225037ce`, based on release baseline `ab137051d920d7fa9aae9a3012a48b2b26e2198b`. Its change is limited to the contact documentation asset test: campaign `.run()` methods are guarded and the publisher uses a checked-in asset fixture. The exact test passed locally on Windows/Python 3.13.1: 1 passed in 1.83 s. It contains no FEM execution. GitHub reports no checks for this PR; it was not merged.

The earlier 73.006-second CI file span predates this separation. The previously measured test-call time fell from 41.10 s to 0.03 s; the current targeted run confirms the replacement test still passes.

### PR #116 — release audit scan composition

PR #116 remains open and GitHub reports `MERGEABLE / CLEAN`, with no checks attached. Its base ref is PR #114, but the recorded base SHA is `6268a263110120b884473c5c5c91a610d7ffcc9e`, while PR #114's live HEAD is `32520eba0aacbce782c0b3cd660074ecf1b7f824`. The intervening PR #114 changes are its optimization report and static inventory. Product source and build metadata are unchanged between those commits. I left the stack and artifacts untouched; no merge or rebase was used to refresh the recorded base.

Commit `368b3ef3e10b5df9e325f25bb62880a50ee24ac2` adds a test-only, session-scoped share of the current public-source audit report. The report is shared only when its input identity remains stable: `HEAD` and tree, Git status, tracked diff content, untracked content, and Git index flags are checked. The fixture rejects assume-unchanged/skip-worktree cases and verifies the identity before and after reuse. If it cannot establish that identity, tests fall back to independent real scans. No product scanner, acceptance rule, finding, threshold or oracle changed.

One real `audit_public_release` call supplies the actual report to the scanner test and the public-document classification test. The `audit_release_archive` scanner and its direct full-current-tree test remain separate and real. The public-source result remains `FAIL` with the existing findings visible.

## 3. Measured audit savings

All paired runs used the same Windows 10 / CPython 3.13.1 / pytest 8.4.1 host, without coverage. The exact nodeids, counts and log hashes are in the JSON evidence file.

| Comparison | Tests | Real source scans | Pytest time | Wall time | CPU | Peak sampled RSS | Read bytes | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Before PR #116, two public-document assertions | 2 | 2 | 270.49 s | 272.46 s | 243.84 s | 200,392,704 B | 1,287,881,919 B | 2 PASS |
| After PR #116 module fixture | 2 | 1 | 119.99 s | 121.94 s | 120.92 s | 197,554,176 B | 652,587,121 B | 2 PASS |
| PR #116 before cross-module sharing | 3 | 2 | 238.05 s | 241.72 s | 239.08 s | 200,441,856 B | 977,317,179 B | 3 PASS |
| PR #116 at clean HEAD `368b3ef3` | 3 | 1 | 132.14 s | 135.68 s | 123.25 s | 196,747,264 B | 655,389,257 B | 3 PASS |

The first comparison reduced measured pytest time by 55.6% and source reads by 49.3%. The same-three-nodeid comparison on the final PR #116 HEAD reduced pytest time by 44.5%, sampled CPU by 48.4%, and process read bytes by 32.9%. These are targeted Windows measurements, not a claim about whole-suite or Linux CI savings. No coverage report was collected.

The three report-composition and integration nodes also passed (3 passed in 6.34 s). Ruff and `git diff --check` passed on the affected tests.

### Residual archive scan

The exact real archive node `test_current_git_archive_keeps_whole_repository_hygiene_findings_visible` was run once with a 480-second measurement cap. The harness interrupted it before pytest produced a verdict. At approximately 456 seconds wall time, the process had consumed at least 452.92 seconds CPU and had a sampled working set of 98,103,296 bytes. The Git archive child process had already exited; Python was still iterating and scanning archive members. This is recorded as `INTERRUPTED_BY_LOCAL_MEASUREMENT_CAP`, not `FAIL` or `PASS`.

The archive implementation blob `d162d167e8429b59a19071c5c4448d63b03bc2c5` is unchanged between the Linux full-suite run and PR #116. The Linux/Python 3.13 quality job in run 41225195330 passed with the real archive test selected. The new PR change does not cache archive contents or replace its real test. One archive is generated per direct invocation; no repeated generation was found inside the scanner itself.

## 4. Historic top 20 cost spans

The run 3 logs did not include node-level timings, CPU or RSS. The table therefore lists the 20 largest **test-file wall proxies** from Ubuntu/Python 3.13, not exact node durations or rankings. The values predate PR #115 and PR #116. Per-node timings cannot be reconstructed from them.

| Rank | Test file | Static functions | File wall proxy (s) | Classification / action |
|---:|---|---:|---:|---|
| 1 | `tests/unit/test_release_readiness.py` | 4 | 2413.651 | Repeated release audit composition; optimized by #116; remeasure on a future representative suite. |
| 2 | `tests/integration/test_release_readiness_pipeline.py` | 1 | 1229.360 | Composition test uses real worktree state and synthetic scanner reports after #116. |
| 3 | `tests/unit/test_public_release_audit.py` | 9 | 1226.984 | Keep real source and archive scanner tests; real archive scan remains costly. |
| 4 | `tests/unit/test_wp_e01_j2_corotational_global.py` | 2 | 504.639 | Global assembly/Newton mechanics; exact nodes need scientific-scope review. |
| 5 | `tests/unit/test_nonlinear_multielement.py` | 31 | 337.249 | Mixed nonlinear, buckling, arc-length and contact scenarios; classify exact nodes. |
| 6 | `tests/unit/test_public_document_audit.py` | 2 | 309.638 | Two assertions shared one actual scan after #116. |
| 7 | `tests/integration/test_contact_verification_cli.py` | 1 | 152.604 | CLI test executes a contact verification campaign; keep separate from pure CLI contract tests. |
| 8 | `tests/unit/test_contact_documentation_assets.py` | 1 | 73.006 | Old test executed three campaigns; #115 replaces this with a pure asset wiring test. |
| 9 | `tests/unit/test_corotational_j2_corrected.py` | 31 | 71.366 | Mechanics and finite-difference tests; exact-node classification required. |
| 10 | `tests/integration/test_examples.py` | 6 | 61.737 | Mixed examples; classify each node as solve, conversion or interface. |
| 11 | `tests/unit/test_wp_e01_j2_coro_phase8.py` | 3 | 58.202 | E01-associated nodes; review for math-only versus assembly/FEM execution. |
| 12 | `tests/unit/test_architecture_rules.py` | 5 | 56.963 | Repository-wide source scans, not FEM. |
| 13 | `tests/unit/test_wp12_diverse_models.py` | 13 | 51.157 | Diverse model and solver cases; exact-node authorization review. |
| 14 | `tests/unit/test_nonlinear_performance.py` | 1 | 40.334 | Nonlinear performance case; preserve as a separate benchmark or authorized campaign. |
| 15 | `tests/unit/test_hex20_campaign.py` | 1 | 34.971 | Campaign-shaped numerical node; keep outside routine unit label unless explicitly authorized. |
| 16 | `tests/integration/test_api_and_cli.py` | 21 | 34.153 | Mixed API/CLI with solves; separate pure interface contracts from solve nodes. |
| 17 | `tests/unit/test_frictional_contact_family_survey.py` | 4 | 33.064 | Contact mechanics/survey nodes; exact-node classification required. |
| 18 | `tests/integration/test_large_model.py` | 27 | 19.461 | Mixed API, conversion, readiness and solver cases; split by behavior only with coverage preserved. |
| 19 | `tests/integration/test_vnv_cli.py` | 5 | 18.570 | V&V command paths; distinguish collect-only/CLI wiring from actual execution. |
| 20 | `tests/unit/test_total_lagrangian_j2.py` | 12 | 18.557 | Finite-kinematic/tangent checks; classify their numerical scope, not by directory name. |

These historical spans are a triage list, not permission to move or suppress tests. PR #115 fixed the documentation-only case. For other numerical candidates, retain the assertions and oracles while routing exact FEM/campaign nodeids under the applicable authorization. The earlier AST comparison found no duplicate group proven redundant; no test was removed solely for cost or body similarity.

## 5. CI proposal and remaining gates

1. Keep a single reference environment on Ubuntu/Python 3.13 for the full authorized standard suite, Ruff, mypy, compilation, API/CLI checks, global branch coverage `>=80%`, P0 coverage `>=90%`, and required quick verification.
2. Use Ubuntu/Python 3.10 and Windows/Python 3.10/3.13 for targeted deterministic compatibility tests covering API, CLI, serialization, loading and installation boundaries. Keep platform-sensitive tests selected explicitly.
3. Keep the new Windows policy diagnostic independent and manually triggered; it is not a substitute for the official suite.
4. Record the previous four-cell full-suite obligation as `NOT_ACQUIRED` until an Owner decision changes that release criterion. No workflow quality thresholds or gates were changed here.
5. Do not automatically launch FEM campaigns or benchmarks from the historical inventory. Route those by exact nodeid and current authorization.

## 6. Corrections, limitations and disposition

- PR #115: test-only separation verified; current exact node passes.
- PR #116: identity-bound sharing added to tests only; targeted scanner, document, composition and integration assertions pass; real source scanner remains exercised. The current archive test is locally incomplete at the measurement cap but has an unchanged implementation and historical Linux full-suite evidence.
- New diagnostic workflow and runner are prepared for review in [PR #117](https://github.com/emptiesvoid-cloud/QF_solver/pull/117); no hosted diagnostic was run because the workflow is not on the default branch. The PR has no checks attached.
- No release package, wheel, sdist, coverage gate, full matrix, tag, publication, site update, or merge into `main` was performed.
- Current P0 status remains `WP13_P0_PARTIAL_OR_BLOCKED`. These measurements do not qualify the release candidate or identify the hosted Windows root cause.

**Next Owner decision:** decide whether the manual diagnostic may be made available on the GitHub default branch so the exact Windows case can be tested on a hosted runner. Until then, the remote cause remains unconfirmed; no full matrix should be relaunched on the basis of this report alone.
