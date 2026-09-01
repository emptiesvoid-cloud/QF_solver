FROM ghcr.io/fenics/dolfinx/dolfinx@sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8

RUN python3 -m pip install --no-cache-dir h5py==3.13.0

RUN python3 -c "import h5py, mpi4py, petsc4py; from mpi4py import MPI; from petsc4py import PETSc; assert h5py.__version__ == '3.13.0'; assert mpi4py.__version__ == '4.1.2'; assert petsc4py.__version__ == '3.25.1'; assert tuple(PETSc.Sys.getVersion()) == (3, 25, 1); print('WP17R PETSc', PETSc.Sys.getVersion(), 'MPI', MPI.Get_version())"

ENV PYTHONPATH=/workspace/src
WORKDIR /workspace

LABEL org.opencontainers.image.title="QF_solver WP17-R PETSc runtime" \
      org.opencontainers.image.version="0.2.7-wp17r" \
      org.opencontainers.image.description="Pinned PETSc/MPI runtime for WP17-R large TET4 diagnostics"
