---
doc_id: DOC-ANALYSIS-000
revision: 1.0
status: controlled
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# Analyses

This page is a public map of analysis routes. The detailed capability matrix
defines the valid element/material combinations.

| Analysis | Status | Boundary |
| --- | --- | --- |
| Linear static | `QUALIFIED_BOUNDED` | Elastic and bounded material routes recorded in the matrix. |
| Modal | `ROUTE_DEPENDENT — see capability index` | Controlled linear eigenvalue cases; WEDGE6 first three modes are separately bounded. |
| Newmark transient | `ROUTE_DEPENDENT — see capability index` | Linear cases with documented mass, damping and time-step assumptions. |
| Harmonic | `ROUTE_DEPENDENT — see capability index` | Controlled frequency-domain cases; not a general dynamic claim. |
| Linear buckling | `ROUTE_DEPENDENT — see capability index` | Bounded first-factor sparse cases; no post-buckling claim. |
| Small-strain J2 | `QUALIFIED_BOUNDED` | TET4, TET10, HEX8 and HEX20 within the recorded constitutive scope. |
| Mixed static and modal | `QUALIFIED_BOUNDED` | Connected conforming serial TET4/WEDGE6/HEX8 benchmark scopes only. |
| Mixed Newmark and harmonic | `EXPERIMENTAL_BOUNDED` | Frozen serial dynamic benchmarks only. |
| Frictionless penalty contact | `EXPERIMENTAL_BOUNDED` | Bounded node-to-triangle small-sliding cases only. |
| Geometric nonlinear | `RESEARCH_ONLY` | Discovery evidence only; no production nonlinear claim. |
| Mixed distributed PETSc/MPI | `NOT_VALIDATED` | Architecture readiness does not constitute runtime qualification. |

## What is not claimed

Finite-kinematic J2, generalized nonlinear production use, contact with a
universal friction law, arbitrary mixed meshes, generalized dynamics and
production finite-sliding are not qualified by this release.

[Read the authoritative 0.2.8 registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/consolidated_registry.json).
For separate mixed workflows and capabilities, use the [central capability index](../capabilities/index.md).
