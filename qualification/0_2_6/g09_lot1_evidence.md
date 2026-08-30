# 026-G09 Contact Lot 1 Evidence

Status: **PASS_WITH_LIMITATIONS**; official gate remains **NOT_STARTED**.
Source SHA: `341ff7111630f6244401ca82addc04414408b9b1`; dirty: `False`.

## Scope

Bounded frictionless node-to-triangle penalty contact on the existing nonlinear common driver. No friction, general surface-to-surface, finite-sliding or external-correlation claim is made.

## Executed cases

| Case | Status | Key evidence |
|---|---|---|
| `G09-L1-001` | `PASS_INTERNAL_RESEARCH` | open/closed active=[]/[0]; common driver residual=1.638e-08 |
| `G09-L1-002` | `PASS_INTERNAL_RESEARCH` | active sequence=[False, True, False, True]; gaps=[0.6448103565750625, -1.5802542735032787e-05, 0.9999999999999996, -1.5802542735032787e-05] |
| `G09-L1-003` | `PASS_INTERNAL_RESEARCH` | penetration monotone=True |
| `G09-L1-004` | `EXPECTED_FAILURE` | Penalty contact trial exceeded contact_max_penetration. |
| `G09-L1-005` | `PASS` | exact deterministic replay |

## Penalty sensitivity

| Penalty | Gap | Penetration | Residual | Iterations |
|---:|---:|---:|---:|---:|
| 1e+02 | -1.52310771e-02 | 1.52310771e-02 | 7.29858473e-16 | 2 |
| 1e+03 | -1.57440039e-03 | 1.57440039e-03 | 5.06642392e-15 | 2 |
| 1e+04 | -1.57972030e-04 | 1.57972030e-04 | 2.67305071e-15 | 2 |
| 1e+05 | -1.58025427e-05 | 1.58025427e-05 | 1.70263886e-13 | 2 |
| 1e+06 | -1.58030769e-06 | 1.58030769e-06 | 1.44001255e-11 | 2 |

| Penalty | Contact force norm | Global reaction norm | Audit verdict |
|---:|---:|---:|---|
| 1e+02 | 2.15399958e+00 | 11.02336601114122 | `WARNING` |
| 1e+03 | 2.22653838e+00 | 11.013120670272631 | `WARNING` |
| 1e+04 | 2.23406188e+00 | 11.012069318145357 | `WARNING` |
| 1e+05 | 2.23481703e+00 | 11.011963909037304 | `WARNING` |
| 1e+06 | 2.23489257e+00 | 11.0119533654343 | `WARNING` |

Penetration monotone non-increasing: `True`.
The production penalty range and conditioning acceptance band remain Owner decisions.

## Failure contract

The excessive-penetration case is expected to fail closed with a structured `NumericalConvergenceError`; it is not counted as a converged case.

## Limitations

- Bounded TET4 node-to-triangle penalty contact only.
- Initial-configuration search only in this lot; finite sliding is not qualified.
- Penalty production range and conditioning band require Owner decision.
- The exact linear active-set route and external contact studies are separate evidence.
- Official G09 remains NOT_STARTED; this is Lot 1 evidence, not gate closure.
