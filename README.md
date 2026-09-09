# QF Solver

**An inspectable Python finite-element solver for structural mechanics.**

QF Solver provides white-box finite-element formulations, numerical diagnostics
and reproducible verification evidence. Support is always scoped by element,
analysis, material, mesh, loading and solver route. A passing example is not a
universal qualification.

## Install

QF Solver `0.2.8` is currently a development candidate in release
preparation; it is not published yet. For the current source checkout:

```powershell
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
Set-Location QF_solver
python -m pip install .
qf-solver --version
```

When a published package is available, the corresponding package-index
installation is:

```bash
python -m pip install qf-solver
```

**QF Solver** is a Python FEM/FEA solver for structural mechanics and dynamics,
with transparent formulations, reproducible V&V, and optional PETSc/MPI
large-scale solving.

[Documentation](https://emptiesvoid-cloud.github.io/QF_solver/) ·
[Capability index](https://emptiesvoid-cloud.github.io/QF_solver/capabilities/) ·
[When to use QF Solver](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/when-to-use-qf-solver/) ·
[Compare FEM solvers](https://emptiesvoid-cloud.github.io/QF_solver/comparisons/)
[Benchmarks](https://emptiesvoid-cloud.github.io/QF_solver/benchmarks/)

## Capabilities

| Capability | Public status | Scope |
| --- | --- | --- |
| Linear static | `QUALIFIED_BOUNDED` | Recorded elastic element and load combinations. |
| Small-strain J2 | `QUALIFIED_BOUNDED` | TET4, TET10, HEX8 and HEX20 within the documented small-strain scope. |
| Modal, Newmark and harmonic | `SUPPORTED_WITH_LIMITATIONS` | Controlled linear cases with route-specific evidence. |
| Linear buckling | `SUPPORTED_WITH_LIMITATIONS` | Bounded family-specific sparse cases; no post-buckling claim. |
| Frictionless contact | `EXPERIMENTAL_BOUNDED` | Penalty node-to-triangle, frictionless small-sliding cases only. |
| WEDGE6 static | `QUALIFIED_BOUNDED` | Gmsh Prism 6, small-strain isotropic linear elasticity and the documented bounded load/mesh scope. |
| WEDGE6 modal | `QUALIFIED_BOUNDED` | Homogeneous isotropic consistent-mass route, first three modes, declared scope only. |
| Mixed static, modal, translational MPC and multi-material | `QUALIFIED_BOUNDED` | Connected conforming serial TET4/WEDGE6/HEX8 benchmarks and their documented limitations only. |
| Mixed Newmark and harmonic | `EXPERIMENTAL_BOUNDED` | Connected serial TET4/WEDGE6/HEX8 frozen dynamic benchmarks only. |
| Bounded Abaqus/CalculiX `.inp` subset | `EXPERIMENTAL_BOUNDED` | Five documented fixtures; this is not general format compatibility. |
| Family-aware mixed HDF5 results | `EXPERIMENTAL_BOUNDED` | Opt-in schema-v1.0 TET4/WEDGE6/HEX8 storage and selective reads. |
| HEX8-SRI | `EXPERIMENTAL_BOUNDED` | Separate locking-sensitive linear-elastic research capability; not locking-free. |
| PYRAMID5 | `INTERNAL_RESEARCH_ONLY` | Internal feasibility kernel; not a supported public element. |
| Mixed distributed PETSc/MPI | `NOT_VALIDATED` | Architecture foundation only; runtime physical and partition gates remain failed. |
| Large-model PETSc/MPI | `SUPPORTED_WITH_LIMITATIONS` | Recorded structured TET4 workloads and pinned environments only. |

The authoritative 0.2.8 source is the tracked
[`qualification/0_2_8/consolidated_registry.json`](qualification/0_2_8/consolidated_registry.json):
32 `QUALIFIED_BOUNDED`, 14 `EXPERIMENTAL`, 0 `NOT_QUALIFIED`, 46 element-analysis
records. Mixed workflows and separate capabilities are not added to those 46.

## Installation

For the current 0.2.8 development source (no tag or publication is implied):

```powershell
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
Set-Location QF_solver
python -m pip install .
qf-solver --version
```

When the package is available from the package index, the equivalent user
installation is:

```powershell
python -m pip install qf-solver
qf-solver --version
```

Optional development and integration extras are documented in
[`docs/getting-started/installation.md`](docs/getting-started/installation.md).
HDF5, PETSc, MPI and SLEPc are optional integrations and are not required for
the core import or the standard small examples.

## Quick start: CLI

From the repository root, run the maintained TET4 example:

```powershell
qf-solver check-mesh --input .\examples\tet4_static.json
qf-solver solve --input .\examples\tet4_static.json --output .\results\tet4.json
```

The full first-calculation guide is
[`docs/getting-started/quickstart.md`](docs/getting-started/quickstart.md).

## Quick start: Python

Use the public `qf_solver` namespace:

```python
from qf_solver import check_mesh, load_model, save_result, solve_model

model = load_model("examples/tet4_static.json")
check_mesh(model)
result = solve_model(model)
save_result(result, "results/tet4.json")
```

The historical `solveur` namespace remains available for compatibility. New
applications should use `qf_solver`; see
[`docs/reference/api_stability.md`](docs/reference/api_stability.md).

## Elements and analyses

The public element summary is in
[`docs/elements/index.md`](docs/elements/index.md), and the analysis summary is
in [`docs/analyses/index.md`](docs/analyses/index.md).

The current 0.2.8 development baseline includes bounded routes for TET4, TET10, HEX8 and HEX20,
along with case-bounded shell, beam and discrete paths. The status is explicit:
WEDGE6 static and modal are `QUALIFIED_BOUNDED` only in their distinct recorded
scopes. That qualification does not transfer to nonlinear or general dynamic
analyses.

## Measured performance

The published performance evidence is bounded, not a universal scaling law:

| Workload | Recorded result | Boundary |
| --- | --- | --- |
| 1,029,000 DOF | Two stable PETSc replays | Structured TET4, recorded host and MPI container. |
| 3,000,000 DOF | Two Silver replays plus bounded Gold Compute evidence | Same frozen PETSc/CG/GAMG route. |
| 5,012,640 DOF | Bronze and two complete 5M Silver replays | 9,773,946 TET4 elements, recorded 8-rank environment. |
| 10,125,000 DOF | C3 `PASS_WITH_LIMITATIONS` evidence | Complete solve evidence exists; deeper scaling analysis remains bounded. |

No claim of GPU, general HPC, hardware-independent scaling, mixed-mesh support
or a general nonlinear performance claim is made.

## Main limitations

- WEDGE6 static and modal are bounded to their separately documented scopes;
  WEDGE15 is not supported and PYRAMID5 remains internal research only.
- Mixed static, modal, translational-MPC and multi-material workflows are
  qualified only on their connected conforming serial TET4/WEDGE6/HEX8 scopes.
- Mixed Newmark, mixed harmonic, bounded `.inp`, mixed HDF5 and frictionless
  contact capabilities remain `EXPERIMENTAL_BOUNDED`.
- Mixed distributed PETSc/MPI is `NOT_VALIDATED`; no partial 2-rank or general
  distributed mixed claim is made.
- HEX8-SRI is a separate `EXPERIMENTAL_BOUNDED` capability; no locking-free,
  arbitrary-distortion or production claim is made. HEX8R and B-bar remain deferred.
- Finite-kinematic J2, generalized nonlinear, contact and finite-sliding routes
  remain experimental or outside the qualified scope.
- 5M Gold and deeper 10M scaling analysis are deferred.
- Code_Aster correlation is bounded to comparable recorded cases. CalculiX is
  `NOT_COMPARABLE` where conventions or observables do not match strictly.
- Linux and Windows evidence is available in the recorded test matrix; macOS
  and some Python versions remain unverified and are not claimed as tested.

## Documentation and verification

- [Getting started](docs/getting-started/quickstart.md)
- [0.2.8 capability index](docs/capabilities/index.md)
- [What's New in 0.2.8](docs/whats-new/0.2.8.md)
- [Elements](docs/elements/index.md)
- [Analyses](docs/analyses/index.md)
- [Solvers and backends](docs/solveurs/index.md)
- [Public roadmap](docs/reference/feuille_de_route.md)
- [0.2.8 verification summary](docs/verification/0_2_8/README.md)
- [V&V and maturity model](docs/verification/evidence-and-maturity.md)
- [Historical 0.2.7 verification summary](docs/verification/0_2_7/README.md)
- [API stability](docs/reference/api_stability.md)
- [Detailed changelog](CHANGELOG.md)

QF Solver distinguishes `IMPLEMENTED`, `TESTED`, `VERIFIED`,
`EXTERNALLY_VALIDATED`, `QUALIFIED` and `EXPERIMENTAL`. The detailed evidence
pack preserves the exact inputs, outputs, manifests and source references used
for each recorded result.

No claim of certification or universal physical validation is made.

## Contributing, license and citation

Development setup and quality checks are described in
[`CONTRIBUTING.md`](CONTRIBUTING.md). The software is distributed under the
[Apache License 2.0](LICENSE); documentation and original examples are under
[`CC BY 4.0`](LICENSE-DOCS). Third-party terms are listed in
[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md). See
[`CITATION.cff`](CITATION.cff) for citation metadata.

Documentation contributors can build the controlled evidence locally with:

```powershell
python .\scripts\build_docs.py --profile engineering
python .\scripts\build_technical_latex.py
```
