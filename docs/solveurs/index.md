---
doc_id: DOC-SOL-000
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# Solvers and backends

The route, element, formulation and evidence boundary determine which solver
path is supported. Method names are not convergence guarantees; inspect the
residual, conditioning, warnings and final diagnostics for every calculation.
This page describes the bounded solver and backend scope of release 0.2.11.

| Analysis / backend | Status | Scope |
| --- | --- | --- |
| Linear static | `QUALIFIED_BOUNDED` | Direct and iterative sparse routes only within the recorded element-analysis matrix. |
| Modal | Route-dependent | Sparse eigenvalue routes for recorded bounded cases; mass and family scope vary. |
| Rotating modal | `EXPERIMENTAL` | Serial dense generalized QEP with `scipy.linalg.eig(A, B)`; explicit complex spectrum, mass normalization and original-polynomial residuals. Not interchangeable with classical `eigh`/`eigsh`. |
| Campbell | `EXPERIMENTAL` | Multiple bounded rotating solves plus complex-MAC global assignment and subspace-aware tracking. Unresolved matches remain ambiguous, including the high-frequency pair at 100 rad/s. |
| Newmark / harmonic | Route-dependent; selected mixed routes `EXPERIMENTAL_BOUNDED` | Linear analysis and documented timestep/frequency/damping limits only. |
| Linear buckling | Route-dependent | Bounded first-factor cases; no postbuckling or bifurcation claim. |
| Nonlinear Newton | Bounded route evidence | Shared Newton/assembly/state infrastructure in selected material/geometric routes; not a general nonlinear solver claim. |
| Arc-length | Experimental bounded evidence | Specialized correction route; no general limit-point or postbuckling claim. |
| Frictionless contact | `EXPERIMENTAL_BOUNDED` | Bounded penalty node-to-triangle route. |
| Frictional contact | Prior bounded Owner acceptance; current-source formal requalification not established | Narrow serial stick/slip route with search and mesh-sensitivity limits. |
| Structured TET4 PETSc/MPI | Route-dependent historical evidence | Exact recorded workload, host and configuration only. |
| Two-rank PETSc/MPI linear static | Owner-accepted bounded evidence | One-element family cases, replicated input/root-side assembly; no scaling claim. |
| Mixed distributed PETSc/MPI runtime | `NOT_VALIDATED` | No generic mixed or nonlinear distributed runtime claim. |

## Optional PETSc/MPI

PETSc, MPI and SLEPc are optional integrations. The bounded two-rank acceptance
does not establish distributed assembly, strong/weak scaling, nonlinear MPI,
contact, dynamics or cross-family result equivalence. Historical structured
TET4 large-model observations apply only to their exact configurations and
environment. The standard installation uses SciPy and does not require these
external runtimes.

The rotating QEP does not use these optional backends. Its initial method is
`dense_qep`; Campbell uses `complex_mac_hungarian` for tracking, not a new
physical solver. The dense characterization reached 1,000 physical DOFs on
synthetic matrix pencils in the recorded environment, without extrapolation
or a universal capacity promise. See [rotating modal](../mechanics/rotating-modal.md)
and [Campbell](../mechanics/campbell.md) for the full scope.

## Public API

New applications should import from `qf_solver` and use the `qf-solver` CLI.
The `solveur` compatibility namespace and legacy launchers remain during 0.2.x;
the current compatibility plan targets removal of `solveur-ef` for 0.3.0.
See the [API stability contract](../reference/api_stability.md) and
[capability index](../capabilities/index.md).
