# Third-party licenses

QF_solver combines original source code with dependencies and reference
materials that remain governed by their own terms. This file is a starting
inventory for release review; it is not a replacement for the license files
distributed by each upstream project.

## Runtime dependencies

| Component | Use | License/reference |
| --- | --- | --- |
| NumPy | numerical arrays and linear algebra | [NumPy licenses](https://numpy.org/doc/stable/license.html) |
| SciPy | sparse matrices and numerical solvers | [SciPy license](https://github.com/scipy/scipy/blob/main/LICENSE.txt) |
| Matplotlib | plots and generated figures | [Matplotlib license](https://matplotlib.org/stable/project/license.html) |

## Optional integrations and documentation tooling

The following packages are optional integrations or documentation tooling. Their
upstream terms remain applicable; the exact installed version must be reviewed
before redistribution. They are not relicensed by QF_solver.

| Component | Extra/use | Upstream reference |
| --- | --- | --- |
| Gmsh | `mesh` and documentation mesh examples | [Gmsh](https://gmsh.info/) |
| h5py | `hdf5` and `large` result storage | [h5py](https://github.com/h5py/h5py) |
| mpi4py | `large`/`hpc` MPI bindings | [mpi4py](https://github.com/mpi4py/mpi4py) |
| PETSc / petsc4py | `large`/`hpc` sparse solver bindings | [PETSc](https://petsc.org/) and [petsc4py](https://gitlab.com/petsc/petsc4py) |
| SLEPc / slepc4py | `hpc` eigensolver bindings | [SLEPc](https://slepc.upv.es/) and [slepc4py](https://gitlab.com/slepc/slepc4py) |
| MkDocs | `docs` public-site builder | [MkDocs](https://www.mkdocs.org/) |
| Material for MkDocs | `docs` public-site theme | [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) |

Test and engineering-only helpers such as pytest, pytest-cov, psutil, PyYAML,
Ruff, mypy, Hypothesis, ReportLab, svglib and pypdf are likewise governed by
their upstream terms. They are not runtime solver dependencies.

## Verification references and external outputs

External solver outputs, benchmark values, publications and downloaded meshes
are not automatically covered by the Apache-2.0 or CC BY 4.0 licenses. Each
published artifact must retain its source, version, URL, license, SHA-256
digest and any applicable usage restrictions.

## Release rule

Before a public release, run the public-source and archive audits and review
every third-party artifact included in the release archive. Remove anything
whose redistribution terms are unknown or incompatible.
