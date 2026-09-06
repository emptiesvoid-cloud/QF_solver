# Python FEM solvers: which one should you use?

There is no single best finite-element solver for every problem.

Python users can choose between lightweight FEM libraries, general PDE
frameworks, structural solvers and external mature engineering solvers.

This page compares several relevant open-source options:

- QF Solver;
- SfePy;
- scikit-fem;
- CalculiX;
- Code_Aster.

The comparison focuses primarily on structural mechanics and solver
development.

---

## Short answer

### Choose QF Solver if

You want a Python structural FEM solver with:

- inspectable formulations;
- explicit engineering-oriented solver routes;
- numerical diagnostics;
- reproducible verification evidence;
- capability maturity tracking;
- static and structural-dynamics workflows;
- selected nonlinear capabilities;
- optional PETSc/MPI large-scale solving.

QF Solver is particularly relevant for FEM developers, computational
mechanics research and controlled engineering calculations where numerical
traceability matters.

### Choose scikit-fem if

You want a lightweight, pure-Python finite-element library centered around
assembling finite-element forms into sparse matrices and vectors.

It is particularly attractive for:

- implementing weak formulations;
- research prototypes;
- teaching;
- custom PDE formulations;
- compact Python FEM applications.

### Choose SfePy if

You want a broader Python framework for solving systems of partial
differential equations using the finite-element method.

SfePy can be used both as a PDE solver and as a Python framework for building
custom FEM applications.

It covers a broader PDE-oriented scope than QF Solver.

### Choose CalculiX if

You want a mature standalone structural finite-element program with:

- linear analysis;
- nonlinear analysis;
- static analysis;
- dynamic analysis;
- thermal analysis;
- a traditional engineering solver workflow.

CalculiX is not primarily designed as a Python-native FEM development
framework.

### Choose Code_Aster if

You need a mature and broad mechanical finite-element solver with an extensive
body of reference documentation and validation cases.

For complex industrial mechanical simulations, Code_Aster provides a much
broader established capability set than QF Solver.

---

# High-level comparison

| Criterion | QF Solver | SfePy | scikit-fem | CalculiX | Code_Aster |
| --- | --- | --- | --- | --- | --- |
| Main orientation | Structural FEM solver | General PDE/FEM framework | FEM assembly library | Structural engineering solver | General mechanical FEM solver |
| Python-native workflow | Strong | Strong | Strong | Limited | Partial / solver-oriented |
| Inspectable FEM development | Strong | Strong | Strong | Lower-level solver source | Available but much larger codebase |
| Structural engineering focus | Strong | Mixed | User-defined | Strong | Strong |
| Weak-form experimentation | Moderate | Strong | Very strong | Low | Low to moderate |
| Built-in engineering solver routes | Yes | Yes | Mostly user-assembled | Yes | Extensive |
| Explicit QF-style maturity registry | Yes | No equivalent QF registry | No equivalent QF registry | Different validation model | Extensive independent validation documentation |
| PETSc/MPI route | Selected QF routes | Depends on configuration | Not its primary focus | Solver-specific parallelism | HPC capabilities available |
| General nonlinear mechanics | Limited / developing | Available depending on formulation | Mostly user-defined | Mature relative to QF Solver | Extensive |
| Complex industrial contact | Limited | Problem-dependent | User-defined | More mature | More mature |
| Learning curve | Moderate | Moderate to high | Low to moderate | Moderate | High |
| Best fit | Structural solver transparency and V&V | PDE research | FEM formulation/prototyping | Standalone structural analysis | Large industrial mechanical studies |

This table describes project orientation rather than claiming equivalent
feature-by-feature qualification.

---

# QF Solver

QF Solver is an open-source Python finite-element solver focused on structural
mechanics.

Its main differentiator is not simply the number of implemented features.

The project emphasizes the relationship between:

- formulation;
- implementation;
- numerical tests;
- verification;
- external correlation;
- qualification;
- published capability claims.

QF Solver 0.2.7 contains bounded routes involving solid elements such as:

- TET4;
- TET10;
- HEX8;
- HEX20.

Its documented analysis routes include, within their respective scopes:

- linear static analysis;
- modal analysis;
- Newmark dynamics;
- harmonic analysis;
- linear buckling;
- small-strain J2 plasticity;
- bounded frictionless contact.

Optional PETSc/MPI infrastructure is also available for selected large sparse
models.

QF Solver should not currently be considered a universal replacement for a
mature industrial FEM solver.

---

# scikit-fem

scikit-fem is a lightweight pure-Python finite-element library.

Its central abstraction is finite-element assembly: bilinear forms can be
assembled into sparse matrices and linear forms into vectors.

It supports multiple common mesh families including:

- triangular meshes;
- quadrilateral meshes;
- tetrahedral meshes;
- hexahedral meshes;
- one-dimensional meshes.

This makes scikit-fem particularly attractive when the user wants to define
the mathematical formulation directly.

## scikit-fem is especially suitable for

- PDE research;
- teaching;
- custom weak formulations;
- compact FEM experiments;
- rapid Python prototyping.

## QF Solver differs because

QF Solver provides more pre-structured structural-engineering solver routes,
diagnostics and qualification infrastructure.

scikit-fem gives the developer more direct control over defining the
mathematical FEM problem.

Neither approach is universally better.

---

# SfePy

SfePy is a Python framework for solving systems of coupled partial
differential equations using the finite-element method.

It can operate as both:

- a PDE solver;
- a Python package for building custom FEM applications.

Its scope extends beyond structural mechanics and is therefore broader in
terms of general PDE formulation.

## SfePy is especially suitable for

- coupled PDE problems;
- multiphysics-oriented research;
- custom FEM formulations;
- scientific computing workflows;
- researchers who want a mature Python PDE framework.

## QF Solver differs because

QF Solver is more narrowly centered on structural mechanics and explicit
engineering solver qualification.

Its design places strong emphasis on numerical diagnostics, capability
maturity and reproducible engineering evidence.

---

# CalculiX

CalculiX is a free three-dimensional structural finite-element program.

It provides traditional engineering FEM workflows and supports linear and
nonlinear calculations as well as static, dynamic and thermal analyses.

Its solver also uses an Abaqus-style input format for many workflows.

This makes CalculiX closer to a traditional standalone engineering FE solver
than to a Python FEM library.

## CalculiX is especially suitable for

- traditional structural FE analysis;
- established nonlinear calculations;
- engineering models using an Abaqus-like input workflow;
- users who need a mature standalone solver.

## QF Solver differs because

QF Solver is Python-native and designed to expose solver behaviour and
verification evidence directly to developers.

CalculiX currently has a broader and more mature general structural-analysis
scope.

---

# Code_Aster

Code_Aster is a mature open-source finite-element solver focused heavily on
mechanical and structural simulation.

It has a large body of:

- user documentation;
- theoretical reference documentation;
- validation cases;
- implementation documentation.

This makes Code_Aster much more established than QF Solver for broad
industrial mechanical simulation.

## Code_Aster is especially suitable for

- advanced structural mechanics;
- nonlinear mechanics;
- industrial FE workflows;
- applications requiring a large validated feature base;
- users prepared to work with a more complex solver ecosystem.

## QF Solver differs because

QF Solver is substantially smaller and easier to inspect as a complete
solver-development project.

It is more suitable when the objective includes understanding, modifying or
experimenting with the solver itself.

For broad industrial capability, Code_Aster currently provides a much larger
established scope.

---

# Which solver should I choose?

| Your main goal | Suggested starting point |
| --- | --- |
| Learn or implement FEM formulations in compact Python | scikit-fem |
| Solve general PDE systems in Python | SfePy |
| Develop or inspect a structural FEM solver | QF Solver |
| Run traditional standalone structural analyses | CalculiX |
| Perform broad mature industrial mechanical FE analysis | Code_Aster |
| Study solver verification and qualification infrastructure | QF Solver |
| Develop custom weak formulations | scikit-fem or SfePy |
| Work with selected large structural Python FEM models using PETSc/MPI | QF Solver, if the route is within documented scope |
| Require mature complex nonlinear mechanics | Code_Aster or CalculiX |

---

# Where QF Solver is strongest

QF Solver is most differentiated by the combination of:

- structural mechanics;
- Python-native development;
- white-box formulations;
- numerical diagnostics;
- reproducible verification;
- explicit capability maturity;
- selected large-model PETSc/MPI execution.

The project is therefore particularly relevant for:

- FEM developers;
- computational mechanics researchers;
- engineering-method developers;
- solver benchmarking;
- verification studies;
- automated engineering pipelines.

---

# Where QF Solver is currently weaker

QF Solver is younger and less mature than established general-purpose
engineering solvers.

Current limitations include areas such as:

- general frictional contact;
- production finite sliding;
- general finite-strain plasticity;
- arbitrary mixed-element industrial meshes;
- complete shell qualification;
- broad GPU acceleration;
- general multiphysics.

Users requiring those capabilities should consider a more mature solver.

---

# A note about validation

Solver comparison should not be based only on whether a feature appears in a
feature list.

Important questions include:

- What exact formulation is implemented?
- Which element and material combination was tested?
- What reference solution was used?
- Is the result numerically converged?
- Has the implementation been externally correlated?
- What limitations are documented?

QF Solver intentionally makes these distinctions explicit.

A feature marked as experimental should not be treated as equivalent to a
qualified engineering capability.

---

# More detailed comparisons

- [QF Solver vs SfePy](qf-vs-sfepy.md)
- [QF Solver vs scikit-fem](qf-vs-scikit-fem.md)
- [QF Solver vs CalculiX](qf-vs-calculix.md)
- [QF Solver vs Code_Aster](qf-vs-code-aster.md)

For QF Solver specifically, also read:

- [When should I use QF Solver?](../getting-started/when-to-use-qf-solver.md)
- [Elements](../elements/index.md)
- [Analyses](../analyses/index.md)
- [Known limitations](../etat/limites.md)
- [QF Solver 0.2.7 verification](../verification/0_2_7/README.md)
