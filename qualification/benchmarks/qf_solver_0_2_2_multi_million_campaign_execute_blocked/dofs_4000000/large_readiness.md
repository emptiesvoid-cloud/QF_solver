# Readiness grand modele

Statut: **FAIL**

- Backend: `petsc`
- DDL cible: 4000000
- Budget mémoire explicite: 34359738368 octets
- DDL estime: 4102893
- Noeuds estimes: 1367631
- Elements estimes: 7986000
- Memoire PETSc indicative: 8295463992 octets
- Borne haute SciPy indicative: 28017525432 octets

## Checks

- DEP-H5PY: **PASS** - h5py available
- DEP-MPI4PY: **PASS** - mpi4py available
- DEP-PETSC4PY: **FAIL** - petsc4py not installed
- BACKEND-SCALE: **PASS** - PETSc selected for scalable solve
- DISK-FREE: **PASS** - free=13526073344 bytes
- CHUNK-SIZE: **PASS** - chunk_size=4096
- MULTI-MILLION-GATE: **PASS** - backend=petsc, budget=34359738368 bytes, indicative requirement=8295463992 bytes
