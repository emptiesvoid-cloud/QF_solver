---
doc_id: DOC-NL-025-030
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 G04 External Branch Diagnostic

## Decision Boundary

This document resolves the discrepancy between the internal two-element TET4
arc-length path and the historical Code_Aster replay. It does not close
`025-G04`, change any acceptance criterion, or make an arc-length production
claim.

| Provenance item | Value |
|---|---|
| Original QF numerical source | `067859c1db8416758f82bc339cc5b2db4bcbaf63` |
| Historical Owner evidence | `8fdbd500e52a2c23174f66c68e19ecfaa57be0c5` |
| Authoritative corrected-run source | `results/vnv_0_2_5/g04_latest/evidence_manifest.json` |
| Gate status | `OPEN` |
| Contract lowered | `NO` |

## Strict Configuration Comparison

| Parameter | QF Solver | Historical Code_Aster deck | Corrected Code_Aster deck | Impact |
|---|---|---|---|---|
| Geometry | five unperturbed nodes; apex `(0, 0, 0.25)` | same | same | match |
| Connectivity | `N1-N3-N4-N5`, `N2-N4-N3-N5` | same | same | match |
| Material | `E=100`, `nu=0.3` | same | same | match in the bounded elastic case |
| Kinematics | Total-Lagrangian, Green-Lagrange / second Piola | `ELAS`, `GREEN_LAGRANGE` | same | bounded formulation match |
| Supports | N1/N2 fixed; crown `UY=0` | same | same | match |
| Physical load | QF reference `+1/3` with target factor `-1`: downward | `FZ=+1/3`: upward | `FZ=-1/3`: downward | historical mismatch resolved |
| Control output | apex node N5 `UZ` (global DOF 14) | mean `CROWN/DZ` | `APEX/DZ` | historical mismatch resolved |
| Continuation window | 80 QF steps through `|u_apex|=0.94194` | `0..100`, 800 intervals | `0..0.96`, 160 intervals | corrected window covers the QF branch |
| Arc constraint | QF augmented displacement/load norm | Code_Aster `LONG_ARC` displacement control | same | compare equilibrium points by apex displacement |

The values are a dimensionless/scaled numerical benchmark. No physical unit
validation is claimed.

## Diagnostic Result

The corrected Code_Aster run gives one turn at the same branch location as QF
Solver. Interpolating Code_Aster's reaction-derived load factor on QF's
absolute apex displacement gives:

| Metric | Result |
|---|---:|
| QF turning point | `u=0.8933769433`, `lambda=-0.03732654177` |
| Code_Aster turning point | `u=0.8940000000`, `lambda=-0.03732647828` |
| Absolute turning-load difference | `6.3485e-08` |
| Maximum branch load-factor difference | `4.8719e-07` |
| RMS branch load-factor difference | `2.0730e-07` |
| Peak-normalized maximum difference | `1.3052e-05` |

QF's reduced tangent is symmetric to numerical precision. Its smallest
eigenvalue crosses from `+1.1649e-03` at step 75 to `-3.3334e-06` at step 76,
then stays negative on the post-limit branch. The reassembled free residual
near the turn is below `5e-13`, and `det(F)` remains positive (`>=0.4414` over
the recorded path). This supports a physical limit-point interpretation within
the bounded two-element model.

## Classification

```text
DIAGNOSIS = B - CODE_ASTER_PATH_FOLLOWING_CONFIGURATION
ROOT CAUSE = opposite physical load direction plus unmatched control observable
             and continuation window in the historical deck
QF_MODEL_VALID = YES, bounded numerical correlation only
CODE_ASTER_MODEL_VALID = YES after deck correction
PUBLISHED_REFERENCE = NOT_IDENTIFIED
CODE_CHANGE_REQUIRED = NO
G04 STATUS = OPEN
```

The exact two-element configuration has no linked published FEM source in the
repository, and no exact public reference was identified for it. The Code_Aster
manual supports `LONG_ARC` as a continuation method but is not a published
reference for this particular geometry or branch.

## Remaining G04 Blockers

1. Link and reproduce an exact published FEM snap-through branch reference, or
   formally replace this custom benchmark through the requirements process.
2. Run the required coarse/medium/fine/refined branch study only after the
   benchmark reference is approved.

No mesh study was run during this diagnostic. The corrected Code_Aster branch
removes the historical external-deviation blocker but does not close the gate.
