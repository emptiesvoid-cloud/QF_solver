from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pytest

from solveur.api import generate_large_tet4_block, load_large_model, postprocess_large_model, solve_large_model
from solveur.core.errors import InputValidationError
from solveur.elements.solid.tet4 import Tet4Element
from solveur.materials.solid import SolidMaterial
from solveur.large.benchmark import _validated_restart_checkpoint
from solveur.large.solver import _load_petsc_restart


def _solved_block(tmp_path: Path) -> tuple[Path, Path, np.ndarray]:
    model_path = tmp_path / "model.h5"
    generate_large_tet4_block(model_path, nx=1, ny=1, nz=1, total_load=100.0)
    solve_large_model(load_large_model(model_path), tmp_path / "solve", solver_backend="scipy")
    displacement_path = tmp_path / "solve" / "displacements.h5"
    with h5py.File(displacement_path, "r") as handle:
        displacement = np.asarray(handle["displacements"], dtype=float)
    return model_path, displacement_path, displacement


def test_large_postprocess_recovers_tet4_fields_and_manifest(tmp_path: Path) -> None:
    model_path, displacement_path, displacement = _solved_block(tmp_path)
    output = tmp_path / "post"

    result = postprocess_large_model(model_path, displacement_path, output, chunk_size=2)

    assert result["status"] == "PASS"
    assert result["processed_element_count"] == 6
    assert result["von_mises_max"] > 0.0
    assert result["strain_energy_sum"] > 0.0
    assert (output / "evidence_manifest.json").is_file()
    assert not (output / "postprocess_checkpoint.json.tmp").exists()
    model = load_large_model(model_path)
    connectivity = model.tet4[0]
    local_u = displacement[connectivity].reshape(12)
    material_data = model.material_for_element(0)
    element = Tet4Element(
        SolidMaterial(material_data["E"], material_data["nu"], material_data.get("density", 0.0))
    )
    with h5py.File(output / "element_results.h5", "r") as handle:
        np.testing.assert_allclose(handle["strain"][0], element.strain(model.nodes[connectivity], local_u))
        np.testing.assert_allclose(handle["stress"][0], element.stress(model.nodes[connectivity], local_u))
        assert float(handle["von_mises"][0]) == pytest.approx(
            element.von_mises(element.stress(model.nodes[connectivity], local_u))
        )
        assert handle.attrs["voigt_order"] == "XX,YY,ZZ,XY,YZ,XZ"


def test_large_postprocess_checkpoint_resume_matches_one_pass(tmp_path: Path) -> None:
    model_path, displacement_path, _ = _solved_block(tmp_path)
    resumed_output = tmp_path / "resumed"
    reference_output = tmp_path / "reference"

    partial = postprocess_large_model(
        model_path,
        displacement_path,
        resumed_output,
        chunk_size=2,
        max_chunks=1,
    )
    assert partial["status"] == "CHECKPOINTED"
    assert partial["processed_element_count"] == 2
    resumed = postprocess_large_model(
        model_path,
        displacement_path,
        resumed_output,
        chunk_size=2,
        resume=True,
    )
    reference = postprocess_large_model(model_path, displacement_path, reference_output, chunk_size=3)

    assert resumed["status"] == reference["status"] == "PASS"
    assert resumed["processed_elements_this_run"] == 4
    with h5py.File(resumed_output / "element_results.h5", "r") as left, h5py.File(
        reference_output / "element_results.h5", "r"
    ) as right:
        for name in ("volume", "strain", "stress", "von_mises", "strain_energy"):
            np.testing.assert_array_equal(left[name][:], right[name][:])


def test_large_postprocess_reads_mpi_binary_without_full_json(tmp_path: Path) -> None:
    model_path, _, displacement = _solved_block(tmp_path)
    binary_root = tmp_path / "binary"
    binary_root.mkdir()
    binary_path = binary_root / "displacements.bin"
    displacement.astype(np.float64).tofile(binary_path)
    (binary_root / "displacements_metadata.json").write_text(
        json.dumps(
            {
                "format": "qf_solver_mpi_binary_v1",
                "dtype": "float64",
                "byte_order": "little" if np.little_endian else "big",
                "shape": list(displacement.shape),
                "flat_size": int(displacement.size),
            }
        ),
        encoding="utf-8",
    )

    result = postprocess_large_model(model_path, binary_path, tmp_path / "post", chunk_size=1)

    assert result["status"] == "PASS"
    summary = json.loads((tmp_path / "post" / "postprocess_summary.json").read_text(encoding="utf-8"))
    assert "displacements" not in summary
    assert summary["processed_element_count"] == 6


def test_large_postprocess_rejects_incompatible_restart_and_output_policy(tmp_path: Path) -> None:
    model_path, displacement_path, _ = _solved_block(tmp_path)
    output = tmp_path / "post"
    postprocess_large_model(model_path, displacement_path, output, chunk_size=2, max_chunks=1)

    with pytest.raises(InputValidationError, match="chunk size"):
        postprocess_large_model(model_path, displacement_path, output, chunk_size=3, resume=True)
    with pytest.raises(InputValidationError, match="already exist"):
        postprocess_large_model(model_path, displacement_path, output, chunk_size=2)
    with pytest.raises(InputValidationError, match="mutually exclusive"):
        postprocess_large_model(model_path, displacement_path, output, resume=True, overwrite=True)


def test_petsc_completed_solution_checkpoint_is_validated_and_read_by_ownership(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    values = np.arange(12, dtype=np.float64)
    values.tofile(checkpoint / "displacements.bin")
    (checkpoint / "displacements_metadata.json").write_text(
        json.dumps(
            {
                "dtype": "float64",
                "byte_order": "little" if np.little_endian else "big",
                "shape": [4, 3],
                "flat_size": 12,
            }
        ),
        encoding="utf-8",
    )
    fingerprint = {"sha256": "abc", "size_bytes": 123}
    (checkpoint / "input_fingerprint.json").write_text(json.dumps(fingerprint), encoding="utf-8")
    source = _validated_restart_checkpoint(checkpoint, fingerprint)

    class FakeVec:
        def __init__(self) -> None:
            self.values = np.zeros(6)

        def getOwnershipRange(self) -> tuple[int, int]:
            return 3, 9

        def getArray(self) -> np.ndarray:
            return self.values

        def norm(self) -> float:
            return float(np.linalg.norm(self.values))

    vector = FakeVec()
    norm = _load_petsc_restart(vector, source, SimpleNamespace(node_count=4, ndof=12))

    np.testing.assert_array_equal(vector.values, values[3:9])
    assert norm == pytest.approx(np.linalg.norm(values[3:9]))


def test_petsc_restart_rejects_different_input_fingerprint(tmp_path: Path) -> None:
    checkpoint = tmp_path / "checkpoint"
    checkpoint.mkdir()
    (checkpoint / "input_fingerprint.json").write_text(
        json.dumps({"sha256": "old", "size_bytes": 1}), encoding="utf-8"
    )
    (checkpoint / "displacements.bin").write_bytes(b"")
    with pytest.raises(InputValidationError, match="different input model"):
        _validated_restart_checkpoint(checkpoint, {"sha256": "new", "size_bytes": 1})
