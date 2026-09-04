---
doc_id: DOC-ELEM-000
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Elements

Element availability is separate from qualification. Each combination must be
read with its analysis, material and mesh restrictions.

| Element | Public status | Evidence boundary |
| --- | --- | --- |
| TET4 | `QUALIFIED_BOUNDED` | Linear static, modal/dynamic bounded routes and small-strain J2 as recorded. |
| TET10 | `QUALIFIED_BOUNDED` | Linear and small-strain J2 scopes with route-specific limits. |
| HEX8 | `QUALIFIED_BOUNDED` | Recorded linear and small-strain J2 cases; no HEX8R/SRI/B-bar claim. |
| HEX20 | `QUALIFIED_BOUNDED` | Recorded linear and small-strain J2 cases with bounded route coverage. |
| WEDGE6 | `EXPERIMENTAL` for static; `QUALIFIED_BOUNDED` for modal | Static is a controlled vertical-slice workflow. Modal is limited to the first three modes and its recorded consistent-mass scope. |
| MITC3/MITC4, BEAM2 and discrete entities | `SUPPORTED_WITH_LIMITATIONS` or `EXPERIMENTAL` | Use the individual route evidence; no blanket qualification is implied. |

## Deferred or excluded

WEDGE15 and PYRAMID5 are not supported. Mixed TET/WEDGE/HEX workflows,
HEX8R, SRI, B-bar and hourglass-control production paths remain deferred or
research-only. The element matrix provides the detailed combination-level
status and evidence links.

## Selecting an element

Check geometry quality, orientation, expected deformation, loading and the
required output quantities before solving. Mesh refinement does not repair an
inappropriate kinematic assumption, invalid Jacobian or unsupported material
route.

[Open the detailed 0.2.7 capability matrix](../verification/0_2_7/0_2_7_capability_matrix.md).
