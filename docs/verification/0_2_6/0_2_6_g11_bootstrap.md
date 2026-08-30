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
| Unified cross-route failure envelope | `MISSING` | future G11 campaign required |
| Observed uncontrolled failures | none in reviewed evidence | no uncontrolled failure was promoted or hidden |

The reviewed evidence includes the six G04 invalid-input cases, G05/G06
inverted-element expected failures, G06 J2 rollback, historical buckling and
contact diagnostics, and the TL failure/cutback/rollback zoos. These are
mapped as diagnostic evidence only and are not automatically requalified.

## Candidate contract

The machine-readable contract is in
`qualification/0_2_6/g11_requirements.json`. It defines eight requirements:
invalid inputs, singular systems, unsupported combinations, numerical
non-convergence, deterministic diagnostics, rollback/state integrity,
provenance, and no silent fail-open. Each records failure classes, expected
behavior, oracle and evidence references.

Current mapping is in `qualification/0_2_6/g11_evidence_mapping.json`.
Four adversarial factory cases remain `PLANNED`; no new policy threshold is
introduced. Any aggregate threshold or maturity promotion requires a separate
Owner review.

## Boundary

G04, G08, G09, G07/TL and Agent A work are untouched. G11 execution is not
ready until the cross-route failure schema, planned adversarial cases and
no-silent-PASS assertions are defined and approved.
