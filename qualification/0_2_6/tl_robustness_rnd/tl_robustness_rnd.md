# TL Robustness Extension R&D

Status: `DIAGNOSTIC_ONLY`. This report records opt-in experiments around the
existing Total-Lagrangian driver. It does not promote TL, change the default
path, or qualify a new numerical domain.

## Provenance

- R&D source/control SHA: `46e9a56e4e7530e6f093bb88f7d028c42c185f1d`
- Starting boundary-study SHA: `de7633ab9806fe49f463bf28847c18a8120cc8af`
- The R&D controls are opt-in. `FORMULATION_CHANGED=NO`, `TANGENT_CHANGED=NO`,
  and `DEFAULT_PATH_CHANGED=NO`.
- The mechanism JSON files are large exploratory outputs and remain local and
  ignored. The tracked failure zoo and this compact decision record are kept.
- The final document commit is evidence/documentation only; it is not a new
  numerical qualification source.

## Baseline reproduction

The relevant 150-case TL boundary campaign was replayed after the opt-in
controls were committed. It covered 75 TET4 and 75 HEX8 cases across four mesh
levels, three load-increment levels, three load levels, four distortion levels,
and the tested aspect-ratio/mode combinations.

| Measurement | Result |
| --- | ---: |
| Physical cases | 150 |
| Fixed-step successes | 134 |
| Adaptive successes | 146 |
| Recovered by cutback | 12 |
| Failed in both modes | 4 |
| Stable zone | 134 |
| Degraded zone | 12 |
| Out-of-recommended-scope zone | 4 |
| Persistent HEX8 failures | 4 |

The high-level counters, zone classification and deterministic nominal
signatures match the previous boundary study. The four persistent cases are:

- `HEX8_m4_a7_compression_l0.2_n16_d0.12`
- `HEX8_m4_a10_compression_l0.2_n16_d0.12`
- `HEX8_m4_a10_compression_l0.2_n8_d0.12`
- `HEX8_m4_a10_compression_l0.2_n32_d0.12`

Observed condition numbers remain descriptive only: stable median about
`3.97e3`, degraded median about `9.25e4`, and persistent out-of-scope median
about `8.22e6`. No universal cutoff was introduced.

The boundary runner reports `dirty=true` when it computes its final output
because the newly selected output directory contains its own untracked report
files. Git status was clean before the replay and was restored clean after
generated outputs were removed. This is recorded as a harness-output detail,
not as source dirtiness.

## Opt-in mechanism screening

The first screening was run on the eight-case adversarial/nominal corpus. The
mechanism JSON artifacts were captured before the clean source commit and are
therefore exploratory evidence, not release qualification evidence. The clean
150-case replay confirms that the default path remains unchanged.

| Mechanism | Targeted result | Decision |
| --- | --- | --- |
| Symmetric system scaling | 0 recoveries, 0 regressions | Rejected: no observed robustness gain |
| Row residual scaling | 0 recoveries, 0 regressions | Rejected: no observed robustness gain |
| SciPy `splu` + `COLAMD` | 0 recoveries, 0 regressions | Rejected: no observed robustness gain |
| SciPy `splu` + `NATURAL` | 0 recoveries, 0 regressions | Rejected: no observed robustness gain |
| Armijo line search | No status change; effectively equivalent on corpus | Rejected: no observed gain |
| Existing line search disabled | One fixed-path status change on degraded HEX8 bending; persistent failures remain | Rejected: negative control, removes a safeguard |
| More conservative adaptive cutback | One persistent HEX8 failure recovered in the selected case | Rejected for full replay: 13,246 Newton iterations, 4 cutbacks, about 46,114 assembly calls, no independent small-step reference |

The cutback recovery ended with relative free residual about `1.44e-14`,
`min(det(F))` about `0.644`, and tangent condition estimate about `8.65e4`.
Those values show that the mechanism can find an equilibrium for one case, but
the cost and missing independent reference do not support retention. It must
not erase the original fixed-step failure or its failure history.

Passive minimum-eigenvalue and conditioning diagnostics were collected where
available. They are observational only; no eigenvalue or conditioning cutoff
was added.

## Holdouts and equivalence

The nominal reference subset included stable TET4/HEX8 compression cases and
the degraded TET4 compression and HEX8 bending cases. Persistent failures were
repeated twice in the clean R&D baseline and all repeated signatures matched.
No mechanism was accepted, so the policy requiring a new 150-case replay after
each retained mechanism was not triggered. Any future retained mechanism must
be replayed on a clean SHA before consideration.

## Checks

- Targeted tests: `64 passed`
- Capability registry and family anti-forgetting checks: `PASS`
- Ruff: `PASS`
- `compileall`: `PASS`
- `git diff --check`: `PASS`
- Full pytest regression: not rerun; no default numerical path changed
- Full 150-case TL boundary replay: `PASS` for baseline counters and zones

## Decisions and remaining limitations

- `MECHANISMS_ACCEPTED=NONE`
- `MECHANISMS_REJECTED=system_scaling,residual_row_scaling,splu_colamd,splu_natural,line_search_armijo,line_search_off,adaptive_cutback`
- `PERSISTENT_FAILURES_BEFORE=4`
- `PERSISTENT_FAILURES_AFTER=4` on the default path
- `TL_ROBUSTNESS_LEVEL=DIAGNOSTIC_ONLY`
- `TL_PROMOTION=DEFERRED`
- The four persistent HEX8 compression cases remain outside the recommended
  domain and in the failure zoo.
- Adaptive cutback remains an experimental observation, not an accepted solver
  policy.
- Wall-clock performance was not accepted as characterized; assembly-call
  counts were used only as a cost diagnostic.

The next step is a separately approved correction-planning review. No solver
formulation fix, tangent change, TL promotion, Arc-Length/G08 work, push, merge,
tag, release, or PyPI publication was performed.
