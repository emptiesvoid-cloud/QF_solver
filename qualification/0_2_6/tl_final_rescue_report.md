# TL Final Rescue Diagnostic Report

Status: `DIAGNOSTIC_ONLY`. This report records a targeted investigation of the
three persistent HEX8 Total-Lagrangian failures. It does not qualify or promote
the TL route and it does not change the default solver behavior.

## Scope and provenance

| Field | Value |
| --- | --- |
| Requested start SHA | `96f32aef4de4cabf1b4c02845e2fe6bdbbc57eb2` |
| Final execution source SHA | `4deb8eaacbc477141952a1042a1a36f3f7a8b1c5` |
| Final execution source worktree | `clean` (`dirty_at_start=false`) |
| Default path changed | `NO` |
| TL formulation changed | `NO` |
| TL tangent changed | `NO` |
| New thresholds introduced | `NO` |
| Default solver policy changed | `NO` |
| Evidence commit SHA | resolved with `git rev-parse HEAD` after this report commit; intentionally not embedded to avoid self-referential provenance |

The execution source SHA is the source of the final `full150`, holdout and
repeat runs. The later report commit, when created, is documentation/evidence
only and must not be treated as a new numerical qualification SHA.

## Final decision fields

```text
RESCUE_STATUS = SUCCESSFUL_OPT_IN_RECOVERY_DIAGNOSTIC
PERSISTENT_FAILURES_BEFORE = 3
PERSISTENT_FAILURES_AFTER_DEFAULT_PATH = 3
PERSISTENT_FAILURES_AFTER_CANDIDATE_POLICY = 0
BEST_NUMERICAL_REGION = max_iterations=200, min_load_increment=1e-6,
                         cutback_factor=0.25, max_cutbacks=64
ROOT_CAUSE_INTERPRETATION = load-control/Newton robustness boundary near a
                             severely conditioned tangent; no solver defect
                             or formulation defect was demonstrated
LOAD_CONTROL_LIMIT = YES
ALTERNATE_CONTROL_REFERENCE = existing TET4 shallow-arch arc-length path;
                               not comparable to these HEX8 cases
PHYSICAL_BRANCH_CONFIRMED = UNRESOLVED
CANDIDATE_STRATEGY = existing adaptive controls, explicit opt-in diagnostic only
STATE_EQUIVALENCE = scalar state metrics agree across n=8/16/32 to about 1e-14;
                    repeat n=16 displacement hash is identical; no independent
                    physical reference exists for the recovered target cases
FULL_150_REPLAY = 150/150 success, 0 failure
HOLDOUTS = 10/10 success, 0 failure
PERFORMANCE_COST = 4536.7938987 s cumulative for full150; 4495.7960847 s HEX8;
                   826992 assembly calls
FORMULATION_CHANGED = NO
TANGENT_CHANGED = NO
READY_FOR_TL_PROMOTION = NO
```

The candidate policy is deliberately not a release policy. It increases the
Newton/retry budget and lowers the minimum load increment through the existing
adaptive-control API. It was used only by the diagnostic harness.

## Persistent-case replay

The three exact target definitions were replayed from the final clean
execution source. All three reached a converged state with the candidate
policy.

| Case | Status | Rejected increments | Newton iterations | Assembly calls | Elapsed (s) | Relative residual | Min det(F) | Max displacement | Tangent condition | Tangent FD error |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HEX8 m4 a10 compression, n=8 | SUCCESS | 4 | 46089 | 136784 | 920.8182 | 2.8070e-14 | 0.6599327 | 11.9764890 | 1.98928e5 | 1.1520e-8 |
| HEX8 m4 a10 compression, n=16 | SUCCESS | 3 | 25931 | 87562 | 517.8373 | 2.0771e-14 | 0.6599327 | 11.9764890 | 1.98928e5 | 1.4378e-8 |
| HEX8 m4 a10 compression, n=32 | SUCCESS | 3 | 46100 | 134341 | 915.1631 | 2.1929e-14 | 0.6599327 | 11.9764890 | 1.98928e5 | 1.2414e-8 |

For the three final source runs, the maximum pairwise difference in scalar
physical state metrics across the three increment partitions was approximately
`7.11e-15` for displacement/residual/reaction/energy/determinant metrics. The
condition-number spread was `4.34e-6`, attributable to a spectral diagnostic.
The raw displacement hashes differ between the three increment partitions, so
exact vector identity across different partitions is not claimed. A repeated
`n=16` run produced the same displacement hash
`de7159fdedd05d0cfdf77d9456c4a49782cdaaf7ec6d41c51fc387428295c5cd`, identical
physical state metrics, identical assembly count (`87562`) and identical
Newton count (`25931`).

## Policy and root-cause evidence

The prior extended-cutback policy had `147/150` successes, one recovery and
three persistent failures. The final diagnostic candidate had `150/150`
successes, with zero status regressions among the 147 previously successful
cases and three recoveries corresponding exactly to the target IDs.

The original default/extended failure state was near a severe conditioning
boundary: the last failed target state had `det(F)` about `0.98915`, tangent
condition number about `1.0003e7`, minimum tangent eigenvalue about
`4.44e-6`, and free residual about `6.26e-2`. The candidate reaches a much
larger-deformation converged state, but no independent converged physical
reference exists for these three recovered cases. The evidence therefore
supports a load-control/Newton robustness interpretation, not a claim that the
candidate state is physically correct or that the default solver is defective.

The candidate policy was:

```text
initial_load_increment = 1 / increments
max_load_increment = 1 / increments
min_load_increment = 1e-6
cutback_factor = 0.25
growth_factor = 1.0
max_cutbacks = 64
max_iterations = 200
```

The default path remains unchanged and still has three persistent failures in
this diagnostic domain. No universal aspect-ratio, conditioning, tolerance or
cutback threshold is proposed.

## Neighbor/frontier observations

These exploratory frontier artifacts were generated before the final harness
corpus corrections, from source `a15b5b85f543ce5d7eec5fa7c5faaa17a60fbc1d`
with `dirty_at_start=true`. They are retained as context only, not as final
qualification evidence.

| Controlled change | Result | Min det(F) | Tangent condition | Max displacement | Residual | Tangent FD error |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| Aspect 10 -> 9.5 | SUCCESS | 0.9845605 | 1.4138e4 | 0.1918623 | 2.1974e-10 | 3.1292e-9 |
| Distortion 0.12 -> 0.10 | FAILURE | 0.9894860 | 1.0741e7 | 0.3772412 | 6.2698e-2 | 2.6545e-9 |
| Load 0.20 -> 0.175 | SUCCESS | 0.9865531 | 1.9565e4 | 0.1760597 | 2.3228e-10 | 2.2715e-9 |
| Neighbor mesh m4 -> m3 | SUCCESS | 0.7408772 | 3.0958e5 | 8.4887438 | 1.8963e-14 | 8.8422e-9 |

These observations are consistent with a narrow numerical/load-control region,
but they do not isolate a physical instability or prove a solver bug. The
existing shallow-arch arc-length implementation is a different two-TET4 model;
it was not used as a comparable alternate-control reference for the HEX8
targets. Therefore `PHYSICAL_BRANCH_CONFIRMED=UNRESOLVED`.

## Full-corpus replay

The final candidate was replayed against the complete 150-case boundary corpus
(75 TET4 and 75 HEX8).

| Measurement | Result |
| --- | ---: |
| Physical cases | 150 |
| Successes | 150 |
| Failures | 0 |
| TET4 successes | 75/75 |
| HEX8 successes | 75/75 |
| Total assembly calls | 826992 |
| Total elapsed | 4536.7939 s (75.61 min) |
| TET4 elapsed | 40.9978 s |
| HEX8 elapsed | 4495.7961 s |
| Maximum single-case elapsed | 920.8182 s |
| Median single-case elapsed | 0.3506 s |
| Status regressions against prior extended candidate | 0 |
| Recoveries against prior extended candidate | 3 |

Among the 147 cases already successful with the prior extended candidate, the
largest measured candidate-minus-reference differences were:

| Metric | Maximum absolute difference |
| --- | ---: |
| Displacement norm | 1.8843e-7 |
| Maximum displacement | 5.2734e-8 |
| Reaction norm | 2.1214e-8 |
| Strain energy | 6.5770e-9 |
| Minimum det(F) | 2.4844e-9 |
| Tangent condition number | 2.1342e5 (diagnostic only) |

These are observed differences, not newly imposed acceptance limits. The
condition-number difference is not used as a physical equivalence criterion.

## Holdouts and determinism

Ten deterministic holdouts, selected from the maintained corpus and separate
from the three target cases, passed under the same candidate policy. They
include five TET4 and five HEX8 cases across compression, bending and traction.

| Holdout group | Result | Notable range |
| --- | --- | --- |
| TET4, 5 cases | 5/5 SUCCESS | 0.05 to 3.78 s; residual 1.23e-12 to 1.89e-10 |
| HEX8, 5 cases | 5/5 SUCCESS | 0.19 to 453.57 s; residual 2.47e-14 to 6.35e-11 |

The full holdout artifact reports `10/10` success and a cumulative elapsed time
of `460.29998 s`. The n=16 repeat is deterministic for the physical output
and execution counts as described above.

## Incomplete or non-comparable experiments

The following are deliberately not represented as PASS:

- The exhaustive cutback-factor, minimum-increment and maximum-cutback sweep
  was started but interrupted because its cost was disproportionate; no
  artifact was produced.
- Individual exploratory runs for cutback factors `0.20` and `0.50` and
  minimum increment `1e-5` were interrupted; they are
  `INCONCLUSIVE_BY_COST`, not failures or recoveries.
- The exact alternate displacement-control/arc-length route was not run for
  the HEX8 target model. The existing TET4 shallow-arch route is not
  comparable.
- No external or independent physical reference was produced for the three
  recovered target states.
- The first `increments.json` and early frontier/control artifacts predate the
  final harness case-coverage correction. They remain superseded diagnostics;
  the final conclusion uses only clean-source `full150`, `holdouts` and
  `repeat` artifacts.

## Artifact manifest

Raw campaign outputs are generated under the ignored directory
`qualification/0_2_6/tl_final_rescue/`. Their SHA-256 digests are recorded here
so that the report remains small and the runs remain reproducible from the
execution source and harness.

| Artifact | Source SHA | Dirty at start | SHA-256 | Role |
| --- | --- | --- | --- | --- |
| `full150_maxit200.json` | `4deb8eaacbc477141952a1042a1a36f3f7a8b1c5` | false | `a93812f01fee79e2233e7ead6e21a210c2bb7f1d094d67447f56e73656c6fda9` | final 150-case replay |
| `holdouts_maxit200.json` | `4deb8eaacbc477141952a1042a1a36f3f7a8b1c5` | false | `e60904b8b6e2809573694b67f52de9b234f143f012b58c18bc6fd25e2ac33714` | final 10-case holdouts |
| `repeat_n16_maxit200.json` | `4deb8eaacbc477141952a1042a1a36f3f7a8b1c5` | false | `bed594793bf73deb0568b9875fae06af61f360e2ea0047cf522af6468ece179f` | deterministic repeat |
| `controls_maxit200_exact.json` | `a15b5b85f543ce5d7eec5fa7c5faaa17a60fbc1d` | true | `7a1b3389bb8cc71865eaeb0776fdf688f9f3a7d7080759152b7baa76f58f14c7` | superseded exact-target exploratory run |
| `frontier_aspect9_5.json` | `a15b5b85f543ce5d7eec5fa7c5faaa17a60fbc1d` | true | `83dca43101dcb584865a874ae5b9b477a544dc95399aa57fd29b61b57ff6e1ac` | exploratory neighbor |
| `frontier_distortion010.json` | `a15b5b85f543ce5d7eec5fa7c5faaa17a60fbc1d` | true | `2b08de1395eba223fac54f00510d264c0293bd9f5980bcf35fe793aefbd936bb` | exploratory neighbor |
| `frontier_load0175.json` | `a15b5b85f543ce5d7eec5fa7c5faaa17a60fbc1d` | true | `d1d0e738b6ec2ae24a4875b05ba91eedc7a74fe79c5942085e98ae33b74300df` | exploratory neighbor |
| `frontier_mesh3.json` | `a15b5b85f543ce5d7eec5fa7c5faaa17a60fbc1d` | true | `3eef05bbf37b862bb11d723aa31a27005df649bdfe7ef9b6d0870008d4f573fe` | exploratory neighbor |
| `increments.json` | `874cc55f987526fa64bdc7c9cf68906ec61aca18` | false | `a46818ddc85b9c78ea0e7c467d078db78fb3ba94c36bc0a25b8565a44a4b9abd` | superseded pre-fix corpus run |
| `tl_boundary_failure_zoo.json` | existing boundary source | n/a | `d2ab25692699a156bce8e6d382145569618b0c0cc6e3cdee24601e6ff9d72a1e` | preserved failure records |

The prior extended-cutback comparison artifact is
`qualification/0_2_6/tl_robustness_rnd/adaptive_cutback_extended_150.json`,
SHA-256
`609e51576a88f940c0b711671b1d8c2e3b08b440d3a53ba22de298feb8279224`.

## Checks and final limitation

The final diagnostic harness passed its targeted lint/compile/diff checks after
the coverage corrections. No full regression, coverage campaign or external
correlation campaign was rerun because no numerical solver source changed.
The report commit itself is documentation/evidence only.

The result is useful evidence that a narrowly configured, very expensive,
opt-in existing adaptive path can recover the three target cases and remain
green on the 150-case corpus plus ten holdouts. It is not evidence for changing
the default path, not evidence of a physically correct post-boundary branch,
and not evidence for TL promotion.

`READY_FOR_CORRECTION_PLANNING = YES` may be considered for a separate future
R&D task. `READY_FOR_TL_PROMOTION = NO` remains the decision for this run.

No solver fix, TL promotion, Arc-Length/G08 work, push, merge, tag, release or
PyPI publication was performed.
