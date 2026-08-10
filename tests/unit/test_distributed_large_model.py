from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from solveur.large.distributed_model import _read_indexed_nodes, inspect_distributed_large_model, load_distributed_large_model
from solveur.large.dofs import dof_index
from solveur.large.generator import generate_tet4_block
from solveur.large.io import load_large_model
from solveur.large.assembler import partition_range


@dataclass(frozen=True)
class FakeComm:
    rank: int
    size: int

    def allgather(self, value):
        return [value for _ in range(self.size)]

    def allreduce(self, value, op=None):
        return value


def test_partitioned_hdf5_loader_reconstructs_global_connectivity(tmp_path: Path) -> None:
    path = tmp_path / "block.h5"
    generate_tet4_block(path, nx=3, ny=2, nz=2)
    full = load_large_model(path)
    partitions = [load_distributed_large_model(path, FakeComm(rank, 3)) for rank in range(3)]

    reconstructed = np.concatenate([partition.global_tet4 for partition in partitions])
    assert np.array_equal(reconstructed, full.tet4)
    assert sum(partition.local_element_count for partition in partitions) == full.element_count
    assert all(partition.node_count == full.node_count for partition in partitions)
    assert all(partition.element_count == full.element_count for partition in partitions)
    for partition in partitions:
        assert np.array_equal(partition.global_node_ids[partition.tet4], partition.global_tet4)
        assert partition.local_node_count <= full.node_count


def test_distributed_audit_reports_halo_node_counts(tmp_path: Path) -> None:
    path = tmp_path / "block.h5"
    generate_tet4_block(path, nx=3, ny=2, nz=2)
    partition = load_distributed_large_model(path, FakeComm(1, 3))

    report = inspect_distributed_large_model(partition, FakeComm(1, 3))
    details = report.details

    assert details["local_compact_node_counts"][1] == partition.local_node_count
    assert details["local_owned_node_counts"][1] + details["local_halo_node_counts"][1] == partition.local_node_count
    assert details["max_halo_node_count"] >= details["local_halo_node_counts"][1]
    assert details["mpi_communication"]["local_halo_node_counts"][1] == details["local_halo_node_counts"][1]
    assert "estimated_halo_coordinate_bytes_total" in details["mpi_communication"]


def test_partitioned_loader_distributes_loads_and_keeps_global_condition_counts(tmp_path: Path) -> None:
    path = tmp_path / "block.h5"
    generate_tet4_block(path, nx=5, ny=3, nz=3)
    full = load_large_model(path)
    partitions = [load_distributed_large_model(path, FakeComm(rank, 4)) for rank in range(4)]

    assert sum(partition.load_values.size for partition in partitions) == full.load_values.size
    assert all(partition.global_load_count == full.load_values.size for partition in partitions)
    assert all(partition.global_fixed_dof_count == full.fixed_nodes.size for partition in partitions)
    for rank, partition in enumerate(partitions):
        row_start, row_stop = partition_range(full.ndof, rank, 4)
        load_dofs = dof_index(partition.load_nodes, partition.load_components)
        assert np.all((load_dofs >= row_start) & (load_dofs < row_stop))
        details = partition.partition_details or {}
        boundary = details["boundary_conditions"]
        assert boundary["method"] == "chunked_hdf5_filter"
        assert boundary["load_global_count"] == full.load_values.size
        assert boundary["fixed_global_count"] == full.fixed_nodes.size


def test_partitioned_loader_rejects_npz(tmp_path: Path) -> None:
    path = tmp_path / "block.npz"
    generate_tet4_block(path, nx=1, ny=1, nz=1)

    try:
        load_distributed_large_model(path, FakeComm(0, 1))
    except ValueError as exc:
        assert "requires HDF5" in str(exc)
    else:
        raise AssertionError("Distributed NPZ input must be rejected.")


def test_blocked_node_reader_matches_hdf5_point_selection(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    path = tmp_path / "nodes.h5"
    nodes = np.column_stack(
        (
            np.arange(800_000, dtype=float),
            np.arange(800_000, dtype=float) * 2.0,
            np.arange(800_000, dtype=float) * -0.5,
        )
    )
    scattered = np.array([0, 7, 262_143, 262_144, 262_145, 524_288, 799_999], dtype=np.int64)
    with h5py.File(path, "w") as handle:
        handle.create_dataset("nodes", data=nodes)
    with h5py.File(path, "r") as handle:
        blocked = _read_indexed_nodes(handle["nodes"], scattered)

    assert np.array_equal(blocked, nodes[scattered])
