# 026-G08 Linear Buckling V&V Execution

Status: **PASS_WITH_LIMITATIONS**

Source SHA: `6589443e1404a2749ac6c0a9b911f00dd9cb8753`; dirty: `False`

This is a bounded first-mode linearized tangent-buckling campaign. It does not qualify post-buckling, multi-mode behavior, physical validation, or unsupported element routes.

## Aggregate

- Executed cases: 23
- PASS: 21
- Expected failures: 2
- FAIL: 0
- SKIP: 0

## Family coverage

| Family | Single-route | Mesh levels | Final adjacent change | Mesh status |
|---|---:|---:|---:|---|
| TET4 | PASS | 4/4 | 8.904e-03 | PASS |
| TET10 | PASS | 4/4 | 3.177e-02 | PASS |
| HEX8 | PASS | 4/4 | 2.636e-02 | PASS |
| HEX20 | PASS | 4/4 | 1.394e-01 | PASS |

## Requirements

| Requirement | Result | Basis |
|---|---|---|
| G08-001 | PASS | scope and controlled invalid-input cases |
| G08-002 | PASS | preload residual and initial-stress route diagnostics |
| G08-003 | PASS_WITH_LIMITATIONS | TET4 Euler oracle; other-family factors retained as bounded route evidence |
| G08-004 | PASS | normalized first-mode residual and finite mode norm |
| G08-005 | PASS_WITH_LIMITATIONS | four-level studies executed; final adjacent eligibility is family-dependent |
| G08-006 | PASS | four-family same-input repeatability |
| G08-007 | PASS | controlled BC/preload failures are fail-closed |
| G08-008 | PASS_WITH_LIMITATIONS | CalculiX same-model solid correlation; partial external execution is retained explicitly |
| G08-009 | PASS | source SHA, clean state, environment and artifact manifest |

## Repeatability

Same-input first-mode replay was executed for TET4, TET10, HEX8 and HEX20.
All four rows passed within the declared absolute floating-point tolerance
`1e-12`; the largest observed factor difference was `1.421e-14`.

## External correlation

Status: **BLOCKED_EXTERNAL_TOOL**

CalculiX results are a bounded numerical correlation only. A blocked or unavailable external tool is not a PASS.

## Controlled failure cases

- `G08-BUC-FAIL-BC-001`: `EXPECTED_FAILURE` — NumericalConvergenceError
- `G08-BUC-FAIL-PRELOAD-001`: `EXPECTED_FAILURE` — NumericalConvergenceError

## Limitations

- First linearized tangent-instability factor and first mode only.
- TET4 Euler is the only analytical factor oracle in this campaign.
- Mesh final-adjacent <=1% eligibility is not reached by every family; no universal mesh claim is made.
- CalculiX is bounded numerical correlation; Code_Aster is not comparable for this solid eigen-buckling route.
- No post-buckling, collapse, multi-mode or physical-validation claim.
