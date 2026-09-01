---
doc_id: DOC-027-019
revision: 0.1
status: controlled_evidence
applicable_version: 0.2.7a0
reviewer: ""
approver: ""
---

# WP19 - Adversarial Robustness and HEX8 Diagnostic

## Decision

WP19 is `PASS_WITH_LIMITATIONS` for the bounded campaign recorded from
execution source SHA `dc5975b78727d9dca6d0a48b716e60f355b8799f`, starting from
`7f7ffbaf0b3fdda7d3ad31ba95f20a54e4719a53`. The work package does not change
an FEM formulation, promote HEX8R/SRI/B-bar, or change any existing maturity
decision.

## Adversarial robustness

The catalog contains 24 predeclared T1 cases: 10 positive cases and 14
expected-failure cases. The campaign produced 10 `PASS` and 14
`EXPECTED_FAILURE_PASS`, with zero `FAIL` and zero `INVALID_EVIDENCE`. All
cases replayed deterministically. No NaN/Inf was accepted and the failure
paths were fail-closed.

| Failure class | Count |
| --- | ---: |
| `MESH_GEOMETRY_INVALID` | 4 |
| `DUPLICATE_NODE` | 1 |
| `SINGULAR_SYSTEM` | 1 |
| `INVALID_BC_OR_LOAD` | 2 |
| `INACTIVE_DOF` | 1 |
| `INVALID_MATERIAL` | 1 |
| `UNSUPPORTED_LOAD` | 1 |
| `NONFINITE_COORDINATES` | 1 |
| `MALFORMED_GMSH` | 1 |
| `MISSING_PHYSICAL_GROUP` | 1 |

The evidence covers inverted and near-degenerate geometry, wrong ordering,
singular and inconsistent constraints, invalid loads/materials, malformed
Gmsh inputs, noncontiguous IDs, rigid transforms and scale checks. It is a
controlled corpus, not a universal guarantee for arbitrary meshes or input
files.

## HEX8 diagnostic

The diagnostic has nine QF rows: three axial refinement levels, three
slenderness levels and three transverse-resolution levels. It uses the
declared Euler cantilever tip displacement only as a diagnostic reference.
The Euler relative error ranges from 38.737% to 90.650%; the axial refinement
trend improves, while the slenderness sweep remains near 71% and transverse
refinement changes the result from 43.243% to 38.737%.

Six same-mesh QF/C3D8 comparisons ran with CalculiX 2.20 in image
`qf-solver/calculix-nafems13h:2.20`. The maximum full-displacement relative
error is `1.997130986610937e-06` and the maximum tip error is
`7.861618752234401e-07`; all six cases pass the existing one-percent
diagnostic displacement threshold. The deck requests displacement only, so
external reaction and strain-energy comparisons are `NOT_COMPARABLE`.

The evidence supports `LOW_ORDER_LIMITATION` with a secondary
`MESH_DEPENDENCE` diagnostic: QF and compatible C3D8 results agree while both
deviate from the slender-beam Euler reference. This is compatible with a
low-order bending/locking limitation, but locking is not proven by this
campaign. The QF response is classified as a global-bending candidate, not as
an eigenmode. No QF-specific bug was found.

No production HEX8R, selective reduced integration, B-bar or hourglass
variant was evaluated or promoted. The reference TET4, TET10, HEX20 and
WEDGE6 positive rows are replay evidence only and do not transfer maturity.

## Golden replay and provenance

The WP13 golden set was run and replayed through the WP19 wrapper as a current
evidence record: 8 `PASS`, 1 `EXPECTED_FAILURE_PASS`, 9/9 replay matches, and
zero drift. Historical WP13 evidence remains tied to its original source SHA
`94ce10a53e31ad6884383c7ec8ce1761d9533eff` and is not rewritten.

Machine-readable records:

- [`wp19_state.json`](../../../qualification/0_2_7/wp19_state.json)
- [`wp19_cases.json`](../../../qualification/0_2_7/wp19_cases.json)
- [`wp19_robustness_summary.json`](../../../qualification/0_2_7/wp19_runtime/wp19_robustness_summary.json)
- [`wp19_robustness_evidence.json`](../../../qualification/0_2_7/wp19_runtime/wp19_robustness_evidence.json)
- [`wp19_hex8_diagnostic.json`](../../../qualification/0_2_7/wp19_runtime/wp19_hex8_diagnostic.json)
- [`wp19_golden_replay.json`](../../../qualification/0_2_7/wp19_runtime/wp19_golden_replay.json)

WP20 may continue with the existing J2 and external V&V scope. This record
does not claim general HEX8 accuracy, universal adversarial robustness, or a
new numerical formulation.
