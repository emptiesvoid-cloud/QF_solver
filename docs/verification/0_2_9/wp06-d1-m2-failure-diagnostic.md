# WP06-D1 — M2 failure diagnostic

This diagnostic preserves the immutable Phase-1 artifact
`qualification/0_2_9/wp06d_phase1_structural_raw.json`. It does not promote,
rewrite, or replace WP06-D evidence.

## Findings

- M1 is numerically successful and observes a local maximum of lambda at
  `q=0.8696694118`, `lambda=0.0356656084`.
- M2 is numerically converged for 80 accepted steps, but lambda remains
  strictly increasing. The frozen M2 limit-point gate therefore fails.
- M2 force balance is `2.5391635e-17`; its moment balance is
  `2.4381964e-05`, above the immutable `1e-8` threshold.
- M1/M2 have equivalent total reference volume, positive orientations,
  persistent parent nodes, inherited symmetry nodes, and the same point load
  at node 4 with zero origin moment.
- The original runner recorded node-4 control displacement. R1 declares the
  mean UZ displacement of crown nodes 2, 3 and 4. The original M2 monitor is
  therefore not contract-valid for a refined-crown claim.

The full displacement states needed for independent per-support reaction
reconstruction were not present in the immutable raw artifact. Two
extended-horizon diagnostic attempts were made, but checkpoint extraction was
incompatible with the baseline reader API. No usable requalification evidence
was accepted and no M3 or WP06-E run was performed.

## Disposition

`M2_MOMENT_FAILURE` remains classified as
`OTHER_PENDING_PER_STATE_RECONSTRUCTION`, not as a numerical floor. The
formal WP06-D status remains `FAIL_CLOSED`; a future Owner-authorized
requalification must archive full accepted displacement states and correct the
declared monitor before causal attribution or remediation.
