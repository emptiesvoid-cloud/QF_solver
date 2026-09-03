from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from solveur.core.errors import InfrastructureError, MeshValidationError
from solveur.large.audit import LargeAuditReport
from solveur.large.generator import generate_tet4_block
from solveur.large import solver


def test_large_result_to_dict_and_distributed_outputs(tmp_path: Path) -> None:
    audit = LargeAuditReport(status="PASS", errors=(), warnings=(), details={})
    result = solver.LargeSolveResult("PASS", "petsc", {"ndof": 12}, audit)
    encoded = result.to_dict()
    assert encoded["audit"]["status"] == "PASS"
    files = solver._write_distributed_outputs(result, tmp_path / "distributed")
    assert files["displacements"] == "displacements.bin"
    assert json.loads((tmp_path / "distributed" / "summary.json").read_text()) == {"ndof": 12}


def test_large_hdf5_output_contains_layout_metadata(tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    path = tmp_path / "displacements.h5"
    solver._write_displacements_hdf5(model, np.zeros(model.ndof), path)
    import h5py

    with h5py.File(path, "r") as handle:
        assert handle["displacements"].shape == (model.node_count, 3)
        assert handle.attrs["layout"] == "node_by_translation_component"


def test_large_matrix_free_private_path_returns_diagnostics(tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    result, displacement = solver._solve_matrix_free(model, chunk_size=2, params={"max_it": 1000})
    assert result.status == "PASS"
    assert result.backend == "matrix_free"
    assert result.summary["solver"]["converged"] is True
    assert displacement.shape == (model.ndof,)


def test_large_solve_dispatches_matrix_free_and_writes_outputs(tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    result = solver.solve_large_model(
        model,
        tmp_path / "output",
        solver_backend="matrix_free",
        chunk_size=2,
    )
    assert result.status == "PASS"
    assert result.output_files["summary"] == "summary.json"
    assert (tmp_path / "output" / "summary.json").is_file()


def test_large_scipy_path_runs_small_model_and_reports_assembly(tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    result = solver.solve_large_model(
        model,
        solver_backend="scipy",
        parameters={"method": "cg", "scipy_max_dofs": model.ndof},
    )
    assert result.status == "PASS"
    assert result.summary["assembly"]["final_nnz"] > 0


def test_large_scipy_path_rejects_no_free_dofs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    assembly = SimpleNamespace(
        fixed_dofs=np.arange(model.ndof, dtype=np.int64),
        stiffness=None,
        loads=np.zeros(model.ndof),
        diagnostics={},
    )
    monkeypatch.setattr(solver.ChunkedScipyAssembler, "assemble", lambda self, value: assembly)
    with pytest.raises(MeshValidationError, match="No free degree"):
        solver._solve_scipy(model, preconditioner="jacobi", chunk_size=2, params={})


def test_large_petsc_output_branch_uses_rank_zero_broadcast(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    audit = LargeAuditReport(status="PASS", errors=(), warnings=(), details={})
    fake_result = solver.LargeSolveResult("PASS", "petsc", {}, audit)
    monkeypatch.setattr(solver, "_solve_petsc", lambda *args, **kwargs: (fake_result, np.zeros(model.ndof)))

    class Comm:
        rank = 0

        def bcast(self, value, root=0):
            return value

        def Barrier(self):
            return None

    monkeypatch.setattr(solver, "_mpi_comm", lambda: Comm())
    monkeypatch.setattr(solver, "_write_outputs", lambda *args: {"summary": "summary.json"})
    result = solver.solve_large_model(model, tmp_path / "petsc", solver_backend="petsc")
    assert result.output_files == {"summary": "summary.json"}


def test_large_mpi_helpers_are_observable_without_mpi_execution(monkeypatch: pytest.MonkeyPatch, capsys) -> None:
    class FakeComm:
        rank = 1
        size = 2

        def allreduce(self, value, op=None):
            return value * 2

    fake_mpi = SimpleNamespace(MAX="max")
    monkeypatch.setattr(solver, "_mpi", lambda: fake_mpi)
    monkeypatch.setenv("QF_SOLVER_MPI_TRACE", "1")
    solver._mpi_trace(FakeComm(), "checkpoint")
    assert "rank=1/2" in capsys.readouterr().out
    assert solver._mpi_max_time(FakeComm(), 1.5) == 3.0
    monkeypatch.delenv("QF_SOLVER_MPI_TRACE")
    solver._mpi_trace(FakeComm(), "silent")
    assert capsys.readouterr().out == ""


def test_optional_petsc_dependency_failure_is_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = __import__

    def blocked(name, *args, **kwargs):
        if name == "petsc4py":
            raise ImportError("not installed for unit test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", blocked)
    with pytest.raises(InfrastructureError, match="petsc4py"):
        solver._petsc()
