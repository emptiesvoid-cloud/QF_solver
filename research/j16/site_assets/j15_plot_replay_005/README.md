# J15 NAFEMS 13H plot replay

Prepared for review; **not published**. This figure is a replay of the
archived J15 `site_data.json`, not a new solve. It marks all 151 plotted
frequency rows as `QF_GUARD_REJECTED`. The source run remains
`PYTEST_FAILED`; the figure does not turn any point into an accepted result.

The frozen input SHA-256, output SHA-256, source commit, elapsed time and
status counts are recorded in `replay_manifest.json` and
`replay_attempt_receipt.json`. Contract
`research/j16/contracts/j15_plotter_replay_005.json` identifies the exact
source worktree commit, input artifact, limits and output checks. Its two
earlier malformed-hash preflight attempts are retained in the adjacent
`research/j16/results/diagnostic-2026-11-17/plotter_replay_003/` and `_004/`
records. No solver or FEM route was called during replay.
