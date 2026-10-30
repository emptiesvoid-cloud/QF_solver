# WP12 shared-controller stabilization

**Status:** `SHARED_CONTROLLER_STABILIZATION_REVIEW_READY_CI_PENDING_OWNER_DECISION`

## Integration state

The stabilization worktree is based on canonical branch `emptiesvoids-cloud/0.2.12` at `b649d73a1c76c5ce8749b5cdc24f6106e0fc4081` (tree `0d9d0b620a14ab0c02812242fbbd597683252c8c`). PR #47, `dc895177a78230bb9ed169dd1ece9a2a2fd31a99`, was already merged by PR #47's merge commit `61f8a9f09fa9aaf89001a70457eec958872fc92c`; PR #48 subsequently advanced the base to the state above. Its partial HEX8-SRI Owner-approval change is therefore present in the stabilization base and was not copied a second time.

WP12-A was applied from commit `5201385c12646c724eda25a9b62341e06d9bfde2` as `500c4ef0d431a0cec52359e50ca6f24c0a00675c`. It fixes the unsupported `--preflight-id` path, binds preparation and execution to a checksummed collect-only receipt, makes missing `decision_id` a controlled WP12-A policy refusal instead of a `KeyError`, and prevents the WP12-A manifest from entering the HEX20-only child provenance contract. The follow-up stabilization change requires a syntactically valid Owner `decision_id` for `wp12_dynamics` and archives it in the receipt and ledger. Missing or malformed IDs are refused before attempt reservation. No science source, allowlist, policy, budget, oracle, threshold, or historical evidence changed.

## Synthetic contracts verified

The controller/policy tests cover WP12-A exact preflight-to-manifest binding, source/controller/solver provenance, Owner authorization, valid decision-ID archival, and controlled refusal of missing or malformed decision IDs with an unchanged empty ledger. The synthetic launch test stubs the supervised child and verifies the expected launch boundary and durable records; it does not invoke pytest or mechanics.

The HEX8-SRI tests inherited from PR #47 cover authorization of one selected case and two selected cases, refusals for empty, duplicate, unregistered, or unselected cases, divergent manifest bindings, changed budgets and fingerprints, selected-manifest archival, and refusal before ledger setup/launcher on the unauthorized path. Existing archive and no-replace tests check preservation of Owner-decision and historical ledger records.

The suite was run one exact test-function nodeid per pytest process, over `tests/unit/test_development_autonomous_policy.py` and `tests/unit/test_wp12b_diagnostic_provenance.py`:

- **209 passed, 0 failed, 0 skipped, 0 errors** across 120 test functions.
- `ruff check` — passed.
- `py_compile` — passed.
- `git diff --check` — passed.
- No FEM, assembly, eigensolve, Newmark, harmonic calculation, or benchmark ran.

## CI and provenance switch

No push, PR, CI run, merge, shared-checkout modification, or `AGENTS.md` designation change has been made. The required PR workflow includes MITC4 and meshed benchmark jobs in addition to broad test jobs. Triggering it would violate the current instruction not to run real FEM. The technical changes are therefore local and reviewable, but not yet merged or CI-verified.

After an approved CI route and protected-branch review, the single provenance switch should point to one clean checkout containing the merged HEX8-SRI and WP12-A controller changes. Only then should its HEAD/tree and official fingerprint be frozen, `AGENTS.md` be updated by the normal Git process, and incompatible preflights/manifests be replaced. Existing manifests and Owner decisions are not transferable across a changed controller fingerprint. No scientific execution is authorized by this report; a fresh WP07 decision must bind a new manifest SHA-256.

## Human decision still required

Choose whether to allow the repository's existing CI workflows to execute their scientific benchmark jobs for this controller-only PR, or specify an already-approved CI route that avoids real FEM without changing or bypassing repository gates. Until that is resolved, do not push/open the PR or switch the designated shared controller.
