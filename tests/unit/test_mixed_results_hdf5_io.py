from __future__ import annotations

import numpy as np
import pytest

from solveur.core.dofs import DofManager
from solveur.large.generic_distributed import (
    ElementBlock,
    ElementResultRecord,
    FamilyAwareResults,
    GenericDistributedModel,
)


def _synthetic_result() -> tuple[GenericDistributedModel, FamilyAwareResults]:
    nodes = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    block = ElementBlock(
        family="TET4",
        connectivity=np.asarray([[0, 1, 2, 3]]),
        element_ids=np.asarray([7]),
        material_ids=np.asarray([0]),
        region_ids=np.asarray([2]),
        material_names=("steel",),
    )
    model = GenericDistributedModel(
        nodes=nodes,
        blocks=(block,),
        materials={"steel": {"type": "synthetic-fixture"}},
        dofs=DofManager.from_node_requirements({node: {"UX", "UY", "UZ"} for node in range(4)}),
        metadata={"units": {"length": "m", "displacement": "m"}},
    )
    results = FamilyAwareResults(
        nodal_displacement=np.zeros((4, 3)),
        element_results=(
            ElementResultRecord(
                element_id=7,
                family="TET4",
                material="steel",
                region_id=2,
                fields={"von_mises": np.asarray([123.0])},
            ),
        ),
    )
    return model, results


def test_hdf5_writer_reader_round_trip_has_stable_semantic_digest(tmp_path) -> None:
    pytest.importorskip("h5py")

    from solveur.io.mixed_results_hdf5 import (
        mixed_results_semantic_digest,
        read_mixed_results_hdf5,
        write_mixed_results_hdf5,
    )

    model, results = _synthetic_result()
    first = tmp_path / "first.h5"
    second = tmp_path / "second.h5"
    write_mixed_results_hdf5(first, model, results, source_sha="synthetic-source")
    write_mixed_results_hdf5(second, model, results, source_sha="synthetic-source")

    payload = read_mixed_results_hdf5(first)
    assert payload["source_sha"] == "synthetic-source"
    np.testing.assert_array_equal(payload["element_blocks"]["TET4"]["fields"]["von_mises"], [[123.0]])
    digest = mixed_results_semantic_digest(first)
    assert len(digest) == 64
    assert digest == mixed_results_semantic_digest(second)


def test_hdf5_writer_does_not_remove_file_created_by_competing_writer(tmp_path, monkeypatch) -> None:
    h5py = pytest.importorskip("h5py")
    from solveur.io.mixed_results_hdf5 import write_mixed_results_hdf5

    model, results = _synthetic_result()
    target = tmp_path / "competing.h5"
    competing_bytes = b"file created by the competing writer"

    def competing_writer(path, mode):
        assert mode == "x"
        target.write_bytes(competing_bytes)
        raise FileExistsError("simulated exclusive-create race")

    monkeypatch.setattr(h5py, "File", competing_writer)
    with pytest.raises(FileExistsError, match="simulated exclusive-create race"):
        write_mixed_results_hdf5(target, model, results, source_sha="synthetic-source")

    assert target.read_bytes() == competing_bytes
