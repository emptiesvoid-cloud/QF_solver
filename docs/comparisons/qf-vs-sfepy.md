# QF Solver vs SfePy

QF Solver and SfePy are both open-source finite-element tools that can be used
from Python, but they are designed around different priorities.

QF Solver is primarily a structural-mechanics finite-element solver with
explicit engineering solver routes, numerical diagnostics and a
capability-qualification framework.

SfePy is a broader Python framework for solving systems of coupled partial
differential equations using the finite-element method.

Neither project is universally better. The appropriate choice depends on
whether the main objective is structural solver engineering or flexible PDE
formulation.

Last reviewed: 2026-09-06.

---

## Short answer

### Choose QF Solver if

Your main objective is structural mechanics and you want:

- a Python-native structural FEM workflow;
- predefined engineering-analysis routes;
- explicit numerical diagnostics;
- inspectable finite-element formulations;
- reproducible verification evidence;
- explicit capability maturity;
- selected PETSc/MPI large-model routes;
- a solver-development platform where implementation and qualification are
  closely connected.

### Choose SfePy if

Your main objective is to formulate and solve general PDE systems and you want:

- a broad finite-element PDE framework;
- support for problems in 1D, 2D and 3D;
- coupled PDE formulations;
- a large collection of predefined weak-form terms;
- a Python framework for custom scientific applications;
- both script-level and solver-style workflows.

---

# High-level comparison

| Criterion | QF Solver | SfePy |
| --- | --- | --- |
| Main orientation | Structural mechanics FEM solver | General FEM/PDE framework |
| Python integration | Native | Native |
| Primary abstraction | Engineering analysis and solver routes | PDE terms and equations |
| Structural mechanics focus | Strong | One application domain among several |
| General PDE formulation | Limited compared with SfePy | Strong |
| 1D/2D/3D PDE framework | Not the central abstraction | Yes |
| Built-in engineering routes | Strong focus | Available through problem definitions |
| Solver transparency | Strong | Strong |
| Explicit capability maturity registry | Yes | No equivalent QF-style registry |
| Verification philosophy | Release-scoped and capability-scoped evidence | Examples, tests and scientific use |
| PETSc/MPI | Selected documented QF routes | Parallel solving exists but is documented as work in progress |
| Nonlinear mechanics | Selected and bounded | Depends on available terms and problem formulation |
| Best fit | Structural solver development and controlled engineering workflows | General PDE research and custom FEM applications |

The table describes project orientation. It does not imply equivalent
feature-by-feature validation.

---

# Design philosophy

## QF Solver

QF Solver is organized around the idea that an implemented FEM feature should
not automatically become a general engineering claim.

Its public documentation distinguishes concepts such as:

- implementation;
- testing;
- verification;
- external correlation;
- qualification;
- experimental capability.

The solver therefore places significant emphasis on the exact combination of:

- element;
- material;
- analysis;
- loading;
- mesh;
- numerical route;
- solver backend.

This approach is useful when numerical traceability is an important part of
the engineering workflow.

## SfePy

SfePy is built around a more general PDE-oriented philosophy.

A problem is assembled from mathematical terms describing the weak form of
the governing equations.

SfePy can be used in two major ways:

1. as a PDE solver;
2. as a Python package for building custom FEM applications.

This makes SfePy particularly flexible when the mathematical model itself is
the main object being developed.

---

# Python workflow

Both projects are strongly Python-oriented.

## QF Solver

QF Solver provides a public Python namespace and engineering-level operations
for loading, checking and solving models.

A typical workflow is based around an explicitly defined structural model and
analysis route.

The objective is to give the user a recognizable solver workflow while
keeping the implementation inspectable.

## SfePy

SfePy gives the user direct access to objects representing:

- meshes;
- domains;
- regions;
- fields;
- variables;
- materials;
- equations;
- solvers.

The user can therefore construct PDE systems directly in Python.

This provides a high degree of flexibility but requires the user to understand
the mathematical formulation of the problem.

---

# Structural mechanics

## QF Solver

Structural mechanics is the central application domain.

QF Solver 0.2.7 includes documented routes involving solid elements such as:

- TET4;
- TET10;
- HEX8;
- HEX20.

Depending on the exact documented scope, analysis capabilities include:

- linear statics;
- modal analysis;
- Newmark dynamics;
- harmonic response;
- linear buckling;
- small-strain J2 plasticity;
- bounded frictionless contact.

Some additional shell, beam, discrete and wedge routes exist with different
maturity levels.

## SfePy

SfePy includes structural-mechanics examples and formulations, including
linear elasticity, but structural mechanics is only part of its broader PDE
scope.

Its architecture is particularly useful when mechanics must be combined with
other PDE formulations or when the user wants to define the governing
equations directly.

---

# General PDE capability

This is one of the clearest differences between the projects.

SfePy is explicitly designed for systems of coupled PDEs.

QF Solver is not currently intended to be a general-purpose PDE framework.

For problems where the primary task is defining custom weak forms or coupling
different physical PDEs, SfePy is generally the more natural starting point.

For a structural-engineering workflow where the analysis route itself should
already exist as part of the solver architecture, QF Solver may be more
appropriate.

---

# Verification and numerical evidence

## QF Solver

QF Solver uses an explicit capability and verification structure.

A feature can be present while remaining:

- experimental;
- supported with limitations;
- qualified only inside a bounded scope.

This is intended to prevent capability inflation.

The project also publishes release-specific numerical evidence and
machine-readable qualification information.

## SfePy

SfePy is a substantially more established scientific project and provides a
large collection of examples, tutorials and scientific applications.

Its validation and maturity model is not organized around the same
QF-specific public capability-state vocabulary.

The difference is therefore primarily one of documentation and release
philosophy rather than a statement that one project's results are inherently
more reliable.

---

# Parallel and large-model solving

QF Solver includes optional PETSc/MPI infrastructure for selected documented
large sparse structural workloads.

QF Solver 0.2.7 contains recorded evidence on structured TET4 workloads
reaching approximately:

- 1 million DOFs;
- 3 million DOFs;
- 5 million DOFs;
- 10 million DOFs.

These are bounded recorded workloads and not a universal scalability claim.

SfePy also documents parallel problem solving, but its current documentation
describes this area as work in progress.

Users selecting either project for HPC should therefore evaluate the exact
problem, solver backend, mesh and hardware rather than relying on the project
name alone.

---

# Extensibility

## QF Solver

QF Solver is attractive when the extension is itself part of an engineering
solver.

Examples include:

- a new structural element;
- a material model;
- a solver backend;
- a nonlinear algorithm;
- mesh diagnostics;
- numerical telemetry;
- qualification infrastructure.

## SfePy

SfePy is particularly attractive when extending the mathematical PDE model.

Examples include:

- a new weak-form term;
- coupled fields;
- custom material behaviour expressed through the framework;
- custom PDE applications;
- research formulations.

---

# Maturity

SfePy is the more established project.

It has existed for many years, has published scientific references and covers
a broad range of PDE applications.

QF Solver is a much younger project.

QF Solver should therefore not claim equivalent ecosystem maturity.

Its differentiator is instead its narrower structural focus combined with
inspectability, diagnostics and explicit qualification tracking.

---

# When QF Solver is the better starting point

QF Solver is likely to be the better choice when:

- the problem is primarily structural mechanics;
- a predefined engineering-analysis route is desirable;
- solver diagnostics matter;
- the numerical implementation needs to be inspected;
- verification evidence must be connected explicitly to public capability
  claims;
- the project involves development of the structural solver itself;
- selected PETSc/MPI structural workloads are relevant.

---

# When SfePy is the better starting point

SfePy is likely to be the better choice when:

- the problem is naturally expressed as a custom PDE system;
- multiple fields must be coupled;
- the user wants to define weak-form equations directly;
- the application extends beyond structural mechanics;
- a mature Python PDE/FEM framework is preferred;
- the user wants access to SfePy's existing term-based formulation system.

---

# They can also be complementary

QF Solver and SfePy do not need to be treated only as competitors.

For research, independent implementations of the same mathematical problem
can be valuable for:

- numerical cross-checking;
- regression studies;
- formulation comparison;
- convergence studies.

The important requirement is to ensure that the compared problems use
compatible:

- equations;
- element formulations;
- material assumptions;
- loads;
- boundary conditions;
- numerical conventions.

---

# Conclusion

Choose **QF Solver** when the priority is a transparent structural FEM solver
with predefined engineering routes, numerical diagnostics and explicit
capability qualification.

Choose **SfePy** when the priority is a flexible Python finite-element
framework for general and coupled PDE systems.

For broad PDE research, SfePy currently has the stronger natural scope.

For structural-solver development and QF-style verification traceability,
QF Solver provides a more specialized workflow.

---

# Related pages

- [Python FEM solvers](python-fem-solvers.md)
- [QF Solver vs scikit-fem](qf-vs-scikit-fem.md)
- [QF Solver vs CalculiX](qf-vs-calculix.md)
- [QF Solver vs Code_Aster](qf-vs-code-aster.md)
- [When should I use QF Solver?](../getting-started/when-to-use-qf-solver.md)
- [QF Solver analyses](../analyses/index.md)
- [Known limitations](../etat/limites.md)
