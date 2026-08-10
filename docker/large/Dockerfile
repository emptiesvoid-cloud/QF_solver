FROM ghcr.io/fenics/dolfinx/dolfinx@sha256:2ae4bfbc0d9077268880faf04c72750528bee986c94ab223a2c159969bd56fa8

RUN python3 -m pip install --no-cache-dir h5py==3.13.0

ENV PYTHONPATH=/workspace
WORKDIR /workspace

LABEL org.opencontainers.image.title="QF_solver large-scale runtime" \
      org.opencontainers.image.version="0.2.0" \
      org.opencontainers.image.description="Pinned PETSc/MPI runtime for QF_solver large TET4 campaigns"
