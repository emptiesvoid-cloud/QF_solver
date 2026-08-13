"""Distributed dual-graph partitioning and TET4 redistribution."""

from __future__ import annotations

import time
import os
from dataclasses import dataclass
from typing import Any

import numpy as np

from solveur.core.errors import InfrastructureError


@dataclass(frozen=True)
class GraphPartitionResult:
    """Rank-local elements after graph partitioning and redistribution."""

    global_tet4: np.ndarray
    material_ids: np.ndarray
    global_element_ids: np.ndarray
    details: dict[str, Any]


def repartition_tet4_graph(
    global_tet4: np.ndarray,
    material_ids: np.ndarray,
    global_element_ids: np.ndarray,
    global_element_count: int,
    comm: Any,
    *,
    partitioner_type: str = "ptscotch",
) -> GraphPartitionResult:
    """Partition the distributed TET4 dual graph and exchange element records."""
    petsc = _petsc()
    timings: dict[str, float] = {}
    stage_start = time.perf_counter()
    _trace(comm, "graph partition: build dual graph")
    adjacency, interior_faces, non_manifold_faces = _dual_graph(
        global_tet4,
        global_element_ids,
        global_element_count,
        comm,
    )
    timings["dual_graph_max_s"] = _comm_max_float(time.perf_counter() - stage_start, comm)
    _trace(comm, f"graph partition: dual graph complete in {timings['dual_graph_max_s']:.3f}s")
    partitioner = petsc.MatPartitioning().create(comm=petsc.COMM_WORLD)
    partitioner.setAdjacency(adjacency)
    try:
        stage_start = time.perf_counter()
        _trace(comm, f"graph partition: apply {partitioner_type}")
        partitioner.setType(str(partitioner_type))
        partitioner.setFromOptions()
        local_parts = petsc.IS().createGeneral(
            np.zeros(global_element_ids.size, dtype=petsc.IntType),
            comm=petsc.COMM_WORLD,
        )
        partitioner.apply(local_parts)
        timings["partition_apply_max_s"] = _comm_max_float(time.perf_counter() - stage_start, comm)
        _trace(comm, f"graph partition: apply complete in {timings['partition_apply_max_s']:.3f}s")
    except Exception as exc:
        raise InfrastructureError(
            f"PETSc graph partitioner {partitioner_type!r} is unavailable or failed: {exc}"
        ) from exc
    parts = np.asarray(local_parts.getIndices(), dtype=np.int64).copy()
    if parts.size != global_element_ids.size or np.any((parts < 0) | (parts >= comm.size)):
        raise InfrastructureError("PETSc graph partitioner returned invalid rank assignments.")
    stage_start = time.perf_counter()
    _trace(comm, "graph partition: count cut faces")
    cut_faces = _partition_cut_faces(global_tet4, global_element_ids, parts, comm)
    timings["cut_faces_max_s"] = _comm_max_float(time.perf_counter() - stage_start, comm)
    _trace(comm, f"graph partition: cut faces complete in {timings['cut_faces_max_s']:.3f}s")
    stage_start = time.perf_counter()
    _trace(comm, "graph partition: redistribute elements")
    records = np.column_stack((global_element_ids, material_ids, global_tet4)).astype(np.int64, copy=False)
    received = _exchange_rows(records, parts, comm)
    if received.size:
        received = received[np.argsort(received[:, 0], kind="stable")]
    timings["redistribute_elements_max_s"] = _comm_max_float(time.perf_counter() - stage_start, comm)
    _trace(comm, f"graph partition: redistribute complete in {timings['redistribute_elements_max_s']:.3f}s")
    local_counts = [int(value) for value in comm.allgather(received.shape[0])]
    details = {
        "strategy": "graph",
        "partitioner": str(partitioner.getType()),
        "local_element_counts": local_counts,
        "imbalance_ratio": max(local_counts) / (sum(local_counts) / len(local_counts)) if local_counts else 0.0,
        "interior_face_count": int(interior_faces),
        "cut_face_count": int(cut_faces),
        "cut_face_ratio": float(cut_faces / interior_faces) if interior_faces else 0.0,
        "non_manifold_face_count": int(non_manifold_faces),
        "timings": timings,
    }
    return GraphPartitionResult(
        global_tet4=received[:, 2:6].copy(),
        material_ids=received[:, 1].copy(),
        global_element_ids=received[:, 0].copy(),
        details=details,
    )


def tet4_faces(connectivity: np.ndarray) -> np.ndarray:
    """Return sorted node triples for all four faces of each TET4."""
    cells = np.asarray(connectivity, dtype=np.int64)
    if cells.ndim != 2 or cells.shape[1] != 4:
        raise ValueError("TET4 connectivity must have shape [n, 4].")
    faces = cells[:, ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3))].reshape((-1, 3))
    return np.sort(faces, axis=1)


def face_owner(faces: np.ndarray, size: int) -> np.ndarray:
    """Map face signatures deterministically to MPI ranks."""
    if size <= 0:
        raise ValueError("MPI size must be positive.")
    values = np.asarray(faces, dtype=np.uint64)
    hashed = values[:, 0] * np.uint64(73856093)
    hashed ^= values[:, 1] * np.uint64(19349663)
    hashed ^= values[:, 2] * np.uint64(83492791)
    return np.asarray(hashed % np.uint64(size), dtype=np.int64)


def element_row_owner(element_ids: np.ndarray, global_element_count: int, size: int) -> np.ndarray:
    """Return the owner rank for PETSc rows split by `_partition_range` semantics."""
    ids = np.asarray(element_ids, dtype=np.int64)
    if global_element_count < 0:
        raise ValueError("Global element count must be non-negative.")
    if size <= 0:
        raise ValueError("MPI size must be positive.")
    boundaries = np.array(
        [global_element_count * rank // size for rank in range(size + 1)],
        dtype=np.int64,
    )
    owners = np.searchsorted(boundaries[1:], ids, side="right")
    return np.minimum(owners, size - 1).astype(np.int64, copy=False)


def _dual_graph(
    global_tet4: np.ndarray,
    element_ids: np.ndarray,
    global_element_count: int,
    comm: Any,
) -> tuple[Any, int, int]:
    stage_start = time.perf_counter()
    faces = tet4_faces(global_tet4)
    records = np.column_stack((faces, np.repeat(element_ids, 4)))
    _trace(comm, f"dual graph: local faces {faces.shape[0]} built in {time.perf_counter() - stage_start:.3f}s")
    stage_start = time.perf_counter()
    received = _exchange_rows(records, face_owner(faces, comm.size), comm)
    _trace(comm, f"dual graph: face exchange received {received.shape[0]} in {time.perf_counter() - stage_start:.3f}s")
    stage_start = time.perf_counter()
    starts, counts = _face_group_bounds(received)
    _trace(comm, f"dual graph: grouped {starts.size} faces in {time.perf_counter() - stage_start:.3f}s")
    interior_starts = starts[counts == 2]
    left = received[interior_starts, 3]
    right = received[interior_starts + 1, 3]
    edges = np.concatenate(
        (np.column_stack((left, right)), np.column_stack((right, left))),
        axis=0,
    )
    row_owners = element_row_owner(edges[:, 0], global_element_count, comm.size)
    stage_start = time.perf_counter()
    local_edges = _exchange_rows(edges, row_owners, comm)
    _trace(comm, f"dual graph: edge exchange received {local_edges.shape[0]} in {time.perf_counter() - stage_start:.3f}s")
    stage_start = time.perf_counter()
    adjacency = _adjacency_from_edges(local_edges, global_element_count, comm)
    _trace(comm, f"dual graph: adjacency assembled in {time.perf_counter() - stage_start:.3f}s")
    interior_local = int(interior_starts.size)
    non_manifold_local = int(np.count_nonzero(counts > 2))
    interior = int(comm.allreduce(interior_local, op=_mpi().SUM))
    non_manifold = int(comm.allreduce(non_manifold_local, op=_mpi().SUM))
    return adjacency, interior, non_manifold


def _partition_cut_faces(
    global_tet4: np.ndarray,
    element_ids: np.ndarray,
    parts: np.ndarray,
    comm: Any,
) -> int:
    faces = tet4_faces(global_tet4)
    records = np.column_stack((faces, np.repeat(element_ids, 4), np.repeat(parts, 4)))
    received = _exchange_rows(records, face_owner(faces, comm.size), comm)
    starts, counts = _face_group_bounds(received)
    interior_starts = starts[counts == 2]
    cut_local = int(
        np.count_nonzero(received[interior_starts, 4] != received[interior_starts + 1, 4])
    )
    return int(comm.allreduce(cut_local, op=_mpi().SUM))


def _face_groups(records: np.ndarray) -> list[tuple[int, int]]:
    starts, counts = _face_group_bounds(records)
    return [(int(start), int(start + count)) for start, count in zip(starts, counts)]


def _face_group_bounds(records: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if records.shape[0] == 0:
        return np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    order = np.lexsort((records[:, 2], records[:, 1], records[:, 0]))
    records[:] = records[order]
    changed = np.any(records[1:, :3] != records[:-1, :3], axis=1)
    starts = np.concatenate(([0], np.flatnonzero(changed) + 1))
    counts = np.diff(np.concatenate((starts, [records.shape[0]])))
    return starts.astype(np.int64, copy=False), counts.astype(np.int64, copy=False)


def _adjacency_from_edges(edges: np.ndarray, global_count: int, comm: Any) -> Any:
    petsc = _petsc()
    row_start = global_count * comm.rank // comm.size
    row_stop = global_count * (comm.rank + 1) // comm.size
    local_count = row_stop - row_start
    if edges.size:
        order = np.lexsort((edges[:, 1], edges[:, 0]))
        sorted_edges = edges[order]
        unique = np.ones(sorted_edges.shape[0], dtype=bool)
        unique[1:] = np.any(sorted_edges[1:] != sorted_edges[:-1], axis=1)
        sorted_edges = sorted_edges[unique]
        if np.any((sorted_edges[:, 0] < row_start) | (sorted_edges[:, 0] >= row_stop)):
            raise InfrastructureError("Dual-graph edges were sent to an inconsistent row owner.")
        row_counts = np.bincount(sorted_edges[:, 0] - row_start, minlength=local_count)
        indices = sorted_edges[:, 1].astype(petsc.IntType, copy=False)
    else:
        row_counts = np.zeros(local_count, dtype=np.int64)
        indices = np.zeros(0, dtype=petsc.IntType)
    indptr = np.concatenate(([0], np.cumsum(row_counts))).astype(petsc.IntType, copy=False)
    values = np.ones(indices.size, dtype=float)
    matrix = petsc.Mat().createAIJ(
        size=((local_count, global_count), (local_count, global_count)),
        csr=(indptr, indices, values),
        comm=petsc.COMM_WORLD,
    )
    matrix.assemble()
    return matrix


def _exchange_rows(records: np.ndarray, destinations: np.ndarray, comm: Any) -> np.ndarray:
    records = np.asarray(records, dtype=np.int64)
    destinations = np.asarray(destinations, dtype=np.int64)
    if records.shape[0] != destinations.size:
        raise ValueError("Each exchanged row requires one destination rank.")
    width = records.shape[1]
    order = np.argsort(destinations, kind="stable")
    send = np.ascontiguousarray(records[order])
    send_counts = np.bincount(destinations, minlength=comm.size).astype(np.int64)
    receive_counts = np.empty(comm.size, dtype=np.int64)
    comm.Alltoall([send_counts, _mpi().INT64_T], [receive_counts, _mpi().INT64_T])
    send_offsets = np.concatenate(([0], np.cumsum(send_counts[:-1]))) * width
    receive_offsets = np.concatenate(([0], np.cumsum(receive_counts[:-1]))) * width
    received = np.empty((int(np.sum(receive_counts)), width), dtype=np.int64)
    comm.Alltoallv(
        [send.ravel(), send_counts * width, send_offsets, _mpi().INT64_T],
        [received.ravel(), receive_counts * width, receive_offsets, _mpi().INT64_T],
    )
    return received


def _comm_max_float(value: float, comm: Any) -> float:
    return float(comm.allreduce(float(value), op=_mpi().MAX))


def _trace(comm: Any, message: str) -> None:
    if os.environ.get("QF_SOLVER_MPI_TRACE") not in {"1", "true", "TRUE", "yes"}:
        return
    print(f"[rank {comm.rank}/{comm.size}] {message}", flush=True)


def _petsc() -> Any:
    try:
        from petsc4py import PETSc
    except ImportError as exc:
        raise InfrastructureError("Graph partitioning requires petsc4py.") from exc
    return PETSc


def _mpi() -> Any:
    from mpi4py import MPI

    return MPI
