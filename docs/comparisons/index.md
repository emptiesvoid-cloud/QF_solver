# FEM solver comparisons

Choosing a finite-element solver depends on the type of problem, the desired
level of control, the numerical methods required and the maturity expected
from the software.

This section compares QF Solver with several open-source finite-element tools.

The objective is not to claim that QF Solver is universally better. Each
project has a different scope and design philosophy.

## Start here

If you are looking for a Python FEM solver, begin with:

[Python FEM solvers: which one should you use?](python-fem-solvers.md)

Detailed comparisons:

- [QF Solver vs SfePy](qf-vs-sfepy.md)
- [QF Solver vs scikit-fem](qf-vs-scikit-fem.md)
- [QF Solver vs CalculiX](qf-vs-calculix.md)
- [QF Solver vs Code_Aster](qf-vs-code-aster.md)

## What makes QF Solver different?

QF Solver focuses on structural mechanics with an emphasis on:

- Python integration;
- inspectable finite-element formulations;
- explicit numerical diagnostics;
- reproducible verification evidence;
- capability maturity tracking;
- sparse numerical solving;
- optional PETSc/MPI large-scale solving.

QF Solver deliberately distinguishes between:

- implemented capabilities;
- tested capabilities;
- verified capabilities;
- externally validated capabilities;
- qualified capabilities;
- experimental capabilities.

This means that the presence of a feature in the source code does not
automatically imply a general engineering qualification.

## QF Solver is not intended to replace every FEM package

More mature finite-element projects generally provide broader physics,
larger element libraries or more established nonlinear workflows.

QF Solver is most relevant when transparency, Python integration,
verification and solver development are important.

For complex industrial nonlinear calculations, advanced contact,
large-strain material models or certification-oriented workflows,
a mature general-purpose solver may be more appropriate.

## Comparison philosophy

The comparisons in this section focus on:

1. primary purpose;
2. Python integration;
3. structural-mechanics orientation;
4. available solver infrastructure;
5. transparency;
6. verification strategy;
7. large-model capability;
8. maturity and limitations.

Feature availability evolves over time.

For any engineering decision, consult the official documentation of each
solver and the active QF Solver capability matrix.

## QF Solver capability reference

The authoritative QF Solver capability information is available in:

- [Elements](../elements/index.md)
- [Analyses](../analyses/index.md)
- [Known limitations](../etat/limites.md)
- [QF Solver 0.2.7 verification](../verification/0_2_7/README.md)
- [When should I use QF Solver?](../getting-started/when-to-use-qf-solver.md)
