---
doc_id: DOC-027-003
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Progress Tracker

This tracker records actual progress, not intent. WP01 through WP04 record
completed foundation controls; no new numerical capability is implied.

| WP | Status | Current test level | Start SHA | Evidence head | Owner decision | Blocker |
| --- | --- | --- | --- | --- | --- | --- |
| WP01 | `PASS` | T1 targeted | `e99289aca40011ca0424944099e2d2093cf21a65` | `bb822839248b5ffb9faef5d79a6c83f288faefb3` | release-truth foundation | - |
| WP02 | `PASS` | T1 targeted | `3058dbcf53967dc50f70814a71b4094d61023dda` | pending commit | registry v2 contract | - |
| WP03 | `PASS` | T1 targeted | `ba6111a257ae567e496adcbcdc74de392dd66b6e` | pending commit | descriptor and fail-closed preflight | - |
| WP04 | `PASS` | T1 targeted | `684c39c72191d43c53e1f21043dc746d213a561d` | pending commit | declarative V&V harness v2 | - |
| WP05 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP06 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP07 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP08 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP09 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP10 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP11 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP12 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP13 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP14 | `NOT_STARTED` | T0 not run | - | - | - | - |

## Update rules

- Record the exact source SHA before a lot starts and the evidence SHA after a
  lot is committed.
- Keep `SUPPORTED`, `TESTED`, `VERIFIED` and `QUALIFIED_BOUNDED` separate.
- Record `SKIPPED`, `RESOURCE_LIMITED`, `NOT_COMPARABLE` and
  `EXPECTED_FAILURE` explicitly; never convert them to `PASS`.
- Update the machine-readable progress record in the same commit as a status
  change.
- A work package can move to `READY_FOR_OWNER_REVIEW` only with the evidence
  listed in the gate matrix and a clean, reproducible replay.

## Current baseline note

The only baseline evidence inherited at foundation start is the controlled
0.2.6 release at `e839373b6aef291a93292186d7553ba5cd12af55`. It is a reference
point, not a 0.2.7 result. WP01 is the first completed foundation control;
WP02 is complete for the registry control; WP03 is complete for the descriptor
and preflight control; WP04 is complete for the additive V&V harness control;
WP05 is the next active action.
