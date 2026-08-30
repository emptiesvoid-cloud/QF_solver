# 026-G11 diagnostics and failure modes bootstrap

G11 remains `NOT_STARTED`. This bootstrap inventories existing mechanisms and
maps historical evidence; it does not requalify another gate or close G11.

## Inventory

| Area | Classification | Current mechanism |
|---|---|---|
| Schema, material, element and load validation | `PUBLIC_FAIL_CLOSED` | `InputValidationError` with field-level messages |
| Mesh, connectivity, geometry and active-DOF checks | `PUBLIC_FAIL_CLOSED` | `MeshValidationError` and deterministic mesh reports |
| Singular linear systems | `PUBLIC_FAIL_CLOSED` | `NumericalConvergenceError` with singular-system message |
| Nonlinear, contact and tangent failures | `INTERNAL_DIAGNOSTIC` plus public failure | `NonlinearFailureReason`, diagnostics payloads and rejection logs |
| Eigenvalue/mode and buckling boundaries | `INTERNAL_DIAGNOSTIC` plus public failure | backend/buckling diagnostics and explicit convergence errors |
| Trial/commit/rollback | `INTERNAL_DIAGNOSTIC` | transaction equality and `rollback_before_retry` evidence |
| Unsupported combinations | `PUBLIC_FAIL_CLOSED` | schema/mesh/route rejection tests |
| Unified cross-route failure envelope | `OWNER_APPROVED_BOUNDED` | focused runner and four native adapters; broad cross-route campaign remains future work |
| Observed uncontrolled failures | none in reviewed evidence | no uncontrolled failure was promoted or hidden |

The reviewed evidence includes the six G04 invalid-input cases, G05/G06
inverted-element expected failures, G06 J2 rollback, historical buckling and
contact diagnostics, and the TL failure/cutback/rollback zoos. These are
mapped as diagnostic evidence only and are not automatically requalified.

## Owner contract review

The machine-readable contract is in
`qualification/0_2_6/g11_requirements.json`. It defines eight requirements:
invalid inputs, singular systems, unsupported combinations, numerical
non-convergence, deterministic diagnostics, rollback/state integrity,
provenance, and no silent fail-open. Each records failure classes, expected
behavior, oracle, evidence references and the Owner review decision `KEEP`.

All eight requirements are retained. The review requires fail-closed behavior,
determinism, no silent NaN/Inf continuation, no silent PASS, exploitable
diagnostics and provenance; state preservation is mandatory whenever mutable
trial state exists.

The transverse failure envelope is `OWNER_APPROVED_BOUNDED` as a qualitative
evidence schema. It requires `FAILURE_CLASS`, `ROUTE`, `EXPECTED_BEHAVIOR`,
`ERROR_TYPE_OR_CODE`, `STATE_PRESERVED`, `DETERMINISTIC`, `NO_NAN_INF`,
`NO_SILENT_PASS` and `EVIDENCE_ID`. Route-native exception types remain
allowed; this schema does not require a common Python exception or imply a
successful qualification result. No numerical threshold is introduced.

Current mapping is in `qualification/0_2_6/g11_evidence_mapping.json`.
The four cases remain planned specifications in
`qualification/0_2_6/g11_adversarial_cases.json`; focused native-route
execution is recorded separately in
`qualification/0_2_6/g11_native_execution_evidence.json`. The execution covers
one singular system, one explicit unsupported combination, one controlled
non-convergence, and one rollback/state-integrity rejection/retry. It is not a
transverse campaign and does not close G11. Any aggregate threshold or
maturity promotion requires a separate Owner review.

The route-neutral runner is `src/solveur/verification/g11_runner.py`, with
route-native adapters in `src/solveur/verification/g11_native_adapters.py` and
focused tests in `tests/unit/test_g11_runner.py` and
`tests/unit/test_g11_native_adapters.py`. It accepts injected route-native
adapters, emits the approved envelope, checks repeatability, NaN/Inf, silent
PASS and state preservation, and archives JSON provenance and diagnostics. It
does not change solver implementations. The four-case focused execution is
recorded; the full G11 campaign remains unexecuted.

The focused cross-route extension is specified in
`qualification/0_2_6/g11_cross_route_cases.json` and recorded in
`qualification/0_2_6/g11_cross_route_execution_evidence.json`. It exercises
one fail-closed case each for `geometric_nonlinear_static`, `modal`,
`linear_buckling` and `linear_static_contact`. These routes remain
`PARTIAL_WITH_RUNTIME_FAILURE_EVIDENCE`; one failure mode per route is not a
qualification of all route capabilities.

## Coverage boundary

The contract is transverse, but evidence remains route-specific. Linear static
input rejection, nonlinear transaction rollback and provenance controls are
the strongest mapped areas. Modal/buckling, contact, geometric-nonlinear route
execution, deterministic cross-route diagnostics and a unified no-silent-PASS
assertion across every route now have focused runtime evidence, but remain
partial pending broader route coverage.
G04, G08, G09, G07/TL and Agent A evidence is reused only at its historical
diagnostic level.

## Boundary

G04, G08, G09, G07/TL and Agent A work are untouched. The contract remains
open and G11 remains `NOT_STARTED`: focused native evidence is recorded, while
the broader adversarial/cross-route campaign and any maturity decision remain
future Owner work.
