# HEX8-SRI Partial Owner Authorization Contract Review

Status: `HEX8SRI_PARTIAL_AUTHORIZATION_PATCH_READY_FOR_REVIEW`

## Scope and base

This prospective controller change permits an `EXECUTION_APPROVED` decision to name an explicit, non-empty subset of the six registered 4×2×2 HEX8-SRI nodeids. The branch is based on canonical target HEAD `8450df7d1b2d6ff598747560978aaf610729028b` (PR #46 is merged). Work was performed in a separate Configuration worktree and does not modify the pinned shared-controller checkout or any scientific source.

The criteria-freeze decision remains bound to all six first-tier cases. Only the subsequent execution decision is subset-scoped. The archived execution decision must carry exactly the selected nodeids, their exact current case-manifest bindings, and their policy-derived limits.

## Contract change

The controller now rejects an execution decision unless `authorized_nodeids` is a non-empty list of unique strings, every nodeid is one of the six first-tier registered cases, and the current execution target is in that list. `limits_by_nodeid` and `case_manifests_by_nodeid` must have exactly the same keys as the selected list; each limit remains equal to the policy budget.

At Owner-decision archival, the controller derives the current bindings for the six first-tier case manifests, selects only the explicitly named entries, and requires the submitted binding map to equal that selected current map byte-for-byte at the JSON-value level. Extra cases, missing cases, stale manifest hashes, or altered bindings are refused. At execution, the exact target must still match its own case binding, preflight receipt, source/controller identities, criteria freeze, mandate, and budget. An authorization for A therefore cannot authorize B.

The existing full-six decision shape remains valid as the complete-set case of the subset rule. Criteria definitions, thresholds, budgets, per-node attempt ceilings, attempt ledger, and all other scopes are unchanged.

## Synthetic coverage

The policy tests cover all six single-node selections and a two-node selection; empty, unknown, and duplicate nodeids; missing/mismatched selected manifests; altered budgets and source fingerprints; a target outside the approved subset; missing execution-decision content; current-manifest binding mismatch and extra bindings; and attempt exhaustion. Existing criteria-freeze-only refusal and historical-scope policy tests remain in the selected test set.

No FEM test body, assembly, eigensolve, preflight, attempt reservation, or Owner decision was run or created for this patch.

## Preserved invariants

| Invariant | Verification / behavior |
|---|---|
| Scope and mandate | Still exact `hex8sri-convergence24` scope and policy mandate. |
| Selected nodeids | Non-empty unique subset of the six first-tier nodeids; no implicit expansion. |
| Manifest and preflight | Selected current manifest binding, nodeid-specific preflight, and archived receipt remain exact. |
| Source/controller identity | Existing source fingerprint, controller fingerprint, and controller HEAD checks remain required. |
| Criteria | A separately archived valid criteria freeze is still mandatory and must precede execution approval. |
| Budgets | Every selected nodeid uses the exact policy limits; altered limits are refused. |
| Attempts | Existing per-node and campaign limits and ledger checks are untouched; no attempt was reserved. |
| Historical data | No historical manifest, decision, receipt, archive, or ledger was modified. |
| Other scopes | No policy entries or controller behavior for other scopes were changed. |

## Provenance and migration

This source change changes the controller runner digest and therefore the controller provenance fingerprint after commit. Existing receipts and execution drafts tied to the prior controller identity must not be presumed reusable. Before any future execution decision:

1. Recompute controller provenance from the selected canonical controller checkout.
2. Revalidate the scientific checkout and its exact raw-byte fingerprint.
3. Regenerate prospective case manifests under the official procedure where the controller identity is embedded; retain all previous versions unchanged.
4. Renew collect-only receipts for every case selected for a future authorization and validate each receipt with the final validator.
5. Archive a new criteria-freeze decision if the official freeze record is identity-bound to the changed controller; do not reinterpret the old freeze as execution authorization.
6. Prepare a separate Owner execution decision whose nodeids, current manifest hashes, preflight receipts, limits, source/controller identities, and expiry match exactly. The patch itself creates no such decision.

The 24 registrations are not changed by this patch. Whether manifest refresh must rewrite all 24 case records is determined by the official refresh/validator contract after integration; no stale artifact is declared acceptable here. In particular, the 18 non-first-tier cases remain unauthorized and are not enabled by a first-tier subset decision.

## Risk and review notes

The main regression risk is inconsistent subset handling between archival validation and per-case execution validation. The implementation validates the selected current manifest map at archival and then validates the exact case binding for each attempted target. A second risk is accidental weakening of the six-case scientific freeze; its six-node binding is deliberately unchanged. Review should confirm the current-binding helper remains the only source for archival manifest hashes and that all future launch paths continue to invoke the per-case validator before reservation.

## Validation performed

On the dedicated branch:

* `python -m pytest tests/unit/test_development_autonomous_policy.py -k hex8sri -q` — **65 passed, 125 deselected**. This selection contains policy and synthetic contract tests only.
* `python -m ruff check scripts/development_autonomous.py tests/unit/test_development_autonomous_policy.py` — **passed**.
* `python -m compileall -q scripts/development_autonomous.py tests/unit/test_development_autonomous_policy.py` — **passed**.
* `git diff --check` — **passed**.

## Delivery

Branch: `codex/hex8sri-partial-owner-authz-20261028`.

The review PR is intentionally draft and is not merged. No science branch, production solver, shared pinned checkout, policy budget, threshold, or historical evidence was changed.
