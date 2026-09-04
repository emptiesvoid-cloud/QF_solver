---
doc_id: DOC-STATE-002
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Capabilities and maturity

This page summarizes the active public scope of QF Solver 0.2.7. A maturity
label applies to the declared combination, not to every possible use of an
element or analysis.

| Scope | Maturity | Qualification boundary |
| --- | --- | --- |
| TET4/TET10/HEX8/HEX20 linear static | `QUALIFIED_BOUNDED` | Recorded elastic materials, meshes, loads and solver routes. |
| TET4/TET10/HEX8/HEX20 small-strain J2 | `QUALIFIED_BOUNDED` | Homogeneous constitutive cases in the active evidence matrix. |
| Modal, Newmark and harmonic | `SUPPORTED_WITH_LIMITATIONS` | Controlled linear cases; mass, damping and element coverage remain route-specific. |
| Linear buckling | `SUPPORTED_WITH_LIMITATIONS` | Bounded sparse first-factor cases. |
| Frictionless contact | `SUPPORTED_WITH_LIMITATIONS` | Bounded node-to-triangle contact cases only. |
| WEDGE6 static | `EXPERIMENTAL` | Small-strain elastic vertical-slice workflow. |
| WEDGE6 modal | `QUALIFIED_BOUNDED` | First three modes, homogeneous isotropic consistent-mass scope. |
| Large-model PETSc/MPI | `SUPPORTED_WITH_LIMITATIONS` | Structured TET4 workloads on recorded configurations. |

## Evidence vocabulary

- `IMPLEMENTED`: code exists.
- `TESTED`: an automated or controlled case was executed.
- `VERIFIED`: an invariant, analytical result or quantitative comparison was
  checked.
- `EXTERNALLY_VALIDATED`: a comparable external reference was used.
- `QUALIFIED`: evidence satisfies a declared qualification gate.
- `EXPERIMENTAL`: the route is usable for bounded exploration but is not a
  general qualified capability.

The machine-readable source of truth is
[`qualification/0_2_7/capability_registry_v2.json`](../../qualification/0_2_7/capability_registry_v2.json).
The readable combination matrix is
[`0.2.7 capability matrix`](../verification/0_2_7/0_2_7_capability_matrix.md).
