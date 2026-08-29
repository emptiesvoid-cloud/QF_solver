# TL Robustness Extension R&D

Status: `DIAGNOSTIC_ONLY`. This record evaluates opt-in numerical robustness
controls around the existing Total-Lagrangian driver. It does not promote TL,
change the default path, or qualify a new numerical domain.

## Provenance and guardrails

- R&D starting reference: `de7633ab9806fe49f463bf28847c18a8120cc8af`
- Clean opt-in controls commit: `491ab821b88da7479862293212bf68279b51db87`
- Full adaptive-growth replay source SHA: `491ab821b88da7479862293212bf68279b51db87`
- Full adaptive-growth replay: `dirty_at_start=false`
- Full extended-cutback replay source SHA: `e0920e01ca7c8833884debc667e850b8d863d1c8`
- Holdout runner source SHA: `cd6a6c62947ec12338747ee979a82699f9334572`
- Historical 150-case boundary record consumed for comparison: `5d16ab839679dcee64e6251085ba52c4b494847c`
- Adaptive-growth replay artifact: `adaptive_growth_150.json`
- Adaptive-growth artifact SHA-256: `2e8abe49af253fee1729b55572d9ed8bdf2917c91c362a4950c9a738d3537ac5`
- Extended-cutback replay artifact: `adaptive_cutback_extended_150.json`
- Extended-cutback artifact SHA-256: `609e51576a88f940c0b711671b1d8c2e3b08b440d3a53ba22de298feb8279224`
- Holdout artifact: `holdouts.json`
- Holdout artifact SHA-256: `4f49041752c2fb33e8d3feb6020a32ed7fbc90115b0a6ab67585c1dff8e6652d`

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
| Extended recovery-only cutback | 1 recovery on the full corpus, 0 regressions; 90,343 Newton iterations and 44 cutbacks | Retained for experimental holdout only |

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

## Full 150-case extended-cutback replay

The retained candidate is deliberately conservative: it keeps the existing
adaptive driver, disables growth, uses `cutback_factor=0.25`, and raises the
retry budget to `max_cutbacks=25`. It is an opt-in R&D policy, not the default
path and not a release qualification.

| Measurement | Candidate | Existing adaptive reference |
| --- | ---: | ---: |
| Physical cases | 150 | 150 |
| Successful cases | 147 | 146 |
| Persistent failures | 3 | 4 |
| Recoveries | 1 | - |
| Status regressions | 0 | - |
| Status changes | 1 | - |
| Newton iterations, all cases | 90,343 | 74,448 |
| Assembly calls, all cases | 363,741 | 349,320 |
| Accepted steps, all cases | 27,713 | 21,355 |
| Cutbacks/rejected increments | 44 | 78 |

The recovered case is
`HEX8_m4_a7_compression_l0.2_n16_d0.12`. The remaining persistent failures
are:

- `HEX8_m4_a10_compression_l0.2_n16_d0.12`
- `HEX8_m4_a10_compression_l0.2_n8_d0.12`
- `HEX8_m4_a10_compression_l0.2_n32_d0.12`

For the 146 cases already successful with the existing adaptive reference, the
largest absolute candidate-minus-reference differences were:

| Metric | Maximum absolute difference |
| --- | ---: |
| Displacement norm | `4.0616241e-08` |
| Maximum displacement | `1.1367402e-08` |
| Free residual norm | `3.4349697e-09` |
| Reaction norm | `4.5723467e-09` |
| Strain energy | `1.4168696e-09` |
| Minimum `det(F)` | `5.3541327e-10` |
| Maximum `det(F)` | `2.2329893e-10` |

These are measured comparisons, not newly imposed acceptance thresholds. The
full replay supports retaining the policy for further bounded experimentation,
but it does not provide an independent converged reference for the recovered
case and does not justify promotion.

## Reproducibility and holdouts

- Targeted repeated signatures: `PASS` on the eight-case development corpus.
- Full 150 adaptive-growth replay: executed once on a clean source SHA;
  candidate status comparison is reproducible from its archived raw artifact
  and digest.
- Full 150 extended-cutback replay: executed once on a clean source SHA;
  `147/150` candidate successes, one recovery, zero regressions, and three
  persistent failures.
- New holdouts: `8` cases, four TET4 and four HEX8, selected from the controlled
  corpus but excluded from the eight-case development set. Baseline and
  candidate both succeeded on all eight; status changes `0`, recoveries `0`,
  regressions `0`. The largest measured state-metric difference was
  `3.4349697e-09` on the degraded HEX8 holdout.
- A repeated candidate signature for the recovered persistent case was
  deterministic (`912ffb3c50e10643253d0b2ca9cbf01fdc4fbf2f3d79a9a9cc745a82421e7b7e`).
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
- Extended-cutback full replay: `150/150` executed, `1` recovery, `0`
  regressions, three persistent failures; retained for experimental holdout
  only.

## Final R&D decision

- `MECHANISMS_ACCEPTED=adaptive_cutback_extended (experimental holdout only)`
- `MECHANISMS_REJECTED=system_scaling,residual_row_scaling,splu_colamd,splu_natural,line_search_armijo,line_search_off,adaptive_cutback,adaptive_growth`
- `PERSISTENT_FAILURES_BEFORE=4`
- `PERSISTENT_FAILURES_AFTER=4` on the default path and `3` under the
  extended-cutback experiment.
- `TL_ROBUSTNESS_LEVEL=DIAGNOSTIC_ONLY`
- `TL_PROMOTION=DEFERRED`
- `READY_FOR_TL_PROMOTION_CAMPAIGN=NO`

Recommended correction-planning topics are diagnostic only: establish an
independent converged reference for the recovered HEX8 case, characterize the
high cost of extended retries, investigate the three remaining persistent
failures, and preserve explicit failure histories. No universal
condition-number cutoff or numerical tolerance change is justified by this
campaign. The extended policy remains opt-in and is not accepted as a default
solver behavior.

No TL promotion, G07 closeout, Arc-Length/G08 work, push, merge, tag, release,
or PyPI publication was performed.
