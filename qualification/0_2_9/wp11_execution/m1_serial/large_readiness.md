# Readiness grand modele

Statut: **PASS**

- Backend: `scipy`
- DDL cible: 24
- Budget mémoire explicite: non fourni octets
- DDL estime: 24
- Noeuds estimes: 8
- Elements estimes: 6
- Memoire PETSc indicative: 46896 octets
- Borne haute SciPy indicative: 21552 octets

## Checks

- DEP-H5PY: **PASS** - h5py available
- DEP-MPI4PY: **PASS** - mpi4py available
- DEP-PETSC4PY: **PASS** - petsc4py not required for selected backend
- BACKEND-SCALE: **PASS** - SciPy allowed for ndof=24
- DISK-FREE: **PASS** - free=32489684992 bytes
- CHUNK-SIZE: **PASS** - chunk_size=4096
- MULTI-MILLION-GATE: **PASS** - not applicable below 2000000 target dofs
