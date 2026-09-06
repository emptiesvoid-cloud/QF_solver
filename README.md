# QF Solver

**An inspectable Python finite-element solver for structural mechanics.**

QF Solver provides white-box finite-element formulations, numerical diagnostics
and reproducible verification evidence. Support is always scoped by element,
analysis, material, mesh, loading and solver route. A passing example is not a
universal qualification.

## Install

```bash
pip install qf-solver
```

**QF Solver** is a Python FEM/FEA solver for structural mechanics and dynamics,
with transparent formulations, reproducible V&V, and optional PETSc/MPI
large-scale solving.

[Documentation](https://emptiesvoid-cloud.github.io/QF_solver/) ·
[When to use QF Solver](https://emptiesvoid-cloud.github.io/QF_solver/getting-started/when-to-use-qf-solver/)

## Capabilities

| Capability | Public status | Scope |
| --- | --- | --- |
| Linear static | `QUALIFIED_BOUNDED` | Recorded elastic element and load combinations. |
| Small-strain J2 | `QUALIFIED_BOUNDED` | TET4, TET10, HEX8 and HEX20 within the documented small-strain scope. |
| Modal, Newmark and harmonic | `SUPPORTED_WITH_LIMITATIONS` | Controlled linear cases with route-specific evidence. |
| Linear buckling | `SUPPORTED_WITH_LIMITATIONS` | Bounded family-specific sparse cases; no post-buckling claim. |
| Frictionless contact | `SUPPORTED_WITH_LIMITATIONS` | Bounded node-to-triangle cases; friction is outside this claim. |
| WEDGE6 static | `EXPERIMENTAL` | Controlled small-strain elastic vertical-slice workflow only. |
| WEDGE6 modal | `QUALIFIED_BOUNDED` | Homogeneous isotropic consistent-mass route, first three modes, declared scope only. |
| Large-model PETSc/MPI | `SUPPORTED_WITH_LIMITATIONS` | Recorded structured TET4 workloads and pinned environments only. |

The active combination matrix is in
[`docs/verification/0_2_7/0_2_7_capability_matrix.md`](docs/verification/0_2_7/0_2_7_capability_matrix.md).
It is the authoritative guide to what a particular combination means.

## Installation

For the stable source release:

```powershell
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
Set-Location QF_solver
git checkout v0.2.7
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
PETSc, MPI and SLEPc are optional integrations and are not required for the
core import or the standard small examples.

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

The current release includes bounded routes for TET4, TET10, HEX8 and HEX20,
along with case-bounded shell, beam and discrete paths. The status is explicit:
WEDGE6 static remains experimental. WEDGE6 modal qualification does not transfer to static,
nonlinear or other dynamic analyses.

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

- WEDGE6 static is experimental; WEDGE15 and PYRAMID5 are not supported.
- Mixed TET/WEDGE/HEX workflows and next-generation HEX8R/SRI/B-bar paths are
  deferred or research-only.
- Finite-kinematic J2, generalized nonlinear, contact and finite-sliding routes
  remain experimental or outside the qualified scope.
- 5M Gold and deeper 10M scaling analysis are deferred.
- Code_Aster correlation is bounded to comparable recorded cases. CalculiX is
  `NOT_COMPARABLE` where conventions or observables do not match strictly.
- Linux and Windows evidence is available in the recorded test matrix; macOS
  and some Python versions remain unverified and are not claimed as tested.

## Documentation and verification

- [Getting started](docs/getting-started/quickstart.md)
- [Elements](docs/elements/index.md)
- [Analyses](docs/analyses/index.md)
- [Solvers and backends](docs/solveurs/index.md)
- [Public roadmap](docs/reference/feuille_de_route.md)
- [0.2.7 verification summary](docs/verification/0_2_7/README.md)
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
