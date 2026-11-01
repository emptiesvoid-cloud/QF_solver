# WP13 release candidate — gate matrix

**Project:** QF Solver v0.2.12 alpha
**Release branch:** `emptiesvoids-cloud/0.2.12`
**Baseline candidate:** `ab137051d920d7fa9aae9a3012a48b2b26e2198b`
**Baseline worktree:** clean managed worktree; host path omitted.
**WP13 worktree:** changes are presented in PR #114 and remain separate from the release branch. The initial worktree was clean; finalization changes are itemized below.
**Owner scope:** WP13 engineering, candidate build and verification only; no final tag, main merge, package publication, GitHub Release, Zenodo deposit or public site synchronization.

This matrix records observed gates at the baseline and will be updated as evidence is acquired. A configured workflow is not a result. `PASS`, `FAIL`, `BLOCKED` and `NOT_RUN` are kept distinct. The initial review identified the latest published version as 0.2.11 and the current repository contents as a 0.2.12 development candidate.

## Initial gates at `ab137051d920d7fa9aae9a3012a48b2b26e2198b`

| Gate | Initial state | Acceptance criterion | Verification method | Owner / responsible | Baseline evidence |
|---|---|---|---|---|---|
| Candidate source identity | **PASS** | Clean integration worktree exactly at refreshed `origin/emptiesvoids-cloud/0.2.12`; no unreviewed baseline edits. | Compare `HEAD`, release ref, remote `ls-remote`, `git status`. | Root integrator | Candidate SHA `ab137051d920d7fa9aae9a3012a48b2b26e2198b`; clean worktree. |
| WP12/WP13 governance boundary | **PASS** | WP12 bounded closure remains authoritative; WP13 OPEN; no publication permission inferred. | Read integrated closeout and Owner directive. | Root integrator | `qualification/0_2_12/vv_local/WP12_CLOSED_AND_RELEASE_BRANCH_READY_FOR_WP13.md`; `WP12_CLOSED_BOUNDED_FOR_0_2_12_ALPHA`. |
| Version metadata targets 0.2.12 | **FAIL** | All candidate package, source, citation, README, changelog and release-note metadata identify 0.2.12 while remaining prepublication. | Cross-file metadata comparison after minimal updates; no fabricated DOI/date. | Root integrator + documentation worker | `pyproject.toml` and `src/solveur/version.py` say 0.2.11; `CITATION.cff` and README identify published 0.2.11. |
| Existing package/build rules understood | **NOT_RUN** | Candidate follows package discovery, data-file, manifest, license and selected-surface policy. | Static audit, then artifact-content checks on frozen candidate. | Packaging worker + root integrator | `pyproject.toml`, `MANIFEST.in`, `PUBLIC_RELEASE_POLICY.md`; details pending audit. |
| Public API, result DTO and serialization runtime | **NOT_RUN** | Required WP07 round-trip, metadata consistency, public/compatibility API and refusal contracts pass their exact targeted tests. | Targeted unit tests by exact function nodeid, then proportionate non-FEM integration tests; no broad suite. | API/runtime worker + root integrator | Static review found no confirmed defect. `solve --analysis` override choices omit three routes accepted through JSON model settings; whether that violates a public promise remains unestablished. No test is claimed at baseline. |
| CLI, load/save and supported-route regressions | **NOT_RUN** | CLI/help, invalid-input refusals, model-load/result-save and supported-route tests pass without launching an unapproved solver calculation. | Exact-nodeid tests and non-solving CLI probes; any solve-backed smoke test requires separate execution identity/budget/manifest. | API/runtime worker + root integrator | No run at baseline. |
| CI/lint/type/coverage gates | **NOT_RUN** | Required release checks pass on the candidate for declared Python/OS coverage; thresholds unchanged. | Run safe target checks; inspect GitHub checks and workflow target filters. Never treat untriggered workflows as PASS. | CI worker + root integrator | `quality.yml`/`docs-tests.yml` do not target this release branch; workflow definitions alone are not PASS. |
| Candidate versioned distribution contract | **BLOCKED** | New prospective frozen contract binds exact post-fix source SHA, selection, tools, exclusions and build/install probes before staging/building. | Review existing contract schema/runner, create and commit candidate-bound contract after source freeze. | Root integrator + packaging worker | Only the 0.2.11 contract is present; it cannot authorize a 0.2.12 candidate. |
| Wheel/sdist, contents and hashes | **BLOCKED** | Two reproducible candidate builds meet the bound selection; archives contain only declared files; checksum manifest and `twine check` pass. | Existing public-package verification workflow from the frozen contract into a new external output directory. | Root integrator + packaging worker | Not built; wait for candidate contract. |
| Fresh installation and import/CLI probes | **BLOCKED** | Wheel and sdist installs use separate clean environments; imports, data, dependencies and CLI probes resolve from installed artifacts outside the checkout. | Contract-bound offline install and non-solving smoke probes. | Root integrator + packaging worker | Not run; wait for frozen candidate artifacts. |
| Selected distribution privacy/licensing | **NOT_RUN** | Selected wheel/sdist and served documentation have no prohibited content, undeclared payloads or unresolved license issues. | Existing strict selected-source and artifact scans plus manual license/content review. | Distribution/privacy worker + root integrator | Prior 0.2.11 scan is not evidence for this SHA. |
| Whole-repository archive clearance (G03) | **FAIL — PRESERVE** | Only a separate future Owner-approved whole-repository review could change this status. | Preserve existing G03 finding; do not infer clearance from selected wheel/sdist checks. | Owner / root integrator | `PUBLIC_RELEASE_POLICY.md` and prior selected-distribution contract record `G03=FAIL_PRESERVED`; whole repository archive not cleared. |
| Public documentation and maturity claims | **NOT_RUN** | Version, APIs, support matrix, limitations and WP12 FAIL/INCONCLUSIVE/NOT_ACQUIRED boundaries agree; no publication announcement. | Static claim matrix and changed-document review after runtime/package stabilization. | Documentation worker + root integrator | README and docs currently identify 0.2.11; public claims audit pending. |
| Public site synchronization | **BLOCKED** | Separate Owner approval for final site synchronization. | Review local site sources and public site read-only; do not deploy. | Documentation worker + Owner | Not synchronized; publication decision remains separate. |
| Tag, `main`, PyPI, GitHub Release, Zenodo | **BLOCKED** | Explicit final Owner authorization after all gates and candidate report. | No action in this mandate. | Owner | Explicitly not authorized in WP13 directive. |

## Runtime and scientific restrictions

- WP12 evidence, thresholds, manifests and ledgers remain immutable. The bounded WP12 decision preserves TET4-L3 energy FAIL, two HEX8-SRI FAILs, HEX20 R4 FAIL and all `NOT_ACQUIRED`/`INCONCLUSIVE` states.
- No historical scientific campaign or benchmark may be launched to satisfy release engineering.
- A test that invokes a solver/FEM model is not assumed to be an ordinary unit test. Before any such smoke test, bind source/input identities, numeric/time/resource limits and an execution manifest, and obtain the separate Owner execution authorization required by the repository policy.
- `SELECTED_DISTRIBUTION_CLEARANCE` and `WHOLE_REPOSITORY_ARCHIVE_CLEARANCE` remain separate; G03 must remain failed unless its own gate is independently satisfied and authorized.

## Baseline candidate status — 2026-10-31 (historical snapshot)

The current P0 package source is
`2865587a44f9e461a0b4e4286c912c17e4f04be5`, based on release baseline
`ab137051d920d7fa9aae9a3012a48b2b26e2198b`. Contract v6 is
`QF-0212-WP13-SELECTED-CANDIDATE-20261031-06`, SHA-256
`f33a72b182439774828f8e604d6ab234bbf206c697c0f1082d7bc0ef81003db9`.
Contract v4 remains historical. The v3 and v5 failures are preserved. V6
selected-artifact checks are complete; this is not a final release
recommendation or publication authorization.

| Gate | Current status | Evidence / limitation |
|---|---|---|
| Candidate source identity | **PASS — frozen** | Selected package source `2865587a44f9e461a0b4e4286c912c17e4f04be5`; report HEAD `d6a49a279b4d8ce548e4d6ed1f48e8cad6f20e23`; v6 contract SHA-256 `f33a72b182439774828f8e604d6ab234bbf206c697c0f1082d7bc0ef81003db9`; release base `ab137051d920d7fa9aae9a3012a48b2b26e2198b`. No release tag, merge to `main` or publication occurred. |
| Version metadata and public release wording | **PASS — source review** | `pyproject.toml`, `src/solveur/version.py` and `CITATION.cff` identify 0.2.12. The CFF has no `date-released` or version DOI; the concept DOI is retained. README/docs continue to identify 0.2.11 as the latest published release. |
| WP12 closeout claims | **PASS — bounded wording** | Roadmap and closeout remain authoritative at `WP12_CLOSED_BOUNDED_FOR_0_2_12_ALPHA`; documentation preserves the TET4-L3 energy FAIL, two HEX8-SRI FAILs, HEX20 QUAD8 R4 FAIL and non-acquired states. WP12 evidence/ledgers are unchanged. |
| Public claims and documentation scope | **PASS — bounded selected surface** | Superseded WP12 status summaries and B* parent-status wording were corrected; the public qualification page now cites its historical source snapshot. Internal engineering and audit reports remain in Git but are excluded from the served site. Strict scan v3 has no selected-doc findings. |
| Targeted API/serialization/CLI tests | **PASS — 21 executions on Windows Python 3.13.1; 4 additional executions on Windows Python 3.12** | Every invocation used one exact test node. Coverage includes JSON refusal, model/result round-trip, public/compatibility APIs, CLI version, citation/release wording and retained rotor limits. No solver/FEM test ran. Exact nodes are listed in the PR evidence. |
| Representative model loading/mesh-check smoke | **PASS — non-solving only** | The same three models passed `check-mesh` on v6 wheel and sdist installs under Windows Python 3.13.1; prior Python 3.12 and 3.13 checks remain. This exercises parsing and mesh/model checks, not element assembly or a structural solve. |
| Ruff | **PASS** | `python -m ruff check src/qf_solver src/solveur tests scripts`. Two prior unused-local findings were corrected while preserving their expressions' evaluation; no oracle, threshold or ledger changed. |
| Mypy | **PASS** | CI's four-file progressive typing command; no issues. |
| Python compilation | **PASS** | CI's `compileall -q src scripts tests qf_solver.py main_solveur.py mitc4_solver.py`. |
| MkDocs | **PASS — local build only** | `python -m mkdocs build --strict -f .github/pages/mkdocs.yml` returned 0 after adding explicit exclusions for internal reports. The generated site was not synchronized or deployed. |
| Standard full test suite and coverage thresholds | **PARTIAL / FAIL — official run 2** | Manual workflow [41210713065](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41210713065) ran on exact commit `2865587a44f9e461a0b4e4286c912c17e4f04be5`. Both Ubuntu cells recorded 17 failures; global branch coverage passed at 84.75%. P0 module coverage, compileall and quick verification were skipped after test failures. Windows jobs were still active at the latest status check. A corrected run is required. |
| Ubuntu/Windows × Python 3.10/3.13 matrix | **INCOMPLETE — official run 2** | Ubuntu/Python 3.10.22 and 3.13.17 completed with the 17 failures. Windows/Python 3.10 and 3.13 remained active; exact final counts, coverage and downstream gates are pending. See the full report for original logs and targeted corrections. |
| Historical snapshot — installed-artifact static/modal/dynamic solve smoke | **BLOCKED / NOT_RUN at that checkpoint** | This earlier state predates the v7 rebind and execution; its preflight and ledger evidence remain historical. Current results are in the v7 execution addendum at the end of this matrix. |
| Candidate contract | **PASS — prospective v6** | Contract `QF-0212-WP13-SELECTED-CANDIDATE-20261031-06` binds source `2865587a44f9e461a0b4e4286c912c17e4f04be5`, selected paths, tools and build settings; its SHA-256 is recorded above. v3/v5 failed runs remain historical. |
| Selected package/documentation scan | **PASS — v6 package and unchanged v4 public docs** | V6 package scan reports 585 wheel and 593 sdist entries, zero findings. Public docs and site configuration are unchanged between v4 source `60c202a75d20c6dea1df35aab591bd3832d12c58` and v6 source `2865587a44f9e461a0b4e4286c912c17e4f04be5`, so the v4 selected-doc scan remains applicable. Neither scan clears G03. |
| Wheel/sdist, contents and hashes | **PASS — v6 two-run reproducibility; v3/v5 failures retained** | The two v6 wheel builds are byte-identical (1,689,662 bytes; SHA-256 `ae521113…b39c287a`). Raw sdist gzip files differ; normalized sdist outputs match (1,294,049 bytes; SHA-256 `183bc444…20611fde`). Both scans pass for 585 wheel / 593 sdist files with zero findings; Twine 7.0.0 passes on wheel and sdist. Full hashes are in [`WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md`](WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md). |
| Fresh installation and import/CLI probes | **PASS — v6 wheel and sdist, Windows Python 3.13.1** | Separate clean environments installed the exact run-2 wheel and raw sdist with dependency resolution. Each verified 501 installed source files and origins outside the checkout; CLI `--version` and `--help` passed. `verify-all` refused as expected because the installed artifact is not a Git checkout; it produced no report or solve. Three check-mesh commands per artifact also passed without assembly or solve. |
| Selected-artifact license inventory | **PASS — historical v4 inventory only** | The prior v4 environments exposed all 14 distributions with license metadata/files. V6 dependency versions differ and were not re-audited for legal inventory; this engineering inventory is not legal clearance. |
| Third-party legal compatibility for final redistribution | **NOT_RUN — no legal clearance claimed** | This engineering inventory is not a legal compatibility determination. Optional integrations and engineering/documentation tools are not bundled in these archives; final distribution review must follow `THIRD_PARTY_LICENSES.md`. |
| Whole-repository G03 / archive | **FAIL_PRESERVED** | `AGENTS.md` is not excluded from Git archives and tracked `docs/generated/results/*.json` are present. Neither issue is cleared by selected-distribution checks. |
| Public site deployment, final tag, main merge and package publication | **BLOCKED — not authorized** | Local docs may be reviewed in the PR; no site synchronization, tag, merge to `main`, GitHub Release, PyPI or Zenodo operation is authorized. |

### V4 installed-artifact non-solving checks

The exact wheel and sdist were each used for `check-mesh` on the TET4, BEAM2
and MITC4 examples. All six checks passed. These validate input/model and mesh
checks only; they do not assemble elements or run a structural solve. The
external report names and SHA-256 digests are recorded in the artifact
verification report.

### Bounded public-scope scan records

- v2: [`wp13_candidate_public_scope_scan_20261031_v2.json`](wp13_candidate_public_scope_scan_20261031_v2.json) records `FAIL_CLOSED_BOUNDED_PUBLIC_SURFACES` at source `0521907e43bbb6f29e95428b471da387950214c8`, with 585 package files / 0 findings and 794 selected documents / 16 findings. This failed scan is retained as history.
- v3: [`wp13_candidate_public_scope_scan_20261031_v3.json`](wp13_candidate_public_scope_scan_20261031_v3.json) records `PASS_BOUNDED_PUBLIC_SURFACES` at source `c4d4fa0a60370df4f023ac8702c5774710d16e60` and contract commit `578cb5be3ee7968a3c533f87b1d278e233c19ccf`, with 585 package files / 0 findings and 773 served documents / 0 findings. It excludes `docs/development/`, the RBE audit report, the WP12-B loads audit and the already-excluded 0.2.9 archive from site publication; their Git history and contents are preserved.
- v4: [`wp13_candidate_public_scope_scan_20261031_v4.json`](wp13_candidate_public_scope_scan_20261031_v4.json) records the same bounded counts and zero findings at source `60c202a75d20c6dea1df35aab591bd3832d12c58` and contract commit `e0d552173f932eaf7a7ef584f1f9026fd84bf336`.

### Candidate build failure retained

[`wp13_candidate_build_run1_failure_20261031_v3.json`](wp13_candidate_build_run1_failure_20261031_v3.json) records the v3 archive-verification failure and the hashes of both generated candidate artifacts. The complete raw output remains in the external run directory `wp13_candidate_build_20261031_run1`; it is not treated as a releasable candidate. Source `60c202a75d20c6dea1df35aab591bd3832d12c58` adds the missing explicit distribution entries without changing scientific code or evidence.

## API observation

Static review and targeted tests found no confirmed public API or serialization
defect. The CLI `solve --analysis` override exposes fewer choices than routes
accepted from JSON model settings (`geometric_nonlinear_static`,
`rotating_modal`, `campbell`). Documentation does not promise all JSON routes
as CLI overrides, so this remains an observed limitation, not a release defect.

### Exact targeted test nodes that passed

Windows Python 3.13.1:

- `tests/unit/test_json_io.py::test_json_reader_rejects_unknown_fields_and_bad_analysis_method`
- `tests/unit/test_json_io.py::test_json_reader_rejects_bad_schema_metadata_and_missing_dynamic_parameters`
- `tests/unit/test_large_solver_and_serialization_edges.py::test_model_writer_rbe_and_round_trip_keep_controlled_fields`
- `tests/unit/test_result_serialization_contracts.py::test_versioned_experimental_result_dtos_round_trip_without_solver_execution`
- `tests/unit/test_result_serialization_contracts.py::test_reduced_harmonic_json_round_trip_preserves_signed_zero_phase_metadata`
- `tests/unit/test_public_api_contract.py::test_public_facade_matches_documented_export_inventory`
- `tests/unit/test_public_api_contract.py::test_02x_compatibility_imports_remain_available`
- `tests/unit/test_save_result_cli_overwrite.py::test_all_json_result_cli_commands_expose_overwrite`
- `tests/unit/test_git_history_audit.py::test_history_path_filter_covers_generated_and_private_markers`
- `tests/integration/test_packaging.py::test_pyproject_declares_installable_solver_package`
- `tests/integration/test_packaging.py::test_solver_cli_version_runs`
- `tests/integration/test_packaging.py::test_portable_and_legacy_launchers_expose_qf_solver_identity`
- `tests/integration/test_packaging.py::test_mitc4_cli_version_runs`
- `tests/documentation/test_docs_generation.py::test_public_release_status_copy_distinguishes_release_and_tagged_source`

## WP13 P0 execution update — 2026-10-31

This section supersedes the prior `NOT_RUN` / `BLOCKED` entries above only for
the gates explicitly updated here; prior v2/v3/v4 records remain historical.

| Gate | Current P0 result | Evidence / limit |
|---|---|---|
| P0 candidate | **CORRECTIONS IN PROGRESS** | PR #114 was refreshed at `375872ec89699b23e5af23151feebc797bc5d94e`; the current worktree has WP13-only uncommitted corrections. The next CI run must bind the resulting commit. |
| Official four-cell standard CI | **FAIL / INCOMPLETE — run 1** | Manual run [41201053221](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41201053221) finished unsuccessfully on `3e2d5f07585b270bb1ac0157a911e94d59991735`. Ubuntu/Python 3.10 had 72 failures; Ubuntu/Python 3.13 was cancelled; Windows/Python 3.10 and 3.13 emitted test summaries but were cancelled before downstream gates. |
| Ruff / mypy | **PASS — run 1, four cells** | All four first-run cells passed Ruff and progressive mypy. Corrected-candidate CI remains pending. |
| Privacy additions gate | **PASS locally against baseline; workflow rerun required** | The first manual run compared the candidate to itself and is rejected. `python scripts/check_privacy_diff.py --base ab137051d920d7fa9aae9a3012a48b2b26e2198b` passed locally; the corrected workflow requires this explicit input. |
| Standard tests | **FAIL — Ubuntu/Python 3.10 run 1** | 4,646 passed, 72 failed, 32 skipped, 107 deselected. The original selector reached policy-controlled historical FEM cases; their results are retained. The next dispatch excludes only exact gated cases and preserves ordinary release-audit tests. |
| Global branch coverage >=80% | **PARTIAL** | Ubuntu/Python 3.10 recorded 84.76%; other cells lack completed coverage results. Corrected four-cell run pending. |
| P0 module branch coverage >=90% | **NOT_RUN** | Run 1 stopped before this downstream gate in all four cells. Corrected run required. |
| Compilation / quick verification | **NOT_RUN in completed workflow** | Run 1 did not reach these downstream steps. Local `compileall` passed; official four-cell execution remains required. |
| Installed wheel/sdist import and non-solving checks | **PASS, bounded v6** | Two source-bound builds, byte-identical wheel, normalized sdist, Twine check, fresh dependency-resolving wheel and sdist installs, installed-origin checks, CLI probes, and six check-mesh checks passed. See [`WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md`](WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md). |
| Historical snapshot — installed wheel/sdist static/modal/dynamic solve smoke | **BLOCKED / NOT_RUN at that checkpoint** | This earlier state predates the v7 rebind and execution. The source-checkout RBE2 test failure remains documented separately; current installed-artifact results are in the v7 execution addendum at the end of this matrix. |
| Overall P0 | **WP13_P0_PARTIAL_OR_BLOCKED** | Run 2 has Linux failures and pending Windows jobs; the next corrected official run is required. Installed-artifact static/modal/dynamic solve smokes remain not run pending a compatible controller, manifest and Owner authorization. No `WP13_P0_VALIDATED` claim is made. |

The complete first-run failure inventory, corrected test-scope exclusions and
local checks are in [`WP13_P0_FULL_VALIDATION_REPORT.md`](WP13_P0_FULL_VALIDATION_REPORT.md).
The exact execution identities and candidate changes are in
[`WP13_P0_EXECUTION_BASELINE.md`](WP13_P0_EXECUTION_BASELINE.md).
- `tests/documentation/test_docs_generation.py::test_current_public_surfaces_use_consistent_version_without_promotion[index.md]`
- `tests/documentation/test_docs_generation.py::test_current_public_surfaces_use_consistent_version_without_promotion[verification/evidence-and-maturity.md]`
- `tests/documentation/test_docs_generation.py::test_current_public_surfaces_use_consistent_version_without_promotion[capabilities/index.md]`
- `tests/integration/test_public_qf_solver_api.py::test_public_facade_exports_documented_workflow`
- `tests/integration/test_public_qf_solver_api.py::test_public_facade_exports_documented_types`
- `tests/integration/test_public_qf_solver_api.py::test_source_launcher_is_also_an_import_compatible_facade`
- `tests/documentation/test_docs_generation.py::test_rotating_public_evidence_retains_limits[verification/evidence-and-maturity.md]`

Windows Python 3.12 (four additional executions):

- `tests/unit/test_result_serialization_contracts.py::test_versioned_experimental_result_dtos_round_trip_without_solver_execution`
- `tests/unit/test_public_api_contract.py::test_public_facade_matches_documented_export_inventory`
- `tests/integration/test_packaging.py::test_solver_cli_version_runs`
- `tests/documentation/test_docs_generation.py::test_public_release_status_copy_distinguishes_release_and_tagged_source`


## P0 performance triage update — 2026-10-31

This addendum supersedes the run-2 status rows above only for the corrected
run-3 evidence. Run 2 and earlier results remain preserved in the linked
reports.

| Gate | Current status | Evidence / limitation |
|---|---|---|
| Candidate identity | PASS for run 3 | Official workflow 41225195330 used PR #114 HEAD f00bbb9c23769f984a12c2dda37802382ffc5414, based on release baseline ab137051d920d7fa9aae9a3012a48b2b26e2198b. |
| Ubuntu / Python 3.10 complete permitted standard suite | PASS | 4,676 passed, 32 skipped, 150 deselected, 4 warnings; 7,537.95 s. |
| Ubuntu / Python 3.13 complete permitted standard suite | PASS | 4,676 passed, 32 skipped, 150 deselected, 4 warnings; 7,120.37 s. |
| Global branch coverage >=80% | PASS on both Ubuntu cells | 84.75% in each cell. |
| Declared P0 module branch coverage >=90% | PASS on both Ubuntu cells | solveur/core/errors.py 100.00%; solveur/verification/traceability.py 92.16%. |
| Ruff, privacy additions, progressive mypy | PASS in four cells | Run-3 workflow completed these gates before each test step. |
| Compileall and official quick verification | PASS on Ubuntu; NOT_RUN on Windows | Both Ubuntu cells completed; Windows jobs were cancelled before downstream steps. |
| Windows / Python 3.10 and 3.13 complete standard suite | BLOCKED / NOT_ACQUIRED | Each job reached 602 passed and 5 skipped, then hit the 180-minute limit at the same 12% progress in the governance-policy module. Exact in-flight nodeid, coverage and downstream gates are unavailable. |
| Installed wheel/sdist mechanical solve smoke | BLOCKED / NOT_RUN | No exact WP13 Owner execution authorization or real attempt ledger; no package solve was run. |
| Overall WP13 P0 | WP13_P0_PARTIAL_OR_BLOCKED | Do not declare P0 validated. The complete four-cell suite obligation remains NOT_ACQUIRED. |

Historical snapshot note: the preceding run-3 gate state predates the explicit
Owner approval below. At that point the proposal had not been accepted and the
full four-cell result was not acquired. The bounded performance findings,
17-failure classification and earlier unmeasured CI proposal are in
[WP13_P0_TEST_PERFORMANCE_AND_CI_OPTIMIZATION_REPORT.md](WP13_P0_TEST_PERFORMANCE_AND_CI_OPTIMIZATION_REPORT.md).
No merge to main, tag, publication or package release occurred.

## Effective Owner-approved matrix — 2026-11-01

The Owner explicitly replaced the four-full-suite policy for QF Solver v0.2.12
with one Ubuntu/Python 3.13 standard reference suite and exact, targeted
non-scientific compatibility nodeids on the other three cells. This is a
policy disposition, not a PASS for the former four-suite criterion. Its three
secondary cells intentionally execute fewer tests; coverage thresholds and
scientific criteria are unchanged.

The single authorized `quality.yml` dispatch was run with
`include_extended_jobs=false` and
`privacy_base_sha=ab137051d920d7fa9aae9a3012a48b2b26e2198b`. It used exactly
commit `698e858e79d6b6ded7cdf764f5e0dd26c710c301` in PR #114:
[Actions run #41328516423](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41328516423).

| Gate | Statut | Preuve | Blocage | Action nécessaire |
|---|---|---|---|---|
| Owner approval of lightweight release matrix | PASS | Explicit Owner decision on 2026-11-01; policy and scope recorded above. | None for the matrix policy. | Keep the old criterion identified as replaced, never PASS. |
| Former four-cell full-suite criterion | REPLACED_BY_OWNER_DECISION (not PASS) | The old Windows full-suite cells remain historically incomplete; the Owner replaced this criterion for v0.2.12. | None under the approved policy. | Do not represent the old criterion as passed. |
| Candidate / workflow identity | PASS | Run #41328516423 is `workflow_dispatch` on the requested branch and exact commit `698e858e79d6b6ded7cdf764f5e0dd26c710c301`; privacy base SHA matches the approved value in all four jobs. | None for this run. | Preserve the run and artifact links. |
| Ubuntu / Python 3.13 reference suite | PASS | Python 3.13.17; 4,679 passed, 0 failed, 32 skipped, 150 deselected; pytest 2,097.90 s; global branch coverage 84.75%; P0 modules `errors.py` 100.00%, `traceability.py` 92.16%. JUnit/coverage artifact ID 13093243065. | None under this gate. | Retain the reports with the run identity. |
| Ubuntu / Python 3.10 targeted compatibility | PASS | Python 3.10.22; the 15-nodeid manifest passed 15/15, 0 failed/skipped; pytest 3.39 s. Artifact ID 13092317209. | Only the manifest selection is covered. | Keep the exact manifest and hash attached to this result. |
| Windows / Python 3.10 targeted compatibility | PASS | Python 3.10.11; the 15-nodeid manifest passed 15/15, 0 failed/skipped; pytest 6.23 s. Artifact ID 13092775721. | Only the manifest selection is covered. | Keep the exact manifest and hash attached to this result. |
| Windows / Python 3.13 targeted compatibility | PASS | Python 3.13.16; the 15-nodeid manifest passed 15/15, 0 failed/skipped; pytest 4.38 s. Artifact ID 13091563751. | Only the manifest selection is covered. | Keep the exact manifest and hash attached to this result. |
| Ruff, progressive mypy, privacy additions, compileall | PASS | All four matrix jobs report success for these checks. | None within the declared checks. | None. |
| Targeted missing-ancestor Windows loop correction | PASS (targeted scope) | Earlier targeted run #41325510873 passed 64 distinct nodeids / 65 occurrences on Python 3.10 and 3.13; the current matrix also passes all 15 compatibility nodeids on Windows. | Does not claim a full Windows standard suite. | No rerun required for this bounded fix. |
| Quick verification / extended jobs | NOT_RUN | Quick verification was skipped for this manual WP13 dispatch; documentation, engineering, and WP14 extended jobs were disabled by the approved input. | These jobs are outside this matrix execution. | Do not infer PASS; run only under their separate authorization/scope. |
| Installed wheel/sdist static/modal/dynamic smoke — checkpoint avant exécution | HISTORICAL (superseded by v7 execution addendum) | À ce checkpoint, les six tentatives étaient PREPARED_NOT_AUTHORIZED et aucune n’avait tourné. Voir l’addendum d’exécution v7 ci-dessous. | Cette ancienne ligne ne représente plus l’état courant. | Utiliser les résultats et hashes de l’addendum courant. |
| v6 wheel/sdist and public documentation identity | HISTORICAL (v6; superseded for current candidate) | This row records the prior v6 candidate and its own bounded evidence. README, `pyproject.toml`, `CITATION.cff`, MkDocs policy and public documentation links changed afterward; v7 has new source and artifact identities recorded in the addendum below. | v6 hashes do not identify the current distribution. Neither v6 nor v7 selected scans clear whole-repository G03 or independent legal review. | Use the v7 contract and hashes for the current candidate; retain v6 only as historical evidence. |
| Prospective source-archive path filtering | PASS (bounded path check) | Root `/AGENTS.md` and `docs/generated/results/**` have `export-ignore`; `git check-attr` confirms the root instruction and generated JSON are excluded while `docs/generated/mitc4_locking_results.md` remains included. Final path listing: 6,714 files; no forbidden prefix. | This proves path selection only, not archive-content clearance or GitHub history clearance. | Preserve the root-only rule and targeted test. |
| G03 whole-repository archive/history criterion | FAIL_PRESERVED | Full prospective audit at source `3ced76d`: 6,711 files, 7,060 findings on 618 paths. The final path listing has 6,714 files (+3 reports, each targeted scan 0 findings); no forbidden paths. History prefilter WARNING: 2,587 reachable commits and 1,429 events. See [`WP13_G03_REMEDIATION_REPORT.md`](WP13_G03_REMEDIATION_REPORT.md). | The 7,060 content findings and public-history warning remain; path exclusions cannot remove committed history. | Keep FAIL_PRESERVED; no history rewrite is authorized here. |
| Full repository source-content audit | NOT_RUN | The prospective archive already has 7,060 content findings and the history prefilter remains WARNING; a second full scan cannot clear either blocker. Selected v6 package/docs scans remain separately PASS. | Whole-source result is not acquired. | Revisit only after a bounded content-remediation plan and a separate history decision. |
| Technical third-party license inventory | PASS (bounded technical review) | The exact v6 wheel/sdist default dependency graph and license files were reviewed; details and limitations are in [`WP13_THIRD_PARTY_LICENSE_AUDIT.md`](WP13_THIRD_PARTY_LICENSE_AUDIT.md). | This is not an independent legal opinion and does not cover every allowed resolver version or optional extra resolution. | Retain license payloads and obtain independent review before publication. |
| Independent third-party legal review | NOT_ACQUIRED | No independent counsel/reviewer determination is recorded. | Redistribution compatibility remains unapproved. | Obtain a scoped review of the exact candidate and optional dependency policy. |
| Scientific qualification / FEM campaigns | NOT_RUN | No independent campaign ran; no smoke result is promoted as scientific qualification. | Separate manifests and Owner authorization remain required. | Use the distinct Scientific V&V gate. |
| Overall WP13 | WP13_PARTIAL_OR_BLOCKED | The approved CI matrix and bounded v7 smoke gate pass; G03, independent legal review and other release gates remain open. | Independent release gates remain. | Keep overall verdict `WP13_PARTIAL_OR_BLOCKED`. |

The explicit compatibility nodeid manifest is
[`wp13_compatibility_nodeids.json`](wp13_compatibility_nodeids.json),
SHA-256 `0fb5add51545ce77e0ce93ddc5c7c1cb20cff2d74f554136c47f24cf423156ba`.
The compatibility artifacts each contain a JUnit report; the reference
artifact contains JUnit plus global and P0 coverage evidence. The effective
CI matrix gate is PASS under the Owner-approved policy. Overall WP13 remains
PARTIAL_OR_BLOCKED.

## WP13 v7 — consolidation documentaire, package et smoke — 2026-11-01

Cette section actualise les gates de documentation et de distribution après les modifications README/métadonnées. Elle supersède les lignes qui identifiaient v6 comme l’artefact courant, sans réécrire les résultats historiques v6. Le statut CI de la matrice Owner reste attribuable à son commit et son run exacts; aucune suite complète n’a été relancée dans cette phase.

| Gate | Statut | Preuve | Blocage | Action nécessaire |
|---|---|---|---|---|
| README, liens et métadonnées | PASS | README global; `pyproject.toml`/`CITATION.cff` pointent au site officiel; 106 liens, 90 locaux valides, 16 URL HTTP 200. | Aucune dans la portée vérifiée; le site n’est pas déployé ici. | Garder 0.2.11 comme version publiée et 0.2.12 comme candidate. |
| Navigation et build MkDocs | PASS | 55 cibles existantes; `mkdocs build --strict` réussi; `docs/ai/**` exclu. | Ne prouve pas un déploiement ni la visibilité du corpus entier dans le menu. | Ne pas synchroniser le site sans mandat distinct. |
| Tests documentaires / lint / compilation | PASS | 22 nodeids ciblés passés en 2,55 s; Ruff et py_compile des modules changés PASS. | Le suite complète n’a pas été relancée et la matrice GitHub acquise est sur le commit antérieur indiqué au rapport. | Ne pas extrapoler au run complet après documentation. |
| Scan public différentiel de documentation | PASS (borné) | 761 docs; 753 blobs strictement identiques à une preuve précédente sans constat; 8 modifiés rescannés, 0 constat; 241 exclus dont 12 `docs/ai/`. Mapping SHA `71371c8e431200bd14ceb406498d4de1f862feb62597080dd7443b2b5f568eb2`; rapport SHA `5099066a3657fa12fd1af9374622c3923f14f628d97472e799f3bcc8fae71992`. | Ne scanne ni le dépôt complet ni l’histoire Git. | G03 reste `FAIL_PRESERVED`. |
| Source candidate du package v7 | PASS | Commit source `7a78cc673da2abb7c3d0afd6cabd378aa327f424`; contrat v7 SHA `d0b0030ecc7de9a34b2d6444303cfc91abe84cd3088fe371841d0f3afb4b9b43`. | Les hashes v6 ne s’appliquent plus. | Conserver v6 comme historique; lier v7 à ses nouveaux hashes. |
| Wheel et sdist normalisée v7 | PASS | Wheel 1 690 080 octets, SHA `c1debafb55a0cf4d4b8fcc349cf66f020ffd784daefde3972003cf9e325d2518`; sdist normalisée 1 295 214 octets, SHA `56c607ae305704b10f4e005c5db5a28bc11ca4902929e6bc6d03c5a1a9759174`; builds A/B identiques après normalisation; Twine PASS. |
| Archivage et scan de package sélectionné | PASS | 585 fichiers sélectionnés, 593 entrées sdist, 501 modules wheel; zéro constat, fichiers sélectionnés conformes aux blobs v7. | N’efface pas les constats hors périmètre. | Maintenir G03 indépendant. |
| Installation fraîche wheel / sdist | PASS (Windows/Python 3.13.1) | Installations propres avec baseline de dépendances; imports installés, version 0.2.12, `pip check`, CLI et six `check-mesh` TET4/BEAM2/MITC4 PASS. Aucun `solve`. |
| CI matrice release Owner | PASS sur son commit exact | Run #41328516423 / commit workflow `698e858e79d6b6ded7cdf764f5e0dd26c710c301`; un Ubuntu/Python 3.13 complet + trois cellules ciblées. | N’est pas une exécution de la matrice sur les commits documentaires ultérieurs. | Garder la politique et sa portée; pas de relance complète demandée. |
| Rebind manifeste/préflight v7 | PASS | HEAD `d0a3df9bd7265429d433b44560c0cd0606aedbf0`; manifeste SHA `4a9398df42b52d1e088d640a6896b6e00873f479f77cf8fdec01310809ffa9cb`; préflight principal SHA `01795a37ef09d67a4bd653fd34aca98d0aadee1eb23cec3ba826c63f0b20cd46`. Les packages/entrées/oracles et fichiers sélectionnés sont restés conformes. | Le préflight initial lié à c3 est historique. | Garder l’ancien rapport comme preuve historique, sans le substituer au rebind. |
| Préflight synthétique v7 | PASS_NO_FEM | Rapport SHA `7790f26725a4b9f56bcb6862de88952c279384b05e521d4b77b9908f8256187e`; ledger synthétique SHA `09b173088615a6039af701481b48b32fdf8c8e4c16b86ed9caac53da1296dd9c`; zéro réservation réelle, zéro FEM. | Contrôle synthétique seulement. | Aucun retry ni réexécution. |
| Six smoke tests installés v7 | PASS — portée exacte | Rapport [`WP13_V7_INSTALLED_PACKAGE_SMOKE_EXECUTION_REPORT.md`](WP13_V7_INSTALLED_PACKAGE_SMOKE_EXECUTION_REPORT.md); six `EXECUTION_PASS` et six `NUMERICAL_ORACLE_PASS`; ledger réel SHA `62c2c843e3cd5c80a2098efef97ca146a332c9a4375df549542d2593522bb67f`. | N’est ni qualification globale ni clôture WP12/WP13. Les sorties ont `qualification_summary=WARNING` et traceabilité `FAIL`. | Ne pas convertir ce résultat en `QUALIFICATION_PASS`. |
| G03 / archive complète et historique | FAIL_PRESERVED | Les scans v7 ne couvrent que package/documents sélectionnés. | Constat complet et risque d’histoire restent ouverts. | Décision indépendante; ne pas reclasser ici. |
| Revue légale indépendante | NOT_ACQUIRED | Inventaire technique versionné; aucune clearance juridique indépendante. | Compatibilité de redistribution non approuvée par un examinateur indépendant. | Revue distincte sur les termes redistribués et extras. |
| WP12 / qualification scientifique | PASS dans sa fermeture bornée; échecs conservés | WP12 reste `WP12_CLOSED_BOUNDED_FOR_0_2_12_ALPHA`; TET4-L3, HEX8-SRI, HEX20, D01/C4/E01 conservent les dispositions existantes. | Ce statut ne vaut pas qualification globale ni WP13 terminé. | Ne pas modifier les résultats/ledgers ni promouvoir une maturité. |
| Publication, tag, merge, déploiement | NOT_RUN | Aucun de ces actes n’a eu lieu. | Hors autorisation actuelle. | Aucun sans décision distincte. |
| Verdict global WP13 | WP13_PARTIAL_OR_BLOCKED | Gate CI selon la matrice approuvée et gate artefacts v7 PASS dans leur portée. | Smoke exact, G03, revue légale et autres gates restent ouverts. | Revue Owner; ne pas déclarer la release terminée. |

Les contrôles système package/build ne mesurent ni CPU ni RSS. Le runner interne rapporte 51,36 s et 47,82 s après matérialisation des sources; les commandes build ont pris 24,40 s et 22,82 s. Le coût de matérialisation Git préalable n’est pas chronométré par ce runner, et aucune mesure CPU/RSS n’est acquise. La nouvelle lecture documentaire a réutilisé des résultats uniquement sur identité SHA-256/taille égale, a lu les blobs via une session `git cat-file --batch`, et a rescanné uniquement les huit documents modifiés; le résultat G03 complet reste indépendant.

**Verdict : `WP13_PARTIAL_OR_BLOCKED`.** Le gate d’artefacts sélectionnés v7 est PASS; il ne ferme pas WP13 et n’autorise ni smoke, ni intégration, ni publication.

## WP13 v7 — exécution des six smoke tests installés — 2026-11-01

Le rebind et les préflights ont réussi sur HEAD `d0a3df9bd7265429d433b44560c0cd0606aedbf0`. Le contrôleur officiel a exécuté les six couples une seule fois, en série, avec arrêt au premier échec. Les six ont terminé avec `EXECUTION_PASS` et `NUMERICAL_ORACLE_PASS`; aucune septième tentative, aucun retry ni timeout.

| # | Artefact / cas | Statut | Durée murale | RSS maximale (octets) |
|---:|---|---|---:|---:|
| 1 | Wheel / STATIC-01 | EXECUTION_PASS · NUMERICAL_ORACLE_PASS | 1,917 s | 119 304 192 |
| 2 | Wheel / MODAL-01 | EXECUTION_PASS · NUMERICAL_ORACLE_PASS | 1,854 s | 119 517 184 |
| 3 | Wheel / DYNAMIC-01 | EXECUTION_PASS · NUMERICAL_ORACLE_PASS | 1,926 s | 119 152 640 |
| 4 | Sdist / STATIC-01 | EXECUTION_PASS · NUMERICAL_ORACLE_PASS | 1,924 s | 119 107 584 |
| 5 | Sdist / MODAL-01 | EXECUTION_PASS · NUMERICAL_ORACLE_PASS | 1,848 s | 119 607 296 |
| 6 | Sdist / DYNAMIC-01 | EXECUTION_PASS · NUMERICAL_ORACLE_PASS | 1,988 s | 119 226 368 |

Le temps total des six processus est 11,457 s; le RSS maximal est 119 607 296 octets (114,07 MiB), sous la limite souple de 512 MiB. Les checks numériques wheel/sdist sont identiques pour les trois cas. Le ledger réel comporte six réservations suivies de six terminaux, SHA-256 `62c2c843e3cd5c80a2098efef97ca146a332c9a4375df549542d2593522bb67f`; le résumé contrôleur SHA-256 `a470fd99ffa146104375f7786cf9bc3c15b8fe8720750036105cb516b55c7fa6`. Les rapports bruts et ledgers restent hors dépôt; le rapport expurgé détaille les valeurs et preuves.

Les fichiers de résultat signalent `qualification_summary.status=WARNING` et `audit.qualification.traceability.status=FAIL` avec zéro formule couverte. Ces signaux restent visibles et ne modifient pas le résultat des oracles numériques des smoke tests; aucun résultat n’est promu en qualification globale.

Le verdict des smoke est **`WP13_V7_INSTALLED_PACKAGE_SMOKES_PASS`**. Le verdict global WP13 reste **`WP13_PARTIAL_OR_BLOCKED`** : G03 reste `FAIL_PRESERVED`, la revue juridique indépendante reste `NOT_ACQUIRED` et les autres gates distincts ne sont pas clos.
