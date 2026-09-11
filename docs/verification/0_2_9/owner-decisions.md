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
change and does not alter the WP01-A/B/C/D evidence. WP02 remains
**NOT STARTED**. The limitations are the future unified checkpoint schema,
frictional-contact migration, adaptive penalty-contact qualification and
inherited mypy/mixin typing debt.

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

**Status:** OPEN. Non-blocking for WP02-A; applies only to the implementation
choice for legacy schema-1 checkpoints with non-empty or stateful contact
topology.

Schema 1 has no contact-state payload, contact topology, accepted metadata or
composite digest. The conservative default is therefore to read/migrate v1
only for bounded contact-free or stateless-compatible cases, write schema 2,
and reject ambiguous contact-bearing v1 inputs explicitly. The alternatives
are to define a separate legacy topology/invariant source or to intentionally
reject all v1 checkpoints. No option is selected by code existence alone.
