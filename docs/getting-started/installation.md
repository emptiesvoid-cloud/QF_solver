---
doc_id: DOC-START-PUB-001
revision: 1.0
status: controlled
applicable_version: 0.2.8
reviewer: ""
approver: ""
---

# Installation

QF Solver `0.2.8` is published on [PyPI](https://pypi.org/project/qf-solver/).
The [central capability index](../capabilities/index.md) and
[What's New](../whats-new/0.2.8.md) describe its bounded public scope.

## User installation

Install the published package from the package index:

```bash
python -m pip install qf-solver
qf-solver --version
```

An unqualified clone follows the repository default branch; it is not a
release selector. Select the immutable release tag explicitly when
reproducibility matters:

```bash
git clone --branch v0.2.8 --single-branch https://github.com/emptiesvoid-cloud/QF_solver.git
cd QF_solver
python -m pip install .
qf-solver --version
```

The default branch is not a promise that it contains a specific release.

The core package requires Python 3.10 or newer. The public import is:

```python
import qf_solver
print(qf_solver.__version__)
```

## Optional extras

The optional extras are intended for specific workflows:

```bash
python -m pip install "qf-solver[mesh]"
python -m pip install "qf-solver[hdf5]"
python -m pip install "qf-solver[large]"
python -m pip install "qf-solver[hpc]"
python -m pip install "qf-solver[docs]"
```

`mesh` adds mesh tooling. `hdf5` adds only the optional family-aware HDF5
result dependency. `large` adds HDF5 and MPI/PETSc support used by the
large-model route. `hpc` adds the optional SLEPc integration. `docs` adds the
MkDocs/MkDocs Material site builder and the controlled Markdown/PDF tooling.
These extras are not required for core import or small standard examples.
Calling an HDF5 API without `h5py` raises a typed `InfrastructureError`;
importing `qf_solver` does not require `h5py`.

The `large` and `hpc` extras expose Python bindings to native MPI, PETSc and
SLEPc environments; they do not make those native runtimes universally
installable through pip. The recorded PETSc/MPI environments are Linux
conda/container setups, and native Windows compatibility is environment-specific
and not guaranteed. The mixed distributed PETSc/MPI runtime remains
`NOT_VALIDATED`.

From a repository checkout, the public documentation site can be built with:

```bash
python -m pip install ".[docs]"
python -m mkdocs build --strict -f .github/pages/mkdocs.yml
```

## Development installation

For project development only:

```bash
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
cd QF_solver
python -m pip install -e ".[test,dev]"
```

Development extras do not expand the qualified numerical scope. PETSc/MPI
availability depends on the host and is reported explicitly by the relevant
commands.

## Distribution traceability data

The wheel and source distribution include only the lightweight public 0.2.8
traceability set: the consolidated 46-record element-analysis registry and the
HEX8-SRI, mixed-dynamics, mixed-MPC, mixed-multimaterial, `.inp`, mixed-HDF5
and contact owner/delivery records. Historical 0.2.7 capability metadata is
retained separately.

Raw NPZ/HDF5 arrays, full campaign output, caches, debug artifacts and
temporary files are intentionally excluded from package data. They remain
repository evidence and are not required for importing or using the base
package.
