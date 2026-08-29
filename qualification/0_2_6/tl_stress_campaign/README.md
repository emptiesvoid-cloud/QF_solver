# TL Stress Campaign

Status: `DIAGNOSTIC_ONLY`; no release thresholds or promotion decisions were applied.

Source SHA: `e522a24394e58d79266bcfde1b431b631381a231`; dirty at capture: `True`.

## Corpus

- 32 global observations (16 per family).
- 16 local objectivity/tangent observations (8 per family).
- 8 small-strain TL-versus-initial-tangent observations.
- Mesh levels: `(1, 2, 3, 4)`; increment levels: `(6, 8, 16, 32)`.
- Per-family case totals, including local and small-strain observations: `{'TET4': 28, 'HEX8': 28}`.

## Observed global outcomes

| Family | Completed | Exceptions |
| --- | ---: | ---: |
| TET4 | 15 | 1 |
| HEX8 | 14 | 2 |

## Findings

- Local rigid translations and rotations produced zero/negligible internal force and zero/negligible energy in the recorded observations.
- Local finite-difference tangent observations were approximately `1.42e-9` maximum for TET4 and `3.31e-9` maximum for HEX8 in the tested states.
- Small-strain relative differences against the initial tangent solve were approximately `1.81e-5` to `2.20e-5` for TET4 and `1.35e-5` to `1.46e-5` for HEX8. These are observations, not accepted error bands.
- Three reproducible high-load/elongated-mesh exceptions were recorded as `NUMERICAL_CONVERGENCE`; mesh validation itself reported no errors for those cases. They require a separate model and load-path audit before any solver attribution.
- No solver bug was demonstrated. No mesh-quality failure was demonstrated in the three convergence exceptions. Broader condition-number and external-reference studies remain open.

## Failure zoo

`tl_failure_zoo.json` contains 5 preserved cases: three numerical-convergence exceptions, one degenerate-reference mesh rejection, and one documented distributed-load boundary.

The full raw observations are in `tl_stress_campaign.json`. Existing TL code and tolerances were not changed.
