"""Compare AIJ and block-assembled matrices on a small controlled model."""

from __future__ import annotations

import argparse

import numpy as np
from petsc4py import PETSc

from solveur.api import load_large_model
from solveur.large.assembler import PetscTET4Assembler


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    model = load_large_model(args.input)
    if model.ndof > 1000:
        raise ValueError("Matrix-format comparison is limited to 1000 dofs.")
    indices = np.arange(model.ndof, dtype=PETSc.IntType)
    aij = PetscTET4Assembler(matrix_format="aij").assemble(model)
    baij = PetscTET4Assembler(matrix_format="baij").assemble(model)
    a = np.asarray(aij.getValues(indices, indices))
    b = np.asarray(baij.getValues(indices, indices))
    difference = a - b
    print("relative_matrix_error", np.linalg.norm(difference) / np.linalg.norm(a))
    print("max_matrix_error", np.max(np.abs(difference)))
    location = np.unravel_index(np.argmax(np.abs(difference)), difference.shape)
    print("max_error_location", location, "aij", a[location], "baij", b[location])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
