---
doc_id: DOC-029-007
revision: 0.1
status: planning
applicable_version: 0.2.9-development
---

# 0.2.9 Owner decision log

## WP01 closure decision

The Owner approved closure of WP01 Unified Nonlinear Core at audit SHA
`6876d867cdd845195e8946b05329b0bc82937fdc` with
`GO_WITH_LIMITATIONS`. WP01 receives **12/12 points**, bringing the validated
roadmap total to **16/100** including WP00 (4/4). The detailed record is
[WP01 Owner closure](wp01-owner-closure.md).

This decision records no production-source, numerical-formulation or maturity
change and does not alter the WP01-A/B/C/D evidence. WP02 implementation is
now in the **ARC_LENGTH_RESTART** phase at 0/6 points, pending WP02-E
independent closure. The limitations are frictional-contact migration,
adaptive penalty-contact qualification, distributed restart and inherited
mypy/mixin typing debt.

## OD-029-01 — bounded J2 plus geometric formulation

**Status:** OPEN. Required before WP09 implementation or any public claim.

The Owner must select one bounded physical direction after reviewing the
stress/strain measures, state transport and required validation basis:

| Option | Direction | Default status before approval |
| --- | --- | --- |
| A | Corotational/large-rotation model with explicitly bounded small-strain J2 | Not selected |
| B | Existing `total_lagrangian_j2` research formulation | Research only |
| C | Proper finite-strain multiplicative plasticity, \(F=F_eF_p\) | Not selected; substantial new work |
| D | Defer public J2 plus geometry claim | **Default** |

No option is selected by the existence of code alone. The selected option must
receive a prospective constitutive/objectivity contract, tangent and
state-transport verification, bounded external correlation and failure limits.

## OD-029-02 — legacy v1 checkpoint compatibility boundary

**Status:** CLOSED — Owner-approved decision:
`READ_V1_WRITE_V2_BOUNDED`.

Schema 1 has no contact-state payload, contact topology, accepted metadata or
composite digest. The approved boundary is therefore to read/migrate
contact-free v1 checkpoints, and stateless-compatible penalty-contact v1
checkpoints only when compatibility is proven from the current model. Any
ambiguous, stateful or contact-history-dependent v1 checkpoint is rejected
explicitly. Missing history is never invented, and all new writes use schema
2. The implementation record is [WP02-B schema-v2 foundation](wp02-b-schema-v2-foundation.md).
