---
doc_id: DOC-ELEM-000
revision: 1.0
status: controlled
applicable_version: 0.2.8-development
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
| WEDGE6 | `QUALIFIED_BOUNDED` for static and modal | Static is bounded to Gmsh Prism 6, isotropic small-strain elasticity and the recorded loads/meshes. Modal is limited to its homogeneous consistent-mass scope. |
| MITC3/MITC4, BEAM2 and discrete entities | `SUPPORTED_WITH_LIMITATIONS` or `EXPERIMENTAL` | Use the individual route evidence; no blanket qualification is implied. |

## Deferred or excluded

WEDGE15 is not supported and PYRAMID5 remains an internal research-only kernel.
Connected conforming mixed TET4/WEDGE6/HEX8 workflows exist only for their
separately recorded scopes. HEX8-SRI is a separate `EXPERIMENTAL_BOUNDED`
capability; HEX8R, B-bar and hourglass-control production paths remain deferred.

## Selecting an element

Check geometry quality, orientation, expected deformation, loading and the
required output quantities before solving. Mesh refinement does not repair an
inappropriate kinematic assumption, invalid Jacobian or unsupported material
route.

[Open the authoritative 0.2.8 registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/consolidated_registry.json).
For the cross-registry current status, use the [central capability index](../capabilities/index.md).
