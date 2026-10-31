# WP13 release candidate — gate matrix

**Project:** QF Solver v0.2.12 alpha  
**Release branch:** `emptiesvoids-cloud/0.2.12`  
**Baseline candidate:** `ab137051d920d7fa9aae9a3012a48b2b26e2198b`  
**Baseline worktree:** clean managed worktree; host path omitted.  
**Baseline branch:** `codex/wp13-release-engineering-20261031`, tracking the release branch at the baseline SHA. The worktree is clean.  
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

## Current candidate status — 2026-10-31

The frozen candidate source is `60c202a75d20c6dea1df35aab591bd3832d12c58`,
based on release baseline `ab137051d920d7fa9aae9a3012a48b2b26e2198b`.
Contract v4 is frozen at `e0d552173f932eaf7a7ef584f1f9026fd84bf336`; its two
artifact executions used source above and execution HEAD
`bf6004a9be324798558b537c744ceb73343bc1a7`. The v3 archive failure remains
preserved. V4 selected-artifact checks are complete; this is not a final release
recommendation or publication authorization.

| Gate | Current status | Evidence / limitation |
|---|---|---|
| Candidate source identity | **PASS — frozen** | Source `60c202a75d20c6dea1df35aab591bd3832d12c58`; contract commit `e0d552173f932eaf7a7ef584f1f9026fd84bf336`; dedicated branch is based on the refreshed release baseline. No release tag, merge to `main` or publication occurred. |
| Version metadata and public release wording | **PASS — source review** | `pyproject.toml`, `src/solveur/version.py` and `CITATION.cff` identify 0.2.12. The CFF has no `date-released` or version DOI; the concept DOI is retained. README/docs continue to identify 0.2.11 as the latest published release. |
| WP12 closeout claims | **PASS — bounded wording** | Roadmap and closeout remain authoritative at `WP12_CLOSED_BOUNDED_FOR_0_2_12_ALPHA`; documentation preserves the TET4-L3 energy FAIL, two HEX8-SRI FAILs, HEX20 QUAD8 R4 FAIL and non-acquired states. WP12 evidence/ledgers are unchanged. |
| Public claims and documentation scope | **PASS — bounded selected surface** | Superseded WP12 status summaries and B* parent-status wording were corrected; the public qualification page now cites its historical source snapshot. Internal engineering and audit reports remain in Git but are excluded from the served site. Strict scan v3 has no selected-doc findings. |
| Targeted API/serialization/CLI tests | **PASS — 21 executions on Windows Python 3.13.1; 4 additional executions on Windows Python 3.12** | Every invocation used one exact test node. Coverage includes JSON refusal, model/result round-trip, public/compatibility APIs, CLI version, citation/release wording and retained rotor limits. No solver/FEM test ran. Exact nodes are listed in the PR evidence. |
| Representative model loading/mesh-check smoke | **PASS — non-solving only** | `check-mesh` returned `MESH STATUS: PASS` for `examples/tet4_static.json`, `examples/beam2_cantilever.json` and `examples/mitc4_shell_static.json` on Windows Python 3.12 and 3.13. This exercises parsing and mesh/model checks, not element assembly or a structural solve. |
| Ruff | **PASS** | `python -m ruff check src/qf_solver src/solveur tests scripts`. Two prior unused-local findings were corrected while preserving their expressions' evaluation; no oracle, threshold or ledger changed. |
| Mypy | **PASS** | CI's four-file progressive typing command; no issues. |
| Python compilation | **PASS** | CI's `compileall -q src scripts tests qf_solver.py main_solveur.py mitc4_solver.py`. |
| MkDocs | **PASS — local build only** | `python -m mkdocs build --strict -f .github/pages/mkdocs.yml` returned 0 after adding explicit exclusions for internal reports. The generated site was not synchronized or deployed. |
| Standard full test suite and coverage thresholds | **NOT_RUN** | CI targets `main`, not this release branch. Repository policy requires one exact unit/integration nodeid per invocation, so the directory-wide suite and 80%/90% coverage gates were not substituted with targeted passes. |
| Linux and Python 3.10/3.11/3.13 matrix | **NOT_RUN** | Available local runtimes are Windows Python 3.12/3.13. WSL has Python 3.14 without a prepared dependency environment; Docker Engine is unavailable. No official Linux/3.10/3.11 matrix result is claimed. |
| Representative solver/FEM smoke tests | **BLOCKED BY EXECUTION POLICY** | No registered WP13 smoke node, exact source/input identity, resource budget or execution manifest is available. No FEM or benchmark ran. |
| Candidate contract | **PASS — prospective v4** | Contract `QF-0212-WP13-SELECTED-CANDIDATE-20261031-04` binds source `60c202a75d20c6dea1df35aab591bd3832d12c58`, selected paths, tools, MkDocs policy and build settings. Contract commit is `e0d552173f932eaf7a7ef584f1f9026fd84bf336`; v3 and its failed artifact result remain recorded. |
| Selected package/documentation scan | **PASS — v4 bounded surfaces** | v4 report binds the contract commit above: 585 selected package files and 773 served documents; zero findings on both. v3 also scanned clean before the packaging correction. v2's 16 documentation findings remain preserved and are bounded to internal reports now excluded from the site. Neither scan clears G03. |
| Wheel/sdist, contents and hashes | **PASS — v4 bounded builds; v3 failure retained** | Both v4 wheel builds are byte-identical (1,689,654 bytes; SHA-256 `8d3e571c…f721b0e`). Raw sdist gzip files differ; normalized sdist outputs match exactly (1,294,041 bytes; SHA-256 `4fba0a1f…f460da1`). Wheel and sdist content scans pass with 585 and 593 files respectively, zero findings; `twine check` passes for both runs. Full hashes and external manifest hashes are in [`WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v4.md`](WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v4.md). |
| Fresh installation and import/CLI probes | **PASS — Windows Python 3.13.1, bounded** | Separate clean environments installed the exact wheel and sdist with normal dependency resolution. Each verified 501 installed source files and origins outside the checkout; CLI `--version` and `--help` passed. `verify-all` refused as expected because the installed artifact is not a Git checkout; it produced no report or solve. |
| Selected-artifact license inventory | **PASS — metadata/files inventoried** | Both installed environments expose all 14 package distributions with license metadata and at least one license-like file. Project license files and wheel metadata are present; dependencies are installed separately and are not bundled in the candidate archives. See the artifact verification report. |
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

