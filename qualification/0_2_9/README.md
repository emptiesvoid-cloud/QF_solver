# QF Solver 0.2.9 qualification planning

This directory is the prospective, machine-readable planning and controlled
closure record for the 0.2.9 **Unified Nonlinear Mechanics** development
cycle. The Owner-approved WP01 closure is recorded in
`wp01_owner_closure.json`; it does not change any 0.2.8 maturity record.

The baseline commit is recorded in `baseline.json`. Work packages may only
add prospective contracts and evidence beneath this directory; historical
0.2.8 evidence remains immutable.

WP03 Newton Robustness / Adaptive Control is **CLOSED** at 7/7 points after
the independent WP03-E audit at `4ca71d549ea13460086f52670baa42c74d9ac1aa`.
The `GO_WITH_LIMITATIONS` decision confirms the four bounded policy
authorities, exact retry rollback and numerical preservation. It also records
the same-model target-clipped arc retry challenge: the final policy reaches
the unchanged physical solution with one rejection where the pre-WP03 route
repeated the same effective radius five times.

WP04 Geometric Nonlinear Qualification is now **HOLD — TET4 mesh convergence**
at 0/12. WP04-B independently demonstrates the bounded TET4/HEX8
Total-Lagrangian Saint-Venant-Kirchhoff objectivity, affine patch,
energy-gradient, tangent and accepted-path work identities. WP04-C then ran a
frozen TET4 cantilever campaign. Its small-load, force/moment balance,
load-step, replay, envelope and failure checks pass, but its M3-vs-M2
displacement/energy/stress mesh differences (16.4%/16.4%/24.3%) exceed the
frozen 2%/2%/10% limits. Neither family is promoted. See the controlled
WP04-C record at `../docs/verification/0_2_9/wp04-c-tet4-structural-qualification.md` and
`wp04_c_tet4_structural_summary.json`.

## Current planning status

- WP00: `CLOSED`, 4/4 points.
- WP01 Unified Nonlinear Core: `CLOSED`, 12/12 points after independent
  Owner closure at audit SHA `6876d867cdd845195e8946b05329b0bc82937fdc`.
- Validated total: `29/100`.
- WP02 State Transactions & Rollback: `CLOSED`, 6/6 points after the
  independent WP02-E audit at `c4e02fbd2d1262f621f6c8d4f07ee2da89d885f5`.
  The decision is `GO_WITH_LIMITATIONS`; Owner review is required before the
  independent WP03-E closure audit.
- OD-029-01: **OPEN**; it blocks WP09 only.
- OD-029-02: **CLOSED** as `READ_V1_WRITE_V2_BOUNDED`; ambiguous/stateful
  contact-bearing v1 checkpoints are rejected.

WP03-C preserves the accepted-state authority and all existing numerical and
maturity boundaries. WP03-D adds the single `UnifiedArcLengthRadiusPolicy`,
preserves the specialized arc-length correction kernel and fixes the
target-clipped retry stall boundary. The independent closure record is
`wp03_e_independent_closure.json`; it awards WP03 7/7 without promoting
maturity or changing a numerical formulation.

WP02-A is recorded in the `wp02_*` planning records. WP02-B adds the schema-v2
checkpoint and deterministic serialization foundation without changing
numerical formulations or maturity claims.

WP04-A freezes the objectivity, affine finite-deformation patch, energy
gradient, tangent, accepted-path work, small-limit, equilibrium, mesh,
cross-family and replay gates before implementation. Historical WP13-11
energy/work evidence is retained unchanged: its coarse 24-sample work path
failed the old discovery threshold. WP02/WP03 now provide an authoritative
accepted-state callback seam for a correct future refinement study, but that
study is deliberately not claimed complete in WP04-A.
