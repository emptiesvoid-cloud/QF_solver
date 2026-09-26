# WP07-D R2.5 Owner acceptance

**Decision:** accepted with limitations on 2026-09-26. This records the
Owner's acceptance of the audited R2.5 requalification evidence; it does not
award additional points or change the existing WP07 score.

## Decision and score

- Existing WP07 award remains **10/10**.
- Incremental points awarded by this decision: **0**.
- Global official total remains **95/100**.
- Historical failures remain preserved.
- This decision does not authorize governing integration or push.
- WP07-E and WP08-E were not rerun or reclassified by this decision.

## Reviewed evidence

- Branch: `codex/wp07d-penalty-r2-5`
- Authorized base: `b2485f98260c7ca9892997eefa3a327637d83cd3`
- Execution SHA: `3c749f30f95a53b4eaadb2159accb4349e6d7ee7`
- Contract SHA-256: `8b3f53c55b08859cbada2668f6e6506f08acb1981a690f62074cac0b4082bf78`
- Binding SHA-256: `55a24836c4369fc4f94ec02a0a430fe5d098fa5c46e71aa814ea1399b23683dc`
- Policy digest: `93a79d72fab9a9305985276f4c912d49c3e6e5df865475ae2108848778ea92ac`
- Final analysis SHA-256: `2176eb503ab5aa609d5903be292111cc23eeefe83c9bdaf803c7bb39e7236abd`
- Normalized replay-gate SHA-256: `7bd9f01ac94fd9c8e884ebbae94450eefa01958676e79b87cca57a9a57f1a926`.

The audit confirmed the ACTIVE_SET and PENALTY M1/M2/M3 candidate evidence,
their independent observable recomputations, and exactly two authorized
replays: ACTIVE_SET/M2 and PENALTY/M1. The gate normalization changed only the
eligible status enum (`success` to `PASS`), retained the raw status, and did
not rewrite primary/reference results, numerical values, thresholds, or
parameters. The pre-normalization gate remains preserved.

## Warning and limits

PENALTY/M1 remains explicitly `run_verdict=WARNING`; the solve converged, the
final relative residual was `1.8185441495457156e-11`, and maturity remains
`research`. The Owner accepts this disclosed warning as a limitation; it is
not relabeled as PASS and no frozen gate was weakened.

The independent references are observable recomputations, not independent
global FEM/Newton solves. The decision is limited to the frozen WP07-D scope.
It does not extend to frictional updated search, finite sliding, or WP08
qualification.

The 99 raw files (3,949,086,874 bytes) remain in the isolated local evidence
directory `qualification/0_2_9/wp07d_contact_requalification_r2/runs_r2_5/`.
They are excluded from Git; their external WP16 archive is still pending.
Preserve this worktree or archive those raw files before removing it.

See the [machine-readable Owner decision](../../../qualification/0_2_9/wp07d_contact_requalification_r2/wp07d_r2_5_owner_acceptance.json)
and the [R2.5 final analysis](../../../qualification/0_2_9/wp07d_contact_requalification_r2/analysis_final_r2_5.json).
