---
doc_id: DOC-029-006
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# 0.2.9 progress tracker

| Work package | Points | Status |
| --- | ---: | --- |
| WP00 | 4 | Closed |
| WP01 | 12 | **Closed** — Owner-approved unified nonlinear core |
| WP02 | 6 | **Closed** — 6/6; independent WP02-E audit `GO_WITH_LIMITATIONS` |
| WP03 | 7 | **Contract phase** — 0/7; WP03-B not authorized |
| WP04–WP08 | 43 | Not started |
| WP09 | 8 | Blocked by OD-029-01 |
| WP10–WP14 | 20 | Not started |
| **Validated total** | **22 / 100** | **WP00 4/4 + WP01 12/12 + WP02 6/6; Owner review is required before WP03-B** |

WP01 is closed by the independent Owner decision recorded in
[the WP01 closure record](wp01-owner-closure.md), based on audit SHA
`6876d867cdd845195e8946b05329b0bc82937fdc`. The decision is
`GO_WITH_LIMITATIONS`, with G01/G05/G06/G07/G10 retaining their documented
bounded/research boundaries. Unified checkpoint persistence, frictional
contact migration and adaptive penalty-contact qualification remain future
work; inherited typing debt remains documented. OD-029-01 stays OPEN and
blocks WP09 only. WP02 is closed by the independent audit; Owner review is
required before WP03-B authorization.

## WP02 closure

WP02-A froze the prospective state, rollback and checkpoint contract at 0/6
points. WP02-B implemented the schema-v2 persistence foundation: one accepted
`NonlinearState` authority, deterministic typed serialization,
component/composite digest validation, topology checks, bounded schema-1
migration and atomic canonical writes. WP02-C migrated solver-level fixed and
adaptive restart ownership. WP02-D now routes the public arc-length restart
path through the accepted composite state while retaining its specialized
correction kernel. WP02-D1 remediates and verifies the caller-visible
material-state mirror after a path-dependent restart. The independent WP02-E
audit at `c4e02fbd2d1262f621f6c8d4f07ee2da89d885f5` found no in-scope production
blocker and closes WP02 at **6/6**, bringing the validated roadmap to
**22/100**. Its `GO_WITH_LIMITATIONS` result is bounded to supported
single-process fixed/adaptive/arc restart routes; it does not claim frictional
contact, distributed, nonlinear-dynamics or adaptive penalty-contact restart.
Owner review is required before WP03-B may begin.

## WP03-A contract phase

WP03-A freezes the Newton robustness and adaptive-control contract at
ecc09f0bae2dab867c12d7e471860887f6ef0548. It records the actual current
authority map, duplicate policy surfaces to consolidate, canonical stagnation
and line-search semantics, the failure/retry matrix and a 16-case baseline
campaign. No production source was changed, no numerical campaign was run,
and no WP03 points were awarded. WP03-B remains unauthorized pending Owner
review.

The controlled records are [the robustness contract](wp03-robustness-contract.md),
[the architecture map](wp03-architecture-map.md), [the failure/retry
matrix](wp03-failure-retry-matrix.md), [the baseline campaign](wp03-baseline-campaign.md),
[the gate matrix](wp03-gate-matrix.md) and [the implementation
decomposition](wp03-implementation-plan.md).

The contract is split into the [state/checkpoint contract](wp02-state-checkpoint-contract.md),
[compatibility matrix](wp02-compatibility-matrix.md),
[failure matrix](wp02-failure-matrix.md), [prospective gates](wp02-gate-matrix.md),
[implementation decomposition](wp02-implementation-plan.md), [WP02-B
schema-v2 evidence](wp02-b-schema-v2-foundation.md), [WP02-C fixed/adaptive
restart evidence](wp02-c-fixed-adaptive-restart.md), [WP02-D arc-length
restart evidence](wp02-d-arc-length-restart.md), [WP02-D1 material-state
ownership remediation](wp02-d1-material-state-alias.md) and the independent
[WP02-E closure audit](wp02-e-independent-closure.md).
