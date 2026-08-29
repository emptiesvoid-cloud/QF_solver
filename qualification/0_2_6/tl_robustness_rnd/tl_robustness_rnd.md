# TL Robustness Extension R&D

Status: `DIAGNOSTIC_ONLY`. This record evaluates opt-in numerical robustness
controls around the existing Total-Lagrangian driver. It does not promote TL,
change the default path, or qualify a new numerical domain.

## Provenance and guardrails

- R&D starting reference: `de7633ab9806fe49f463bf28847c18a8120cc8af`
- Clean opt-in controls commit: `491ab821b88da7479862293212bf68279b51db87`
- Full adaptive replay source SHA: `491ab821b88da7479862293212bf68279b51db87`
- Full adaptive replay: `dirty_at_start=false`
- Historical 150-case boundary record consumed for comparison: `5d16ab839679dcee64e6251085ba52c4b494847c`
- Full replay artifact: `adaptive_growth_150.json`
- Full replay artifact SHA-256: `2e8abe49af253fee1729b55572d9ed8bdf2917c91c362a4950c9a738d3537ac5`

The default Total-Lagrangian path remains unchanged. No formulation, material
tangent, convergence tolerance, or default solver behavior was changed. The
controls are explicit opt-in experiments. `FORMULATION_CHANGED=NO`,
`TANGENT_CHANGED=NO`, and `DEFAULT_PATH_CHANGED=NO`. The experimental control
implementation is functional code, but it is not a release promotion.

## Baseline boundary reproduction

The controlled corpus contains 150 physical cases: 75 TET4 and 75 HEX8 cases,
covering four mesh levels, load and increment variations, distortion levels,
aspect-ratio/mode combinations, and the preserved adversarial cases.

| Measurement | Historical baseline |
| --- | ---: |
| Physical cases | 150 |
| Fixed-step successes | 134 |
| Existing adaptive successes | 146 |
| Recovered by existing cutback | 12 |
| Failed in both modes | 4 |
| Stable zone | 134 |
| Degraded zone | 12 |
| Out-of-recommended-scope zone | 4 |
| Persistent HEX8 failures | 4 |

The four persistent cases remain in the controlled failure zoo:

- `HEX8_m4_a7_compression_l0.2_n16_d0.12`
- `HEX8_m4_a10_compression_l0.2_n16_d0.12`
- `HEX8_m4_a10_compression_l0.2_n8_d0.12`
- `HEX8_m4_a10_compression_l0.2_n32_d0.12`

Observed conditioning values remain descriptive only: stable median about
`3.97e3`, degraded median about `9.25e4`, and out-of-recommended-scope median
about `8.22e6`. No universal conditioning or aspect-ratio cutoff was added.

## Mechanism screening

The initial screening used an eight-case corpus containing stable references,
degraded references, and the four persistent HEX8 compression failures.
Persistent cases were repeated; repeated deterministic outcome signatures passed
after runtime-only timing fields were excluded from the comparison digest.

| Mechanism | Observed result | Decision |
| --- | --- | --- |
| Symmetric system scaling | 0 recoveries, 0 regressions | Rejected: no observed robustness gain |
| Row residual scaling | 0 recoveries, 0 regressions | Rejected: no observed robustness gain |
| SciPy `splu` + `COLAMD` | 0 recoveries, 0 regressions | Rejected: no observed robustness gain |
| SciPy `splu` + `NATURAL` | 0 recoveries, 0 regressions | Rejected: no observed robustness gain |
| Armijo line search | No status change on the corpus | Rejected: no observed gain |
| Existing line search disabled | One fixed-path status change; persistent failures remain | Rejected negative control |
| Conservative adaptive cutback | One selected persistent case recovered; 13,246 Newton iterations, 4 cutbacks, about 46,114 assembly calls | Rejected: cost and no independent reference |
| Adaptive growth | 4 targeted recoveries, then full replay showed large state/branch differences | Rejected: physical equivalence not established |

All rejected mechanisms remain experimental observations. A status change alone
is not treated as a recovery suitable for retention.

## Full 150-case adaptive-growth replay

The candidate policy used only existing adaptive-load controls, explicitly
opted in for the experiment:

```text
initial_load_increment = 1 / increments
min_load_increment = 1.0e-4
max_load_increment = 1.0
cutback_factor = 0.5
growth_factor = 1.5
grow_below_iterations = 25
shrink_above_iterations = 50
max_cutbacks = 25
```

| Measurement | Candidate | Baseline adaptive |
| --- | ---: | ---: |
| Physical cases | 150 | 150 |
| Successful cases | 150 | 146 |
| Persistent failures | 0 | 4 |
| Recoveries | 4 | - |
| Status regressions | 0 | - |
| Status changes | 4 | - |
| Candidate Newton iterations, all cases | 15,456 | not comparable in this compact replay |
| Candidate cutbacks, all cases | 16 | not comparable in this compact replay |

The four persistent cases reached a converged state under the candidate policy,
but that does not establish equivalence. More importantly, several cases that
already succeeded with the historical adaptive path ended on materially
different states. The largest observed absolute differences among the 146
baseline-success comparisons were:

| Metric | Maximum absolute difference |
| --- | ---: |
| Displacement norm | 26.32564243 |
| Maximum displacement | 8.93173237 |
| Reaction norm | 2.25436816 |
| Strain energy | 1.13482623 |
| Minimum `det(F)` | 0.33678993 |
| Maximum `det(F)` | 0.04305267 |

The largest displacement differences occurred in compression cases including
`HEX8_m4_a8_compression_l0.2_n16_d0.12`,
`HEX8_m4_a8_compression_l0.2_n32_d0.12`,
`HEX8_m3_a10_compression_l0.2_n16_d0.12`, and
`TET4_m4_a10_compression_l0.2_n32_d0.12`. The candidate accepted much larger
growth steps and therefore followed a different equilibrium path in cases near
loss of stiffness. No independent reference was available in this run to
decide that the new path was physically preferable.

Decision: `adaptive_growth=REJECTED`. The full replay is recorded as an
executed diagnostic campaign with zero status regressions, but it is not a
qualified or retained solver policy. The four default-path persistent failures
and their original histories remain preserved.

## Reproducibility and holdouts

- Targeted repeated signatures: `PASS` on the eight-case development corpus.
- Full 150 replay: executed once on the clean source SHA; candidate status
  comparison is reproducible from the archived raw artifact and digest.
- New holdouts: `NOT_RUN`, because no mechanism was retained after the full
  replay. The default path remains unchanged and its original boundary corpus
  remains the reference.
- Failure zoo: preserved at
  `qualification/0_2_6/tl_boundary_study/tl_boundary_failure_zoo.json`.

## Checks

- Targeted nonlinear/robustness tests: `39 passed` in the final local check.
- Earlier R&D targeted suite: `64 passed`.
- Capability registry: `PASS`.
- Anti-forgetting: `PASS`.
- Ruff: `PASS` using the repository virtual environment.
- `compileall`: `PASS`.
- `git diff --check`: `PASS`.
- Full default-path regression: `NOT_RERUN`; no default numerical path changed.
- Full 150-case TL boundary replay for the adaptive candidate: `150/150`
  executed, `0` status regressions, mechanism rejected on state/branch
  equivalence.

## Final R&D decision

- `MECHANISMS_ACCEPTED=NONE`
- `MECHANISMS_REJECTED=system_scaling,residual_row_scaling,splu_colamd,splu_natural,line_search_armijo,line_search_off,adaptive_cutback,adaptive_growth`
- `PERSISTENT_FAILURES_BEFORE=4`
- `PERSISTENT_FAILURES_AFTER=4` on the default path;
  `0` only for the rejected adaptive-growth candidate.
- `TL_ROBUSTNESS_LEVEL=DIAGNOSTIC_ONLY`
- `TL_PROMOTION=DEFERRED`
- `READY_FOR_TL_PROMOTION_CAMPAIGN=NO`

Recommended correction-planning topics are diagnostic only: characterize the
branch-selection/path-dependence introduced by adaptive load growth, define an
independent reference before accepting recovered cases, and preserve explicit
failure histories. No universal condition-number cutoff or numerical tolerance
change is justified by this campaign.

No TL promotion, G07 closeout, Arc-Length/G08 work, push, merge, tag, release,
or PyPI publication was performed.
