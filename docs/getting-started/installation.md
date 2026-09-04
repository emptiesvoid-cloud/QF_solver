---
doc_id: DOC-START-PUB-001
revision: 1.0
status: controlled
applicable_version: 0.2.7
reviewer: ""
approver: ""
---

# Installation

## User installation

Install the stable package when it is available from the package index:

```powershell
python -m pip install qf-solver
qf-solver --version
```

For a reproducible source checkout, use the stable tag:

```powershell
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
Set-Location QF_solver
git checkout v0.2.7
python -m pip install .
qf-solver --version
```

The core package requires Python 3.10 or newer. The public import is:

```python
import qf_solver
print(qf_solver.__version__)
```

## Optional extras

The optional extras are intended for specific workflows:

```powershell
python -m pip install "qf-solver[mesh]"
python -m pip install "qf-solver[large]"
python -m pip install "qf-solver[hpc]"
```

`mesh` adds mesh tooling. `large` adds HDF5 and MPI/PETSc support used by the
large-model route. `hpc` adds the optional SLEPc integration. These extras are
not required for core import or small standard examples.

## Development installation

For project development only:

```powershell
git clone https://github.com/emptiesvoid-cloud/QF_solver.git
Set-Location QF_solver
git checkout v0.2.7
python -m pip install -e ".[test,dev]"
```

Development extras do not expand the qualified numerical scope. PETSc/MPI
availability depends on the host and is reported explicitly by the relevant
commands.
