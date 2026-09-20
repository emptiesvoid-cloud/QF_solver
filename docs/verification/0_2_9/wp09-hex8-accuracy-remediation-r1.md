# WP09 HEX8 refinement and equilibrium-accuracy remediation

## Conclusion

The isotropic HEX8 diagnostic series was extended through `H9 = 9×9×9`,
and the two finest levels were rerun with the solver tolerance tightened from
`1e-7` to `1e-9`. The refinement trend is improving and the strict H8/H9 pair
passes the existing diagnostic mesh-delta limits. The equilibrium miss seen on
the original H8/H9 runs is reproduced as a termination-accuracy effect:
force and moment balance move from approximately `1e-7` to approximately
`1e-11` without changing the production mechanics or the frozen thresholds.

This remains diagnostic evidence. The WP09 formal contract was not rebound,
no formal points were awarded, and no merge or push was performed.

## Scope and invariants

- Family: HEX8 only; historical TET4 evidence remains unchanged.
- Load scale: `0.25` of the reference load.
- Material, geometry, boundary conditions, load path and local-strain limit:
  unchanged.
- Original extended sequence: H4, H5, H6, H7, H8, H9.
- Strict accuracy pair: H8 and H9, tolerance `1e-9`.
- Production mechanics changed: `NO`.
- Thresholds changed: `NO`.
- Formal contract changed: `NO`.

## Extended mesh sequence

The previously archived H4–H9 sequence shows decreasing consecutive changes:

| Transition | displacement | energy | von Mises | PEEQ |
|---|---:|---:|---:|---:|
| H4 → H5 | 13.324% | 15.883% | 15.710% | 14.704% |
| H5 → H6 | 8.836% | 10.940% | 10.114% | 9.759% |
| H6 → H7 | 6.044% | 7.759% | 6.907% | 6.826% |
| H7 → H8 | 4.249% | 5.674% | 4.941% | 5.010% |
| H8 → H9 | 3.049% | 4.271% | 3.679% | 3.799% |

The last transition is within the diagnostic comparison limits of 5% for
displacement and energy, and 10% for stress. This is a mesh-closure signal for
the declared HEX8 observables, not a general 3-D qualification claim.

## Strict H8/H9 accuracy runs

| Level | Nodes | Elements | DOFs | displacement | energy | von Mises | max local strain | free residual | force balance | moment balance | elapsed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| H8, tol 1e-9 | 729 | 512 | 2187 | 0.0212303440 | 0.00209381725 | 0.310574483 | 0.042193976 | 5.157e-10 | 3.270e-11 | 2.309e-11 | 1772.18 s |
| H9, tol 1e-9 | 1000 | 729 | 3000 | 0.0218979954 | 0.00218723826 | 0.322436775 | 0.043858721 | 5.397e-10 | 2.220e-11 | 1.570e-11 | 2465.44 s |

Strict H8 → H9 deltas are:

```text
displacement = 3.048916 %
energy       = 4.271186 %
von Mises    = 3.678951 %
PEEQ         = 3.798882 %
```

Both strict runs accepted all four load increments, with zero rejected
increments. The local strain bound remains below `0.05`.

## Before/after diagnosis

The original H9 run used tolerance `1e-7` and ended with:

```text
free residual  = 8.601116e-08
force balance  = 1.931590e-07
moment balance = 1.365839e-07
```

The strict H9 run ended with:

```text
free residual  = 5.397145e-10
force balance  = 2.220094e-11
moment balance = 1.570391e-11
```

The force and moment errors therefore decrease by about `8.7×10^3`, and the
free residual decreases by about `1.59×10^2`. The primary observables change by
less than `0.0001%` between the original and strict H9 runs. This strongly
supports solver termination accuracy as the cause of the previous equilibrium
failure; it is not evidence for changing the equilibrium thresholds.

The strict H9 run took `2465.44 s` versus `2110.73 s` originally, an overhead
of approximately `16.8%`. This is an observational cost, not a performance
benchmark.

## Formal status

```text
HEX8_EXTENDED_MESH_SERIES       = DIAGNOSTIC_PASS
HEX8_STRICT_H8_H9_EQUILIBRIUM   = PASS_DIAGNOSTIC
HEX8_H8_H9_MESH_CLOSURE         = PASS_DIAGNOSTIC
WP09_FORMAL_REQUALIFICATION     = NOT_REBOUND
WP09_FORMAL_POINTS               = 0/8
PRODUCTION_MECHANICS_CHANGED     = NO
THRESHOLDS_CHANGED               = NO
MERGE                           = NO
PUSH                            = NO
```

Before any formal claim, the next controlled step is to freeze a new HEX8
contract that explicitly records the fine H8/H9 hierarchy and strict solver
accuracy requirement, then run the required independent observable checks and
replay from that contract. The existing historical FAIL_CLOSED evidence must
remain preserved.

## Evidence

- Extended mesh study: `qualification/0_2_9/wp09_hex8_extended_refinement_r1/`
  through `r3/`.
- Strict H8 evidence: `qualification/0_2_9/wp09_hex8_accuracy_remediation_r2/`.
- Strict H9 evidence: `qualification/0_2_9/wp09_hex8_accuracy_remediation_r1/`.
- Machine-readable consolidation:
  `qualification/0_2_9/wp09_hex8_accuracy_diagnostic_summary.json`.
