---
doc_id: DOC-ANALYSIS-000
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Analyses

This page is a public map of analysis routes. The detailed capability matrix
defines the valid element/material combinations.

| Analysis | Status | Boundary |
| --- | --- | --- |
| Linear static | `QUALIFIED_BOUNDED` | Elastic and bounded material routes recorded in the matrix. |
| Modal | `SUPPORTED_WITH_LIMITATIONS` | Controlled linear eigenvalue cases; WEDGE6 first three modes are separately bounded. |
| Newmark transient | `SUPPORTED_WITH_LIMITATIONS` | Linear cases with documented mass, damping and time-step assumptions. |
| Harmonic | `SUPPORTED_WITH_LIMITATIONS` | Controlled frequency-domain cases; not a general dynamic claim. |
| Linear buckling | `SUPPORTED_WITH_LIMITATIONS` | Bounded first-factor sparse cases; no post-buckling claim. |
| Small-strain J2 | `QUALIFIED_BOUNDED` | TET4, TET10, HEX8 and HEX20 within the recorded constitutive scope. |
| Nonlinear, contact and finite-sliding | `EXPERIMENTAL` or not qualified | Use only the explicitly documented cases and failure contracts. |

## What is not claimed

Finite-kinematic J2, generalized nonlinear production use, contact with a
universal friction law, mixed meshes, generalized dynamics and production
finite-sliding are not qualified by this release.

[Read the capability and evidence matrix](../verification/0_2_7/0_2_7_capability_matrix.md).
