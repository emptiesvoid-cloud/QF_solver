from __future__ import annotations

import numpy as np
import pytest

from scripts.run_wp07_mixed_static import _base_model, _manufactured_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.errors import InputValidationError
from solveur.large.generic_distributed import (
    ElementBlock,
    GenericDistributedModel,
    boundary_ownership,
    build_result_schema,
    dispatch_element,
    partition_generic_model,
    preallocation_metadata,
    reduce_reactions,
    shadow_assemble,
)


def test_family_aware_schema_preserves_all_three_element_blocks() -> None:
    distributed = GenericDistributedModel.from_finite_element_model(_base_model(1))

    assert [block.family for block in distributed.blocks] == ["TET4", "WEDGE6", "HEX8"]
    assert distributed.element_counts() == {"TET4": 1, "WEDGE6": 1, "HEX8": 1}
    assert distributed.element_count == 3
    assert distributed.ndof == 33


def test_shadow_two_partition_recomposition_matches_serial_mixed_assembly() -> None:
    model = _base_model(1)
    distributed = GenericDistributedModel.from_finite_element_model(model)
    partitions = partition_generic_model(distributed, 2)
    matrix, contributions = shadow_assemble(distributed, partitions)
    serial = GlobalAssembler().assemble_stiffness(model, model.dof_manager())

    assert {element.element_id for partition in partitions for element in partition.elements} == {0, 1, 2}
    assert len({element.element_id for partition in partitions for element in partition.elements}) == 3
    assert any(partition.ghost_node_ids.size for partition in partitions)
    assert all(partition.interface_node_ids.size for partition in partitions)
    assert partitions[0].neighboring_ranks == (1,)
    assert partitions[1].neighboring_ranks == (0,)
    assert {item.family for item in contributions} == {"TET4", "WEDGE6", "HEX8"}
    np.testing.assert_allclose(matrix.toarray(), serial.toarray(), rtol=1.0e-12, atol=1.0e-10)


def test_generic_dof_ownership_bc_loads_and_preallocation_are_family_aware() -> None:
    loaded_model, _, _ = _manufactured_model(1)
    distributed = GenericDistributedModel.from_finite_element_model(loaded_model)
    partitions = partition_generic_model(distributed, 2)
    ownership = boundary_ownership(distributed, partitions)
    metadata = [preallocation_metadata(partition, distributed) for partition in partitions]

    assert ownership["duplicate_fixed_ownership"] is False
    assert ownership["duplicate_load_ownership"] is False
    assert ownership["loads"]
    assert sum(item["family_element_counts"]["TET4"] for item in metadata) == 1
    assert sum(item["family_element_counts"]["WEDGE6"] for item in metadata) == 1
    assert sum(item["family_element_counts"]["HEX8"] for item in metadata) == 1
    assert all(item["strategy"] == "connectivity_exact_family_aware" for item in metadata)
    assert all(item["reallocations_expected"] == 0 for item in metadata)
    assert all(len(item["diag_nnz_per_owned_row"]) == len(item["owned_row_ids"]) for item in metadata)


def test_dispatch_derives_local_sizes_and_reaction_reduction_is_single_owner() -> None:
    distributed = GenericDistributedModel.from_finite_element_model(_base_model(1))
    partition = partition_generic_model(distributed, 1)[0]
    shapes = [dispatch_element(distributed, element).stiffness.shape for element in partition.elements]

    assert shapes == [(12, 12), (18, 18), (24, 24)]
    reduced = reduce_reactions({0: {0: 1.0, 3: 2.0}, 1: {0: 2.0, 3: 3.0}}, {0: 0, 3: 1})
    assert reduced == {0: {"owner": 0, "value": 3.0}, 3: {"owner": 1, "value": 5.0}}


def test_family_aware_result_schema_keeps_nodal_and_element_outputs_separate() -> None:
    distributed = GenericDistributedModel.from_finite_element_model(_base_model(1))
    result = build_result_schema(
        distributed,
        np.zeros(distributed.ndof),
        element_fields={0: {"strain": np.zeros(6), "stress": np.zeros(6)}},
    )

    assert result.nodal_displacement.shape == (distributed.node_count, 3)
    assert [item.family for item in result.element_results] == ["TET4", "WEDGE6", "HEX8"]
    assert result.element_results[0].fields["strain"].shape == (6,)


def test_generic_architecture_fails_closed_for_unsupported_family_and_partition_size() -> None:
    with pytest.raises(InputValidationError, match="Unsupported distributed element family"):
        ElementBlock(
            family="MITC4",
            connectivity=np.zeros((1, 4), dtype=np.int64),
            element_ids=np.zeros(1, dtype=np.int64),
            material_ids=np.zeros(1, dtype=np.int64),
            region_ids=np.zeros(1, dtype=np.int64),
            material_names=("solid",),
        )
    distributed = GenericDistributedModel.from_finite_element_model(_base_model(1))
    with pytest.raises(InputValidationError, match="partition size"):
        partition_generic_model(distributed, 0)
