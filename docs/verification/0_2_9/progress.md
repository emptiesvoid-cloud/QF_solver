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
| WP02 | 6 | **Fixed/adaptive restart** — 0/6; WP02-D arc-length migration remains |
| WP03–WP08 | 50 | Not started |
| WP09 | 8 | Blocked by OD-029-01 |
| WP10–WP14 | 20 | Not started |
| **Validated total** | **16 / 100** | **WP00 4/4 + WP01 12/12; WP02 closure remains pending independent review** |

WP01 is closed by the independent Owner decision recorded in
[the WP01 closure record](wp01-owner-closure.md), based on audit SHA
`6876d867cdd845195e8946b05329b0bc82937fdc`. The decision is
`GO_WITH_LIMITATIONS`, with G01/G05/G06/G07/G10 retaining their documented
bounded/research boundaries. Unified checkpoint persistence, frictional
contact migration and adaptive penalty-contact qualification remain future
work; inherited typing debt remains documented. OD-029-01 stays OPEN and
blocks WP09 only. WP02 is now in the fixed/adaptive restart phase.

## WP02 current phase

WP02-A froze the prospective state, rollback and checkpoint contract at 0/6
points. WP02-B implements the schema-v2 persistence foundation: one accepted
`NonlinearState` authority, deterministic typed serialization,
component/composite digest validation, topology checks, bounded schema-1
migration and atomic canonical writes. WP02-C adds solver-level fixed and
adaptive restart ownership; complete arc-length restart remains deferred to
WP02-D.

The contract is split into the [state/checkpoint contract](wp02-state-checkpoint-contract.md),
[compatibility matrix](wp02-compatibility-matrix.md),
[failure matrix](wp02-failure-matrix.md), [prospective gates](wp02-gate-matrix.md),
[implementation decomposition](wp02-implementation-plan.md), [WP02-B
schema-v2 evidence](wp02-b-schema-v2-foundation.md) and [WP02-C
fixed/adaptive restart evidence](wp02-c-fixed-adaptive-restart.md).
