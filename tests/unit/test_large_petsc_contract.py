from __future__ import annotations

from types import SimpleNamespace

import numpy as np

from solveur.large import solver
from solveur.large.generator import generate_tet4_block


class _FakeVec:
    def __init__(self, size: int) -> None:
        self.data = np.zeros(size, dtype=float)

    def setValues(self, indices, values, addv=None) -> None:
        if str(addv).endswith("ADD"):
            self.data[np.asarray(indices, dtype=int)] += np.asarray(values, dtype=float)
        else:
            self.data[np.asarray(indices, dtype=int)] = np.asarray(values, dtype=float)

    def setValue(self, index: int, value: float, addv=None) -> None:
        self.data[index] = value

    def assemble(self) -> None:
        return None

    def duplicate(self):
        return _FakeVec(self.data.size)

    def getOwnershipRange(self):
        return 0, self.data.size

    def getArray(self, readonly=False):
        return self.data

    def norm(self) -> float:
        return float(np.linalg.norm(self.data))

    def copy(self):
        result = _FakeVec(self.data.size)
        result.data[:] = self.data
        return result

    def axpy(self, alpha: float, other) -> None:
        self.data[:] += alpha * other.data

    def dot(self, other) -> float:
        return float(np.dot(self.data, other.data))


class _FakeMatrix:
    def __init__(self, size: int) -> None:
        self.size = size

    def createVecRight(self):
        return _FakeVec(self.size)

    def mult(self, vector, output) -> None:
        output.data[:] = 2.0 * vector.data


class _FakePC:
    def __init__(self) -> None:
        self.kind = "none"

    def setType(self, value: str) -> None:
        self.kind = value

    def getType(self) -> str:
        return self.kind

    def getHYPREType(self):
        return None


class _FakeKSP:
    def __init__(self) -> None:
        self.pc = _FakePC()
        self.kind = "cg"
        self.solution = None

    def create(self):
        return self

    def setOperators(self, matrix) -> None:
        self.matrix = matrix

    def setType(self, value: str) -> None:
        self.kind = value

    def getPC(self):
        return self.pc

    def setTolerances(self, **kwargs) -> None:
        self.tolerances = kwargs

    def setInitialGuessNonzero(self, value: bool) -> None:
        self.initial_guess_nonzero = value

    def setFromOptions(self) -> None:
        return None

    def setUp(self) -> None:
        return None

    def solve(self, rhs, solution) -> None:
        solution.data[:] = 1.0
        self.solution = solution

    def getConvergedReason(self) -> int:
        return 1

    def getIterationNumber(self) -> int:
        return 3

    def getResidualNorm(self) -> float:
        return 1.0e-12

    def getType(self) -> str:
        return self.kind


class _FakeOptions:
    values: dict[str, object] = {}

    def hasName(self, key: str) -> bool:
        return key in self.values

    def __setitem__(self, key: str, value: object) -> None:
        self.values[key] = value


class _FakeComm:
    rank = 0
    size = 1

    def allreduce(self, value, op=None):
        return value

    def allgather(self, value):
        return [value]

    def bcast(self, value, root=0):
        return value

    def Barrier(self) -> None:
        return None


class _FakePetscAssembler:
    def __init__(self, chunk_size: int, matrix_format: str) -> None:
        self.chunk_size = chunk_size
        self.matrix_format = matrix_format

    def assemble(self, model):
        return _FakeMatrix(model.ndof)


def test_petsc_contract_covers_serial_ksp_metrics_without_claiming_hpc(monkeypatch, tmp_path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    comm = _FakeComm()
    fake_petsc = SimpleNamespace(
        IntType=np.int32,
        InsertMode=SimpleNamespace(ADD_VALUES="ADD", INSERT_VALUES="INSERT"),
        KSP=_FakeKSP,
        Options=_FakeOptions,
        MAX="MAX",
    )
    audit = SimpleNamespace(
        status="PASS",
        errors=(),
        warnings=(),
        details={"ndof": model.ndof},
        to_dict=lambda: {"status": "PASS", "errors": [], "warnings": [], "details": {"ndof": model.ndof}},
    )
    monkeypatch.setattr(solver, "_require_mpi4py", lambda: None)
    monkeypatch.setattr(solver, "_petsc", lambda: fake_petsc)
    monkeypatch.setattr(solver, "_mpi", lambda: SimpleNamespace(DOUBLE="DOUBLE", MAX="MAX"))
    monkeypatch.setattr(solver, "_mpi_comm", lambda: comm)
    monkeypatch.setattr(solver, "PetscTET4Assembler", _FakePetscAssembler)
    monkeypatch.setattr(solver, "fixed_dof_indices", lambda value: np.asarray([0], dtype=np.int64))
    monkeypatch.setattr(solver, "assemble_loads", lambda value: np.zeros(value.ndof))
    monkeypatch.setattr(solver, "petsc_ksp_diagnostics", lambda ksp, matrix: {"contract": "PASS"})
    monkeypatch.setattr(solver, "inspect_large_model", lambda *args, **kwargs: audit)
    monkeypatch.setattr(solver, "_gather_petsc_displacement", lambda solution, ndof, value: (np.ones(ndof), [[0, ndof]]))
    monkeypatch.setattr(solver, "_mpi_trace", lambda *args: None)

    result, displacement = solver._solve_petsc(
        model,
        preconditioner="jacobi",
        chunk_size=128,
        params={"ksp_type": "cg", "pc_type": "jacobi", "max_it": 25},
        distributed_output_dir=None,
    )

    assert result.status == "PASS"
    assert result.backend == "petsc"
    assert result.summary["solver"]["iterations"] == 3
    assert result.summary["solver"]["preconditioner_diagnostics"] == {"contract": "PASS"}
    assert result.summary["mpi"]["size"] == 1
    assert np.array_equal(displacement, np.ones(model.ndof))
