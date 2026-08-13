"""Partitioned HDF5 model representation for PETSc/MPI runs."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InfrastructureError, InputValidationError
from solveur.large.audit import LargeAuditReport
from solveur.large.dofs import dof_index
from solveur.large.mpi_diagnostics import communication_diagnostics
from solveur.large.partitioning import repartition_tet4_graph


@dataclass
class DistributedLargeModel:
    """Local TET4 partition with compact ghost nodes and global numbering."""

    nodes: np.ndarray
    tet4: np.ndarray
    global_tet4: np.ndarray
    global_element_ids: np.ndarray
    global_node_ids: np.ndarray
    material_ids: np.ndarray
    materials: dict[str, dict[str, Any]]
    material_names: tuple[str, ...]
    fixed_nodes: np.ndarray
    fixed_components: np.ndarray
    load_nodes: np.ndarray
    load_components: np.ndarray
    load_values: np.ndarray
    analysis: dict[str, Any]
    global_node_count: int
    global_element_count: int
    local_element_start: int
    global_fixed_dof_count: int = 0
    global_load_count: int = 0
    partition_strategy: str = "contiguous"
    partition_details: dict[str, Any] | None = None
    schema_version: int = 1
    units: dict[str, str] | None = None
    verification_profile: str = "engineering"

    @property
    def node_count(self) -> int:
        return self.global_node_count

    @property
    def element_count(self) -> int:
        return self.global_element_count

    @property
    def local_node_count(self) -> int:
        return int(self.nodes.shape[0])

    @property
    def local_element_count(self) -> int:
        return int(self.tet4.shape[0])

    @property
    def ndof(self) -> int:
        return 3 * self.global_node_count


def load_distributed_large_model(
    path: str | Path,
    comm: Any | None = None,
    *,
    partition_strategy: str = "contiguous",
    graph_partitioner: str = "ptscotch",
) -> DistributedLargeModel:
    """Read only the rank-owned connectivity and compact referenced nodes."""
    comm = comm or _mpi().COMM_WORLD
    source = Path(path)
    if source.suffix.lower() not in {".h5", ".hdf5"}:
        raise InputValidationError("Distributed large-model input requires HDF5.")
    h5py = _h5py()
    try:
        with h5py.File(source, "r") as handle:
            metadata = json.loads(handle.attrs.get("metadata_json", "{}"))
            global_node_count = int(handle["nodes"].shape[0])
            global_element_count = int(handle["tet4"].shape[0])
            start, stop = _partition_range(global_element_count, comm.rank, comm.size)
            global_tet4 = np.asarray(handle["tet4"][start:stop], dtype=np.int64)
            material_ids = np.asarray(handle["material_ids"][start:stop], dtype=np.int64)
            global_element_ids = np.arange(start, stop, dtype=np.int64)
            strategy = str(partition_strategy).lower()
            partition_details: dict[str, Any]
            if strategy == "graph":
                partitioned = repartition_tet4_graph(
                    global_tet4,
                    material_ids,
                    global_element_ids,
                    global_element_count,
                    comm,
                    partitioner_type=graph_partitioner,
                )
                global_tet4 = partitioned.global_tet4
                material_ids = partitioned.material_ids
                global_element_ids = partitioned.global_element_ids
                partition_details = partitioned.details
                local_element_start = -1
            elif strategy == "contiguous":
                partition_details = {
                    "strategy": "contiguous",
                    "partitioner": "index_range",
                    "local_element_counts": [
                        _partition_range(global_element_count, rank, comm.size)[1]
                        - _partition_range(global_element_count, rank, comm.size)[0]
                        for rank in range(comm.size)
                    ],
                }
                local_element_start = start
            else:
                raise InputValidationError("Distributed partition strategy must be 'contiguous' or 'graph'.")
            global_node_ids = np.unique(global_tet4)
            node_read_start = time.perf_counter()
            nodes = _read_indexed_nodes(handle["nodes"], global_node_ids)
            node_read_time = time.perf_counter() - node_read_start
            boundary_start = time.perf_counter()
            boundary = _read_distributed_boundary_conditions(
                handle,
                global_node_ids,
                global_node_count,
                comm.rank,
                comm.size,
            )
            boundary_time = time.perf_counter() - boundary_start
            partition_details["node_read"] = {
                "method": "blocked_hdf5_ranges",
                "local_time_s": node_read_time,
                "max_time_s": _comm_max_float(node_read_time, comm),
                "block_size": _NODE_READ_BLOCK_SIZE,
                "local_node_count": int(global_node_ids.size),
            }
            partition_details["boundary_conditions"] = {
                "method": "chunked_hdf5_filter",
                "local_time_s": boundary_time,
                "max_time_s": _comm_max_float(boundary_time, comm),
                "fixed_global_count": boundary.fixed_global_count,
                "fixed_local_count": int(boundary.fixed_nodes.size),
                "load_global_count": boundary.load_global_count,
                "load_local_count": int(boundary.load_values.size),
                "loads_owned_by_dof_range": True,
                "fixed_kept_for_element_halo_or_dof_owner": True,
            }
            local_tet4 = np.searchsorted(global_node_ids, global_tet4)
            return DistributedLargeModel(
                nodes=nodes,
                tet4=local_tet4,
                global_tet4=global_tet4,
                global_element_ids=global_element_ids,
                global_node_ids=global_node_ids,
                material_ids=material_ids,
                materials=dict(metadata["materials"]),
                material_names=tuple(metadata["material_names"]),
                fixed_nodes=boundary.fixed_nodes,
                fixed_components=boundary.fixed_components,
                load_nodes=boundary.load_nodes,
                load_components=boundary.load_components,
                load_values=boundary.load_values,
                analysis=dict(metadata.get("analysis", {"type": "linear_static", "method": "cg"})),
                global_node_count=global_node_count,
                global_element_count=global_element_count,
                global_fixed_dof_count=boundary.fixed_global_count,
                global_load_count=boundary.load_global_count,
                local_element_start=local_element_start,
                partition_strategy=strategy,
                partition_details=partition_details,
                schema_version=int(metadata.get("schema_version", 1)),
                units=dict(metadata.get("units", {"system": "SI"})),
                verification_profile=str(metadata.get("verification_profile", "engineering")),
            )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise InputValidationError(f"Invalid distributed HDF5 model {source}: {exc}") from exc


def inspect_distributed_large_model(
    model: DistributedLargeModel,
    comm: Any,
    *,
    solution_metrics: dict[str, float] | None = None,
) -> LargeAuditReport:
    """Build a global audit from local partition statistics."""
    coords = model.nodes[model.tet4]
    volumes = np.einsum(
        "ij,ij->i",
        np.cross(coords[:, 1] - coords[:, 0], coords[:, 2] - coords[:, 0]),
        coords[:, 3] - coords[:, 0],
    ) / 6.0
    local_invalid = int(np.count_nonzero(volumes <= 1.0e-14))
    invalid = int(comm.allreduce(local_invalid))
    local_min = float(np.min(volumes)) if volumes.size else float("inf")
    global_min = float(comm.allreduce(local_min, op=_mpi_op("MIN")))
    partition_counts = [int(value) for value in comm.allgather(model.local_element_count)]
    node_counts = [int(value) for value in comm.allgather(model.local_node_count)]
    owned_node_start, owned_node_stop = _partition_range(model.global_node_count, comm.rank, comm.size)
    local_owned_node_count = int(
        np.count_nonzero((model.global_node_ids >= owned_node_start) & (model.global_node_ids < owned_node_stop))
    )
    local_halo_node_count = int(model.local_node_count - local_owned_node_count)
    owned_node_counts = [int(value) for value in comm.allgather(local_owned_node_count)]
    halo_node_counts = [int(value) for value in comm.allgather(local_halo_node_count)]
    fixed = np.unique(dof_index(model.fixed_nodes, model.fixed_components))
    global_fixed_count = model.global_fixed_dof_count or int(fixed.size)
    local_fixed_counts = [int(value) for value in comm.allgather(fixed.size)]
    local_load_counts = [int(value) for value in comm.allgather(model.load_values.size)]
    communication = communication_diagnostics(
        node_counts=node_counts,
        owned_node_counts=owned_node_counts,
        halo_node_counts=halo_node_counts,
        fixed_counts=local_fixed_counts,
        load_counts=local_load_counts,
        partition_details=model.partition_details,
    )
    errors = (f"{invalid} TET4 elements have invalid signed volume.",) if invalid else ()
    warnings = ("No fixed degree of freedom is defined; solve may be singular.",) if global_fixed_count == 0 else ()
    details: dict[str, Any] = {
        "node_count": model.node_count,
        "element_count": model.element_count,
        "ndof": model.ndof,
        "fixed_dof_count": int(global_fixed_count),
        "local_fixed_dof_count": int(fixed.size),
        "local_fixed_dof_counts": local_fixed_counts,
        "free_dof_count": int(model.ndof - global_fixed_count),
        "load_count": int(model.global_load_count or model.load_values.size),
        "local_load_count": int(model.load_values.size),
        "local_load_counts": local_load_counts,
        "distributed_input": True,
        "mpi_size": int(comm.size),
        "local_element_counts": partition_counts,
        "local_compact_node_counts": node_counts,
        "local_owned_node_counts": owned_node_counts,
        "local_halo_node_counts": halo_node_counts,
        "max_halo_node_count": int(max(halo_node_counts)) if halo_node_counts else 0,
        "halo_node_ratio_max": float(max(halo_node_counts) / max(node_counts)) if node_counts and max(node_counts) else 0.0,
        "mpi_communication": communication,
        "replicated_connectivity": False,
        "replicated_global_nodes": False,
        "partition_strategy": model.partition_strategy,
        "partition": dict(model.partition_details or {}),
        "minimum_signed_volume": global_min,
        "invalid_volume_count": invalid,
    }
    if solution_metrics:
        details["solution"] = solution_metrics
    details["error_count"] = len(errors)
    details["warning_count"] = len(warnings)
    status = "FAIL" if errors else "WARNING" if warnings else "PASS"
    return LargeAuditReport(status, errors, warnings, details)


def _partition_range(count: int, rank: int, size: int) -> tuple[int, int]:
    return count * rank // size, count * (rank + 1) // size


_NODE_READ_BLOCK_SIZE = 262_144
_BOUNDARY_READ_CHUNK_SIZE = 262_144


@dataclass(frozen=True)
class _DistributedBoundaryConditions:
    fixed_nodes: np.ndarray
    fixed_components: np.ndarray
    load_nodes: np.ndarray
    load_components: np.ndarray
    load_values: np.ndarray
    fixed_global_count: int
    load_global_count: int


def _read_indexed_nodes(dataset: Any, global_node_ids: np.ndarray) -> np.ndarray:
    """Read sorted node ids through contiguous HDF5 ranges.

    h5py point selection becomes very slow when graph partitioning scatters node
    ids. Reading moderate contiguous blocks keeps I/O predictable while
    preserving the compact local numbering expected by the assembler.
    """
    ids = np.asarray(global_node_ids, dtype=np.int64)
    if ids.size == 0:
        return np.zeros((0, int(dataset.shape[1])), dtype=float)
    if np.any(ids[1:] < ids[:-1]):
        raise InputValidationError("Global node ids must be sorted before distributed HDF5 reads.")
    result = np.empty((ids.size, int(dataset.shape[1])), dtype=float)
    block_ids = ids // _NODE_READ_BLOCK_SIZE
    starts = np.concatenate(([0], np.flatnonzero(block_ids[1:] != block_ids[:-1]) + 1))
    stops = np.concatenate((starts[1:], [ids.size]))
    for start_index, stop_index in zip(starts, stops):
        selected = ids[start_index:stop_index]
        block_start = int(selected[0] // _NODE_READ_BLOCK_SIZE * _NODE_READ_BLOCK_SIZE)
        block_stop = int(min(dataset.shape[0], (selected[-1] // _NODE_READ_BLOCK_SIZE + 1) * _NODE_READ_BLOCK_SIZE))
        block = np.asarray(dataset[block_start:block_stop], dtype=float)
        result[start_index:stop_index] = block[selected - block_start]
    return result


def _read_distributed_boundary_conditions(
    handle: Any,
    global_node_ids: np.ndarray,
    global_node_count: int,
    rank: int,
    size: int,
) -> _DistributedBoundaryConditions:
    fixed_nodes, fixed_components = _read_distributed_fixed_conditions(
        handle["fixed_nodes"],
        handle["fixed_dofs"],
        global_node_ids,
        global_node_count,
        rank,
        size,
    )
    load_nodes, load_components, load_values = _read_owned_loads(
        handle["load_nodes"],
        handle["load_dofs"],
        handle["load_values"],
        global_node_count,
        rank,
        size,
    )
    return _DistributedBoundaryConditions(
        fixed_nodes=fixed_nodes,
        fixed_components=fixed_components,
        load_nodes=load_nodes,
        load_components=load_components,
        load_values=load_values,
        fixed_global_count=int(handle["fixed_nodes"].shape[0]),
        load_global_count=int(handle["load_values"].shape[0]),
    )


def _read_distributed_fixed_conditions(
    node_dataset: Any,
    component_dataset: Any,
    global_node_ids: np.ndarray,
    global_node_count: int,
    rank: int,
    size: int,
) -> tuple[np.ndarray, np.ndarray]:
    row_start, row_stop = _partition_range(3 * global_node_count, rank, size)
    local_nodes = set(int(value) for value in np.asarray(global_node_ids, dtype=np.int64))
    kept_nodes: list[np.ndarray] = []
    kept_components: list[np.ndarray] = []
    for start, stop in _chunk_ranges(int(node_dataset.shape[0]), _BOUNDARY_READ_CHUNK_SIZE):
        nodes = np.asarray(node_dataset[start:stop], dtype=np.int64)
        components = np.asarray(component_dataset[start:stop], dtype=np.int8)
        dofs = dof_index(nodes, components)
        in_halo = np.fromiter((int(node) in local_nodes for node in nodes), dtype=bool, count=nodes.size)
        owned = (dofs >= row_start) & (dofs < row_stop)
        keep = in_halo | owned
        if np.any(keep):
            kept_nodes.append(nodes[keep])
            kept_components.append(components[keep])
    return _concat_int64(kept_nodes), _concat_int8(kept_components)


def _read_owned_loads(
    node_dataset: Any,
    component_dataset: Any,
    value_dataset: Any,
    global_node_count: int,
    rank: int,
    size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    row_start, row_stop = _partition_range(3 * global_node_count, rank, size)
    kept_nodes: list[np.ndarray] = []
    kept_components: list[np.ndarray] = []
    kept_values: list[np.ndarray] = []
    for start, stop in _chunk_ranges(int(value_dataset.shape[0]), _BOUNDARY_READ_CHUNK_SIZE):
        nodes = np.asarray(node_dataset[start:stop], dtype=np.int64)
        components = np.asarray(component_dataset[start:stop], dtype=np.int8)
        values = np.asarray(value_dataset[start:stop], dtype=float)
        dofs = dof_index(nodes, components)
        keep = (dofs >= row_start) & (dofs < row_stop)
        if np.any(keep):
            kept_nodes.append(nodes[keep])
            kept_components.append(components[keep])
            kept_values.append(values[keep])
    return _concat_int64(kept_nodes), _concat_int8(kept_components), _concat_float(kept_values)


def _chunk_ranges(count: int, chunk_size: int) -> list[tuple[int, int]]:
    return [(start, min(start + chunk_size, count)) for start in range(0, count, chunk_size)]


def _concat_int64(chunks: list[np.ndarray]) -> np.ndarray:
    return np.concatenate(chunks).astype(np.int64, copy=False) if chunks else np.zeros(0, dtype=np.int64)


def _concat_int8(chunks: list[np.ndarray]) -> np.ndarray:
    return np.concatenate(chunks).astype(np.int8, copy=False) if chunks else np.zeros(0, dtype=np.int8)


def _concat_float(chunks: list[np.ndarray]) -> np.ndarray:
    return np.concatenate(chunks).astype(float, copy=False) if chunks else np.zeros(0, dtype=float)


def _comm_max_float(value: float, comm: Any) -> float:
    if not hasattr(comm, "allreduce"):
        return float(value)
    return float(comm.allreduce(float(value), op=_mpi_op("MAX")))


def _h5py() -> Any:
    try:
        import h5py
    except ImportError as exc:
        raise InfrastructureError("Distributed HDF5 input requires h5py.") from exc
    return h5py


def _mpi() -> Any:
    from mpi4py import MPI

    return MPI


def _mpi_op(name: str) -> Any:
    try:
        return getattr(_mpi(), name)
    except ImportError:
        return None
