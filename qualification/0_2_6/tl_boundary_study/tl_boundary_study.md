# TL Mesh / Conditioning Boundary Study

Status: `DIAGNOSTIC_ONLY`; no solver, formulation, tangent, Newton criterion or tolerance was changed.

- Source SHA: `5d16ab839679dcee64e6251085ba52c4b494847c`
- Worktree dirty at capture: `False`
- Physical cases: `150`; fixed/adaptive solver runs: `300`
- Generated: `2026-08-29T15:47:55.706393+00:00`

## Observed zones

The zones below describe observed behavior in the tested domain only. They are not qualification thresholds or universal mesh rules.

| Zone | Cases |
| --- | ---: |
| `STABLE_ZONE` | 134 |
| `DEGRADED_ZONE` | 12 |
| `OUT_OF_RECOMMENDED_SCOPE` | 4 |

## Fixed versus adaptive

| Family | Fixed success | Adaptive success | Recovered by cutback | Failed in both |
| --- | ---: | ---: | ---: | ---: |
| TET4 | 70 | 75 | 5 | 0 |
| HEX8 | 64 | 71 | 7 | 4 |

## Aspect observations

| Family | Nominal aspect | Cases | Stable | Degraded | Out of recommended scope |
| --- | ---: | ---: | ---: | ---: | ---: |
| TET4 | 4 | 12 | 12 | 0 | 0 |
| TET4 | 5 | 3 | 3 | 0 | 0 |
| TET4 | 6 | 22 | 22 | 0 | 0 |
| TET4 | 7 | 12 | 12 | 0 | 0 |
| TET4 | 8 | 7 | 5 | 2 | 0 |
| TET4 | 9 | 3 | 2 | 1 | 0 |
| TET4 | 10 | 16 | 14 | 2 | 0 |
| HEX8 | 4 | 12 | 12 | 0 | 0 |
| HEX8 | 5 | 3 | 3 | 0 | 0 |
| HEX8 | 6 | 22 | 22 | 0 | 0 |
| HEX8 | 7 | 12 | 10 | 1 | 1 |
| HEX8 | 8 | 7 | 4 | 3 | 0 |
| HEX8 | 9 | 3 | 3 | 0 | 0 |
| HEX8 | 10 | 16 | 10 | 3 | 3 |

## Boundary interpretation

- Nominal aspect ratio is not sufficient by itself; the report retains actual edge/Jacobian/element-quality metrics and shows cases sharing an aspect with different outcomes.
- Conditioning is reported descriptively alongside Newton behavior; no causal threshold is asserted.
- Adaptive cutback can recover load-step-sensitive cases, while cases that exhaust the minimum increment remain explicit failures.
- CASE2 and the historical TL failures remain in the failure zoo; this study does not convert them into qualification evidence.

The compact machine-readable [boundary failure zoo](tl_boundary_failure_zoo.json)
preserves all 16 non-stable cases, including the CASE2 boundary anchor. The
full raw observation artifact is reproducible from the source SHA and remains
ignored because it is large.

## Proposed Owner-review policies

- `CANDIDATE_MESH_POLICY = PROPOSED_OWNER_REVIEW`: use the observed family/mode/load/distortion zones only as a bounded usage discussion.
- `CANDIDATE_CONDITIONING_POLICY = PROPOSED_OWNER_REVIEW`: require reported conditioning diagnostics and fail-closed behavior; do not encode a universal numeric cutoff from this campaign.
