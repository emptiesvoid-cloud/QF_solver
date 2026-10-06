# QF Solver

[![Python](https://img.shields.io/pypi/pyversions/qf-solver.svg)](https://pypi.org/project/qf-solver/)
[![PyPI](https://img.shields.io/pypi/v/qf-solver.svg)](https://pypi.org/project/qf-solver/)
[![License](https://img.shields.io/github/license/emptiesvoid-cloud/QF_solver.svg)](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-2f80ed.svg)](https://emptiesvoid-cloud.github.io/QF_solver/)
[![CI](https://github.com/emptiesvoid-cloud/QF_solver/actions/workflows/quality.yml/badge.svg)](https://github.com/emptiesvoid-cloud/QF_solver/actions/workflows/quality.yml)

QF Solver is an open-source Python finite-element solver for structural
mechanics and dynamics, designed for inspectable formulations,
engineering-method development and reproducible numerical verification. It
offers linear, dynamic and selected nonlinear analysis routes through a
Python API and command-line interface. Tests, benchmarks, evidence records and
explicit scope limits help users inspect what a result does—and does not—show.

QF Solver is intended for engineering-method development, research and
reproducible studies. An implemented route or a converged example is not
automatically qualified or physically validated. The project is not certified
and is not a general-purpose replacement for industrial FEA software.

On this page: [Capabilities](#capabilities) · [How it works](#how-qf-solver-works) ·
[Quick start](#quick-start) · [Analysis families](#analysis-families) ·
[Rotating dynamics](#rotating-dynamics) · [Verification](#verification-and-maturity) ·
[Limitations](#limitations) · [Current release](#current-release-and-citation).

## Capabilities

The capabilities below are cumulative, but maturity belongs to a specific
element, analysis, material, configuration and evidence record—not to the
solver as a whole. Use the [capability index](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/)
and [element map](https://emptiesvoid-cloud.github.io/QF_solver/elements/)
before relying on a particular combination.

| Domain | Current capabilities | Evidence status and boundary |
| --- | --- | --- |
| Elements | TET4, TET10, HEX8, HEX20, WEDGE6, BEAM2, MITC3 and MITC4 routes | Family support and maturity vary by analysis and formulation; see the element-analysis records. |
| Linear statics | Structural solves, reactions and selected stress/result fields | Bounded element, material, constraint and load combinations; not every combination is qualified. |
| Modal and dynamics | Classical modal analysis, Newmark transient response and harmonic response | Route-specific mass, damping, timestep, element-family and mixed-model limits apply. |
| Stability | Linear buckling | Does not establish postbuckling or general nonlinear stability behavior. |
| Material nonlinearity | Selected small-strain J2 plasticity routes | Bounded material/element evidence; this is not general finite-strain plasticity. |
| Geometric nonlinearity | Selected Total-Lagrangian and corotational routes | Formulation and element scopes are narrow; corotational J2 assumes small local strains. |
| Contact and constraints | RBE2-style constraints, frictionless contact, and bounded frictional stick/slip evidence | Contact search, sliding, mesh sensitivity and current-source requalification remain limited. |
| Nonlinear solution | Newton methods, line search, adaptive increments, cutback/retry, and selected continuation/arc-length routes | Shared infrastructure does not imply convergence or qualification for arbitrary models. |
| Larger models | Structured-TET4 workflows and selected PETSc/MPI linear-static cases | Optional dependencies and recorded configurations only; no general HPC or nonlinear distributed claim. |
| Rotating dynamics | Experimental disk-gyroscopic `rotating_modal` and Campbell analysis in the 0.2.11 candidate | Linear BEAM2 shaft with centered rigid axisymmetric disks; serial dense QEP and explicit scope limits. |
| I/O and interfaces | JSON models, public `qf_solver` Python namespace, CLI, bounded `.inp` import and optional mixed HDF5 results | Import/export formats and optional backends are not general-purpose interchange guarantees. |
| Verification and validation | Analytical checks, regression tests, controlled benchmarks, reproducible evidence and selected Code_Aster correlations | Numerical verification, external solver correlation and physical validation are distinct claims. |

Status terms such as `QUALIFIED_BOUNDED`, `EXPERIMENTAL_BOUNDED`,
`EXPERIMENTAL` and `NOT_VALIDATED` refer only to the scope documented by the
controlling record. The [published 0.2.8 registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json)
remains the authority for its historical element-analysis decisions; later
evidence does not silently rewrite those decisions.

## How QF Solver works

The public API and CLI validate a model, route it to an analysis-specific
driver, assemble the required contributions and return results with
route-specific diagnostics. Not every analysis assembles or uses every
contribution shown here.

```text
Model / input
     ↓
Public qf_solver API or CLI
     ↓
AnalysisRouter
     ↓
Analysis driver
     ↓
Assembly: elements · materials · loads · constraints · contact · rotating terms
     ↓
Linear / nonlinear / eigenvalue solver
     ↓
Results · diagnostics · provenance
```

Linear, dynamic, nonlinear and rotating analyses have distinct contracts and
solver routes. SciPy provides the standard numerical stack; selected large
linear workflows can use optional PETSc/MPI components. Optional packages do
not expand the validated scope by themselves. See the [architecture](https://emptiesvoid-cloud.github.io/QF_solver/architecture/)
and [API stability](https://emptiesvoid-cloud.github.io/QF_solver/reference/api_stability/)
pages for implementation boundaries and compatibility status.

## Quick start

The latest published PyPI release is 0.2.10. From a repository checkout with
the maintained example files, install that release and run a small linear
static case:

```bash
python -m pip install "qf-solver==0.2.10"
qf-solver check-mesh --input examples/tet4_static.json
qf-solver solve --input examples/tet4_static.json --output results/tet4.json
```

The equivalent public Python workflow is:

```python
from qf_solver import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
report = check_mesh(model)
if report.status == "FAIL":
    raise RuntimeError(report.errors)
result = solve_model(model)
save_result(result, "results/tet4.json")
```

Inspect the result fields, residuals, reactions and route-specific diagnostics
before relying on an output. The [first-calculation guide](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/quickstart/)
explains the workflow. New integrations should use `qf_solver`; `solveur` and
the legacy launchers remain 0.2.x compatibility paths.

## Analysis families

| Analysis | Orientation | Documentation |
| --- | --- | --- |
| Linear static | Small-strain structural equilibrium and reactions | [Analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/) · [elements](https://emptiesvoid-cloud.github.io/QF_solver/elements/) |
| Modal | Classical structural eigenvalue analysis | [Analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/) · [capability index](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/) |
| Transient and harmonic | Newmark time integration and linear frequency response | [Analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/) |
| Buckling | Linearized eigenvalue buckling | [Analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/) · [limitations](https://emptiesvoid-cloud.github.io/QF_solver/etat/limites/) |
| Nonlinear mechanics | Material, geometric, continuation and contact routes | [Nonlinear overview](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/nonlinear-overview/) |
| Rotating modal | Experimental disk-gyroscopic eigenanalysis | [Model and limits](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/rotating-modal/) |
| Campbell | Experimental speed sweep and explicit modal tracking | [Tracking and limits](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/campbell/) |

The [examples index](examples/README.md) groups maintained inputs by the
mechanical problem they illustrate. It also identifies controlled verification
fixtures and intentionally invalid inputs.

## Rotating dynamics

The 0.2.11 candidate adds **experimental serial gyroscopic modal analysis for
linear BEAM2 structures carrying centered rigid axisymmetric disks**, plus
experimental Campbell diagrams using explicit complex-mode tracking. This is
a bounded extension to the solver, not a general rotating-machinery solver.

The initial model is a straight circular-isotropic BEAM2 shaft with centered
rigid axisymmetric disks, constant prescribed signed spin, small perturbations,
zero damping and no centrifugal prestress. The route uses a dense serial
quadratic eigenvalue solve. Distributed shaft gyroscopy, speed-dependent
bearings, centrifugal stress stiffening, unbalance response, rotor/stator
contact, nonlinear rotors, PETSc/SLEPc and MPI are outside this scope.

At 100 rad/s, the high-frequency pair in the bounded Campbell verification
remains ambiguous. The tracker preserves that gap instead of forcing branch
continuity. GYRO-06 provides **internal mesh-convergence evidence**, not
independent physical validation. Campbell frequencies are not a forced
response, amplitude, operational-danger or validated critical-speed
prediction. Both `rotating_modal` and Campbell remain `EXPERIMENTAL`.

## Verification and maturity

QF Solver distinguishes implementation, a passing test, numerical
verification, external solver correlation, maturity decisions and physical
validation. These are separate kinds of evidence. The [V&V and maturity guide](https://emptiesvoid-cloud.github.io/QF_solver/verification/evidence-and-maturity/)
explains the labels; the [0.2.11 verification summary](https://emptiesvoid-cloud.github.io/QF_solver/verification/0_2_11/)
links the candidate gyro and Campbell records.

Selected Code_Aster 18.1 results provide same-mesh **linear-static solver
correlation** for declared cases and comparable observables. This is not
experimental physical validation or general nonlinear correlation. Internal
independent recomputation of selected observables is also not a second global
FEM/Newton solve. Large-model and PETSc/MPI evidence is tied to specific
workloads and environments; it does not establish general scalability or
distributed nonlinear support.

## Limitations

- General multiplicative finite-strain plasticity, nonlinear transient
  dynamics, universal postbuckling, finite-sliding/self-contact and
  impact/contact dynamics are outside the demonstrated scope.
- Corotational J2 permits large rotations only under a small-local-strain
  assumption. Higher-order nonlinear routes are narrower than linear element
  support.
- Frictional contact remains bounded and mesh-sensitive; general updated
  search, finite sliding and self-contact are not claimed.
- Optional PETSc/MPI workflows do not establish general HPC scaling, nonlinear
  distributed solving or a validated mixed-distributed runtime.
- Rotating modal and Campbell are experimental and restricted to the model
  described above; the 100 rad/s high-frequency branch ambiguity remains
  visible.
- QF Solver is not certified and has no universal physical-validation claim.

See the detailed [technical limitations](https://emptiesvoid-cloud.github.io/QF_solver/etat/limites/)
and the controlling evidence record for the chosen analysis.

## Current release and citation

The latest **published** release is `0.2.10` ([PyPI](https://pypi.org/project/qf-solver/0.2.10/),
[GitHub Release](https://github.com/emptiesvoid-cloud/QF_solver/releases/tag/v0.2.10),
source tag [`v0.2.10`](https://github.com/emptiesvoid-cloud/QF_solver/tree/v0.2.10)).
Version 0.2.11 is a **candidate, not yet published**. Its cumulative additions
and bounded evidence are summarized in [What's New in 0.2.11](docs/whats-new/0.2.11.md);
the [changelog](CHANGELOG.md) retains the full project history.

For reproducibility, cite the exact published version DOI
[`10.5281/zenodo.23106744`](https://doi.org/10.5281/zenodo.23106744). Use the
project concept DOI [`10.5281/zenodo.22697897`](https://doi.org/10.5281/zenodo.22697897)
when citing the evolving project rather than a specific release. The candidate
[`CITATION.cff`](CITATION.cff) identifies version 0.2.11 but intentionally has
no release date or version DOI until publication. The whole-repository G03
archive gate remains **FAIL**, the full repository archive is not cleared, and
WP14 remains **HOLD_NOT_PROMOTED**; selected distribution checks do not change
those states.

## Documentation and project

- [Documentation home](https://emptiesvoid-cloud.github.io/QF_solver/)
- [Capabilities](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/),
  [elements](https://emptiesvoid-cloud.github.io/QF_solver/elements/) and
  [analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/)
- [Public API contract](https://emptiesvoid-cloud.github.io/QF_solver/reference/qf_solver_api/)
  and [API stability](https://emptiesvoid-cloud.github.io/QF_solver/reference/api_stability/)
- [Benchmarks](https://emptiesvoid-cloud.github.io/QF_solver/benchmarks/) and
  [V&V evidence](https://emptiesvoid-cloud.github.io/QF_solver/verification/evidence-and-maturity/)
- [Contributing](CONTRIBUTING.md) · [code license](LICENSE) ·
  [documentation/examples license](LICENSE-DOCS)

The solver code is licensed under Apache-2.0; documentation and original
examples are under CC BY 4.0. Third-party terms are listed in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md).
