# 0.2.6 G04 execution evidence

## Decision boundary

This is the official execution of the controlled G04 READY selection. It does
not close the global gate, change maturity, or replace missing family-wide and
external evidence. The branch-local record originally left the global gate
unchanged; multi-agent consolidation now records `026-G04` globally as
`PASS_WITH_LIMITATIONS` with the bounded scope and limitations preserved.

The complete machine-readable per-case relation is in
`qualification/0_2_6/g04_execution_evidence.json`. Every row records:

`CASE_ID -> REQUIREMENTS -> ELEMENT FAMILY -> ORACLE STATUS -> POLICY RESULTS -> RESULT`.

## Execution provenance

| Item | Value |
|---|---|
| Source SHA | `5e798e2fd052cb4fe8618d06495a2287f29e01b3` |
| Branch | `agent-b/026-work` |
| Runner | `scripts/run_vnv_026.py --profile FULL --case ...` |
| Registry digest | `d2e5f587ac2d67c3c875782c8558aa7aac60cec09df9f43614319eff1b99ea59` |
| Runner run ID | `vnv026-full-d2e5f587ac2d` |
| READY selection | 65 cases: 56 LIN + 9 SHL |
| PLANNED selection | 4 not materialized; no requirement required them |
| NOT_APPLICABLE selection | 3 mixed SHL records not executed |

## Results

| Result | Count |
|---|---:|
| PASS | 65 |
| WARNING | 0 |
| EXPECTED_FAILURE | 0 |
| FAIL | 0 |
| SKIP (case execution) | 0 |

Resolved element-family counts are BEAM2 2, MITC3 3, MITC4 3, TET4 14,
TET10 8, HEX8 25, HEX20 9 and RBE2 1. No registered DISCRETE element case is
READY in this selection. The RBE2 record is diagnostic-only and is not counted
as DISCRETE G04 evidence. All 65 cases are linear-static dispatches and
completed deterministically.

## Quantitative policy checks

| Policy | Maximum observed | Bound | Status |
|---|---:|---:|---|
| Free relative residual | `2.6741e-14` | `<=1e-8` | PASS |
| Force balance | `1.4873e-12` | `<=1e-10` | PASS |
| Moment balance | `3.2411e-12` | `<=1e-10` | PASS |

The four repeated HEX8 mesh series (`nx=1,2,4,8`) were executed and show
sub-1% final adjacent changes for `max_displacement`. They are retained as
diagnostic series only: the G04 registry did not predeclare the required
`q_ref`, so the Owner-approved mesh policy is not marked PASS retroactively.

## Analytical and external evidence

Twenty cases had an executable predeclared constrained-free-DOF analytical
oracle. They all passed with maximum relative error `0.0` and tolerance
`1e-10`. Thirty cases declare `ANALYTICAL` in the registry but have no
executable oracle configuration; they are reported as
`DECLARED_NOT_EXECUTED`, never as analytical PASS. Fifteen cases have internal
regression/invariant evidence only.

Code_Aster and CalculiX executables were unavailable. Both external
correlations are therefore `SKIP`; no external PASS or non-comparable claim is
made.

## Requirement coverage and limitations

| Requirement | Status | Limitation |
|---|---|---|
| G04-LIN-001 | PASS | All selected routes dispatched and completed. |
| G04-LIN-002 | PARTIAL | Foundation patch/invariant cases ran; family-wide patch coverage is not established. |
| G04-LIN-003 | PASS | Load, reaction, force/moment and residual audits ran for all cases. |
| G04-LIN-004 | PASS_WITH_LIMITATIONS | Isotropic routes pass; orthotropic/laminate records remain deferred from the base claim. |
| G04-LIN-005 | PARTIAL | Four-level HEX8 records ran; q_ref and quality/distortion evidence remain incomplete. |
| G04-LIN-006 | PARTIAL | No invalid-input case was in the READY G04 selection; rejection tests remain separate evidence. |
| G04-LIN-007 | NOT_COVERED | External executables unavailable. |
| G04-LIN-008 | PASS | Source, clean state, registry digest and per-case artifacts recorded. |

The resulting execution status is `PASS_WITH_LIMITATIONS`: the numerical
selection is clean, but the missing analytical configurations, external
correlation, family-wide patch/failure coverage and predeclared mesh reference
prevent an unconditional G04 decision.
