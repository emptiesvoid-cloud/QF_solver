# WP07 R2.5 governing integration and push record

**Status:** integrated and pushed after separate Owner authorization on
2026-09-26. This record is additive: it does not alter the earlier WP07-D
evidence-acceptance decision, historical failures, or qualification results.

## Authorization and integration

- Governing branch: `0.2.9-unified-nonlinear`.
- Source branch: `codex/wp07d-penalty-r2-5`.
- Governing HEAD before integration: `b2485f98260c7ca9892997eefa3a327637d83cd3`.
- Accepted source HEAD: `624701020c24cab70382ba0e549af7504d21a813`.
- Integration: fast-forward; no force push.
- A stale R2.2-binding test was then corrected to assert fail-closed behavior
  at the newer source. Historical R2.2 binding/evidence was not changed.
- Targeted test-only commit: `7b079efa84529eadb19b155920342c54dcc9fb4e`.
- Initial pushed head: `7b079efa84529eadb19b155920342c54dcc9fb4e`.
- After `git fetch`, `origin/0.2.9-unified-nonlinear` matched that head; the
  branch had zero ahead/behind divergence at verification.

## Validation and scope

- Targeted contact/WP07 regressions: **118 passed**.
- Ruff: PASS; compileall: PASS; `git diff --check`: PASS.
- Full repository test suite: not run.
- No production source changed after the authorized WP07-D R2.5 execution SHA.
- No force push, WP08 qualification, or score change occurred.
- WP07 remains Owner-accepted at 10/10; this integration adds no points.
- WP08's historical 8/8 award is preserved, but its frictional-contact
  requalification remains open and is not covered by WP07-D acceptance.
- Global official total remains 95/100.

## Raw evidence preservation

The 99 raw R2.5 files (3,949,086,874 bytes) were not added to Git or pushed.
They remain in the isolated local worktree at
`C:/Users/fari/AppData/Local/Temp/qf_solver_wp07d_contact_r2_5_20260925/qualification/0_2_9/wp07d_contact_requalification_r2/runs_r2_5/`.
Preserve that worktree until the planned WP16 archive verifies and records the
external archive. Do not delete it before then.

The evidence decision and the later integration authorization are distinct:
the former accepted bounded R2.5 evidence; the latter authorized the
fast-forward and push. See `OD-029-WP07-R2.5-INTEGRATION-01` in
`qualification/0_2_9/owner_decisions.json` and the machine-readable record at
`qualification/0_2_9/wp07d_contact_requalification_r2/wp07_r2_5_integration_record.json`.
