# When should I use QF Solver?

QF Solver is an open-source Python finite-element solver focused on
structural mechanics, transparent formulations, reproducible numerical
verification and inspectable solver behaviour.

It is designed primarily for engineers, researchers and developers who want
to understand, verify and control the finite-element calculation rather than
treat the solver as a black box.

QF Solver is not intended to replace every industrial finite-element package.
Its capabilities are deliberately classified by maturity and by validated
scope.

This page helps decide whether QF Solver is an appropriate choice for a given
problem.

---

## Short answer

QF Solver is a good fit if you need:

- a Python-native finite-element workflow;
- transparent and inspectable FEM formulations;
- structural mechanics calculations;
- reproducible verification evidence;
- linear static analysis;
- modal and structural dynamic analysis within documented limits;
- small-strain elastoplastic calculations within qualified routes;
- sparse linear solving;
- PETSc/MPI solving for selected large models;
- an engineering solver that exposes numerical diagnostics;
- a solver that explicitly separates implemented, tested, verified and
  qualified capabilities.

QF Solver is currently a poor fit if you need:

- production-grade general-purpose nonlinear analysis;
- large-strain plasticity;
- general frictional contact;
- production finite-sliding contact;
- arbitrary mixed-element industrial models;
- mature GPU acceleration;
- full multiphysics;
- certification-oriented industrial workflows;
- a drop-in replacement for Abaqus, ANSYS, Code_Aster or similar mature
  general-purpose platforms.

---

# Typical good use cases

## 1. Structural finite-element analysis in Python

QF Solver is particularly suitable when the finite-element solver is part of a
larger Python engineering workflow.

Typical examples include:

- structural preprocessing;
- automated parametric studies;
- solver development;
- optimization loops;
- research prototypes;
- surrogate-model data generation;
- FEM verification studies;
- automated mechanical simulation pipelines.

The public Python API allows QF Solver to be integrated directly into Python
applications rather than only controlled through an external solver process.

---

## 2. Linear static structural mechanics

Linear static analysis is one of the strongest current use cases.

QF Solver provides bounded qualified routes for several solid finite elements,
including:

- TET4;
- TET10;
- HEX8;
- HEX20.

Qualification remains dependent on the complete combination of:

- element;
- material;
- loading;
- boundary conditions;
- mesh;
- solver route;
- analysis type.

A qualified element does not imply that every possible model using that
element is qualified.

Users should always consult the active capability matrix before making a
reliability claim.

---

## 3. Modal analysis

QF Solver can be used for structural modal analysis when the problem lies
inside the documented route-specific scope.

Typical applications include:

- natural-frequency estimation;
- structural mode extraction;
- model verification;
- comparison with analytical solutions;
- comparison with reference finite-element solutions.

WEDGE6 modal analysis has bounded qualification for a specifically documented
homogeneous isotropic consistent-mass route and for the first three modes.

This qualification must not be generalized to other WEDGE6 analyses.

---

## 4. Structural dynamics

QF Solver contains dynamic-analysis routes including:

- modal analysis;
- Newmark time integration;
- harmonic analysis.

These capabilities are currently supported with documented limitations.

They are appropriate for controlled structural-dynamics studies when the
chosen formulation, model and solver route match the available verification
evidence.

For safety-critical or production-critical dynamic analyses, users should
independently verify the model against analytical solutions, experimental
results or an established reference solver.

---

## 5. Small-strain J2 plasticity

QF Solver provides bounded qualification evidence for small-strain J2
plasticity on:

- TET4;
- TET10;
- HEX8;
- HEX20.

This makes QF Solver useful for studying and developing nonlinear solid
mechanics workflows where:

- strains remain inside the documented small-strain assumptions;
- the constitutive route matches the qualified implementation;
- the complete element/material/solver combination is covered by the
  qualification evidence.

This qualification does not currently extend to general finite-strain
plasticity.

---

## 6. Solver and FEM method development

QF Solver is deliberately designed as a white-box solver.

It is therefore particularly suitable for developers working on:

- finite-element formulations;
- numerical integration;
- constitutive models;
- nonlinear algorithms;
- sparse matrix assembly;
- eigensolvers;
- iterative linear solvers;
- preconditioning;
- mesh diagnostics;
- verification infrastructure;
- solver reproducibility.

The objective is that numerical behaviour can be inspected rather than hidden
behind a proprietary execution layer.

For research and solver-development workflows, this transparency can be more
important than having the broadest possible feature set.

---

## 7. Verification and validation studies

QF Solver places unusual emphasis on numerical evidence.

The project distinguishes several concepts that are often mixed together:

- `IMPLEMENTED`;
- `TESTED`;
- `VERIFIED`;
- `EXTERNALLY_VALIDATED`;
- `QUALIFIED`;
- `EXPERIMENTAL`.

A feature being implemented does not automatically mean that it is ready for
engineering use.

A passing example also does not constitute universal validation.

This makes QF Solver useful for:

- verification methodology development;
- FEM regression studies;
- solver-to-solver comparison;
- reproducibility studies;
- numerical-quality auditing;
- engineering-method development.

---

# Large models and HPC

QF Solver includes optional PETSc/MPI integrations for selected large-scale
finite-element calculations.

Recorded QF Solver 0.2.7 evidence includes structured TET4 workloads at
approximately:

- 1 million DOFs;
- 3 million DOFs;
- 5 million DOFs;
- 10 million DOFs.

These results demonstrate that QF Solver can execute large sparse calculations
under the documented PETSc/MPI environments.

They must not be interpreted as a universal scalability claim.

In particular, the current evidence does not demonstrate equivalent scaling
for:

- every element family;
- arbitrary mixed meshes;
- every nonlinear route;
- every hardware configuration;
- every PETSc configuration;
- GPU execution.

Use QF Solver for large models when the intended solver route is close to the
documented large-scale configurations.

---

# When QF Solver is probably not the right tool

## General industrial nonlinear simulation

QF Solver is not currently a general replacement for mature industrial
nonlinear finite-element platforms.

If your model requires combinations such as:

- large deformation;
- complex plasticity;
- frictional contact;
- finite sliding;
- complex shell assemblies;
- complex mixed-element assemblies;
- sophisticated nonlinear stabilization;
- highly mature automatic nonlinear control;

a mature general-purpose solver will normally be the safer choice.

Examples include Code_Aster, CalculiX, Abaqus, ANSYS and other established
finite-element platforms depending on the application.

---

## Frictional contact

QF Solver currently contains bounded frictionless node-to-triangle contact
capabilities.

General friction is outside the currently qualified scope.

Do not choose QF Solver solely for a production model dominated by complex
frictional contact.

---

## Large-strain plasticity

The currently qualified J2 scope is based on small-strain formulations.

Finite-kinematic J2 and broader finite-strain nonlinear workflows remain
experimental or outside the qualified scope.

For large deformation elastoplasticity, another solver should currently be
preferred unless the objective is specifically research or solver
development.

---

## Arbitrary mixed meshes

QF Solver supports several important solid element families, but this does not
mean arbitrary mixed TET/WEDGE/HEX models are production-qualified.

Mixed-element workflows remain limited.

Complex industrial meshes should therefore be checked carefully against the
active capability matrix.

---

## WEDGE elements

WEDGE6 support must be interpreted carefully.

Current status:

- WEDGE6 static: `EXPERIMENTAL`;
- WEDGE6 modal: bounded qualification for a specific documented route.

A successful WEDGE6 modal qualification does not imply static, nonlinear or
general dynamic qualification.

WEDGE15 is currently outside the supported qualified scope.

---

## Pyramid elements

PYRAMID5 is not currently part of the qualified production scope.

Models requiring pyramid transition elements should therefore not assume that
QF Solver can currently reproduce a general industrial mixed-mesh workflow.

---

## GPU solving

QF Solver currently makes no general GPU-solving claim.

The large-scale solver route is primarily based on sparse CPU workflows and
optional PETSc/MPI integration.

If GPU acceleration is a primary requirement, QF Solver is currently unlikely
to be the best choice.

---

# QF Solver versus a mature industrial solver

QF Solver and large industrial finite-element platforms solve different
problems.

A mature industrial solver usually prioritizes:

- very broad element libraries;
- mature nonlinear algorithms;
- complex contact;
- industrial preprocessing;
- extensive material models;
- decades of validation;
- production support.

QF Solver prioritizes:

- Python integration;
- inspectability;
- transparent formulations;
- explicit numerical diagnostics;
- reproducible verification;
- machine-readable qualification evidence;
- controlled solver development;
- traceability between claims and numerical evidence.

The correct choice depends on what matters most for the application.

---

# QF Solver versus a lightweight Python FEM library

A lightweight Python FEM library can be preferable when the goal is:

- teaching;
- rapid implementation of a weak formulation;
- small research experiments;
- minimal solver infrastructure.

QF Solver becomes more interesting when the project also requires:

- engineering-oriented solver routes;
- explicit capability maturity;
- numerical diagnostics;
- regression infrastructure;
- verification evidence;
- large sparse solving;
- structured release qualification.

---

# Recommended user profiles

## Engineering user

QF Solver may be appropriate if you want to perform controlled structural
calculations while retaining access to the numerical details of the solver.

Always check the capability matrix before relying on a result.

---

## Researcher

QF Solver can be useful for:

- computational mechanics research;
- FEM methodology;
- nonlinear algorithms;
- structural dynamics;
- solver benchmarking;
- verification studies;
- surrogate-model dataset generation.

Its white-box architecture is particularly useful when the numerical method
itself is part of the research.

---

## FEM developer

This is one of the strongest use cases.

QF Solver can serve as a platform for experimenting with:

- new elements;
- new materials;
- new integration schemes;
- solver backends;
- preconditioners;
- nonlinear algorithms;
- verification methods.

---

## Student

QF Solver can be useful for learning finite-element mechanics because the
implementation is inspectable.

However, the project is an engineering solver rather than a simplified
teaching-only FEM implementation.

Users should already be familiar with basic:

- continuum mechanics;
- finite-element theory;
- numerical linear algebra;
- structural mechanics.

---

# Decision checklist

Before choosing QF Solver, answer the following questions.

### Analysis

- Is the required analysis available?
- What is its current maturity status?
- Is the route qualified, limited or experimental?

### Elements

- Are the required elements supported?
- Is the exact element-analysis combination covered?

### Materials

- Is the required material model supported?
- Are the assumptions compatible with the intended problem?

### Nonlinearity

- Does the problem involve large deformation?
- Plasticity?
- Contact?
- Friction?
- Material nonlinearity?

### Scale

- How many DOFs are expected?
- Is the standard SciPy route sufficient?
- Is PETSc/MPI required?
- Is the model similar to an existing large-scale verified workload?

### Verification

- Is an analytical reference available?
- Can the result be compared with another FEM solver?
- Does QF Solver provide existing qualification evidence for the same route?

### Production requirements

- Is certification required?
- Is the calculation safety critical?
- Is industrial vendor support required?

If certification, production liability or safety-critical qualification is a
primary requirement, QF Solver should not be treated as a certified solver.

---

# Capability status matters

The most important rule when using QF Solver is:

> Do not infer capability from implementation alone.

QF Solver uses explicit maturity levels to prevent this.

For example:

| Capability | Current public status |
| --- | --- |
| Linear static solid routes | `QUALIFIED_BOUNDED` |
| Small-strain J2 on TET4/TET10/HEX8/HEX20 | `QUALIFIED_BOUNDED` |
| Modal analysis | `SUPPORTED_WITH_LIMITATIONS` |
| Newmark dynamics | `SUPPORTED_WITH_LIMITATIONS` |
| Harmonic analysis | `SUPPORTED_WITH_LIMITATIONS` |
| Linear buckling | `SUPPORTED_WITH_LIMITATIONS` |
| Frictionless contact | `SUPPORTED_WITH_LIMITATIONS` |
| WEDGE6 static | `EXPERIMENTAL` |
| WEDGE6 modal, declared route | `QUALIFIED_BOUNDED` |
| PETSc/MPI large-model route | `SUPPORTED_WITH_LIMITATIONS` |
| General frictional contact | Not qualified |
| General finite-strain plasticity | Not qualified |
| GPU solving | Not claimed |

The active capability registry remains the authoritative source for the exact
supported combinations.

---

# Recommended workflow

For a new QF Solver project:

1. Identify the required analysis.
2. Identify the element family.
3. Check the active capability matrix.
4. Read the documented limitations.
5. Start with a small reference problem.
6. Verify the result against an analytical or independent reference whenever
   possible.
7. Increase model complexity progressively.
8. Record solver diagnostics and convergence information.
9. Use the qualified route whenever an engineering claim is required.

---

# Getting started

Install QF Solver with:

```bash
python -m pip install qf-solver
