---
doc_id: DOC-SOL-000
revision: 1.0
status: controlled
applicable_version: 0.2.7
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
| Modal | `SUPPORTED_WITH_LIMITATIONS` | Sparse eigenvalue routes for the recorded bounded cases. |
| Newmark / harmonic | `SUPPORTED_WITH_LIMITATIONS` | Controlled linear routes with documented mass and damping assumptions. |
| Linear buckling | `SUPPORTED_WITH_LIMITATIONS` | Bounded sparse tangent-instability cases. |
| Nonlinear and contact | `EXPERIMENTAL` or bounded | Newton, load-control, Arc-Length and contact paths remain route-specific. |
| Large model | `SUPPORTED_WITH_LIMITATIONS` | PETSc/MPI for recorded structured TET4 workloads; SciPy is for small or intermediate cases. |

## Optional PETSc/MPI route

PETSc and MPI are optional integrations. The large-model route uses a
distributed AIJ matrix with structured diagonal/off-diagonal preallocation on
the recorded qualification path. Its 1M, 3M, 5M and bounded 10M results apply
only to the declared workloads, host and configuration. They are not a general
HPC or GPU claim.

## Public API

New applications should import from `qf_solver` and use the documented CLI
`qf-solver`. The compatibility namespace `solveur` and legacy entry points are
retained for existing integrations; see the [API stability contract](../reference/api_stability.md).
