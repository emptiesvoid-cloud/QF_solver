---
doc_id: DOC-SOLVER-GUIDE-001
revision: 2.0
status: controlled_candidate
applicable_version: 0.2.11
reviewer: ""
approver: ""
---

# When should I use QF Solver?

QF Solver is an open-source Python finite-element solver for structural
mechanics and dynamics. It emphasizes inspectable formulations, explicit
solver diagnostics and traceable verification evidence. This 0.2.11 guide
describes the cumulative solver, with route-specific evidence rather than
a blanket maturity claim.

QF Solver can suit controlled analysis, solver development, computational
mechanics research and reproducible FEM studies when the exact route appears
in the [capability index](../capabilities/index.md). It is not certified and
is not a general replacement for Abaqus, ANSYS, Code_Aster or other mature
industrial systems.

## Current route picture

| Domain | Status | Decision boundary |
| --- | --- | --- |
| Linear static TET4/TET10/HEX8/HEX20 | `QUALIFIED_BOUNDED` in the published 0.2.8 registry | Exact materials, meshes, loads and routes only. |
| Small-strain J2, four solid families | `QUALIFIED_BOUNDED` within the recorded published scope | Does not imply finite-strain or arbitrary cyclic behavior. |
| Corotational J2 | Owner-accepted bounded qualification for HEX8 | Large rotations with small local strain; not general finite-strain plasticity. |
| TET10/HEX20 corotational J2 extensions | Owner-accepted bounded extension evidence | Non-scoring evidence; not an all-family qualification. |
| Total-Lagrangian StVK geometric static | WP04 bounded identity/structural audit for TET4 and HEX8 | Audit closure retained limitations and did not update public maturity; Owner/maturity integration is not recorded as a promotion. |
| Frictionless penalty contact | `EXPERIMENTAL_BOUNDED` | Node-to-triangle, bounded small-sliding cases. |
| Frictional contact | Prior Owner acceptance for a narrow serial/direct linear-static route; current-source formal requalification open | Recent area-supported stick/slip evidence is experimental and mesh-sensitive. |
| Arc-length / postbuckling | Bounded experimental continuation evidence | No formal limit-point, bifurcation or general structural postbuckling claim. |
| PETSc/MPI | Route-specific | Bounded recorded linear-static executions only; no general distributed nonlinear claim. |
| General mixed distributed PETSc/MPI | `NOT_VALIDATED` | Historical runtime physical-balance and partition gates failed. |
| Gyroscopic modal analysis | `EXPERIMENTAL` | Straight circular BEAM2 shafts with centered rigid axisymmetric disks; dense serial QEP only. |
| Campbell diagrams | `EXPERIMENTAL` | Explicit speed sweeps and complex-mode tracking within that disk model; ambiguity is retained, including the high-frequency pair at 100 rad/s. |

The internal roadmap score is not a public capability score. Read the
[0.2.11 V&V summary](../verification/0_2_11/README.md) and the inherited
[0.2.10 evidence](../verification/0_2_10/README.md) for the records behind
these labels.

## Good-fit workflows

QF Solver is a reasonable candidate when you need:

- a Python-native, inspectable FEM workflow;
- bounded structural linear static, modal or dynamic routes matching a
  documented record;
- small-strain J2 within its declared family and material scope;
- a controlled experiment with the nonlinear driver, state
  transaction or continuation policies;
- numerical diagnostics and reproducible input/result artifacts;
- exploratory disk-gyroscopic modes or Campbell diagrams within the
  [rotating-modal scope](../mechanics/rotating-modal.md);
- a solver whose implementation, verification and maturity decisions are
  kept distinct.

For a first run, follow the [linear quick start](quickstart.md). The
[nonlinear example](nonlinear-example.md) is a one-element TET4
Total-Lagrangian demonstration: the solver returns a result with
`run_verdict=WARNING` because that experimental route is not promoted to a
general qualified public capability.

## Nonlinear mechanics: what is and is not demonstrated

The development cycle introduced common assembly, Newton, state-transaction
and robustness components for selected routes. Fixed-load material and
geometric analyses use the shared Newton engine; supported continuation paths
share accepted-state/rollback contracts. The augmented arc-length correction
kernel remains specialized, and contact routes do not all participate in the
same lifecycle.

The bounded geometric audit covers homogeneous isotropic Saint-Venant–
Kirchhoff Total-Lagrangian static cases on TET4 and HEX8, with serial dead-load
conditions and a frozen deformation envelope. Its original TET4 mesh failure
is preserved alongside the later bounded closure evidence. The audit did not
itself change the public maturity registry. It does not cover J2 plus
geometry, contact, high-order elements, follower loads, dynamics or
distributed execution.

The HEX8 corotational J2 Owner decision permits large rotations while retaining
a small-local-strain constitutive assumption. The TET10/HEX20 extensions and
multi-family coupled static cases have separate evidence and limitations;
they do not imply general finite-strain plasticity. See [nonlinear
mechanics](../mechanics/nonlinear-overview.md) for definitions and links.

## External comparison and physical validation

The accepted Code_Aster evidence is a same-mesh numerical correlation for
frozen linear-static models and observables. Supplementary mesh-gallery
results have their own contract and status. These comparisons do not establish
physical accuracy, general mesh convergence, nonlinear solver correlation or
an independent second global FEM/Newton implementation. For any safety- or
production-critical use, obtain independent engineering review and
application-specific physical validation.

## Large models and optional backends

PETSc/MPI and SLEPc require native runtimes beyond a plain `pip` installation.
The historical structured-TET4 large-model evidence applies only to recorded
workloads, host and configuration. A separate Owner-accepted two-rank
linear-static study covers bounded one-element cases for TET4, HEX8, TET10
and HEX20 with replicated input and root-side assembly. Neither is a strong-
or weak-scaling claim. Mixed distributed nonlinear mechanics, general GPU
support and equivalent behavior on arbitrary models are not demonstrated.

The core package does not require PETSc, MPI, SLEPc or HDF5. See
[installation](installation.md) and [solver backends](../solveurs/index.md)
before selecting an optional route.

## Poor-fit requirements

Choose a different tool or treat the work as research when the primary need
is:

- general finite-strain or multiplicative J2 plasticity;
- general-purpose nonlinear production analysis;
- robust frictional updated-search or finite-sliding contact, self-contact,
  impact or contact dynamics;
- general nonlinear transient dynamics;
- general rotordynamics, distributed shaft gyroscopy, unbalance response,
  rotor/stator contact or operational critical-speed validation;
- general nonlinear MPI/PETSc, universal HPC scaling or GPU acceleration;
- unrestricted mixed-element behavior, certified workflows or universal
  physical validation.

The [known limitations](../etat/limites.md) page gives the more detailed
technical boundaries.

## Decision checklist

Before relying on a result, match the exact analysis, element, material,
geometry, mesh quality, load/constraint model, solver/backend and requested
observable to an authoritative record. Start with a small reference case;
inspect convergence, reactions and solver diagnostics; preserve the input and
environment; and independently verify the result where appropriate. An
implemented feature, passing unit test or successful demonstration is not by
itself a qualification decision.
