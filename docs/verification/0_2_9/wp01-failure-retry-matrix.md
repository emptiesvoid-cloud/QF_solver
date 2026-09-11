---
doc_id: DOC-029-WP01-005
revision: 0.1
status: prospective_contract
applicable_version: 0.2.9-development
---

# WP01 failure and retry contract

The existing `NonlinearFailureReason` enum remains canonical. Contributions
may report a reason and recommended retry class; only the authoritative driver
may cut back or retry.

| Retry class | Reasons |
| --- | --- |
| RETRYABLE | `MAX_ITERATIONS`, `CONVERGENCE_STAGNATION`, `LINE_SEARCH_FAILURE`, `CONTACT_UPDATE_FAILURE`, `CONTACT_PENETRATION_EXCESSIVE`, `ARC_LENGTH_FAILURE` |
| OWNER/POLICY_DEPENDENT | `SINGULAR_TANGENT`, `LINEAR_SOLVER_FAILURE` |
| NON_RETRYABLE | `MATERIAL_UPDATE_FAILURE`, `STATE_CORRUPTION`, `NAN_DETECTED`, `INF_DETECTED`, `INVALID_ELEMENT`, `MIN_INCREMENT_REACHED`, `CHECKPOINT_FAILURE` |

No duplicate equivalent reason may be introduced. Two identical injected
failure replays must produce the same terminal reason, retry class and
deterministic diagnostics digest.
