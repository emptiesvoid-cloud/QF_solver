---
doc_id: DOC-027-020
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Mesh Quality Contract

WP06 installs a common diagnostic contract for the existing `TET4`, `TET10`,
`HEX8` and `HEX20` families. It is implemented by
`solveur.mesh.quality_contract` and does not replace the element kernels,
their integration rules, or the legacy validator.

## Contract boundary

The contract returns one deterministic `ElementQualityAssessment` per element
and an aggregated `MeshQualityAssessment` for a model. The classification is:

- `VALID`: finite, positively oriented geometry with consistent sampled
  Jacobians and no inherited diagnostic warning;
- `VALID_WITH_WARNING`: calculation remains permitted, with a warning retained
  for a family-specific legacy diagnostic;
- `INVALID`: non-finite, degenerate, non-positive or sign-inconsistent geometry
  that must fail closed before assembly when the preflight path is available.

Each result retains the element ID and family, signed and absolute volume,
sampled Jacobian extrema and ratio, sign consistency, orientation, degeneracy,
edge aspect indicator, distortion indicator, warnings, fatal findings and
metric provenance. A matrix condition number is not inferred: the
`geometric_conditioning_indicator` is explicitly `null` unless a justified
estimator is added in a later contract revision.

## Threshold policy

No universal aspect-ratio or conditioning cutoff is introduced. TET4/TET10
warnings may report existing values from
`solveur.mesh.quality.MeshQualityThresholds`; those values are identified as
legacy diagnostics and are not qualification policies. Absolute legacy volume
cutoffs are not used for the common classification, so dimensionless quality
classification remains invariant under a change of coordinate scale. Existing
solver validation behavior is unchanged.

## Preflight behavior

`preflight_model` now evaluates the common contract before dispatch completes.
An invalid geometry adds a structured `UNSUPPORTED_ROUTE` result with reason
`MESH_GEOMETRY_INVALID` and the fatal findings. `VALID_WITH_WARNING` is
diagnostic-only and does not block calculation. Unknown element capability
remains governed by the WP03 descriptor/preflight contract.

## Controlled cases

The declarative cases in
`qualification/0_2_7/vnv_v2/mesh_quality_cases.json` cover nominal TET4 and
HEX8 geometry, a legacy-warning TET4, and an inverted TET4 expected failure.
The unit corpus additionally covers TET10 and HEX20, duplicate nodes, rigid
translations/rotations, dimensionless scale changes, deterministic
serialization and model preflight.

## WEDGE6 readiness

The future quality contract reserves a six-node prism with two `TRI3` and
three `QUAD4` faces. It will require prism-oriented signed volume, declared
Jacobian sampling, six-node orientation, face-normal orientation,
degeneracy, and prism-compatible distortion metrics. `WEDGE6_IMPLEMENTED` is
`NO`; no active capability or public maturity claim is created by WP06.
