from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from solveur.core.errors import InputValidationError
from solveur.large import campaign, memory, solver as large_solver
from solveur.large.dofs import component_from_dof, dof_index
from solveur.large.mpi_diagnostics import petsc_ksp_diagnostics, communication_diagnostics
from solveur.large.model import LargeModel
from solveur.large.generator import generate_tet4_block
from solveur.large.tet4_batch import (
    apply_homogeneous_constraints_batch,
    element_dofs_batch,
    petsc_block_values_batch,
    tet4_response_batch,
    tet4_stiffness_batch,
)


def _model_kwargs() -> dict[str, object]:
    return {
        "nodes": np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]),
        "tet4": np.asarray([[0, 1, 2, 3]], dtype=np.int64),
        "material_ids": np.asarray([0], dtype=np.int64),
        "materials": {"steel": {"E": 210.0e9}},
        "material_names": ("steel",),
    }


@pytest.mark.parametrize("value, expected", [("ux", 0), ("UY", 1), ("Uz", 2), (0, 0), (2, 2)])
def test_large_dof_names_and_indices_are_normalized(value: str | int, expected: int) -> None:
    assert component_from_dof(value) == expected
    assert np.array_equal(dof_index(np.asarray([4, 5]), expected), np.asarray([12 + expected, 15 + expected]))


@pytest.mark.parametrize("value", ["URX", "", -1, 3])
def test_large_dof_names_reject_unsupported_components(value: str | int) -> None:
    with pytest.raises(ValueError):
        component_from_dof(value)


@pytest.mark.parametrize(
    "changes, message",
    [
        ({"nodes": np.zeros((4, 2))}, "nodes"),
        ({"tet4": np.zeros((1, 3), dtype=np.int64)}, "connectivity"),
        ({"material_ids": np.zeros(2, dtype=np.int64)}, "material_ids"),
        ({"fixed_nodes": np.zeros(1), "fixed_components": np.zeros(0)}, "fixed_nodes"),
        ({"load_nodes": np.zeros(1), "load_components": np.zeros(1), "load_values": np.zeros(0)}, "load arrays"),
        ({"tet4": np.asarray([[0, 1, 2, 8]], dtype=np.int64)}, "invalid node"),
        ({"material_ids": np.asarray([1], dtype=np.int64)}, "unknown material"),
        ({"fixed_nodes": np.asarray([0]), "fixed_components": np.asarray([3])}, "components"),
    ],
)
def test_large_model_rejects_invalid_shapes_and_references(changes: dict[str, object], message: str) -> None:
    values = _model_kwargs()
    values.update(changes)
    with pytest.raises(ValueError, match=message):
        LargeModel(**values)


def test_large_model_material_lookup_and_empty_defaults() -> None:
    model = LargeModel(**_model_kwargs())
    assert model.node_count == 4
    assert model.element_count == 1
    assert model.ndof == 12
    assert model.material_for_element(0)["E"] == 210.0e9


def test_memory_snapshot_fallbacks_are_explicit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(memory.os, "name", "posix")
    monkeypatch.setattr(memory, "_proc_memory", lambda: None)
    monkeypatch.setattr(memory, "_resource_peak_rss", lambda: 2048)
    partial = memory.process_memory_snapshot()
    assert partial == {"source": "platform_partial", "current_rss_bytes": None, "peak_rss_bytes": 2048}

    monkeypatch.setattr(memory, "_resource_peak_rss", lambda: None)
    assert memory.process_memory_snapshot()["source"] == "unavailable"


def test_memory_windows_snapshot_is_used_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    expected = {"source": "windows_psapi:test", "current_rss_bytes": 10, "peak_rss_bytes": 20}
    monkeypatch.setattr(memory.os, "name", "nt")
    monkeypatch.setattr(memory, "_windows_memory", lambda: expected)
    assert memory.process_memory_snapshot() == expected


class _IncompletePC:
    pass


class _Incomplete:
    def getPC(self):
        return _IncompletePC()


def test_petsc_diagnostics_are_tolerant_of_missing_or_invalid_runtime_methods() -> None:
    diagnostics = petsc_ksp_diagnostics(_Incomplete(), SimpleNamespace(getInfo=lambda: {"bad": "x"}))
    assert diagnostics["ksp_type"] is None
    assert diagnostics["pc_type"] is None
    assert diagnostics["matrix_info"] is None

    empty = communication_diagnostics(
        node_counts=[], owned_node_counts=[], halo_node_counts=[], fixed_counts=[], load_counts=[]
    )
    assert empty["max_halo_node_count"] == 0
    assert empty["halo_node_ratio_max"] == 0.0
    assert empty["graph_cut_face_count"] == 0


def test_batched_tet4_empty_and_invalid_contracts() -> None:
    empty_coords = np.empty((0, 4, 3), dtype=float)
    empty_elasticity = np.eye(6)
    assert tet4_stiffness_batch(empty_coords, empty_elasticity).shape == (0, 12, 12)
    response = tet4_response_batch(empty_coords, np.empty((0, 12)), empty_elasticity)
    assert response["strain"].shape == (0, 6)
    assert np.asarray(apply_homogeneous_constraints_batch(np.ones((0, 12, 12)), np.empty((0, 12), dtype=int), np.zeros(0, dtype=bool))).shape == (0, 12, 12)

    with pytest.raises(ValueError, match="coordinates"):
        tet4_stiffness_batch(np.zeros((1, 4, 2)), empty_elasticity)
    with pytest.raises(ValueError, match="elasticity"):
        tet4_stiffness_batch(np.zeros((1, 4, 3)), np.eye(3))
    with pytest.raises(ValueError, match="connectivity"):
        element_dofs_batch(np.zeros((1, 3), dtype=int))
    with pytest.raises(ValueError, match="stiffness"):
        petsc_block_values_batch(np.zeros((1, 6, 6)))
    with pytest.raises(ValueError, match="displacements"):
        tet4_response_batch(np.zeros((1, 4, 3)), np.zeros((1, 6)), empty_elasticity)


def test_campaign_status_scaling_and_markdown_contracts(tmp_path: Path) -> None:
    assert campaign._campaign_status([], execute=False) == "PLANNED"
    assert campaign._campaign_status([{"status": "BLOCKED"}], execute=False) == "BLOCKED"
    assert campaign._campaign_status([{"status": "PASS"}, {"status": "FAIL"}], execute=True) == "PARTIAL"
    assert campaign._campaign_status([{"status": "FAIL"}], execute=True) == "FAIL"
    assert campaign._ratio(None, 1.0) is None
    assert campaign._ratio(1.0, 0.0) is None

    stages = [
        {"status": "PASS", "metrics": {"pipeline_time_seconds": 2.0, "dofs_per_second": 5.0}, "actual_dofs": 10},
        {"status": "PASS", "metrics": {"pipeline_time_seconds": 4.0, "dofs_per_second": 7.0}, "actual_dofs": 20},
    ]
    records = campaign._scaling_records(stages)
    assert records[0]["dof_ratio"] == 2.0
    assert records[0]["pipeline_time_ratio"] == 2.0
    assert records[0]["throughput_ratio"] == pytest.approx(1.4)

    summary = {
        "status": "PLANNED",
        "mode": "plan_only",
        "backend": "matrix_free",
        "preconditioner": "jacobi",
        "chunk_size": 64,
        "memory_budget_bytes": None,
        "stages": [{"target_dofs": 10, "actual_dofs": 12, "element_count": 1, "status": "READY", "metrics": {}}],
    }
    markdown = campaign._markdown(summary)
    assert "Aucun calcul n'a ete execute" in markdown
    assert "non execute" in markdown


class _GatherComm:
    rank = 0
    size = 2

    def allgather(self, value):
        return [(0, 2), (2, 4)]

    def Gatherv(self, local, receive, root=0) -> None:
        receive[0][:] = np.asarray([*local, 3.0, 4.0])


class _GatherVec:
    def getArray(self, readonly=False):
        return np.asarray([1.0, 2.0])

    def getOwnershipRange(self):
        return 0, 2


def test_petsc_displacement_gather_and_automatic_options(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(large_solver, "_mpi", lambda: SimpleNamespace(DOUBLE="double"))
    gathered, ownership = large_solver._gather_petsc_displacement(_GatherVec(), 4, _GatherComm())
    assert np.array_equal(gathered, np.asarray([1.0, 2.0, 3.0, 4.0]))
    assert ownership == [[0, 2], [2, 4]]
    assert large_solver._automatic_petsc_options(
        "gamg", 4, explicit_keys=set(), existing_keys=set()
    ) == {"pc_gamg_repartition": True}
    assert large_solver._automatic_petsc_options(
        "gamg", 4, explicit_keys={"pc_gamg_repartition"}, existing_keys=set()
    ) == {}
    assert large_solver._automatic_petsc_options(
        "jacobi", 8, explicit_keys=set(), existing_keys=set()
    ) == {}


def test_petsc_restart_loader_validates_metadata_and_finiteness(tmp_path: Path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    source = tmp_path / "displacements.bin"
    values = np.arange(model.ndof, dtype=np.float64)
    values.tofile(source)
    metadata = {
        "dtype": "float64",
        "byte_order": "little",
        "shape": [model.node_count, 3],
        "flat_size": model.ndof,
    }
    source.with_name("displacements_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    vector = SimpleNamespace(
        data=np.zeros(model.ndof),
        getOwnershipRange=lambda: (0, model.ndof),
        getArray=lambda: vector.data,
        norm=lambda: float(np.linalg.norm(vector.data)),
    )
    assert large_solver._load_petsc_restart(vector, source, model) == pytest.approx(np.linalg.norm(values))
    assert np.array_equal(vector.data, values)

    source.with_name("displacements_metadata.json").write_text("{}", encoding="utf-8")
    with pytest.raises(InputValidationError, match="Invalid PETSc restart metadata"):
        large_solver._load_petsc_restart(vector, source, model)

    source.with_name("displacements_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    np.full(model.ndof, np.nan).tofile(source)
    with pytest.raises(ValueError, match="non-finite"):
        large_solver._load_petsc_restart(vector, source, model)


def test_large_solver_dispatch_and_output_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    with pytest.raises(InputValidationError, match="Unsupported large solver backend"):
        large_solver.solve_large_model(model, solver_backend="dense")

    result = large_solver.LargeSolveResult(
        "PASS", "scipy", {"ndof": model.ndof}, SimpleNamespace(to_dict=lambda: {"status": "PASS"})
    )
    monkeypatch.setattr(large_solver, "_write_displacements_hdf5", lambda *args: (_ for _ in ()).throw(ImportError()))
    files = large_solver._write_outputs(model, result, np.zeros(model.ndof), tmp_path / "fallback")
    assert files["displacements"].endswith(".npz")
    assert (tmp_path / "fallback" / files["displacements"]).is_file()
