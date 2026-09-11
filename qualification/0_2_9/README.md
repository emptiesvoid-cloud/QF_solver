# QF Solver 0.2.9 qualification planning

This directory is the prospective, machine-readable planning and controlled
closure record for the 0.2.9 **Unified Nonlinear Mechanics** development
cycle. The Owner-approved WP01 closure is recorded in
`wp01_owner_closure.json`; it does not change any 0.2.8 maturity record.

The baseline commit is recorded in `baseline.json`. Work packages may only
add prospective contracts and evidence beneath this directory; historical
0.2.8 evidence remains immutable.

## Current planning status

- WP00: `CLOSED`, 4/4 points.
- WP01 Unified Nonlinear Core: `CLOSED`, 12/12 points after independent
  Owner closure at audit SHA `6876d867cdd845195e8946b05329b0bc82937fdc`.
- Validated total: `16/100`.
- WP02 State Transactions & Rollback: `SCHEMA_V2_FOUNDATION`, 0/6 points;
  WP02-B implemented the bounded schema-v2 serialization foundation; full
  solver restart migration remains future WP02-C/WP02-D work.
- OD-029-01: **OPEN**; it blocks WP09 only.
- OD-029-02: **CLOSED** as `READ_V1_WRITE_V2_BOUNDED`; ambiguous/stateful
  contact-bearing v1 checkpoints are rejected.

WP02-A is recorded in the `wp02_*` planning records. WP02-B adds the schema-v2
checkpoint and deterministic serialization foundation without changing
numerical formulations or maturity claims.
