# TL Newton Robustness Fix

This report evaluates opt-in adaptive load cutback on the existing TL failure zoo.
The TL formulation, tangent, assembly and convergence tolerance are unchanged.

- Source SHA at execution: `f7b3dc200cbd7178ce26813d7fb096c01828353d`
- Worktree dirty at execution: `False`
- Generated: `2026-08-29T14:59:04.845921+00:00`

## Failure zoo replay

| Case | Fixed baseline | Adaptive result | Rejected increments | Final reason |
| --- | --- | --- | ---: | --- |
| CASE_1 | FAILURE / MAX_ITERATIONS | SUCCESS | 3 | - |
| CASE_2 | FAILURE / MAX_ITERATIONS | FAILURE | 8 | MIN_INCREMENT_REACHED |
| CASE_3 | FAILURE / MAX_ITERATIONS | SUCCESS | 2 | - |

## Paired increment study

| Case | Status | Reason | Displacement norm | Free residual |
| --- | --- | --- | ---: | ---: |
| PAIRED_TET4_16 | SUCCESS | - | 0.3581038712071078 | 1.147513890079785e-11 |
| PAIRED_TET4_32 | SUCCESS | - | 0.3581038712987276 | 1.1217766819820617e-13 |
| PAIRED_HEX8_16 | SUCCESS | - | 0.3299777959648277 | 7.012726230530734e-10 |
| PAIRED_HEX8_32 | SUCCESS | - | 0.3299777961023633 | 3.336727650714235e-11 |

## Interpretation

- Fixed-step failure records are retained as the historical baseline.
- Adaptive cutback is opt-in and reuses the existing Full Newton driver and line search.
- A failed attempt is discarded before retry; reaching a configured limit fails closed.
- Mesh-conditioning failures are not promoted to successful solves by this report.
