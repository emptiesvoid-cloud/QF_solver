import json
from pathlib import Path

import numpy as np

from solveur.large.verification import _displacement_shape


def _write_binary_displacements(directory: Path, shape: tuple[int, int]) -> Path:
    path = directory / "displacements.bin"
    values = np.arange(shape[0] * shape[1], dtype=np.float64)
    values.tofile(path)
    metadata = {
        "format": "qf_solver_mpi_binary_v1",
        "dtype": "float64",
        "byte_order": "little" if np.little_endian else "big",
        "shape": list(shape),
        "flat_size": int(values.size),
        "layout": "node_by_translation_component",
    }
    (directory / "displacements_metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return path


def test_binary_displacement_shape_is_checked_without_loading_values(tmp_path: Path) -> None:
    path = _write_binary_displacements(tmp_path, (8, 3))
    assert _displacement_shape(path) == (8, 3)


def test_binary_displacement_shape_rejects_truncated_file(tmp_path: Path) -> None:
    path = _write_binary_displacements(tmp_path, (8, 3))
    path.write_bytes(path.read_bytes()[:-8])
    assert _displacement_shape(path) is None


def test_binary_displacement_shape_rejects_inconsistent_metadata(tmp_path: Path) -> None:
    path = _write_binary_displacements(tmp_path, (8, 3))
    metadata_path = tmp_path / "displacements_metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["flat_size"] = 25
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    assert _displacement_shape(path) is None
