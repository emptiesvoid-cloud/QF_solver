---
doc_id: DOC-SOLVER-COMP-003
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---
# QF Solver vs scikit-fem

QF Solver and scikit-fem are both Python finite-element projects, but they
operate at different abstraction levels.

scikit-fem is primarily a lightweight finite-element assembly library.

QF Solver is primarily a structural-mechanics solver with predefined analysis
routes, engineering diagnostics and explicit verification states.

The central choice is therefore often:

> Do I want a library for building a finite-element formulation, or a
> structural solver containing predefined engineering workflows?

Last reviewed: 2026-09-06.

---

## Short answer

### Choose QF Solver if

You want:

- a ready structural FEM solver architecture;
- predefined structural-analysis routes;
- engineering diagnostics;
- explicit capability maturity;
- reproducible verification evidence;
- selected nonlinear and structural-dynamic functionality;
- optional PETSc/MPI large-model solving.

### Choose scikit-fem if

You want:

- a lightweight pure-Python FEM library;
- direct weak-form implementation;
- sparse matrix and vector assembly;
- compact research code;
- teaching or numerical-method experimentation;
- control over the mathematical formulation with minimal solver
  infrastructure.

---

# High-level comparison

| Criterion | QF Solver | scikit-fem |
| --- | --- | --- |
| Main purpose | Structural FEM solver | FEM assembly library |
| Language/workflow | Python-native | Pure Python |
| Primary abstraction | Engineering models and analyses | Forms, basis functions and assembly |
| Structural mechanics focus | Strong | User-defined |
| Custom weak forms | Possible but not central | Core strength |
| Sparse assembly | Internal solver infrastructure | Core public abstraction |
| Built-in engineering routes | Yes | Usually assembled by the user |
| Dynamics | Documented QF routes | User formulation/application dependent |
| Nonlinear engineering mechanics | Selected bounded capabilities | User/application dependent |
| Explicit capability registry | Yes | No equivalent QF-style registry |
| PETSc/MPI | Selected documented routes | Not the primary project focus |
| Best fit | Structural solving and solver development | FEM mathematics, research and prototyping |

---

# The main conceptual difference

The two projects answer different questions.

scikit-fem asks approximately:

> How can I express and assemble this finite-element formulation efficiently
> in Python?

QF Solver asks approximately:

> How can I run, inspect and qualify this structural finite-element analysis?

That distinction affects nearly every part of the workflow.

---

# scikit-fem's assembly model

scikit-fem is centered around finite-element assembly.

The user typically:

1. creates a mesh;
2. chooses an element;
3. creates a basis;
4. defines bilinear or linear forms;
5. assembles sparse matrices and vectors;
6. applies boundary conditions;
7. solves the resulting algebraic problem.

This architecture is compact and particularly attractive for users who want to
work close to the mathematical formulation.

Its official documentation describes the central purpose of the library as
transforming bilinear forms into sparse matrices and linear forms into
vectors.

---

# QF Solver's engineering model

QF Solver exposes a higher-level solver workflow.

Rather than requiring every user to rebuild the governing FEM procedure from
forms, QF Solver contains defined analysis routes.

The project aims to connect:

- input model;
- element implementation;
- assembly;
- solver;
- diagnostics;
- result;
- verification evidence;
- capability maturity.

This is closer to the architecture expected from a structural-engineering
solver.

---

# Mesh and element experimentation

scikit-fem supports common mesh types including:

- one-dimensional meshes;
- triangles;
- quadrilaterals;
- tetrahedra;
- hexahedra.

The library is therefore well suited to experimentation with basis functions
and finite-element formulations.

QF Solver also contains multiple element families, but its public claims are
restricted by element-analysis combinations.

For QF Solver 0.2.7, major bounded solid routes involve:

- TET4;
- TET10;
- HEX8;
- HEX20.

Additional families can have different maturity states.

---

# Structural mechanics

Structural mechanics is one of the areas where the project philosophy differs
most clearly.

## QF Solver

The solver already contains structural concepts and analysis routes.

Depending on capability scope, these include:

- linear static analysis;
- modal extraction;
- time integration;
- harmonic analysis;
- buckling;
- selected plasticity;
- bounded contact.

The user is therefore operating inside an engineering solver architecture.

## scikit-fem

Structural mechanics can be implemented using scikit-fem, but the framework is
more general.

The user generally defines the appropriate mathematical forms and assembles
the problem.

This gives greater formulation freedom at the cost of requiring more of the
solver logic to be developed at application level.

---

# Teaching and research

scikit-fem is particularly attractive for teaching FEM because its core
workflow maps closely onto the mathematical formulation:

- mesh;
- finite-element space;
- weak form;
- assembly;
- boundary conditions;
- solution.

It is also attractive for research prototypes because a new weak form can be
implemented without adopting a large engineering-solver architecture.

QF Solver is more relevant when the subject of the research includes:

- structural solver architecture;
- element implementation;
- diagnostics;
- solver robustness;
- verification;
- qualification;
- large sparse execution.

---

# Verification philosophy

QF Solver explicitly distinguishes between capability states.

For example, the project can describe a route as:

- experimental;
- supported with limitations;
- qualified within a bounded scope.

This public capability classification is one of the defining parts of QF
Solver.

scikit-fem does not try to expose the same engineering qualification model.

That is appropriate for its role as a numerical library.

Users building an engineering application with scikit-fem remain responsible
for validating the complete application they construct.

---

# Solver infrastructure

scikit-fem deliberately remains relatively lightweight.

Its primary contribution is the finite-element discretization and assembly
layer.

This makes it easy to combine with the wider Python scientific ecosystem.

QF Solver contains more solver-specific infrastructure, including:

- engineering model checking;
- structural-analysis dispatch;
- diagnostics;
- result management;
- verification infrastructure;
- optional PETSc/MPI routes.

This additional infrastructure is useful for solver development but also makes
QF Solver a larger and more opinionated project.

---

# Large models

QF Solver has published bounded large-model evidence using selected PETSc/MPI
routes.

Recorded QF Solver 0.2.7 structured TET4 workloads extend into multi-million
DOF ranges.

These measurements are not a general HPC claim.

scikit-fem is primarily documented as a finite-element assembly library rather
than an HPC structural solver platform.

Users needing large distributed simulations should evaluate the entire
application architecture rather than assuming that either project's Python
interface alone determines scalability.

---

# Ease of modification

## scikit-fem

For a researcher who wants to change the mathematical formulation quickly,
scikit-fem is often simpler.

A new weak form can remain small and explicit.

## QF Solver

For a developer who wants to integrate a new capability into a complete
engineering solver, QF Solver can provide more surrounding infrastructure:

- dispatch;
- diagnostics;
- tests;
- qualification;
- documentation;
- regression evidence.

The cost is that a new feature needs to fit into a larger solver contract.

---

# When QF Solver is the better choice

Prefer QF Solver when:

- you want a structural solver rather than an FEM assembly toolkit;
- analysis routes should already exist;
- structural dynamics matter;
- solver diagnostics matter;
- you want explicit verification status;
- the solver itself is being developed;
- large sparse PETSc/MPI structural workflows are relevant.

---

# When scikit-fem is the better choice

Prefer scikit-fem when:

- you want to implement the weak form yourself;
- you want minimal infrastructure;
- you are teaching FEM;
- you are prototyping a mathematical formulation;
- you are studying discretization techniques;
- your application does not need a full engineering solver architecture;
- direct manipulation of finite-element forms is more important than
  predefined solver routes.

---

# Which is easier?

For a small custom PDE or teaching example, scikit-fem will often be simpler.

For a user who wants to run an already-supported structural-analysis route,
QF Solver can be simpler because more of the solver workflow is already
provided.

The answer therefore depends on whether "easy" means:

- easy to define a mathematical FEM formulation; or
- easy to execute a predefined structural-engineering analysis.

---

# Conclusion

Choose **scikit-fem** when the primary requirement is a lightweight and direct
Python interface for finite-element assembly and mathematical formulation.

Choose **QF Solver** when the primary requirement is a structural FEM solver
with defined engineering routes, diagnostics and explicit verification
maturity.

scikit-fem is the cleaner foundation for many custom weak-form experiments.

QF Solver is the more specialized foundation for structural solver
engineering.

---

# Related pages

- [Python FEM solvers](python-fem-solvers.md)
- [QF Solver vs SfePy](qf-vs-sfepy.md)
- [QF Solver vs CalculiX](qf-vs-calculix.md)
- [QF Solver vs Code_Aster](qf-vs-code-aster.md)
- [When should I use QF Solver?](../getting-started/when-to-use-qf-solver.md)

## External references

- scikit-fem documentation: https://scikit-fem.readthedocs.io/
- scikit-fem source repository: https://github.com/kinnala/scikit-fem

External product information reviewed: 2026-09-06.
