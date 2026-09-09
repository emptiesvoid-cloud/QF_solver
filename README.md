# QF Solver

[![Python](https://img.shields.io/pypi/pyversions/qf-solver.svg)](https://pypi.org/project/qf-solver/)
[![PyPI](https://img.shields.io/pypi/v/qf-solver.svg)](https://pypi.org/project/qf-solver/)
[![License](https://img.shields.io/github/license/emptiesvoid-cloud/QF_solver.svg)](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/LICENSE)
[![Documentation](https://img.shields.io/badge/docs-GitHub%20Pages-2f80ed.svg)](https://emptiesvoid-cloud.github.io/QF_solver/)
[![CI](https://github.com/emptiesvoid-cloud/QF_solver/actions/workflows/quality.yml/badge.svg)](https://github.com/emptiesvoid-cloud/QF_solver/actions/workflows/quality.yml)

Python FEM/FEA solver for structural mechanics and dynamics, with inspectable
formulations, reproducible V&V and bounded large-model workflows.

QF Solver is deliberately evidence-led: support is scoped by element,
analysis, material, mesh, loading and solver route. A passing example is not a
universal qualification.

On this page: [Why QF Solver?](README.md#why-qf-solver) ·
[Installation](README.md#installation) · [Quick start](README.md#quick-start) ·
[Main capabilities](README.md#main-capabilities) ·
[Verification](README.md#verification-and-maturity) ·
[Performance](README.md#performance-context) · [Limitations](README.md#limitations) ·
[Documentation](README.md#documentation) ·
[Contributing](README.md#contributing-citation-and-license) ·
[CLI](README.md#command-line) · [Python API](README.md#python) ·
[Status labels](README.md#verification-and-maturity) ·
[Performance table](README.md#performance-context) ·
[Limitations](README.md#limitations)

## Why QF Solver?

- Python-native API and inspectable finite-element implementations.
- Numerical diagnostics intended to make assumptions and failure modes visible.
- Reproducible verification evidence with explicit capability maturity.
- Optional integrations for bounded HDF5 and PETSc/MPI large-model workflows.

Current source version: `0.2.8`. See [GitHub Releases](https://github.com/emptiesvoid-cloud/QF_solver/releases)
and [PyPI](https://pypi.org/project/qf-solver/) for published availability.

## Installation

For a published package:

```bash
python -m pip install qf-solver
qf-solver --version
```

To evaluate the current pre-publication source candidate specifically:

```bash
git clone --branch 0.2.8-pre-publication https://github.com/emptiesvoid-cloud/QF_solver.git
cd QF_solver
python -m pip install .
qf-solver --version
```

Use the matching release tag or source archive when one is published. Optional
development and integration extras are described in the
[installation guide](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/installation/).
HDF5, PETSc, MPI and SLEPc remain optional integrations and are not required
for the core import or standard small examples.

## Quick start

### Command line

From the repository root, run the maintained TET4 example:

```bash
qf-solver check-mesh --input examples/tet4_static.json
qf-solver solve --input examples/tet4_static.json --output results/tet4.json
```

See the [first-calculation guide](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/quickstart/)
for the complete workflow.

### Python

Use the public `qf_solver` namespace:

```python
from qf_solver import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
check_mesh(model)
result = solve_model(model)
save_result(result, "results/tet4.json")
```

The historical `solveur` namespace remains available for compatibility. New
applications should use `qf_solver`; see the
[API stability guide](https://emptiesvoid-cloud.github.io/QF_solver/reference/api_stability/).

## Main capabilities

The public status model is bounded and route-specific. The
[central capability index](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/)
links each status to its evidence and limitations.

| Capability | Status | Boundary |
| --- | --- | --- |
| Linear static and small-strain solid routes | `QUALIFIED_BOUNDED` | Recorded element/material/load combinations only. |
| WEDGE6 static | `QUALIFIED_BOUNDED` | Documented Gmsh Prism 6 static scope. |
| WEDGE6 modal | `QUALIFIED_BOUNDED` | Documented homogeneous consistent-mass modal scope. |
| Mixed static, modal, translational MPC and multi-material | `QUALIFIED_BOUNDED` | Connected conforming serial TET4/WEDGE6/HEX8 workflows. |
| Mixed Newmark and harmonic | `EXPERIMENTAL_BOUNDED` | Connected serial TET4/WEDGE6/HEX8 frozen dynamic cases. |
| Bounded Abaqus/CalculiX `.inp` subset | `EXPERIMENTAL_BOUNDED` | Documented subset; not general format compatibility. |
| Family-aware mixed HDF5 results | `EXPERIMENTAL_BOUNDED` | Opt-in schema 1.0 storage and selective reads. |
| Frictionless contact | `EXPERIMENTAL_BOUNDED` | Penalty node-to-triangle, bounded small-sliding cases. |
| HEX8-SRI | `EXPERIMENTAL_BOUNDED` | Locking-sensitive linear-elastic capability; not locking-free. |
| MITC4 modal | `EXPERIMENTAL` | Experimental route with its recorded scope. |
| Mixed distributed PETSc/MPI | `NOT_VALIDATED` | Architecture evidence only; no validated runtime claim. |
| PYRAMID5 | `INTERNAL` / `RESEARCH_ONLY` | Internal feasibility path; not a supported public element. |

The authoritative [0.2.8 element-analysis registry](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/qualification/0_2_8/consolidated_registry.json)
contains 32 `QUALIFIED_BOUNDED`, 14 `EXPERIMENTAL`, 0 `NOT_QUALIFIED` and 46
records. Mixed workflows and separate capabilities are not added to those 46
records.

## Verification and maturity

Qualification records use prospective contracts, frozen gates, reproducible
evidence, replay checks and failure cases. The maturity labels mean:

- `QUALIFIED_BOUNDED`: frozen gates passed within the declared scope; not a universal claim.
- `EXPERIMENTAL_BOUNDED`: usable route with bounded evidence and explicit limitations.
- `EXPERIMENTAL`: evidence exists, but the route remains below bounded qualification.
- `RESEARCH_ONLY`: discovery or feasibility work; no production support claim.
- `NOT_VALIDATED`: implementation or architecture exists, but required runtime evidence is absent or failed.
- `INTERNAL`: not part of the supported public surface.

Read the [V&V and maturity model](https://emptiesvoid-cloud.github.io/QF_solver/verification/evidence-and-maturity/)
and the [0.2.8 verification summary](https://emptiesvoid-cloud.github.io/QF_solver/verification/0_2_8/).

## Performance context

Recorded large-model results are historical, bounded evidence for structured
TET4 workloads in documented PETSc/MPI environments:

| Workload | Recorded context | Boundary |
| --- | --- | --- |
| ~1.029M DOF | Two stable PETSc replays | Structured TET4 only. |
| ~3M DOF | Silver replays and bounded Gold evidence | Same recorded route and environment. |
| ~5.01264M DOF | Bronze and two complete 5M Silver replays | Structured TET4, recorded 8-rank environment. |
| ~10M DOF | Bounded C3 capacity/solve context | Not a universal scaling guarantee. |

No claim of GPU, general HPC, hardware-independent scaling, mixed-mesh support
or general nonlinear scaling is made. The mixed distributed PETSc/MPI runtime
remains `NOT_VALIDATED`.

## Limitations

- General nonlinear dynamics and finite-kinematic material routes are not production-qualified.
- PYRAMID5 is internal/research only; WEDGE15 is not supported.
- MITC4 modal remains `EXPERIMENTAL`.
- HEX8-SRI remains `EXPERIMENTAL_BOUNDED`, not locking-free or universally robust.
- The `.inp` reader supports a bounded Abaqus/CalculiX subset only.
- Contact is limited to the documented frictionless penalty node-to-triangle scope.
- Mixed Newmark and harmonic are bounded linear serial workflows.
- Mixed distributed PETSc/MPI is `NOT_VALIDATED`; no partial-rank or general distributed claim is made.

See the dedicated [limitations page](https://emptiesvoid-cloud.github.io/QF_solver/etat/limites/)
and [solver/backend notes](https://emptiesvoid-cloud.github.io/QF_solver/solveurs/).

## Documentation

- [Getting started](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/quickstart/)
- [Capability index](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/)
- [Elements](https://emptiesvoid-cloud.github.io/QF_solver/elements/)
- [Analyses](https://emptiesvoid-cloud.github.io/QF_solver/analyses/)
- [What's New in 0.2.8](https://emptiesvoid-cloud.github.io/QF_solver/whats-new/0.2.8/)
- [Benchmarks](https://emptiesvoid-cloud.github.io/QF_solver/benchmarks/)
- [V&V and maturity](https://emptiesvoid-cloud.github.io/QF_solver/verification/evidence-and-maturity/)
- [API stability](https://emptiesvoid-cloud.github.io/QF_solver/reference/api_stability/)
- [Historical 0.2.7 verification](https://emptiesvoid-cloud.github.io/QF_solver/verification/0_2_7/)
- [Detailed changelog](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CHANGELOG.md)

## Contributing, citation and license

Development setup and quality checks are described in
[CONTRIBUTING.md](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CONTRIBUTING.md).
QF Solver is distributed under the
[Apache License 2.0](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/LICENSE);
documentation and original examples are under
[CC BY 4.0](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/LICENSE-DOCS).
Third-party terms are listed in
[THIRD_PARTY_LICENSES.md](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/THIRD_PARTY_LICENSES.md).
For citation metadata, see
the [CITATION.cff file](https://github.com/emptiesvoid-cloud/QF_solver/blob/main/CITATION.cff).

No claim of certification or universal physical validation is made.
