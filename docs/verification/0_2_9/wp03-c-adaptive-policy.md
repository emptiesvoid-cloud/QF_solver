---
doc_id: DOC-029-WP03-010
revision: 0.1
status: implementation_migration
applicable_version: 0.2.9-development
---

# WP03-C — unified adaptive cutback and growth policy

> **Targeted implementation evidence, not a release claim.** This step keeps
> WP03 at 0/7 points, does not change any FEM formulation or maturity status,
> and leaves arc-length radius policy for WP03-D.

## Scope and baseline

WP03-C was implemented from
`e2f3e07310b4348c01ee68f764de0f986436995e` on branch
`0.2.9-unified-nonlinear`. The structured pre-edit observations are recorded
in `qualification/0_2_9/wp03_c_baseline.json`; the baseline document is
`wp03-c-baseline.md`.

The two adaptive surfaces remain physically distinct:

- `solve_adaptive_full_newton` retains stateless/geometric assembly;
- `NonlinearLoadControlMixin._solve_adaptive_load_steps` retains material
  trial-state assembly and mirror synchronization.

Both now delegate increment decisions to the single
`UnifiedAdaptiveStepPolicy`. `UnifiedContinuationController` and
`NonlinearStateTransaction` remain the authority for accepted physical state.

## Frozen policy semantics

The policy preserves the existing `AdaptiveLoadControls` values, including
`cutback_factor=0.5`, `growth_factor=1.5` and `maximum_cutbacks=25`.

| Situation | Common decision |
| --- | --- |
| retryable failure | rollback first, then `proposed * cutback_factor` |
| candidate below minimum | `MIN_INCREMENT_REACHED` |
| candidate equal to minimum | retry is permitted |
| Nth rejection at `maximum_cutbacks` | terminal `MAX_ITERATIONS`; no N+1 attempt |
| `iterations <= grow_below_iterations` | grow, capped at maximum |
| `iterations >= shrink_above_iterations` | shrink, floored at minimum |
| final target clipping | clip only the current proposal; retain the unclipped policy increment for the next decision |

Canonical retry classification is consumed before a decision. Material/state
corruption, non-finite state, invalid elements and checkpoint failure remain
terminal; checkpoint failure never causes a physical cutback. The policy
records deterministic JSON-compatible diagnostics with policy id/version,
classification, controls, counters, decision and next increment.

## Signature mismatch resolution

The inherited B16 failure was `TypeError` in the injected verification
subclass because its `_solve_load_step` override omitted the existing
keyword-only `commit_to_inputs` seam. The seam is intentional: adaptive
production code passes `commit_to_inputs=False` so a rejected trial cannot
publish caller mirrors. The verification fixture was updated to accept and
forward that keyword. This is classified as `TEST_FIXTURE_STALE`; no
production compatibility semantics were changed.

## Observed adaptive results

The post-change synthetic diagnostics reproduce the frozen schedule:

- B08 easy stateless case: one accepted increment `[1.0]`, zero rejections;
- B09 one injected retry: `1.0 -> 0.5`, then accepted factors `[0.5, 1.0]`;
- B10 three injected retries: `1.0 -> 0.5 -> 0.25 -> 0.125`, then eight
  accepted `0.125` increments to factor `1.0`;
- B11 candidate `0.5 < 0.75`: explicit `MIN_INCREMENT_REACHED`;
- maximum-cutback boundary: explicit `MAX_ITERATIONS` after the second
  rejected attempt, with no third attempt.

The stateful adaptive tests report `11 passed, 14 deselected`; the stateless
and stateful route-delegation tests both observe the same policy id and
decision schema. B16 now passes its intended clean-retry assertion.

## Validation

| Target | Result |
| --- | --- |
| WP03-C focused tests | `35 passed` |
| WP03-B authority tests | `30 passed` |
| WP02-B/C/D/D1 targeted regression | `28 passed`; `25 passed`; `28 passed`; `10 passed` |
| WP01-C/D and state/transaction regression | `34 passed`; `12 passed` |
| failure modes/campaign | `21 passed` |
| J2 targeted regression | `5 passed` |
| geometric regression | `20 passed` |
| penalty-contact regression | `30 passed` |
| Ruff | PASS |
| compileall | PASS |
| mypy changed nonlinear modules | 14 inherited load-control diagnostics; 0 WP03-C-added diagnostics |

The complete repository suite was not run. JSON qualification validation and
MkDocs strict validation passed after the controlled records were updated.
The exact command/results list is retained in
`qualification/0_2_9/wp03_c_adaptive_policy.json`.

## Gate status

| Gate | Status | Boundary |
| --- | --- | --- |
| G03-01 | **PARTIAL** | Fixed/adaptive load-control authority is common; arc-length radius policy remains WP03-D. |
| G03-02 | **PASS_BOUNDED** | One policy object serves both adaptive surfaces; physics kernels remain separate. |
| G03-03 | **PASS** | WP03-B stagnation authority remains green. |
| G03-04 | **PASS** | WP03-B line-search authority remains green. |
| G03-05 | **PASS** | Retry/cutback and rollback-before-retry behavior is focused-tested. |
| G03-06 | **PASS** | Growth/shrink inclusive thresholds, caps and floors are common. |
| G03-07 | **PASS** | Minimum and maximum terminal boundaries are common and off-by-one tested. |
| G03-08 | **PASS_BOUNDED** | Adaptive state preservation is tested; arc-length radius remains deferred. |
| G03-09 | **PASS_BOUNDED** | Easy and injected adaptive regressions remain bounded with no maturity change. |
| G03-10 | **NOT_YET_DEMONSTRATED** | No difficult physical convergence improvement is claimed. |

WP03 remains `ADAPTIVE_POLICY_AUTHORITY` at **0/7** points and the validated
roadmap remains **22/100**. The next permitted action is Owner review before
WP03-D.
