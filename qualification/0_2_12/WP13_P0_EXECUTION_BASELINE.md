# WP13 P0 execution baseline

**Owner-specified PR head checked:** `57d011c9e228ffae642ff0e9b68098939c87e586`
**Latest PR head revalidated before correction work:** `375872ec89699b23e5af23151feebc797bc5d94e`
**Release baseline:** `ab137051d920d7fa9aae9a3012a48b2b26e2198b`
**Frozen package source:** `60c202a75d20c6dea1df35aab591bd3832d12c58`
**Frozen package contract:** `QF-0212-WP13-SELECTED-CANDIDATE-20261031-04`
**P0 workflow execution source:** `3e2d5f07585b270bb1ac0157a911e94d59991735`
**P0 workflow execution tree:** `6f4372b7978b089c020c3c250f473bd2dd89d4ea`

## Identity check

At the start of P0 work, GitHub PR #114 and the remote branch both resolved to
`57d011c9e228ffae642ff0e9b68098939c87e586`; the release base remained
`ab137051d920d7fa9aae9a3012a48b2b26e2198b`. No concurrent PR-head change was
observed. The clean integration worktree is
`E:\QFSolverAgents\wp13-release-engineering-20261031`, separate from the
historical release checkout. A second managed worktree checkout was attempted
but failed because the C: volume had only 248 MiB free; no second worktree was
created and no space cleanup was attempted. The existing E: worktree is clean.

Before preparing the corrections below, PR #114 was refreshed and revalidated
at `375872ec89699b23e5af23151feebc797bc5d94e`, still open against
`emptiesvoids-cloud/0.2.12`. The E: worktree was clean at that revision before
the current WP13-only edits; it now contains those uncommitted edits. The first
CI run and v4 artifact work are retained as historical evidence.

The v4 wheel and sdist are bound to package source `60c202a75d20c6dea1df35aab591bd3832d12c58`.
The source-to-execution-HEAD diff consists only of WP13 records, the gate
matrix, and the CI dispatch guard; it contains no changes to `src/`, `tests/`,
examples, `pyproject.toml`, or `MANIFEST.in`. The frozen package selection is
therefore unchanged. The execution-only CI workflow adjustment does not
invalidate v4 package artifact hashes.

## Candidate artifacts

| Artifact | Exact identity | Installation evidence |
| --- | --- | --- |
| Wheel | `qf_solver-0.2.12-py3-none-any.whl`, 1,689,654 bytes; SHA-256 `8d3e571ce7d4ced533d7b97ed0bc0f7a91e29a3d530e3a1b406716fecf721b0e` | Installed into a fresh Windows Python 3.13.1 environment with dependency resolution; the pip report binds this wheel hash. |
| Raw sdist | `qf_solver-0.2.12.tar.gz`, 1,320,055 bytes; SHA-256 `4d9e571583b3bd345abdbf4bca5f6b86e17d776c6d2a386019da32c8c0b8a44b` | Installed into a separate fresh Windows Python 3.13.1 environment with dependency resolution; the pip report binds this sdist hash. |
| Normalized sdist | 1,294,041 bytes; SHA-256 `4fba0a1f1e700aaa6bf58c4cdd1a0edd5adea1145db886d5bf1903d30f460da1` | Byte-identical output from the two v4 builds. |

Prior installed-artifact probes verified 501 package source files and the
installed import origin outside the checkout. Those probes did not execute a
mechanical solve. See
[`WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v4.md`](WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v4.md)
for the full external manifest hashes and dependency inventory.

## P0 controls to execute

The official workflow matrix is Ubuntu/Windows × Python 3.10/3.13. Its locked
baseline is `requirements/baseline-standard.txt`. For each matrix cell, the
workflow records the exact commit, Python, OS, and `pip freeze`, then runs:

- Ruff and the privacy additions gate.
- Progressive mypy on the four configured files.
- `tests/unit` and `tests/integration` with the existing `benchmark`, `large`,
  `evidence`, `scientific_vv`, and `native_vv` marker exclusions, plus exact
  names for policy-controlled historical FEM cases; branch coverage remains
  enabled with the unchanged global threshold of 80%.
- The P0 module coverage gate in `.coveragerc-p0` / `check_p0_coverage.py`, with the existing 90% threshold for both declared modules.
- Python compileall and both configured quick verification commands.

The broad test suite is run only through this official CI workflow; no direct
local directory-wide pytest command is used. This honors the local
`DEVELOPMENT_AUTONOMOUS` rule requiring exact nodeids for local generic unit or
integration work. Exclusions and their policy reasons are enumerated in the
P0 report. The separate WP14 archive job, full engineering campaign, and
documentation benchmark/evidence job are disabled for manual P0 dispatch. The
four standard matrix jobs have a 180-minute job timeout; quality thresholds
are unchanged.

The two `verify --quick` commands remain explicit steps in the official P0
workflow and execute the repository's fixed reduced MITC4 verification route.
They are not the extended engineering or documentation benchmark jobs.

## Existing CI failures retained

The six latest release-branch `quality.yml` runs (IDs `40947504858`,
`40950131357`, `40962192076`, `41010380832`, `41018655166`, and
`41025434653`) stopped at Ruff on all four matrix cells. The latest original
logs report F841 for unused locals `historical_front` and `exact_pressure`.
The candidate preserves evaluation of both expressions while removing the
lint findings; the current run rechecks all subsequent gates. The original
logs remain available in their GitHub Actions run records.

## First P0 execution — run 1, completed with failure

The official `quality.yml` `workflow_dispatch` ran on
`codex/wp13-release-engineering-20261031`, commit
`3e2d5f07585b270bb1ac0157a911e94d59991735`, run
[41201053221](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41201053221),
with `include_extended_jobs=false`. The run finished unsuccessfully. Ubuntu
Python 3.10 reported 4,646 passed, 72 failed and 32 skipped in 4,197.98 s;
global branch coverage was 84.76%. Its privacy step compared the candidate to
itself and is rejected as evidence. Ubuntu Python 3.13 was cancelled at 90
minutes without final counts. Windows Python 3.10 and 3.13 emitted 602 passes
and 5 skips each, then were cancelled at the 90-minute job limit; their P0
module coverage, compileall, quick verification and artifact upload steps did
not complete. The full failure inventory and log digests are in
[`WP13_P0_FULL_VALIDATION_REPORT.md`](WP13_P0_FULL_VALIDATION_REPORT.md).

The direct privacy script passed against release base
`ab137051d920d7fa9aae9a3012a48b2b26e2198b`. The corrected workflow requires
that base explicitly on manual dispatch. Corrections also add the missing
standard-test-only `cryptography==48.0.0`, repair synthetic test fixtures and
mocks, make release-audit CLI subprocess tests use a small temporary Git root,
and replace a stale post-publication assertion with checks for the actual
unreleased 0.2.12 candidate state. Exact local non-FEM checks are listed in
the full report. The corrected official matrix has not yet run.

Run 1's controlled WP12/WP19 nodes and RBE2 solve were reached before their
boundaries were recognized. Their exact outputs remain in the archived log;
the corrected selector excludes only exact policy-controlled FEM nodes and
campaign tests. It does not exclude the release-audit CLI tests or the
candidate publication-state test.

## Separate installed-artifact FEM smoke authorization

No package-installed static, modal, or dynamic solve has been executed. The
pre-existing `scripts/run_local_vv.py` runner only supports exact pytest
nodeids whose imported `solveur` path is the source checkout; its current
preflight is not compatible with imports from the installed wheel/sdist. The
WP12 development controller scopes are not transferable to WP13. The exact
cases and an adapted shell-free runner/manifest must be reviewed before a
separate Owner decision; no smoke permission is inferred here.

## Candidate v6 package identity and P0 run 2

The latest PR/report HEAD at the v6 package verification was
`d6a49a279b4d8ce548e4d6ed1f48e8cad6f20e23`. The package source and official
workflow code/test commit are
`2865587a44f9e461a0b4e4286c912c17e4f04be5`. The v6 contract is
`QF-0212-WP13-SELECTED-CANDIDATE-20261031-06`, SHA-256
`f33a72b182439774828f8e604d6ab234bbf206c697c0f1082d7bc0ef81003db9`.
Its two independent build manifests, build results, normalized archives,
fresh wheel/sdist installs, dependencies, probes and check-mesh outputs are
summarized in
[`WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md`](WP13_CANDIDATE_ARTIFACT_VERIFICATION_20261031_v6.md).

The wheel hash is `ae5211136a2eab912cdb73222937a84b1cec75f7af0a425f1162b288b39c287a`.
The selected run-2 raw sdist hash is
`15c838af12c8401b61c561f5f079debc702e072241e9ee8c17cd5861cbf082e5`; the
normalized sdist hash is
`183bc4448d4a83c5e24d9c8b0d7f15e9e2cca37b63b25646d9ec030220611fde`.
No structural solves were run in either package build/install pass.

Corrected official CI run
[41210713065](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41210713065)
is bound to commit `2865587a44f9e461a0b4e4286c912c17e4f04be5`, with
release privacy base `ab137051d920d7fa9aae9a3012a48b2b26e2198b` and extended
jobs disabled. At the latest check all four matrix jobs had passed setup,
dependency installation, identity, Ruff, privacy and progressive mypy, and
were still executing tests and branch coverage. No final counts or downstream
gate results were available at this baseline update.


## Corrected P0 execution and performance triage — 2026-10-31

PR #114 was revalidated at candidate HEAD f00bbb9c23769f984a12c2dda37802382ffc5414, based on release baseline ab137051d920d7fa9aae9a3012a48b2b26e2198b. The official quality workflow run 41225195330 used this exact HEAD; no quality workflow remained active after it completed.

| Environment | Result | Timing and gates |
|---|---|---|
| Ubuntu / Python 3.10.22 | 4,676 passed, 32 skipped, 150 deselected, 4 warnings | 7,537.95 s. Global branch coverage 84.75%; declared P0 module coverage, compileall, quick verification and upload PASS. |
| Ubuntu / Python 3.13.17 | 4,676 passed, 32 skipped, 150 deselected, 4 warnings | 7,120.37 s. Global branch coverage 84.75%; declared P0 module coverage, compileall, quick verification and upload PASS. |
| Windows / Python 3.10.11 | 602 passed, 5 skipped, 150 deselected before cancellation | 10,681.97 s in the test/coverage step; job reached its 180-minute limit. No coverage or downstream gate result. |
| Windows / Python 3.13.16 | 602 passed, 5 skipped, 150 deselected before cancellation | 10,724.65 s in the test/coverage step; job reached its 180-minute limit. No coverage or downstream gate result. |

All four cells passed setup, environment identity, Ruff, privacy additions and progressive mypy. The Windows cells did not reach coverage, compileall or quick verification. Their logs stop at the same 12% point in test_development_autonomous_policy.py and a pathlib traceback, but no verbose in-flight nodeid was recorded. The Windows full-suite gate is therefore BLOCKED / NOT_ACQUIRED, not PASS. Run 41210713065 and its original 17 failures remain historical; the corrected run has no Linux test failures.

The bounded local profile and its exact nodeids, CPU/wall/RSS observations, limits, contact-campaign scope deviation, CI proposal and overall verdict are recorded in [WP13_P0_TEST_PERFORMANCE_AND_CI_OPTIMIZATION_REPORT.md](WP13_P0_TEST_PERFORMANCE_AND_CI_OPTIMIZATION_REPORT.md). The profile is not a whole-suite top-20 ranking. No suite was rerun to collect timing data, no additional scientific execution was performed after the one disclosed profiling scope deviation, and no qualification ledger or historical evidence was changed.

The official four-cell complete-suite requirement remains NOT_ACQUIRED because Windows did not finish. The proposed reference-full plus targeted-compatibility matrix is not adopted. Installed-artifact static/modal/dynamic solve smokes remain NOT_RUN pending their exact separate Owner authorization.
