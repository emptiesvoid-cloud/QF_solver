"""Minimal real PETSc/MPI smoke for the WP13-01C runtime environment."""

from __future__ import annotations

import json

from mpi4py import MPI
from petsc4py import PETSc


comm = PETSc.COMM_WORLD
size = comm.getSize()
rank = comm.getRank()
if size < 2:
    raise RuntimeError("WP13-01C PETSc smoke requires at least two MPI ranks.")

global_size = 4 * size
matrix = PETSc.Mat().createAIJ(size=(global_size, global_size), nnz=3, comm=comm)
matrix.setUp()
start, end = matrix.getOwnershipRange()
for row in range(start, end):
    matrix.setValue(row, row, 2.0)
    if row > 0:
        matrix.setValue(row, row - 1, -1.0)
    if row + 1 < global_size:
        matrix.setValue(row, row + 1, -1.0)
matrix.assemblyBegin()
matrix.assemblyEnd()

right = PETSc.Vec().createMPI(global_size, comm=comm)
right.set(1.0)
solution = right.duplicate()
ksp = PETSc.KSP().create(comm=comm)
ksp.setOperators(matrix)
ksp.setType(PETSc.KSP.Type.CG)
ksp.getPC().setType(PETSc.PC.Type.JACOBI)
ksp.setTolerances(rtol=1.0e-12)
ksp.solve(right, solution)
residual = right.duplicate()
matrix.mult(solution, residual)
residual.axpy(-1.0, right)
final_residual = residual.norm()

if rank == 0:
    print(
        json.dumps(
            {
                "mpi_vendor": MPI.get_vendor(),
                "ranks": size,
                "petsc_version": PETSc.Sys.getVersion(),
                "scalar_type": str(PETSc.ScalarType),
                "int_type": str(PETSc.IntType),
                "matrix_assembly": "PASS",
                "vector_assembly": "PASS",
                "ksp_type": ksp.getType(),
                "pc_type": ksp.getPC().getType(),
                "iterations": ksp.getIterationNumber(),
                "converged_reason": int(ksp.getConvergedReason()),
                "final_residual": final_residual,
            },
            sort_keys=True,
        ),
        flush=True,
    )
