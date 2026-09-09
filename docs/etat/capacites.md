---
doc_id: DOC-STATE-002
revision: 1.0
status: controlled
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# Capabilities and maturity

This page summarizes the active public scope of QF Solver 0.2.8. A maturity
label applies to the declared combination, not to every possible use of an
element or analysis.

| Scope | Maturity | Qualification boundary |
| --- | --- | --- |
| TET4/TET10/HEX8/HEX20 linear static | `QUALIFIED_BOUNDED` | Recorded elastic materials, meshes, loads and solver routes. |
| TET4/TET10/HEX8/HEX20 small-strain J2 | `QUALIFIED_BOUNDED` | Homogeneous constitutive cases in the active evidence matrix. |
| Modal, Newmark and harmonic | `SUPPORTED_WITH_LIMITATIONS` | Controlled linear cases; mass, damping and element coverage remain route-specific. |
| Linear buckling | `SUPPORTED_WITH_LIMITATIONS` | Bounded sparse first-factor cases. |
| Frictionless contact | `EXPERIMENTAL_BOUNDED` | Penalty, node-to-triangle, small-sliding static/quasi-static cases only. |
| WEDGE6 static | `QUALIFIED_BOUNDED` | Approved isotropic linear-elastic static scope only. |
| WEDGE6 modal | `QUALIFIED_BOUNDED` | First three modes, homogeneous isotropic consistent-mass scope. |
| Mixed static and modal | `QUALIFIED_BOUNDED` | Connected conforming TET4/WEDGE6/HEX8 benchmark scopes only. |
| Mixed translational MPC and multi-material static | `QUALIFIED_BOUNDED` | Separate frozen mixed-workflow scopes only. |
| Mixed Newmark and harmonic | `EXPERIMENTAL_BOUNDED` | Serial linear workflows with the recorded timestep/frequency and damping scopes. |
| Bounded `.inp` subset | `EXPERIMENTAL_BOUNDED` | Provisional C3D4/C3D6/C3D8 linear-static Abaqus/CalculiX subset; not full compatibility. |
| Family-aware mixed HDF5 results | `EXPERIMENTAL_BOUNDED` | Opt-in schema v1.0 storage and selective reads; no restart, XDMF or general scalability claim. |
| HEX8-SRI | `EXPERIMENTAL_BOUNDED` | Separate opt-in linear-static locking-sensitive research capability. |
| PYRAMID5 | `INTERNAL / RESEARCH_ONLY` | No public supported-element claim. |
| MITC4 modal | `EXPERIMENTAL` | Element-analysis record remains experimental. |
| Structured TET4 PETSc/MPI | `SUPPORTED_WITH_LIMITATIONS` | Historical recorded workloads and exact environments only. |
| Mixed distributed PETSc/MPI | `NOT_VALIDATED` | Architecture foundation exists; runtime physical and partition gates fail. |

## Evidence vocabulary

- `IMPLEMENTED`: code exists.
- `TESTED`: an automated or controlled case was executed.
- `VERIFIED`: an invariant, analytical result or quantitative comparison was
  checked.
- `EXTERNALLY_VALIDATED`: a comparable external reference was used.
- `QUALIFIED`: evidence satisfies a declared qualification gate.
- `EXPERIMENTAL`: the route is usable for bounded exploration but is not a
  general qualified capability.

The machine-readable source of truth for the 46 element-analysis combinations
is [`qualification/0_2_8/consolidated_registry.json`](https://github.com/emptiesvoid-cloud/QF_solver/blob/0b356330bdbf63ca6c0406d9a5f816bd75246764/qualification/0_2_8/consolidated_registry.json):
32 `QUALIFIED_BOUNDED`, 14 `EXPERIMENTAL`, 0 `NOT_QUALIFIED`, total 46.
Mixed workflows and the `.inp`, HDF5, contact and HEX8-SRI capabilities are
separate records and are not added to those 46 combinations.

Use the [central capability index](../capabilities/index.md) to navigate from
this registry to the separate mixed-workflow, capability and research records.
