# Remaining code integration reviews (separate from document archive)

This document records review queues only. It does not authorize a merge, test run, FEM campaign, policy update, or status change.

| Workstream | Current source identity / exclusive content | Required review before code integration |
|---|---|---|
| WP07 serialization | `fix/wp12-wp07-serialization` commit `0a2e8135a9d4`; integrated equivalent commit `bf8732c49b20`. The serializer and serialization-test file trees compare equal to current integration. | Confirm ancestry/content equivalence and review the commit already present; do not cherry-pick a duplicate patch. The branch remains retained while its worktree is attached. |
| Dynamic/harmonic | Local branch `630d22b7667a`, remote branch `d9deddbd6b42`; local-only report commit plus scientific test/source changes. | Review exact test contracts, source fingerprints, execution receipts, current policy registrations, and the difference between the report source `d9deddb...` and branch HEAD. Do not merge only because three development outcomes are reported. |
| TET4 convergence | `9c48bd5559b8`; includes prep scripts/tests plus report/metrics/figures. | Review experiment scripts and exact receipt/source identities separately. Raw receipts/mechanics data are external and should be archived/verified under an Owner-approved evidence process before relying on this report for a formal gate. |
| HEX8-SRI fix | `research/hex8-sri-equilibrium` current observed ref `76d9161951fe`; includes the scientific quadrature change, tests, operator study, draft manifests, and a newer gated campaign harness. Its worktree also has uncommitted builder edits and an untracked final-candidates directory. | Independently review formulation, affected standard/SRI paths, frozen two-FAIL record, generated manifests, and compatibility. Do not let new diagnostics overwrite negative historical results. |
| HEX8-SRI regression campaign | `test/wp12-fem-regressions` `fa889f480766`; contains new verification test and planning docs. | Review test scope and link it to policy only after exact source/test identities are checked. The working matrix/pre-execution plan create no execution authority. |
| WP12-C advanced physics | `audit/wp12-advanced-physics`; this branch contains only audit/protocol documents in its two exclusive commits. | Documents copied. Treat the objectivity protocol as proposed, not executed. |
| Policy/controller variants | `codex/wp12-policy-reconciliation`, `codex/hex8sri-controller-registration` (current observed ref `616c9e2be7f0`), `codex/wp12-policy-finalization`, `emptiesvoids-cloud/wp12-autonomous-policy-*`, and rotor-registration branch. | Compare schemas, budgets, allowlists, receipts and dirty worktree contents. Do not take a stale or alternative policy wholesale; retain all local edits and only consolidate with an explicit registration review. |
| Concurrent selective-integration branch | `emptiesvoids-cloud/wp12-dynamics-selective-integration` current observed ref `f843d9286894`; its delta mixes report copies with scientific test changes. | Do not cherry-pick it wholesale; report artifacts are separately pinned in SOURCE_INDEX, and tests await independent review. |
| Legacy cross-route and elements/loads | `verify/wp12-legacy-cross-route`, `verify/wp12-elements-loads`; exclusive commits are documentation-only. | Reports copied. Follow up the reported absent nodeids / not-run gaps through the common policy process; this documentation does not register or authorize them. |
| Rotor performance | `verify/wp12-rotor-performance`; exclusive commit is a plan, not results. | Plan copied. Keep GYRO-01..06 historical/EXPERIMENTAL and require separate authorization before any campaign. |

## Required regression / traceability controls

1. Review each proposed code patch against the current integration merge-base and its exact changed paths; avoid whole-branch merges where code and evidence are mixed.
2. Verify scientific-source, test, fixture and policy fingerprints independently. Historical report references are not current-HEAD execution evidence.
3. Preserve TET4 bounded PASS records, both HEX8-SRI FAILs, U3 FAIL, C01 negative/remediation-open and all inconclusive statuses without rewriting archives.
4. For any later code integration, select only approved static/unit checks first. FEM execution requires its own currently valid policy registration, manifest and Owner decision.
5. Do not update WP statuses or maturity from these branch/documentation changes.
