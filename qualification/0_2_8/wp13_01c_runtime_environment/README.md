# WP13-01C PETSc/MPI runtime environment

This optional Docker image isolates the PETSc runtime from the Windows Python
installation.  It uses conda-forge Linux packages for Python, MPICH, PETSc,
mpi4py and petsc4py.  It is a prerequisite environment only: it neither
executes the WP13-01C mixed campaign nor changes QF Solver numerical source.

Build from the repository root:

```powershell
docker build -t qf-solver-wp13-01c-petsc:2026-09 -f qualification/0_2_8/wp13_01c_runtime_environment/Dockerfile .
```

Run the real PETSc/MPI smoke with the repository mounted read-only:

```powershell
docker run --rm -v "${PWD}:/workspace:ro" -w /workspace qf-solver-wp13-01c-petsc:2026-09 mpiexec -n 2 python qualification/0_2_8/wp13_01c_runtime_environment/petsc_mpi_smoke.py
```

The QF Solver source is imported through `PYTHONPATH=/workspace/src`; no
optional PETSc dependency is added to the public package installation.
