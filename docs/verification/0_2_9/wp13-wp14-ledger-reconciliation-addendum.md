---
doc_id: DOC-029-WP13-WP14-LEDGER-ADDENDUM-001
revision: 0.1
status: audit_addendum
applicable_version: 0.2.9-development
---

# WP13/WP14 ledger reconciliation addendum

This addendum clarifies the score evidence inspected after the overnight
preflight commit. It changes no score, roadmap, Owner decision, or qualification
artifact.

## Current total versus historical snapshots

The current total is **94/100** in both `qualification/0_2_9/progress.json`
and the current summary table in `docs/verification/0_2_9/progress.md`.
`qualification/0_2_9/owner_decisions.json` also records the current total as
94/100 after the Owner awards for WP09, WP10, WP11 and WP12. The previously
seen totals 70, 78, 84 and 90 are dated historical checkpoints in the decision
sequence (before those later awards), not competing current totals.

## Remaining allocation discrepancy

The frozen `qualification/0_2_9/roadmap.json` assigns WP13=2 and WP14=2 and
contains no WP15 entry. The current progress ledger instead assigns WP13=1,
WP14=1 and WP15=2. Both vectors sum to 100, but they are not the same
allocation: the current ledger effectively assigns one point from each of
WP13 and WP14 to WP15.

`qualification/0_2_9/wp15/wp15_integration_audit.json` records WP15=2/2 and a
validated-total transition from 41 to 43. The machine Owner-decision record
contains no WP15 point-award entry or explicit WP13/WP14-to-WP15 transfer. Its
ledger reconciliation says `weight_changes=false` and
`allocation_mismatch_status=CONSISTENT`, but that reconciliation discusses
the WP07 historical total and does not account for the WP15 allocation. The
documents therefore do not establish an authorized revision of the frozen
package weights.

This does **not** change the current 94/100 earned total. It leaves the
remaining available-point ceiling ambiguous: under the frozen roadmap WP13
and WP14 have 2 points each and WP15 is outside that roadmap; under the
current ledger WP13 and WP14 have 1 each and WP15 has 2. No execution or
points decision may resolve this implicitly.

## Owner action required

Record an explicit decision either to (a) preserve the frozen roadmap
allocation and reconcile WP15's status outside it, or (b) approve and version
an allocation revision that assigns WP15=2 and WP13/WP14=1 each. Do not edit
the roadmap or ledger until that decision is recorded. Separately, freeze the
missing WP13 and WP14 execution contracts before running their campaigns.

```text
CURRENT_EARNED_TOTAL = 94/100 — CONSISTENT
CURRENT_REMAINING_POINT_ALLOCATION = HOLD — ROADMAP/LEDGER DIFFER
WP13_WP14_EXECUTION = NOT_AUTHORIZED_BY_FROZEN_CONTRACTS
LEDGER_OR_ROADMAP_MODIFIED = NO
```
