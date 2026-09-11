---
doc_id: DOC-029-WP03-003
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# WP03-A — failure and retry matrix

> This is a frozen prospective policy. It preserves the existing
> NonlinearFailureReason vocabulary and does not change current numerical
> behavior in WP03-A.

The machine-readable record is
qualification/0_2_9/wp03_failure_retry_matrix.json.

| Reason | Classification | Adaptive load control | Arc-length | Owner policy | Terminal boundary |
| --- | --- | --- | --- | --- | --- |
| MAX_ITERATIONS | RETRYABLE | Cutback/retry when budget allows | Radius shrink/retry when policy allows | No | Minimum increment or max cutbacks |
| CONVERGENCE_STAGNATION | RETRYABLE | Cutback/retry | Radius shrink/retry when policy allows | No | Minimum increment or minimum radius |
| LINE_SEARCH_FAILURE | RETRYABLE | Cutback/retry | Radius retry only when arc policy declares it | No | Route limit |
| CONTACT_UPDATE_FAILURE | RETRYABLE | Cutback/retry in supported frictionless penalty scope | Context-dependent radius retry | No | Route policy limit |
| CONTACT_PENETRATION_EXCESSIVE | RETRYABLE | Cutback/retry in supported scope | Context-dependent radius retry | No | Route policy limit |
| ARC_LENGTH_FAILURE | RETRYABLE | Not applicable | Radius shrink/retry | No | Minimum radius or explicit arc limit |
| SINGULAR_TANGENT | OWNER_POLICY_DEPENDENT | No retry by default | No retry by default | Yes | Terminal unless explicit policy |
| LINEAR_SOLVER_FAILURE | OWNER_POLICY_DEPENDENT | No retry by default | No retry by default | Yes | Terminal unless explicit policy |
| MATERIAL_UPDATE_FAILURE | NON_RETRYABLE | No cutback | No radius retry | No | Immediate terminal failure |
| STATE_CORRUPTION | NON_RETRYABLE | No cutback | No radius retry | No | Immediate terminal failure |
| NAN_DETECTED | NON_RETRYABLE | No cutback | No radius retry | No | Immediate terminal failure |
| INF_DETECTED | NON_RETRYABLE | No cutback | No radius retry | No | Immediate terminal failure |
| INVALID_ELEMENT | NON_RETRYABLE | No cutback | No radius retry | No | Immediate terminal failure |
| MIN_INCREMENT_REACHED | NON_RETRYABLE | No cutback | Not applicable | No | Explicit terminal outcome |
| CHECKPOINT_FAILURE | NON_RETRYABLE | No physical cutback | No physical radius shrink | No | Infrastructure failure |
| BUCKLING_FAILURE | NON_RETRYABLE | No cutback | No radius retry | No | Immediate terminal failure |

## Invariants

- Rollback occurs before a retry decision.
- Every retry begins from the last accepted composite state digest.
- A cutback or radius candidate is next-trial policy state, never accepted
  physical state before a successful commit.
- Failure reason, retry class and policy action are deterministic diagnostics.
- CHECKPOINT_FAILURE never masquerades as physical non-convergence.
- A non-retryable failure is not converted to a silent cutback.

## Terminal policy

Adaptive load control emits MIN_INCREMENT_REACHED when a permitted retry
would fall below the minimum increment, or the declared cutback budget is
exhausted according to the route's existing canonical terminal mapping.
Arc-length emits ARC_LENGTH_FAILURE at the minimum radius or another
declared arc terminal limit. These are explicit terminal records, not generic
MAX_ITERATIONS substitutions unless the existing route already defines that
specific terminal reason.

## Scope boundary

The matrix applies to public fixed/adaptive/arc lifecycle ownership. It does
not make active-set or frictional contact public, does not add distributed
nonlinear support and does not change the existing maturity registry.
