# WP13 P0 full validation report

**Project:** QF Solver v0.2.12 alpha  
**Status:** `WP13_P0_PARTIAL_OR_BLOCKED` (P0 execution in progress; package solve smokes await a policy-compatible controller and explicit Owner authorization)  
**PR:** #114 — [WP13] Verify v0.2.12 release candidate artifacts  
**Release base:** `ab137051d920d7fa9aae9a3012a48b2b26e2198b`

## 1. Candidate identity

- Owner-specified PR head observed at start: `57d011c9e228ffae642ff0e9b68098939c87e586`.
- P0 workflow source and tree: commit `3e2d5f07585b270bb1ac0157a911e94d59991735`, tree `6f4372b7978b089c020c3c250f473bd2dd89d4ea`.
- Frozen package source: `60c202a75d20c6dea1df35aab591bd3832d12c58`.
- Frozen selected-distribution contract: `QF-0212-WP13-SELECTED-CANDIDATE-20261031-04`, contract file SHA-256 `f8c43bd1bad5987acb589c7735ac7a1e39e0f7119e50a49dd2061cd135954833`.
- No source, tests, examples, package metadata, or manifest change was made from the frozen package source through the P0 workflow commit. The workflow change is isolated to `.github/workflows/quality.yml`.
- The original attempt to create a second managed worktree failed because C: had 248 MiB free. No cleanup was attempted; the existing clean WP13 worktree on E: is separate from the historical release checkout.

## 2. CI matrix and official workflow

The official `.github/workflows/quality.yml` was manually dispatched on the exact P0 workflow commit with `include_extended_jobs=false`:

- Run: [41201053221](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41201053221).
- Expected standard cells: Ubuntu latest / Python 3.10; Ubuntu latest / Python 3.13; Windows latest / Python 3.10; Windows latest / Python 3.13.
- Locked dependency input: `requirements/baseline-standard.txt`.
- Gates per cell: Ruff, privacy additions check, configured progressive mypy, filtered unit and integration suite with branch coverage and global minimum 80%, P0 module coverage gate with existing 90% module thresholds, `compileall`, and both officially configured quick verification commands.
- Tests marked `benchmark`, `large`, or `evidence` are excluded by the unchanged official selector. Three extended jobs (WP14 recovered evidence, full engineering campaign, and documentation evidence/benchmarks) are disabled for this dispatch. No historical campaign or benchmark was launched by those jobs.
- The workflow records commit, exact Python version, platform, and `pip freeze` in each matrix job. The four per-cell results, test counts, coverage, timings, and step logs will be recorded below after completion.

At the most recent poll, all four cells had passed dependency installation,
identity capture, Ruff, and mypy. The standard test/branch-coverage step was
still running. The workflow's privacy step printed PASS, but its manual-dispatch
fallback used `github.sha` and compared the candidate to itself; that workflow
result is invalid. The official privacy script was separately run with release
baseline `ab137051d920d7fa9aae9a3012a48b2b26e2198b` and passed. A workflow
correction now requires an explicit base SHA on manual dispatch. Final cell
verdicts and quantitative results remain pending.

## 3. Test counts, coverage, and failures

**Pending completion of run 41201053221.** Original logs will be preserved; no threshold changes or automatic reruns are permitted. The six earlier release-branch quality runs remain historical Ruff failures (F841 for `historical_front` and `exact_pressure`); they are not rewritten by this run. Their run IDs are `40947504858`, `40950131357`, `40962192076`, `41010380832`, `41018655166`, and `41025434653`.

## 4. API, CLI, serialization, and non-regression evidence

The frozen source already has 21 exact targeted test executions on Windows Python 3.13.1 and four additional exact executions on Windows Python 3.12, covering public/compatibility exports, model/result JSON round trips, refusal contracts, CLI version and packaging identity, release wording, and preserved rotor limitations. Exact nodeids and the bounded scope are listed in [`WP13_RELEASE_GATE_MATRIX.md`](WP13_RELEASE_GATE_MATRIX.md). These tests ran no solver/FEM cases. Their source remains identical to the package source `60c202a...`; no claims beyond their named assertions are made.

## 5. Installed package artifacts and checks

The v4 candidate artifacts remain bound to frozen package source `60c202a...`:

- Wheel: `qf_solver-0.2.12-py3-none-any.whl`, 1,689,654 bytes, SHA-256 `8d3e571ce7d4ced533d7b97ed0bc0f7a91e29a3d530e3a1b406716fecf721b0e`.
- Raw sdist: `qf_solver-0.2.12.tar.gz`, 1,320,055 bytes, SHA-256 `4d9e571583b3bd345abdbf4bca5f6b86e17d776c6d2a386019da32c8c0b8a44b`.
- Normalized sdist: 1,294,041 bytes, SHA-256 `4fba0a1f1e700aaa6bf58c4cdd1a0edd5adea1145db886d5bf1903d30f460da1`.
- Separate fresh Windows Python 3.13.1 environments installed the wheel and sdist with normal dependency resolution. Prior v4 import-origin, CLI version/help, package-file inventory, and six check-mesh checks passed. These did not assemble or solve a structural model.

Installed wheel and sdist copies of the selected TET4 static, modal, and dynamic examples are byte-identical to each other and parse to the same JSON values as the frozen source examples. Exact installed input and oracle hashes, mathematical tolerances, and the six proposed artifact/case runs are in [`WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md`](WP13_P0_PACKAGE_FEM_SMOKE_DECISION_DOSSIER.md). No installed-artifact solve has run.

## 6. FEM smoke status and controller gap

Static TET4, modal TET4, and undamped Newmark TET4 cases are identified from the existing examples and campaign oracles. The current `scripts/run_local_vv.py` only accepts exact pytest nodeids and checks for the solver imported from the scientific source checkout. The installed wheel/sdist import is therefore incompatible with its current preflight. No WP13 package-smoke scope, exact smoke nodeids, manifest, preflight, or reservation ledger exists. Existing WP12 development scopes are not transferable.

**Gate: BLOCKED / NOT_RUN.** No FEM was executed. The decision dossier requests authorization to prepare a minimal shell-free WP13 installed-package controller and a no-FEM synthetic CLI-to-preflight-to-manifest-to-reservation check. After that concrete controller, exact nodes, manifest, budgets, and hashes are reviewed, separate explicit Owner approval must bind the frozen manifest before any solve. If compatibility cannot be achieved without weakening the policy, leave the gate BLOCKED.

## 7. Contract, manifest, and ledger references

- Package build/install contract v4: `QF-0212-WP13-SELECTED-CANDIDATE-20261031-04`, with source and archive digests above; detailed external manifest hashes are recorded in [`WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v4.md`](WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v4.md).
- CI run 41201053221 is bound to the P0 workflow commit shown above.
- No FEM smoke execution manifest or reservation ledger was created because the compatible WP13 controller and Owner execution authorization are absent.
- Historical WP12 contracts, proof artifacts, and ledgers were not modified.

## 8. WP13 P0-specific change

`.github/workflows/quality.yml` allows a manual dispatch on the candidate branch and defaults its three non-P0 extended jobs to disabled for `workflow_dispatch`. The manual path now requires `privacy_base_sha`, validates it as a commit, and compares the candidate against it. Push/PR-to-main behavior is unchanged. The standard matrix and all quality thresholds are unchanged. The workflow records per-cell candidate/runtime identity and gives the standard matrix jobs a 90-minute timeout. YAML parsing and `git diff --check` passed before the first dispatch; the corrected workflow must be parsed and dispatched on the final workflow commit. No scientific code, test oracle, historical evidence, or package artifact was changed.

## 9. Remaining limits and anomalies

- The cross-platform/Python matrix result is not yet final while the run is active.
- Package solve smokes remain blocked on controller compatibility and explicit Owner authorization.
- v4 installed package probes cover Windows Python 3.13.1 only; they do not establish cross-platform artifact execution.
- G03 whole-repository archive clearance remains `FAIL_PRESERVED`; selected wheel/sdist checks do not clear it.
- No merge to `main`, tag, PyPI upload, GitHub Release, Zenodo deposit, or site deployment occurred or is authorized.

## 10. Gate verdicts

| Gate | Verdict | Evidence / next action |
|---|---|---|
| Exact frozen package source and artifact identity | PASS, bounded | v4 contract and hashes; no package source delta through P0 workflow commit. |
| Ruff and progressive mypy | PASS at latest poll; final run pending | Run 41201053221, four matrix cells. |
| Privacy additions gate | PASS, bounded local command; workflow rerun required | `scripts/check_privacy_diff.py --base ab137051d920d7fa9aae9a3012a48b2b26e2198b` returned 0. The first dispatch's self-comparison is rejected; rerun corrected workflow with the same base. |
| Standard unit/integration suite and global branch coverage >=80% | IN_PROGRESS | Await run result; record executed/passed/failed/skipped/deselected counts and coverage for each matrix cell. |
| P0 module branch coverage gate >=90% for declared modules | IN_PROGRESS | Await run artifacts/logs for each cell. |
| Python compilation and official quick verification | NOT_RUN_YET | Steps are pending in the same run. |
| API/CLI/serialization targeted regression set | PASS, bounded | 21 executions on Windows 3.13.1 plus four on 3.12; exact nodes are in the gate matrix. |
| Wheel/sdist install, CLI, import, check-mesh | PASS, bounded | v4 only; no assembly or solve. |
| Installed wheel/sdist static, modal, dynamic solve smokes | BLOCKED / NOT_RUN | No compatible WP13 controller or explicit exact-manifest Owner authorization. |
| Overall WP13 P0 | `WP13_P0_PARTIAL_OR_BLOCKED` | Cannot declare `WP13_P0_VALIDATED` while the required installed-artifact solve smokes are not executed and CI is pending. |

No release publication or final release authorization is implied.
