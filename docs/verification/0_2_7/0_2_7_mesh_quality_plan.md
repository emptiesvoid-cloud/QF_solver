---
doc_id: DOC-027-009
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# 0.2.7 Mesh Quality and Distortion Contract

## Principle

Mesh quality is a multidimensional diagnostic. No universal acceptance rule
based only on nominal aspect ratio is proposed. A quality decision must retain
the actual geometry, Jacobian samples, orientation, volume, distortion,
conditioning and relevant response metrics.

## Metrics

For every controlled mesh level, record:

- element count, node count, active DOF and connectivity hash;
- signed Jacobian minimum/maximum and sampling locations;
- volume/area and orientation signs;
- edge/face measures and aspect-ratio indicators;
- distortion/skew/warpage indicators appropriate to the family;
- tangent or stiffness conditioning diagnostic when available;
- displacement, reaction, energy and residual observables relevant to the case;
- solver iterations, convergence status and deterministic replay digest.

## Planned matrix

Each new element campaign should include a regular mesh, orientation changes,
controlled distortion, near-invalid geometry and at least three compatible
levels when a convergence statement is made. A mesh-sensitive result is
reported as a limitation, not hidden by selecting the most favorable level.

## Failure policy

Invalid Jacobian, non-positive volume, unsupported topology and non-finite
metric must be rejected explicitly. A severe conditioning observation may
explain a failure but is not itself a universal cutoff. Retry/cutback must not
turn an invalid model into a silent PASS.

## Owner review items

Numerical thresholds, family-specific quality bands and any use of a
conditioning indicator remain `PROPOSED_OWNER_REVIEW` until justified by
predeclared mechanics, reproducible evidence and an explicit decision.
