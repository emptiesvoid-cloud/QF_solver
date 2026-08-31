---
doc_id: DOC-027-003
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Progress Tracker

This tracker records actual progress, not intent. It is initialized before
implementation and therefore contains no completed V&V.

| WP | Status | Current test level | Start SHA | Evidence head | Owner decision | Blocker |
| --- | --- | --- | --- | --- | --- | --- |
| WP01 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP02 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP03 | `NOT_STARTED` | T0 not run | - | - | - | - |
| WP04 | `NOT_STARTED` | T0 not run | - | - | - | - |
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
point, not a 0.2.7 result. The first active action is WP01.
