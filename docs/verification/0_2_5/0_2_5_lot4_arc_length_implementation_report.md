---
doc_id: DOC-NL-025-024
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.5a0
reviewer: ""
approver: ""
---

# QF Solver 0.2.5a0 - Lot 4 Arc-Length Implementation Report

**Scope:** implementation work for `025-G04` only
**Base SHA:** `d6ede9d8c3cf01ea6d381ff84441ad2067482095`
**Working tree at report time:** dirty, because this report and the Lot 4 code changes are uncommitted
**Gate decision:** `025-G04 = OPEN`

## 1. Result summary

The existing arc-length path is now exercised by the common finite-kinematic
FEM driver on a true, assembled two-element TET4 model. The continuation
records a signed load-factor path, a displacement control quantity, predictor
signs, branch alignment, arc-length radius, residual histories and rejected
increments. A turning point is crossed: the load-factor increment reverses
sign while the controlled displacement continues on the same displacement
branch.

This is an implementation and internal research result. It is not an external
correlation, a production snap-through qualification, or a closure of G04.

## 2. Implementation changes

| Area | Change | Purpose |
| --- | --- | --- |
| Common FEM driver | `total_lagrangian` and `total_lagrangian_j2` use the shared finite-kinematic assembly route | Keep arc-length on the common sparse nonlinear path |
| Predictor | Previous displacement increment is the primary branch orientation; previous signed load increment is a tie-breaker | Permit a legitimate load-factor reversal at a limit point |
| Control | Optional `arc_length_control_dof` is validated as a free global DDL | Make the tracked branch quantity explicit and reproducible |
| Diagnostics | `NonlinearStep` records predictor sign, branch direction, alignment and arc constraint residual | Make branch decisions auditable |
| Checkpoint | `previous_dlambda` is persisted and restored | Preserve continuation orientation across restart |
| Post-processing | Plain Total-Lagrangian results use the existing finite-kinematic result route | Avoid an element-specific post-processing path |

No new element family, material law or external backend was introduced.

## 3. Controlled FEM benchmark

The benchmark is intentionally small for unit-level execution, but it uses
global sparse assembly and the production `NonlinearStaticSolver` with
`method=arc_length` and `kinematics=total_lagrangian`.

| Quantity | Observed value |
| --- | ---: |
| Elements | 2 TET4 |
| Nodes / global DDL | 5 / 15 |
| Continuation steps | 80 |
| Arc-length radius | 0.02 |
| Control DDL | 14 |
| Load-factor range | `[-0.0373265418, -0.0007272447]` |
| Control-displacement range | `[-0.9419440185, -0.0115649488]` |
| Branch turns | 1 |
| Observed limit-point step | 75 (the reversal occurs between steps 76 and 77) |
| Maximum relative residual | `2.8114e-11` |
| Minimum `det(F)` | `0.4414340033` |
| Rejected increments | 0 |
| Status | `PASS_INTERNAL_RESEARCH` |

Around the observed turning point:

| Step | Load factor | Control displacement | Predictor sign |
| ---: | ---: | ---: | ---: |
| 75 | `-0.0373059776` | `-0.8813023618` | -1 |
| 76 | `-0.0373265418` | `-0.8933769433` | -1 |
| 77 | `-0.0373037970` | `-0.9054750168` | +1 |
| 78 | `-0.0372311272` | `-0.9175995337` | +1 |

The displacement remains monotone along the selected branch while the signed
load-factor increment changes from negative to positive. The benchmark's
classification therefore checks a real branch turn rather than only Newton
convergence.

## 4. Restart evidence

The continuous run writes per-step checkpoints. Restart runs start from the
checkpoint immediately before and immediately after the observed turn and are
compared with the corresponding suffixes of the continuous run.

| Quantity | Observed value |
| --- | ---: |
| Restart checkpoint steps | 75 (before), 76 (after) |
| Continuous steps | 80 |
| Resumed suffix steps | 5 (before), 4 (after) |
| Restart metadata | exact |
| Suffix load-factor maximum error | `0.0` |
| Final displacement relative error | `0.0` |
| Material-state comparison | equal |
| Status | `PASS_INTERNAL_RESEARCH` for both positions |

The restart result demonstrates continuation-state fidelity for this controlled
case. It does not replace adversarial restart/failure coverage or external
solver correlation.

## 5. Adversarial rollback near the turning point

An internal failure injection was applied at continuation step 76, near the
observed limit point, after two Newton corrections. The trial displacement was
mutated and the step was rejected. The common driver then rolled back and
retried the same step with a smaller radius.

| Quantity | Observed value |
| --- | ---: |
| Failure step | 76 |
| Base load factor | `-0.0373059776` |
| Newton corrections before failure | 2 |
| Rejected radius | `0.02` |
| Retry radius | `0.01` |
| Retry state | exact committed state |
| Accepted steps after retry | 80 total, no duplicated step |
| Branch continuity after retry | control displacement strictly continues; branch direction remains `+1` |
| Status | `PASS_INTERNAL_RESEARCH` |

This verifies the transaction boundary and radius cutback in the common FEM
driver. It is a controlled internal failure test, not an external or physical
qualification.

## 6. Tests and checks executed

All commands below were run with the authoritative source tree on `PYTHONPATH`:

| Command | Result |
| --- | --- |
| `pytest tests/unit/test_nonlinear_multielement.py -k 'common_fem_arc_length or finite_kinematic_arc_length' -q` | 5 passed, 27 deselected |
| `pytest tests/unit/test_nonlinear_load_path.py -k 'arc_length' -q` | 9 passed, 16 deselected |
| `pytest tests/unit/test_nonlinear_checkpoint.py -k 'arc_length' -q` | 1 passed, 9 deselected |
| `pytest tests/unit/test_nonlinear_multielement.py -k 'arc_length' -q` | 7 passed, 24 deselected |
| `pytest tests/unit/test_nonlinear_multielement.py -k 'common_fem_arc_length' -q` | 4 passed, 28 deselected |
| `pytest tests/unit/test_schema_validation_paths.py -k 'arc_length' tests/unit/test_analysis_features.py -k 'arc_length' -q` | 3 passed, 33 deselected |
| `pytest tests/unit/test_nonlinear_load_path.py -k 'arc_length' -q` | 9 passed, 16 deselected |
| Restart positions before/after turn | both passed with exact suffix comparison |
| `ruff check` on all modified source and test files | passed |
| `compileall` on all modified Python files | passed |
| `git diff --check` | passed; only Git line-ending warnings |

The pre-change focused baseline was 87 passed on the nonlinear and schema
subset. No full release campaign or coverage campaign was rerun for this
implementation step.

## 7. G04 status and remaining proof

The implementation now provides a common-driver FEM branch-tracking path and
an exact restart check. The following mandatory G04 evidence is still absent:

- a documented published or externally reproducible FEM snap-through model;
- coarse/medium/fine mesh sensitivity for the branch and limit point;
- a qualified production scope beyond the minimal two-element TET4 case;
- Code_Aster external correlation of the complete branch;
- the required failure, radius adaptation and retry evidence on the final
  candidate SHA;
- regenerated final-SHA evidence with `dirty=false` after a clean candidate is
  created.

Accordingly, the correct decision remains:

```text
025-G04 = OPEN
evidence status = PASS_INTERNAL_RESEARCH
release claim = not promoted
```

## 8. Next G04 action

Run the bounded external/reproducible FEM snap-through campaign on a clean
candidate after adding the required mesh levels and failure/restart cases.
Only then should the gate matrix be reconsidered. This report deliberately
does not modify that gate.
