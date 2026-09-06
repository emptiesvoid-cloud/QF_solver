---
doc_id: DOC-SOLVER-BENCH-001
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# QF Solver benchmarks and reproducibility

QF Solver publishes bounded numerical and large-model evidence for selected
finite-element routes.

This page is a public summary of reproducible measurements. It is not a claim
that QF Solver has the same performance for arbitrary meshes, elements,
materials, solver settings or hardware.

## Large-model evidence

The strongest QF Solver 0.2.7 large-model evidence currently concerns
structured TET4 linear-static models using selected PETSc/MPI routes.

| Model size | Recorded result | Scope |
| ---: | --- | --- |
| 1,029,000 DOF | Two stable PETSc replays | Structured TET4, recorded environment |
| 3,000,000 DOF | Two Silver replays plus bounded Gold Compute evidence | Frozen PETSc/CG/GAMG route |
| 5,012,640 DOF | Two Silver replays | 9,773,946 TET4, recorded PETSc/MPI environment |
| 10M scale | Bounded C3 evidence only | Not presented as a general 10M performance claim |

These results do not establish universal scalability.

## 5M Silver result

The 5M Silver campaign recorded:

- 5,012,640 degrees of freedom;
- 9,773,946 TET4 elements;
- 1,243 solver iterations;
- free residual near `9.85e-11`;
- equilibrium error near `1.39e-9`;
- energy error below `2e-14`;
- two recorded runtimes of approximately 4,428 s and 4,379 s.

The measurements describe this specific workload and environment. They are not
a general performance guarantee.

## Earlier scaling evidence

QF Solver also contains controlled scaling experiments for smaller structured
TET4 models.

The historical matrix-free campaign includes completed iterative solves through
750,141 DOF and a bounded 1,029,000-DOF readiness attempt.

That campaign records:

- model topology;
- wall time;
- memory consumption;
- residuals;
- sparse matrix information;
- environment metadata;
- deterministic replay information.

The historical campaign should not be confused with the later PETSc/MPI
qualification evidence.

## What is reproducible?

QF Solver attempts to preserve enough information to distinguish:

- the model being solved;
- element and material formulation;
- solver backend;
- convergence tolerance;
- execution environment;
- residual and equilibrium checks;
- replay consistency;
- resource-limited and solver-limited cases.

Failed or resource-limited attempts are not converted into successful results.

## Reproduction and evidence

Detailed evidence for QF Solver 0.2.7 is available in:

- [0.2.7 verification overview](../verification/0_2_7/README.md)
- [Large-scale readiness evidence](../verification/0_2_7/0_2_7_large_scale_readiness.md)
- [0.2.7 gate matrix](../verification/0_2_7/0_2_7_gate_matrix.md)
- [Numerical and performance regression audit](../verification/0_2_7/0_2_7_f6_numerical_performance_regression_audit.md)

Machine-readable qualification records are retained in the repository under:

`qualification/0_2_7/`

## Interpretation

The published measurements should be used to answer:

> Has this particular QF Solver route been exercised reproducibly at this scale?

They should not be used to claim:

> QF Solver will solve every finite-element problem of this size.

Performance comparisons with other FEM solvers require equivalent models,
elements, formulations, tolerances, solver configurations and hardware.
