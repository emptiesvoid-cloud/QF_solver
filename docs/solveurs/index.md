---
doc_id: DOC-SOL-000
revision: 1.0
status: controlled
applicable_version: 0.2.8-development
reviewer: ""
approver: ""
---

# Solvers and backends

The route and element combination determine which backend is appropriate.
Method names alone are not convergence guarantees; inspect the residual,
conditioning and final diagnostics for every calculation.

| Analysis | Public status | Available methods or backend |
| --- | --- | --- |
| Linear static | `QUALIFIED_BOUNDED` | Direct and iterative sparse routes within the element matrix. |
| Modal | `ROUTE_DEPENDENT — see capability index` | Sparse eigenvalue routes for the recorded bounded cases. |
| Newmark / harmonic | `ROUTE_DEPENDENT — see capability index` | Controlled linear routes; mixed TET4/WEDGE6/HEX8 variants are separate `EXPERIMENTAL_BOUNDED` workflows. |
| Linear buckling | `ROUTE_DEPENDENT — see capability index` | Bounded sparse tangent-instability cases. |
| Nonlinear and contact | `ROUTE_DEPENDENT — see capability index` | Newton, load-control, Arc-Length and contact paths remain route-specific. |
| Structured TET4 large model | `ROUTE_DEPENDENT — see capability index` | PETSc/MPI for recorded historical workloads; SciPy is for small or intermediate cases. |
| Mixed distributed PETSc/MPI | `NOT_VALIDATED` | Architecture foundation only; physical balance and three-rank runtime gates remain failed. |

## Optional PETSc/MPI route

PETSc and MPI are optional integrations. The large-model route uses a
distributed AIJ matrix with structured diagonal/off-diagonal preallocation on
the recorded qualification path. Its 1M, 3M, 5M and bounded 10M results apply
only to the declared workloads, host and configuration. They are not a general
HPC or GPU claim. It does not qualify the newer generic mixed distributed
runtime, which remains `NOT_VALIDATED`.

## Public API

New applications should import from `qf_solver` and use the documented CLI
`qf-solver`. The compatibility namespace `solveur` and legacy entry points are
retained for existing integrations; see the [API stability contract](../reference/api_stability.md).
