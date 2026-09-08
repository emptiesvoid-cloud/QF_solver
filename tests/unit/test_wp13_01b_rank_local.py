"""Targeted WP13-01B tests for the rank-local mixed architecture boundary."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace

import numpy as np
import pytest

from scripts.run_wp07_mixed_static import _manufactured_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.errors import InputValidationError
from solveur.core.solvers.static import LinearStaticSolver
from solveur.large.generic_distributed import (
    GenericDistributedModel,
    build_rank_local_model,
    dispatch_element,
    dispatch_rank_local_element,
    exchange_preallocation_metadata,
    partition_generic_model,
    rank_local_assembly_packet,
    rank_local_load_packet,
    rank_local_preallocation_metadata,
    rank_local_reaction_packet,
    recompose_local_assembly_packets,
    reduce_reactions,
    validate_partitions,
)


def _rank_local_models(partition_count: int):
    model = _manufactured_model(1)[0]
    distributed = GenericDistributedModel.from_finite_element_model(model)
    partitions = partition_generic_model(distributed, partition_count)
    return model, distributed, partitions, tuple(build_rank_local_model(distributed, partition) for partition in partitions)


@pytest.mark.parametrize("partition_count", [2, 3])
def test_rank_local_envelopes_dispatch_all_families_and_recompose_debug_assembly(partition_count: int) -> None:
    model, distributed, _partitions, local_models = _rank_local_models(partition_count)
    packets = tuple(rank_local_assembly_packet(local) for local in local_models)
    serial = GlobalAssembler().assemble_stiffness(model, model.dof_manager())
    recomposed = recompose_local_assembly_packets(packets, distributed.ndof)

    assert all(not hasattr(local, "nodes") and not hasattr(local, "blocks") for local in local_models)
    assert all(local.metadata["global_model_retained"] is False for local in local_models)
    assert {element.family for local in local_models for element in local.elements} == {"TET4", "WEDGE6", "HEX8"}
    assert {
        dispatch_rank_local_element(local, element).stiffness.shape
        for local in local_models
        for element in local.elements
    } == {(12, 12), (18, 18), (24, 24)}
    for local in local_models:
        for local_element in local.elements:
            global_element = next(element for element in distributed.iter_elements() if element.element_id == local_element.element_id)
            np.testing.assert_allclose(
                dispatch_rank_local_element(local, local_element).stiffness,
                dispatch_element(distributed, global_element).stiffness,
                rtol=1.0e-12,
                atol=1.0e-10,
            )
    np.testing.assert_allclose(recomposed.toarray(), serial.toarray(), rtol=1.0e-12, atol=1.0e-10)


@pytest.mark.parametrize("partition_count", [2, 3])
def test_row_owner_preallocation_is_exact_without_rank_global_connectivity(partition_count: int) -> None:
    _model, _distributed, _partitions, local_models = _rank_local_models(partition_count)
    packets = tuple(rank_local_assembly_packet(local) for local in local_models)
    metadata = exchange_preallocation_metadata(local_models)
    expected_pattern: dict[int, set[int]] = defaultdict(set)
    global_dof_owner = {dof: owner for local in local_models for dof, owner in local.dof_owner.items()}
    for packet in packets:
        for row, column in zip(packet.row_ids, packet.column_ids, strict=True):
            expected_pattern[int(row)].add(int(column))

    for local, record in zip(local_models, metadata, strict=True):
        provisional = rank_local_preallocation_metadata(local)
        assert provisional["owned_row_pattern_complete"] is False
        assert provisional["global_connectivity_required"] is False
        assert record["strategy"] == "connectivity_exact_family_aware_row_owner_exchange"
        assert record["owned_row_pattern_complete"] is True
        assert record["global_connectivity_required"] is False
        expected_diag = []
        expected_offdiag = []
        for row in record["owned_row_ids"]:
            columns = expected_pattern[row]
            expected_diag.append(sum(global_dof_owner[column] == local.rank for column in columns))
            expected_offdiag.append(sum(global_dof_owner[column] != local.rank for column in columns))
        assert record["diag_nnz_per_owned_row"] == expected_diag
        assert record["offdiag_nnz_per_owned_row"] == expected_offdiag


@pytest.mark.parametrize("partition_count", [2, 3])
def test_rank_local_boundary_load_and_reaction_packets_match_the_serial_route(partition_count: int) -> None:
    model, distributed, partitions, local_models = _rank_local_models(partition_count)
    dofs = model.dof_manager()
    serial_load = np.asarray(GlobalAssembler().assemble_loads(model, dofs), dtype=float)
    local_load = np.zeros_like(serial_load)
    for local in local_models:
        for dof, value in rank_local_load_packet(local).items():
            local_load[dof] += value
    np.testing.assert_allclose(local_load, serial_load, rtol=1.0e-12, atol=1.0e-10)

    shared_nodes = set(partitions[0].owned_node_ids).intersection(set(partitions[1].ghost_node_ids))
    assert any(load.node in shared_nodes for local in local_models for load in local.owned_loads)
    assert all(
        local.node_owner[load.node] == local.rank and load.global_dof in set(local.dof_map.owned_dof_ids)
        for local in local_models
        for load in local.owned_loads
    )

    result = LinearStaticSolver().solve(model, detail_level="summary")
    contributions = {
        local.rank: rank_local_reaction_packet(
            local,
            {int(dof): float(result.displacements[dof]) for dof in local.dof_map.local_dof_ids},
        )
        for local in local_models
    }
    dof_owner = {dof: owner for local in local_models for dof, owner in local.dof_owner.items()}
    reduced = reduce_reactions(contributions, dof_owner)
    serial_residual = np.asarray(
        GlobalAssembler().assemble_stiffness(model, dofs) @ result.displacements - serial_load,
        dtype=float,
    )
    reconstructed = np.zeros_like(serial_residual)
    for dof, record in reduced.items():
        reconstructed[dof] = record["value"]
    np.testing.assert_allclose(reconstructed, serial_residual, rtol=1.0e-12, atol=1.0e-9)
    with pytest.raises(InputValidationError, match="every local and ghost DOF"):
        rank_local_reaction_packet(local_models[0], {})


def test_rank_local_boundary_fails_closed_for_invalid_map_missing_material_and_partition_owner() -> None:
    _model, distributed, partitions, local_models = _rank_local_models(2)
    local = local_models[0]
    broken_map = dict(local.dof_map.node_global_to_local)
    first = next(iter(broken_map))
    broken_map[first] = 99
    with pytest.raises(InputValidationError, match="node local/global mapping"):
        replace(local.dof_map, node_global_to_local=broken_map)
    with pytest.raises(InputValidationError, match="unknown material"):
        replace(local, materials={})
    wrong_owner = dict(partitions[0].element_owner)
    wrong_owner[next(iter(wrong_owner))] = 1
    with pytest.raises(InputValidationError, match="element-owner maps disagree|invalid owner"):
        validate_partitions(distributed, (replace(partitions[0], element_owner=wrong_owner), partitions[1]))
