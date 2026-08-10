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

Optional integrations such as Gmsh, h5py, mpi4py and PETSc/petsc4py must be
reviewed with the exact version installed before redistribution. They are not
relicensed by QF_solver.

## Verification references and external outputs

External solver outputs, benchmark values, publications and downloaded meshes
are not automatically covered by the Apache-2.0 or CC BY 4.0 licenses. Each
published artifact must retain its source, version, URL, license, SHA-256
digest and any applicable usage restrictions.

## Release rule

Before a public release, run the public-source and archive audits and review
every third-party artifact included in the release archive. Remove anything
whose redistribution terms are unknown or incompatible.
