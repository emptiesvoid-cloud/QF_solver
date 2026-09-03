from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest

from solveur.large import assembler
from solveur.large.generator import generate_tet4_block


class _FakeMatrix:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def setUp(self) -> None:
        self.calls.append(("setup", None))

    def setValuesBlocked(self, rows, cols, values, addv=None) -> None:
        self.calls.append(("blocked", (np.asarray(rows), np.asarray(cols), np.asarray(values), addv)))

    def setValues(self, rows, cols, values, addv=None) -> None:
        self.calls.append(("scalar", (np.asarray(rows), np.asarray(cols), np.asarray(values), addv)))

    def assemble(self) -> None:
        self.calls.append(("assemble", None))

    def getOwnershipRange(self):
        return 0, 10_000

    def setValue(self, row, col, value, addv=None) -> None:
        self.calls.append(("dirichlet", (row, col, value, addv)))

    def convert(self, kind) -> None:
        self.calls.append(("convert", kind))

    def getInfo(self):
        return {"mallocs": 0.0, "nz_allocated": 120.0, "nz_used": 72.0}


class _FakeMatFactory:
    Type = SimpleNamespace(AIJ="aij")

    def __init__(self) -> None:
        self.matrix = _FakeMatrix()

    def createBAIJ(self, *args, **kwargs):
        self.matrix.calls.append(("create_baij", (args, kwargs)))
        return self.matrix

    def createAIJ(self, *args, **kwargs):
        self.matrix.calls.append(("create_aij", (args, kwargs)))
        return self.matrix


class _FakeComm:
    def getRank(self):
        return 0

    def getSize(self):
        return 1


class _RankTelemetry:
    def __init__(self) -> None:
        self.markers: list[tuple[str, str, dict[str, object] | None]] = []

    def marker(self, name, *, phase, context=None) -> None:
        self.markers.append((name, phase, context))


def _fake_petsc(factory: _FakeMatFactory):
    def mat():
        return factory

    mat.Type = SimpleNamespace(AIJ="aij")
    return SimpleNamespace(
        COMM_WORLD=_FakeComm(),
        Mat=mat,
        IntType=np.int32,
        InsertMode=SimpleNamespace(ADD_VALUES="add", INSERT_VALUES="insert"),
    )


def test_large_assembler_helpers_cover_loads_constraints_and_partitioning(tmp_path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    model.load_nodes = np.asarray([1, 1], dtype=np.int64)
    model.load_components = np.asarray([0, 0], dtype=np.int8)
    model.load_values = np.asarray([2.0, 3.0])

    loads = assembler.assemble_loads(model)
    assert loads[3] == pytest.approx(5.0)
    assert assembler.fixed_dof_indices(model).size > 0
    assert assembler.fixed_dof_indices(SimpleNamespace(fixed_nodes=np.zeros(0), fixed_components=np.zeros(0))).size == 0
    assert np.array_equal(
        assembler.element_dofs(np.asarray([0, 2, 4, 6])),
        np.asarray([0, 1, 2, 6, 7, 8, 12, 13, 14, 18, 19, 20]),
    )
    assert assembler.partition_range(10, 1, 3) == (3, 6)
    assert assembler.partition_range(0, 0, 1) == (0, 0)
    with pytest.raises(ValueError, match="non-negative"):
        assembler.partition_range(-1, 0, 1)
    with pytest.raises(ValueError, match="inconsistent"):
        assembler.partition_range(10, 2, 2)

    stiffness = np.ones((12, 12))
    untouched = assembler.apply_homogeneous_element_constraints(stiffness, np.arange(12), set())
    assert untouched is stiffness
    constrained = assembler.apply_homogeneous_element_constraints(stiffness, np.arange(12), {0, 11})
    assert np.all(constrained[[0, 11], :] == 0.0)
    assert np.all(constrained[:, [0, 11]] == 0.0)


def test_petsc_assembler_contract_covers_baij_and_aij_insertions(monkeypatch, tmp_path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    material_cache = assembler._material_cache(model)
    assert set(material_cache) == {0}
    batch = assembler._stiffness_batch(model, 0, 1, material_cache)
    assert batch.shape == (1, 12, 12)

    for matrix_format in ("baij", "aij"):
        factory = _FakeMatFactory()
        monkeypatch.setattr(assembler, "_petsc", lambda factory=factory: _fake_petsc(factory))
        result = assembler.PetscTET4Assembler(chunk_size=1, matrix_format=matrix_format).assemble(model)
        assert result is factory.matrix
        call_names = [name for name, _ in factory.matrix.calls]
        assert "setup" in call_names
        assert "assemble" in call_names
        assert "dirichlet" in call_names
        assert ("blocked" if matrix_format == "baij" else "scalar") in call_names
        if matrix_format == "baij":
            assert "convert" in call_names


def test_petsc_assembler_rejects_invalid_format_and_chunk_is_clamped() -> None:
    with pytest.raises(ValueError, match="matrix_format"):
        assembler.PetscTET4Assembler(matrix_format="dense")
    assert assembler.PetscTET4Assembler(chunk_size=0).chunk_size == 1


def test_petsc_assembler_emits_post_insertion_boundaries_and_diagnostics(monkeypatch, tmp_path) -> None:
    model = generate_tet4_block(tmp_path / "model.h5", nx=1, ny=1, nz=1)
    factory = _FakeMatFactory()
    markers = _RankTelemetry()
    monkeypatch.setattr(assembler, "_petsc", lambda: _fake_petsc(factory))

    assembled = assembler.PetscTET4Assembler(
        chunk_size=1,
        matrix_format="aij",
        rank_telemetry=markers,
        capture_diagnostics=True,
    )
    assembled.assemble(model)

    assert [name for name, _, _ in markers.markers] == [
        "POST_INSERTION",
        "PRE_ASSEMBLE_1",
        "POST_ASSEMBLE_1",
        "PRE_CONSTRAINTS",
        "POST_CONSTRAINTS",
        "PRE_ASSEMBLE_2",
        "POST_ASSEMBLE_2",
    ]
    diagnostics = assembled.last_diagnostics
    assert diagnostics["preallocation"]["strategy"] == "structured_six_tet4_exact_diag_offdiag"
    assert diagnostics["preallocation"]["diag_offdiag_preallocation"] == "EXACT_STRUCTURED_STENCIL"
    assert diagnostics["preallocation"]["diagonal_nnz"]["max"] <= 45
    assert diagnostics["preallocation"]["off_diagonal_nnz"]["sum"] == 0
    assert diagnostics["preallocation"]["matrix_info_after_assemble_2"]["available"] is True
    assert diagnostics["insertions"]["matsetvalues_call_count"] == model.element_count
    assert diagnostics["insertions"]["scalar_values_submitted"] == model.element_count * 144
    assert set(diagnostics["phase_timing_seconds"]) == {
        "element_insertion",
        "assemble_1",
        "constraints",
        "assemble_2",
        "total_assembler",
    }


def test_structured_six_tet4_aij_preallocation_matches_generated_connectivity(tmp_path) -> None:
    model = generate_tet4_block(tmp_path / "structured.h5", nx=3, ny=2, nz=2)
    for rank in range(4):
        row_start, row_stop = assembler._petsc_contiguous_ownership_range(model.ndof, rank, 4)
        actual = assembler._structured_six_tet4_aij_nnz(model, row_start, row_stop, np.int64)
        assert actual is not None
        diagonal, off_diagonal = actual
        expected_diagonal, expected_off_diagonal = _brute_aij_preallocation(model, row_start, row_stop)
        assert np.array_equal(diagonal, expected_diagonal)
        assert np.array_equal(off_diagonal, expected_off_diagonal)


def test_structured_stencil_preallocation_refuses_unproven_topology(tmp_path) -> None:
    model = generate_tet4_block(tmp_path / "centered.h5", nx=2, ny=2, nz=2, decomposition="centered")
    row_start, row_stop = assembler._petsc_contiguous_ownership_range(model.ndof, 0, 2)
    assert assembler._structured_six_tet4_aij_nnz(model, row_start, row_stop, np.int32) is None


def test_explicit_aij_ownership_matches_petsc_remainder_distribution() -> None:
    ranges = [assembler._petsc_contiguous_ownership_range(89_373, rank, 8) for rank in range(8)]
    assert ranges == [
        (0, 11_172),
        (11_172, 22_344),
        (22_344, 33_516),
        (33_516, 44_688),
        (44_688, 55_860),
        (55_860, 67_031),
        (67_031, 78_202),
        (78_202, 89_373),
    ]


def _brute_aij_preallocation(model, row_start: int, row_stop: int) -> tuple[np.ndarray, np.ndarray]:
    columns_by_row = [set() for _ in range(row_stop - row_start)]
    for tet in model.tet4:
        dofs = assembler.element_dofs(tet)
        local_rows = dofs[(dofs >= row_start) & (dofs < row_stop)]
        for row in local_rows:
            columns_by_row[int(row - row_start)].update(int(column) for column in dofs)
    diagonal = np.zeros(row_stop - row_start, dtype=np.int64)
    off_diagonal = np.zeros(row_stop - row_start, dtype=np.int64)
    for index, columns in enumerate(columns_by_row):
        diagonal[index] = sum(row_start <= column < row_stop for column in columns)
        off_diagonal[index] = len(columns) - diagonal[index]
    return diagonal, off_diagonal
