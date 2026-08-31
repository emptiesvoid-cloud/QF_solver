---
doc_id: DOC-027-019
revision: 0.1
status: controlled_candidate
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# WP05 WEDGE6 External Oracle Review Pack

This pack is a preflight for a future WEDGE6 implementation. It contains no
WEDGE6 kernel and no QF WEDGE6 result.

## Controlled inputs

- Contract: `qualification/0_2_7/external_oracles/wedge6/contract.json`
- Node/face map: `qualification/0_2_7/external_oracles/wedge6/mapping.json`
- Planned cases: `qualification/0_2_7/external_oracles/wedge6/specs/cases.json`
- Preflight evidence: `qualification/0_2_7/external_oracles/wedge6/preflight_evidence.json`

## Oracle state

| Oracle | State | Version | Scope of current evidence |
| --- | --- | --- | --- |
| CalculiX C3D6 | `AVAILABLE_LOCAL_ONLY` | 2.20 | affine C3D6 deck validation only |
| Code_Aster PENTA6 | `AVAILABLE_LOCAL_ONLY` | 18.1.0 | affine PENTA6/MECA_PENTA6 deck validation only |

Both images are pinned by digest and both minimal affine decks completed in a
single-thread Docker run. CI availability is not claimed. The outputs are
controlled deck-validation artifacts, not QF correlation evidence.

## Mapping review

The controlled primary order is `[1, 2, 3, 4, 5, 6]`: lower TRI3 then upper
TRI3 in the reference coordinate record. The five topological faces are two
TRI3 faces and three QUAD4 faces. An asymmetric affine fixture validates the
reference coordinates and external deck connectivity; QF kernel replay is not
applicable because WEDGE6 is not implemented. Outward cycles, orientation
checks and positive Jacobian checks are explicit in `mapping.json`; no
automatic repair is permitted. Future adapters must record any permutation
and replay the face pressure checks before comparing results.

## Benchmark plan

The eight planned cases are affine patch, uniaxial, shear, bending, TRI3
pressure, QUAD4 pressure, mesh refinement and distorted prism. Each case
declares geometry, material, load/resultant, observable, units and a
pre-declared comparison policy. Tolerances remain `OWNER_REVIEW_REQUIRED`;
the deck-validation records do not set correlation acceptance thresholds.

Primary observables are displacement, total reaction and strain energy. For an
affine same-mesh case, the predeclared relative candidate is `1e-6` for those
observables, with `PROPOSED_OWNER_REVIEW` status and a near-zero absolute-scale
rule. Non-affine, distorted and refinement cases require a case-specific
Owner-approved tolerance before execution; no value may be retuned after a QF
result. These policies are not derived from observed QF differences. Stress is
secondary and requires identical measure and sampling location. Modal
frequency is reserved for a later, separately qualified route.

## Open questions and stop conditions

- Confirm the QF future WEDGE6 shape-function convention against both external
  decks after the kernel design review.
- Confirm every pressure/traction face sign with an oriented normal test.
- Confirm exact quadrature and stress sampling for the selected versions.
- Stop on an ambiguous permutation, a negative Jacobian, a non-reproducible
  external output or a need for a post-observation tolerance.
- External unavailability or non-comparability is an explicit skip, never a
  PASS.

Sources for the element naming and documented topology are recorded in
`mapping.json`. This pack does not authorize WP07 or implement WEDGE6.
