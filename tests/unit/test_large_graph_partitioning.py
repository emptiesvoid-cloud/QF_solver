from __future__ import annotations

import numpy as np
import pytest

from solveur.large import partitioning
from solveur.large.partitioning import _face_groups, element_row_owner, face_owner, tet4_faces


class _SerialMpi:
    MAX = "max"
    SUM = "sum"
    INT64_T = "int64"


class _SerialComm:
    rank = 0
    size = 1

    def allreduce(self, value, op=None):
        return value

    def allgather(self, value):
        return [value]

    def Alltoall(self, send, receive) -> None:
        receive[0][...] = send[0]

    def Alltoallv(self, send, receive) -> None:
        receive[0][...] = send[0]


class _FakeAdjacency:
    def __init__(self, size, csr) -> None:
        self.size = size
        self.csr = csr

    def assemble(self) -> None:
        return None


class _FakeMat:
    def createAIJ(self, *, size, csr, comm):
        return _FakeAdjacency(size, csr)


class _FakePetsc:
    IntType = np.int64
    COMM_WORLD = "world"
    Mat = _FakeMat


class _FakeIs:
    def __init__(self, values) -> None:
        self.values = np.asarray(values, dtype=np.int64)

    def getIndices(self):
        return self.values


class _FakePartitioner:
    def __init__(self) -> None:
        self.partitioner_type = ""

    def create(self, comm):
        return self

    def setAdjacency(self, adjacency) -> None:
        self.adjacency = adjacency

    def setType(self, value) -> None:
        self.partitioner_type = value

    def setFromOptions(self) -> None:
        return None

    def apply(self, local_parts) -> None:
        local_parts.values[:] = 0

    def getType(self):
        return self.partitioner_type


class _FakeGraphPetsc(_FakePetsc):
    MatPartitioning = _FakePartitioner

    class IS:
        @staticmethod
        def createGeneral(values, comm):
            return _FakeIs(values)


def test_tet4_faces_are_sorted_and_shared_face_is_identical() -> None:
    connectivity = np.asarray([[0, 1, 2, 3], [0, 2, 1, 4]], dtype=np.int64)

    faces = tet4_faces(connectivity)

    assert faces.shape == (8, 3)
    assert np.all(faces[:, 1:] >= faces[:, :-1])
    shared = np.count_nonzero(np.all(faces == np.asarray([0, 1, 2]), axis=1))
    assert shared == 2


def test_face_owner_is_deterministic_and_bounded() -> None:
    faces = np.asarray([[0, 1, 2], [10, 20, 30], [0, 1, 2]], dtype=np.int64)

    owners = face_owner(faces, 4)

    assert np.array_equal(owners[[0, 2]], [owners[0], owners[0]])
    assert np.all((owners >= 0) & (owners < 4))
    with pytest.raises(ValueError, match="positive"):
        face_owner(faces, 0)


def test_element_row_owner_matches_partition_ranges_when_count_is_not_divisible() -> None:
    element_ids = np.arange(17, dtype=np.int64)

    owners = element_row_owner(element_ids, global_element_count=17, size=4)

    assert np.array_equal(owners, np.asarray([0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3, 3]))
    with pytest.raises(ValueError, match="positive"):
        element_row_owner(element_ids, global_element_count=17, size=0)


def test_face_groups_collect_equal_signatures() -> None:
    records = np.asarray(
        [
            [3, 4, 5, 8],
            [0, 1, 2, 3],
            [3, 4, 5, 9],
            [6, 7, 8, 10],
        ],
        dtype=np.int64,
    )

    groups = _face_groups(records)

    assert [stop - start for start, stop in groups] == [1, 2, 1]
    assert np.array_equal(records[1:3, :3], np.asarray([[3, 4, 5], [3, 4, 5]]))


def test_tet4_faces_rejects_invalid_connectivity() -> None:
    with pytest.raises(ValueError, match="shape"):
        tet4_faces(np.zeros((2, 3), dtype=np.int64))


def test_dual_graph_builds_one_symmetric_edge_for_shared_face(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partitioning, "_mpi", lambda: _SerialMpi)
    monkeypatch.setattr(partitioning, "_petsc", lambda: _FakePetsc)
    connectivity = np.asarray([[0, 1, 2, 3], [0, 2, 1, 4]], dtype=np.int64)
    element_ids = np.asarray([0, 1], dtype=np.int64)

    adjacency, interior, non_manifold = partitioning._dual_graph(
        connectivity,
        element_ids,
        global_element_count=2,
        comm=_SerialComm(),
    )

    assert interior == 1
    assert non_manifold == 0
    assert adjacency.size == ((2, 2), (2, 2))
    indptr, indices, values = adjacency.csr
    assert np.array_equal(indptr, [0, 1, 2])
    assert np.array_equal(indices, [1, 0])
    assert np.array_equal(values, [1.0, 1.0])


def test_exchange_rows_is_stable_for_serial_communicator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partitioning, "_mpi", lambda: _SerialMpi)
    records = np.asarray([[2, 4], [1, 3]], dtype=np.int64)

    received = partitioning._exchange_rows(records, np.zeros(2, dtype=np.int64), _SerialComm())

    assert np.array_equal(received, records)


def test_empty_face_bounds_are_explicit() -> None:
    starts, counts = partitioning._face_group_bounds(np.zeros((0, 4), dtype=np.int64))

    assert starts.dtype == np.int64
    assert counts.dtype == np.int64
    assert starts.size == 0
    assert counts.size == 0


def test_adjacency_from_edges_handles_empty_and_invalid_row_ownership(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partitioning, "_petsc", lambda: _FakePetsc)
    empty = partitioning._adjacency_from_edges(
        np.zeros((0, 2), dtype=np.int64), global_count=2, comm=_SerialComm()
    )
    assert np.array_equal(empty.csr[0], [0, 0, 0])
    assert empty.csr[1].size == 0

    with pytest.raises(partitioning.InfrastructureError, match="inconsistent row owner"):
        partitioning._adjacency_from_edges(
            np.asarray([[2, 0]], dtype=np.int64), global_count=2, comm=_SerialComm()
        )


def test_partition_cut_faces_counts_cross_rank_shared_faces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partitioning, "_mpi", lambda: _SerialMpi)
    connectivity = np.asarray([[0, 1, 2, 3], [0, 2, 1, 4]], dtype=np.int64)
    parts = np.asarray([0, 1], dtype=np.int64)

    cut = partitioning._partition_cut_faces(
        connectivity,
        np.asarray([0, 1], dtype=np.int64),
        parts,
        _SerialComm(),
    )

    assert cut == 1


def test_exchange_rows_rejects_mismatched_destinations() -> None:
    with pytest.raises(ValueError, match="one destination"):
        partitioning._exchange_rows(
            np.zeros((2, 3), dtype=np.int64),
            np.zeros(1, dtype=np.int64),
            _SerialComm(),
        )


def test_non_manifold_face_is_reported_in_dual_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partitioning, "_mpi", lambda: _SerialMpi)
    monkeypatch.setattr(partitioning, "_petsc", lambda: _FakePetsc)
    connectivity = np.asarray(
        [[0, 1, 2, 3], [0, 2, 1, 4], [0, 1, 2, 5]],
        dtype=np.int64,
    )
    adjacency, interior, non_manifold = partitioning._dual_graph(
        connectivity,
        np.asarray([0, 1, 2], dtype=np.int64),
        global_element_count=3,
        comm=_SerialComm(),
    )

    assert adjacency.size == ((3, 3), (3, 3))
    assert interior == 0
    assert non_manifold == 1


def test_graph_repartition_archives_partition_and_cut_face_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(partitioning, "_mpi", lambda: _SerialMpi)
    monkeypatch.setattr(partitioning, "_petsc", lambda: _FakeGraphPetsc)
    connectivity = np.asarray([[0, 1, 2, 3], [0, 2, 1, 4]], dtype=np.int64)

    result = partitioning.repartition_tet4_graph(
        connectivity,
        np.asarray([0, 0], dtype=np.int64),
        np.asarray([0, 1], dtype=np.int64),
        global_element_count=2,
        comm=_SerialComm(),
        partitioner_type="mock",
    )

    assert result.details["strategy"] == "graph"
    assert result.details["partitioner"] == "mock"
    assert result.details["local_element_counts"] == [2]
    assert result.details["cut_face_count"] == 0
    assert np.array_equal(result.global_element_ids, [0, 1])
    assert result.global_tet4.shape == (2, 4)
