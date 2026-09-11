# QF Solver 0.2.9 qualification planning

This directory is the prospective, machine-readable planning and controlled
closure record for the 0.2.9 **Unified Nonlinear Mechanics** development
cycle. The Owner-approved WP01 closure is recorded in
`wp01_owner_closure.json`; it does not change any 0.2.8 maturity record.

The baseline commit is recorded in `baseline.json`. Work packages may only
add prospective contracts and evidence beneath this directory; historical
0.2.8 evidence remains immutable.

WP03 Newton Robustness / Adaptive Control is now in
**ADAPTIVE_POLICY_AUTHORITY** at 0/7 points. WP03-A froze the authority map,
robustness contracts, failure/retry matrix and 16-case baseline campaign.
WP03-B recorded the common stagnation/line-search authority, and WP03-C now
records the targeted common adaptive increment/retry policy. Arc-length
radius robustness remains future WP03-D work and requires Owner review before
it begins.

## Current planning status

- WP00: `CLOSED`, 4/4 points.
- WP01 Unified Nonlinear Core: `CLOSED`, 12/12 points after independent
  Owner closure at audit SHA `6876d867cdd845195e8946b05329b0bc82937fdc`.
- Validated total: `22/100`.
- WP02 State Transactions & Rollback: `CLOSED`, 6/6 points after the
  independent WP02-E audit at `c4e02fbd2d1262f621f6c8d4f07ee2da89d885f5`.
  The decision is `GO_WITH_LIMITATIONS`; Owner review is required before any
  WP03-C implementation.
- OD-029-01: **OPEN**; it blocks WP09 only.
- OD-029-02: **CLOSED** as `READ_V1_WRITE_V2_BOUNDED`; ambiguous/stateful
  contact-bearing v1 checkpoints are rejected.

WP03-C preserves the accepted-state authority and all existing numerical and
maturity boundaries. Its controlled evidence is recorded in
`wp03_c_adaptive_policy.json`; no WP03 points are awarded before independent
closure.

WP02-A is recorded in the `wp02_*` planning records. WP02-B adds the schema-v2
checkpoint and deterministic serialization foundation without changing
numerical formulations or maturity claims.
