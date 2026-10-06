# QF Solver

[![Python](https://img.shields.io/pypi/pyversions/qf-solver.svg)](https://pypi.org/project/qf-solver/)
[![PyPI](https://img.shields.io/pypi/v/qf-solver.svg)](https://pypi.org/project/qf-solver/)
[![License](https://img.shields.io/github/license/emptiesvoid-cloud/QF_solver.svg)](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-2f80ed.svg)](https://emptiesvoid-cloud.github.io/QF_solver/)
[![CI](https://github.com/emptiesvoid-cloud/QF_solver/actions/workflows/quality.yml/badge.svg)](https://github.com/emptiesvoid-cloud/QF_solver/actions/workflows/quality.yml)

QF Solver is a Python finite-element solver for structural mechanics and
dynamics. It provides inspectable formulations, a public CLI and Python API,
and reproducible verification evidence. Linear analyses form the established
base; selected nonlinear material, geometric, contact and continuation routes
have their own, narrower evidence scopes. PETSc/MPI workflows are optional.

QF Solver is intended for engineering-method development, research and
reproducible studies. An implemented feature or a converged example is not
automatically qualified or physically validated. The project is not certified
and is not a general-purpose replacement for industrial FEA software.

**Published release:** 0.2.10. **0.2.11 candidate:** not yet published; it
adds experimental serial gyroscopic modal and Campbell analysis for a narrowly
bounded BEAM2/disk model. See [What's New in 0.2.11](docs/whats-new/0.2.11.md)
for its evidence and limitations. The candidate does not change the current
installation or citation instructions below.

On this page: [Purpose](#why-qf-solver) · [First calculation](#quick-start) ·
[Capabilities](#capabilities) · [Nonlinear mechanics](#nonlinear-mechanics) ·
[Evidence](#verification-and-maturity) · [Limits](#limitations) ·
[Release and citation](#release-and-citation) · [Documentation](#documentation).

## Why QF Solver?

- **Inspect the method:** Python-native model and result APIs, visible
  formulations, mesh checks, residuals and reaction diagnostics.
- **Start small:** maintained JSON examples cover solids, shells, statics and
  dynamics; the standard package does not require PETSc, MPI or HDF5.
- **Choose a route deliberately:** elements, materials, analyses, backends and
  maturity are documented separately, with links to controlling evidence.
- **Reproduce a study:** retain inputs, environment, diagnostics and the exact
  software version. Large-model workflows and V&V campaigns have their own
  recorded boundaries.

## Installation

Python 3.10 or newer is required. Install the published package:

```bash
python -m pip install "qf-solver==0.2.10"
qf-solver --version
```

The unpinned command `python -m pip install qf-solver` selects the latest
version available on PyPI. For reproducible source access, use the immutable
[`v0.2.10` tag](https://github.com/emptiesvoid-cloud/QF_solver/tree/v0.2.10),
not an unqualified clone of `main`. Optional `mesh`, `hdf5`, `large`,
`hpc` and `docs` extras are described in the
[installation guide](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/installation/).
Native MPI/PETSc/SLEPc availability remains environment-dependent.

## Quick start

From a repository checkout containing the maintained example:

```bash
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

Inspect the result and its diagnostics before relying on it; output fields and
their interpretation depend on the selected route. The
[first-calculation guide](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/quickstart/)
explains the workflow, and the
[example index](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/examples/README.md)
groups additional inputs. New integrations should use `qf_solver`; `solveur`
and the legacy launchers remain compatibility paths in 0.2.x.

## Capabilities

The table is an orientation, not a substitute for an element-analysis
decision. Check the
[capability index](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/)
and the applicable record before choosing a mesh, material or backend.

| Area | What is available | Scope to check |
| --- | --- | --- |
| Elements | TET4, TET10, HEX8, HEX20 and WEDGE6 solids; BEAM2 and MITC3/MITC4 routes | Analysis-specific family and formulation records; WEDGE15 is unsupported and PYRAMID5 is internal/research-only. |
| Linear statics | Small-strain structural solves, including selected mixed-family, multi-material and MPC workflows | `QUALIFIED_BOUNDED` only for recorded combinations; mixed workflows have separate decisions. |
| Dynamics and stability | Modal, linear Newmark transient, harmonic response and linear buckling routes | Mass, damping, timestep, family and mixed-route maturity vary; linear buckling does not establish postbuckling. |
| Materials | Linear elastic and selected small-strain J2 plasticity routes | Small-strain J2 has bounded element-analysis decisions; other constitutive paths require their own evidence. |
| Nonlinear mechanics | Selected geometric, coupled material/geometric, corotational J2, contact and continuation routes | Evidence differs by route; see [below](#nonlinear-mechanics). |
| Rotating dynamics (0.2.11 candidate) | Experimental `rotating_modal` and Campbell sweep | Linear straight BEAM2 shaft with centered rigid axisymmetric disks; serial dense QEP; the high-frequency pair remains ambiguous at 100 rad/s. Not general rotordynamics or critical-speed prediction. |
| Inputs and results | JSON model workflow, bounded Abaqus/CalculiX `.inp` import, optional mixed HDF5 results | `.inp` and HDF5 paths are provisional/bounded, not general format or parallel-storage guarantees. |
| Larger models | Structured-TET4 workloads and selected PETSc/MPI linear-static cases | Recorded hardware and rank configurations only; mixed distributed runtime remains `NOT_VALIDATED`. |

The published
[0.2.8 consolidated registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/v0.2.8/qualification/0_2_8/consolidated_registry.json)
remains authoritative for its 46 element-analysis decisions: 32
`QUALIFIED_BOUNDED`, 14 `EXPERIMENTAL`, 0 `NOT_QUALIFIED`. The 0.2.10
development-cycle records add separate evidence; they do not silently
reclassify those historical decisions. For example:

| Route | Published status | Boundary |
| --- | --- | --- |
| WEDGE6 static | `QUALIFIED_BOUNDED` | Declared Gmsh Prism 6 static scope. |
| WEDGE6 modal | `QUALIFIED_BOUNDED` | Homogeneous consistent-mass route and first three modes. |
| Frictionless penalty contact | `EXPERIMENTAL_BOUNDED` | Node-to-triangle, bounded small-sliding cases. |
| Mixed distributed PETSc/MPI | `NOT_VALIDATED` | No validated generic mixed-distributed runtime claim. |

## Nonlinear mechanics

Version 0.2.10 adds shared residual/tangent assembly, Newton iteration and
diagnostics, trial/accepted-state transactions, commit/rollback and selected
checkpoint/restart paths. Full Newton, line search, adaptive increments,
cutback/retry and a specialized arc-length route support recorded cases. Shared
infrastructure does **not** qualify every combination of element, material,
geometry, contact and backend; some contact recovery and arc-length machinery
remains route-specific.

- **Small-strain J2:** use the bounded decisions for the recorded element and
  analysis combinations. Corotational J2 permits large rotations under a
  small-local-strain assumption; formal bounded acceptance is HEX8-only.
  TET10/HEX20 extensions have separate limited evidence. This is not general
  multiplicative finite-strain plasticity.
- **Geometric nonlinearity:** selected static, serial TET4/HEX8
  Total-Lagrangian St. Venant–Kirchhoff cases passed a
  `GO_WITH_LIMITATIONS` audit. That audit did not promote public maturity or
  establish general geometric nonlinearity.
- **Coupled routes:** Owner-accepted bounded static material/geometric
  evidence exists for selected TET4/TET10/HEX8/HEX20 cases. It does not extend
  to friction, dynamics or distributed execution.
- **Contact:** frictionless penalty contact remains experimental and bounded.
  Frictional stick/slip has narrow prior Owner-accepted serial evidence, but
  current-source formal requalification is not established. Mesh sensitivity
  and search/sliding limits remain.
- **Robustness:** state transactions, retry, restart and continuation apply
  only where their route records say so. Arc-length evidence does not establish
  general bifurcation or postbuckling capability.

The [nonlinear mechanics overview](https://emptiesvoid-cloud.github.io/QF_solver/mechanics/nonlinear-overview/)
explains the architecture. A
[small nonlinear example](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/nonlinear-example/)
demonstrates a selected TET4 route and its engineering-profile warning;
convergence of that example is not a general maturity claim.

## Verification and maturity

QF Solver separates an implemented path, an executed test, a verified
invariant, external numerical correlation, an Owner-accepted maturity
decision, and physical validation. These are different kinds of evidence.
The [V&V and maturity guide](https://emptiesvoid-cloud.github.io/QF_solver/verification/evidence-and-maturity/)
defines the status labels; the
[0.2.10 verification summary](https://emptiesvoid-cloud.github.io/QF_solver/verification/0_2_10/)
links the newer bounded records.

Code_Aster 18.1 comparisons provide same-mesh **linear-static solver
correlation** for recorded TET4, HEX8, TET10 and HEX20 cases. They are not
physical validation or general nonlinear correlation. Internal independent
recomputation of selected observables is not a second global FEM/Newton solve.

Historical structured-TET4 large-model evidence includes recorded ~1.029M,
~3M, ~5.01264M and bounded ~10M DOF observations. The two complete 5M Silver replays
were recorded on the declared eight-rank environment. Separate two-rank
PETSc/MPI evidence covers selected linear-static cases with replicated input
and root-side assembly. No claim of GPU, general HPC, hardware-independent
scaling, mixed nonlinear support or general distributed assembly is made.
No claim of certification or universal physical validation is made.

## Limitations

- General finite-strain plasticity, nonlinear transient dynamics, universal
  postbuckling, finite-sliding/self-contact and impact/contact dynamics are
  outside the demonstrated scope.
- Higher-order nonlinear evidence is narrower than linear element support;
  frictional contact remains mesh-sensitive and is not generally requalified
  on the current source.
- Mixed Newmark/harmonic workflows, MITC4 modal, HEX8-SRI, the `.inp` subset
  and mixed HDF5 results have their own experimental or provisional bounds.
- Optional PETSc/MPI workflows do not establish general scalability,
  nonlinear distributed solving or a validated mixed-distributed runtime.

Read the [technical limitations](https://emptiesvoid-cloud.github.io/QF_solver/etat/limites/)
and the controlling capability record for the chosen route.

## Release and citation

| Item | Status |
| --- | --- |
| Release line | `0.2.10` |
| 0.2.11 candidate | Experimental rotating modal and Campbell routes; not yet published |
| Source tag | [`v0.2.10`](https://github.com/emptiesvoid-cloud/QF_solver/tree/v0.2.10) |
| PyPI distribution | [`qf-solver==0.2.10`](https://pypi.org/project/qf-solver/0.2.10/) |
| GitHub Release | [QF Solver 0.2.10](https://github.com/emptiesvoid-cloud/QF_solver/releases/tag/v0.2.10) |
| Version DOI | [`10.5281/zenodo.23106744`](https://doi.org/10.5281/zenodo.23106744) |
| Project concept DOI | [`10.5281/zenodo.22697897`](https://doi.org/10.5281/zenodo.22697897) |

QF Solver 0.2.10 is the first published release after 0.2.8. The intervening
`v0.2.9` tag is a source snapshot, not a PyPI, GitHub Release or Zenodo
version. For changes since the last published release, read
[What's New in 0.2.10](https://emptiesvoid-cloud.github.io/QF_solver/whats-new/0.2.10/)
or the [changelog](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CHANGELOG.md).

For reproducibility, cite the exact version DOI; use the concept DOI when
referring to the evolving project. The machine-readable record is
[`CITATION.cff`](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CITATION.cff).
It records the latest published 0.2.10 release; no 0.2.11 version DOI is
claimed while that candidate remains unpublished. The audited distribution
scope is the selected wheel and sdist. The whole-repository G03 archive gate
remains **FAIL** and WP14 remains on
**HOLD**. Automatic GitHub source archives—and the full-repository ZIP while
it remains attached to the Zenodo record—are **not** cleared distribution
artifacts. A DOI resolving does not change that boundary.

## Documentation

- [Documentation home](https://emptiesvoid-cloud.github.io/QF_solver/)
- [Elements](https://emptiesvoid-cloud.github.io/QF_solver/elements/) and
  [analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/)
- [Capability index](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/)
  and [known limitations](https://emptiesvoid-cloud.github.io/QF_solver/etat/limites/)
- [Public API contract](https://emptiesvoid-cloud.github.io/QF_solver/reference/qf_solver_api/)
  and [API stability](https://emptiesvoid-cloud.github.io/QF_solver/reference/api_stability/)
- [Benchmarks](https://emptiesvoid-cloud.github.io/QF_solver/benchmarks/) and
  [V&V evidence](https://emptiesvoid-cloud.github.io/QF_solver/verification/evidence-and-maturity/)

Development guidance is in
[`CONTRIBUTING.md`](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CONTRIBUTING.md).
Code is licensed under
[Apache-2.0](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/LICENSE);
documentation and original examples are under
[CC BY 4.0](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/LICENSE-DOCS).
Third-party terms are listed in
[`THIRD_PARTY_LICENSES.md`](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/THIRD_PARTY_LICENSES.md).
