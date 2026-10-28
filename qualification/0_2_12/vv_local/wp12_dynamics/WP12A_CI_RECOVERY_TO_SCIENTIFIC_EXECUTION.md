# WP12-A CI recovery and controlled WP07 readiness

**Current state:** local candidate is prepared for a safe CI PR; merge is gated by the repository ruleset's required scientific checks. No scientific execution has occurred.

## Canonical history coordinated

The candidate is based on canonical `emptiesvoids-cloud/0.2.12` at `268d80c3403df67aa87578e7e17f5c8c0f0ca95f` (PR #50). PRs #47 and #48 are in its ancestry. PR #49, `f8086be271d3cb26a5a7a620f0a59aec9ea4539c`, and PR #50, `268d80c3403df67aa87578e7e17f5c8c0f0ca95f`, are also merged. The local branch `stabilize/wp12-shared-controller-20261028` was rebased onto this base, so HEX8-SRI partial-approval handling and HEX20 dependency provenance are coordinated with WP12-A in one candidate.

## Controller and registration corrections

The WP12-A code fixes CLI propagation and validation of `--preflight-id`, binds the manifest to the checksummed collect-only receipt, replaces the unguarded `decision_id` lookup with controlled validation, and omits HEX20-only child provenance unless its complete binding exists. WP12-A now refuses a missing or malformed Owner `decision_id` before reservation and archives a valid ID in the execution receipt and attempt ledger.

The merged PR #49 provenance check requires an active WP12 registration to contain the exact local test-source dependency inventory. The 13 active WP12-A registrations predated that field, so they were correctly refused. The official `register-nodeid` process now permits an append-only metadata refresh when the scientific source fingerprint is unchanged but its dependency inventory is missing or stale; a true duplicate with the same source fingerprint and dependency inventory is still refused. Using that command, all 13 exact WP12-A nodeids were refreshed against the clean source worktree `E:\QFSolverAgents\wp12-dynamics`, branch `codex/wp12-dynamic-harmonic-verification`, HEAD `630d22b7667a0d84dd7b136b9f8c7d89ae00fc66`. The ledger of registrations grew from 21 to 34 records; prior entries remain intact, all 13 allowlisted identities remain exact, active inventories are present, DDL selections are unchanged, and all active timeouts remain 300 seconds. The scientific worktree was not modified.

## Local validation

The official controller synthetic runner discovers test functions only from the policy/controller contract, WP12-B provenance, and HEX20 sidecar-support unit modules. It invokes each exact function nodeid in a separate pytest process. It excludes `test_wp12b_hex20_affine_diagnostic.py`, whose test performs a real HEX20 solve.

- Synthetic contracts after rebasing on PR #49/#50 and refreshing WP12-A registrations: **220 passed, 0 failed, 0 skipped, 0 errors**.
- Ruff, Python compilation, policy JSON parsing, workflow YAML parsing, and `git diff --check`: passed.
- No FEM, assembly, eigensolve, Newmark, harmonic, or benchmark ran.

## Workflow and branch-protection audit

The repository ruleset `protect-main-release` is active on non-default branches, including `emptiesvoids-cloud/0.2.12`. It forbids deletion and non-fast-forward updates, requires a pull request, and lists these seven required status contexts:

1. `docs-tests`
2. `Documentation evidence / ubuntu-latest`
3. `Full engineering campaign`
4. `ubuntu-latest / Python 3.10`
5. `ubuntu-latest / Python 3.13`
6. `windows-latest / Python 3.10`
7. `windows-latest / Python 3.13`

`quality.yml` runs on pushes and PRs to `main`, and manually. Its four `standard-baseline` matrix jobs run broad unit/integration suites and `qf_solver.py verify --quick` plus `mitc4_solver.py verify --quick`; `command_verify` calls `MechanicalVerifier.run`, so quick mode still performs mechanical solves. `Full engineering campaign` runs full MITC4 verification and the engineering profile. The `wp14-recovered-evidence` dependency runs three mesh-convergence checks. `Documentation evidence / ubuntu-latest` runs `pytest -m benchmark` and rebuilds engineering documentation evidence. These are scientific/FEM jobs. `docs-tests.yml` runs documentation-generation and packaging tests. `pages.yml` is push/manual only; `publish-pypi.yml` is manual only and contains release quality and publication work.

The required `standard-baseline` contexts are also unsuitable as a non-FEM controller-only gate because their job includes quick mechanical verification. The `quality.yml` and `docs-tests.yml` PR triggers currently target `main`, while the release branch is a separate non-default target. The ruleset nevertheless requires their contexts for the release branch.

An additional workflow, `wp12-controller-validation.yml`, has been prepared for PRs to `emptiesvoids-cloud/0.2.12` and pushes to this stabilization branch. It runs only the synthetic controller/provenance contract runner, Ruff, `py_compile`, JSON validation, and Git whitespace checks. It does not modify or mark any scientific job successful. The new context is not yet in the ruleset's required-check list.

## Exact integration blocker and safe policy option

The release ruleset still requires the four platform/Python `standard-baseline` contexts, `Full engineering campaign`, and `Documentation evidence / ubuntu-latest`. A no-FEM PR cannot honestly satisfy these contexts under the current workflows. The quality and documentation workflows do not target this release branch, so their required contexts may remain absent; the PR check state must confirm this after the safe workflow runs. No existing workflow, ruleset, required check, or merge protection was disabled or bypassed.

To integrate a controller-only change without FEM, the Owner/repository admin must approve a protected controller-integration path whose required CI is `WP12 controller / synthetic contracts` plus any explicitly approved non-FEM checks, while retaining the existing engineering and documentation science checks for the scientific/release gate. Current GitHub ruleset conditions are branch-based, not path-based; preserving a separate scientific release gate may therefore require a dedicated protected integration branch and an explicit promotion rule. Alternatively, the Owner can authorize the existing scientific CI campaign. Neither choice is made by this change.

The branch is not merged, the shared controller designation has not changed, and no scientific manifest has been prepared against the candidate. After allowed integration and the single controller switch, compute final identities, run a fresh WP12-A collect-only preflight, prepare a new WP07 manifest, and request one new Owner decision bound to its exact SHA-256 and the 300-second budget. The earlier Owner authorization is not reusable.
