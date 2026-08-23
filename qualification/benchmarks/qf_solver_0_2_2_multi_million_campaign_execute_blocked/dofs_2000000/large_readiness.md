# Readiness grand modele

Statut: **FAIL**

- Backend: `petsc`
- DDL cible: 2000000
- Budget mémoire explicite: 34359738368 octets
- DDL estime: 2044416
- Noeuds estimes: 681472
- Elements estimes: 3951018
- Memoire PETSc indicative: 4132385424 octets
- Borne haute SciPy indicative: 13861824912 octets

## Checks

- DEP-H5PY: **PASS** - h5py available
- DEP-MPI4PY: **PASS** - mpi4py available
- DEP-PETSC4PY: **FAIL** - petsc4py not installed
- BACKEND-SCALE: **PASS** - PETSc selected for scalable solve
- DISK-FREE: **PASS** - free=13526085632 bytes
- CHUNK-SIZE: **PASS** - chunk_size=4096
- MULTI-MILLION-GATE: **PASS** - backend=petsc, budget=34359738368 bytes, indicative requirement=4132385424 bytes
