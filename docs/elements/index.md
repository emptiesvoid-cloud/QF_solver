---
doc_id: DOC-ELEM-000
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# Elements

Element support and maturity are separate. The published 0.2.8 consolidated
registry remains authoritative for its 46 recorded element-analysis
combinations; 0.2.10 nonlinear evidence and its limitations are reported
separately and remain relevant in 0.2.11.

| Element family | 0.2.8 bounded scope | 0.2.10 nonlinear evidence / limitation |
| --- | --- | --- |
| TET4 | Recorded linear and small-strain J2 routes | Selected Total-Lagrangian StVK static audit (`GO_WITH_LIMITATIONS`, no maturity promotion); selected coupled static evidence. |
| TET10 | Recorded linear and small-strain J2 routes | Bounded extension/coupled evidence; no blanket geometric or corotational-J2 promotion. |
| HEX8 | Recorded linear and small-strain J2 routes | Corotational J2 has bounded Owner acceptance; selected Total-Lagrangian audit; coupled evidence. Each scope has separate limitations. |
| HEX20 | Recorded linear and small-strain J2 routes | Bounded extension/coupled evidence; not a general finite-strain or contact qualification. |
| WEDGE6 | Bounded static and modal scopes | No nonlinear maturity claim from the cited development-cycle evidence. |
| MITC3/MITC4, BEAM2 and discrete entities | Route-dependent; see their records | Do not infer nonlinear support from linear availability. |
| WEDGE15 | Not supported | No claim. |
| PYRAMID5 | Internal / `RESEARCH_ONLY` | Not a public supported-element claim. |

HEX8-SRI is a separate experimental capability; it is not a blanket claim for
HEX8R, B-bar, or hourglass-control formulations. Higher-order families may
have narrower nonlinear evidence than their linear registry coverage.

The 0.2.11 rotating extension uses only a straight, collinear BEAM2 shaft
with circular isotropic sections and centered rigid axisymmetric disks.
It is `EXPERIMENTAL`; legacy beam or shell support does not extend that
scope to shells, solid rotor meshes, eccentric disks or distributed shaft
gyroscopy. Each disk owns its mass and gyroscopic term; duplicate generic
disk mass at the same node is rejected. See [rotating modal](../mechanics/rotating-modal.md)
and [Campbell](../mechanics/campbell.md).

Before selecting an element, check geometry quality, orientation, expected
deformation, loading, material model, and required output. Refinement cannot
repair an invalid Jacobian or an unsupported kinematic/constitutive route.

See the [analysis map](../analyses/index.md),
[capability matrix](../capabilities/index.md), and
[known limitations](../etat/limites.md). The original
[0.2.8 consolidated registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json)
is not silently re-scored by this page.
