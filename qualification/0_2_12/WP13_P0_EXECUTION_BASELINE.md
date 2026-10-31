# WP13 P0 execution baseline

**Owner-specified PR head checked:** `57d011c9e228ffae642ff0e9b68098939c87e586`
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
- `tests/unit` and `tests/integration` with `not benchmark and not large and not evidence`, branch coverage enabled, and the unchanged global threshold of 80%.
- The P0 module coverage gate in `.coveragerc-p0` / `check_p0_coverage.py`, with the existing 90% threshold for both declared modules.
- Python compileall and both configured quick verification commands.

The broad test suite is being run only through this exact official CI workflow;
no direct local directory-wide pytest command is used. This honors the local
`DEVELOPMENT_AUTONOMOUS` rule requiring exact nodeids for local generic unit or
integration work. Tests marked `benchmark`, `large`, or `evidence` are excluded
by the unchanged standard-CI selector. The separate WP14 archive job, full
engineering campaign, and documentation benchmark/evidence job are disabled
for manual P0 dispatch. The four standard matrix jobs have a 90-minute job
timeout; no acceptance threshold is changed.

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

## Current P0 execution

The official `quality.yml` `workflow_dispatch` was started on
`codex/wp13-release-engineering-20261031`, commit
`3e2d5f07585b270bb1ac0157a911e94d59991735`, run
[41201053221](https://github.com/emptiesvoid-cloud/QF_solver/actions/runs/41201053221),
with `include_extended_jobs=false`. At the latest poll all four matrix jobs
had passed installation, identity capture, Ruff, and mypy; the standard tests
and branch-coverage step was still running. Although the workflow step
reported the privacy additions check as PASS, its `workflow_dispatch` fallback
selected `github.sha` and compared the candidate to itself. That result is not
accepted as a valid privacy gate. The same official privacy script passed when
run with the actual release baseline
`ab137051d920d7fa9aae9a3012a48b2b26e2198b`. The workflow is being corrected
to require an explicit privacy base SHA on manual dispatch; final per-cell
results and durations are pending.

## Separate installed-artifact FEM smoke authorization

No package-installed static, modal, or dynamic solve has been executed. The
pre-existing `scripts/run_local_vv.py` runner only supports exact pytest
nodeids whose imported `solveur` path is the source checkout; its current
preflight is not compatible with imports from the installed wheel/sdist. The
WP12 development controller scopes are not transferable to WP13. The exact
cases and an adapted shell-free runner/manifest must be reviewed before a
separate Owner decision; no smoke permission is inferred here.
