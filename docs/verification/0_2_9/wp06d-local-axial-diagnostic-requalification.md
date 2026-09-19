# WP06-D local-axial diagnostic requalification

## Conclusion

The local axial M2/M3 diagnostic completed successfully. The production
accepted paths, the independent observable recomputation, and the archival
evidence replay are internally consistent. No limit point was detected in the
160 accepted states, so this package does **not** establish the frozen WP06-D
limit-point qualification and awards no formal point.

```text
PRODUCTION_M2 = PASS, 160/160 accepted states
PRODUCTION_M3 = PASS, 160/160 accepted states
INDEPENDENT_M2 = PASS_OBSERVABLE_RECOMPUTATION_NO_LIMIT_POINT
INDEPENDENT_M3 = PASS_OBSERVABLE_RECOMPUTATION_NO_LIMIT_POINT
EVIDENCE_REPLAY = PASS_EVIDENCE_REPLAY_ONLY
PRODUCTION_SOLVER_REPLAY = NOT_RUN
LIMIT_POINT = NOT_DETECTED
WP06D_FORMAL_STATUS = HOLD_NO_LIMIT_POINT_AND_NO_PRODUCTION_REPLAY
WP06D_FORMAL_POINTS = 0/2
```

## Provenance

| Field | Value |
|---|---|
| Branch | `codex/wp06-score-requalification` |
| Executed HEAD | `504c952287295cd525f1c4183b3c2764c5294b38` |
| Worktree at launch | dirty because of pre-existing WP06 preparation/diagnostic work |
| Production mechanics changed | NO |
| Thresholds changed | NO |
| Local mesh manifest | `b415aaefa9e6f91b7e4e704ad5da04bbc32ef6e422febd5da02af1fa54870918` |
| Production diagnostic runner | `c8a4201033314806f04b4c01910c55d71e02c3099f78b1f26847ded14968f84c` |
| Independent reference source | `2f66e3bb1e23e78bb95426c09c8a773a1aed12d11a1b58ea400c93df296232d9` |
| Evidence replay source | `3a5eb0632ae267382dc359586757d2d92e3332ace23e8cce061fb06b7a88dda7` |

## Production diagnostic results

| Level | Mesh | Nodes | TET4 | DOFs | Accepted | Status | Elapsed |
|---|---:|---:|---:|---:|---:|---|---:|
| M2 | local axial `104x4x4` | 2,625 | 9,984 | 7,875 | 160/160 | PASS | 4,828.09 s |
| M3 | local axial `188x4x4` | 4,725 | 18,048 | 14,175 | 160/160 | PASS | 9,108.50 s |

M3 final diagnostics:

- `q = 0.0351440173`;
- `min(det(F)) = 0.9957018494`;
- principal stretches: `[0.9924946701, 1.0049640263]`;
- maximum `||E||F = 0.0079097402`;
- maximum free residual: `9.10e-16`;
- maximum force balance relative error: `1.21e-11`;
- maximum current-moment balance relative error: `6.93e-14`.

The local refinement remains axial only; the transverse section is still `4x4`.

## Independent observable recomputation

The independent path uses only NumPy TET4 StVK kinematics/internal-force
assembly. It does not import production solver/contact/continuation routines
and does not solve Newton or arc-length equations.

| Level | States | Observable comparison | Envelope | Equilibrium | Limit point |
|---|---:|---|---|---|---|
| M2 | 160 | PASS | PASS | PASS | Not detected |
| M3 | 160 | PASS | PASS | PASS | Not detected |

The raw case-result observables and the recomputed values agree within
`rtol=2e-10`, `atol=1e-13`. The absence of a detected limit point is a genuine
result, not a converted failure.

## Evidence replay

The evidence replay read every accepted checkpoint twice for both M2 and M3.
All byte hashes, checkpoint composite digests, step numbers, and reference-row
links were identical. This is an archival/readback replay only; it is not a
second production FEM solve.

- replay summary: `qualification/0_2_9/wp06d_local_axial_diagnostic_20260919/evidence_replay.json`;
- independent summary: `qualification/0_2_9/wp06d_local_axial_diagnostic_20260919/independent_reference/independent_reference_summary.json`;
- production study: `qualification/0_2_9/wp06d_local_axial_diagnostic_20260919/study_final.json`.

## Formal interpretation

This package supports a bounded diagnostic statement: the local axial meshes
remain numerically stable over 160 accepted continuation states and their
declared observables are independently reproducible. It does not support the
formal WP06-D limit-point claim because:

1. no limit point was observed on this path;
2. no independent nonlinear path solve was executed;
3. no second production solver replay was executed;
4. the local refinement does not refine the transverse section.

WP06-A/B/C remain at **4/4 accepted points**. WP06-D remains **0/2** and
WP06-E/F remain blocked by the formal D dependency.

## Next action

Freeze a revised Owner-approved WP06-D scope before any formal score change:
either define a bounded continuation qualification that does not require a
limit point, or retain the existing limit-point contract and run a dedicated
benchmark/path that demonstrably reaches one. A genuine independent path solve
and a production solver replay are required before formal attribution.
