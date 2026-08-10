from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from solveur.core.errors import InputValidationError
from solveur.verification.vnv_visualization import (
    exterior_tet4_faces,
    load_vtu_displacements,
    write_tet4_displacement_vtu,
)


def test_tet4_vtu_displacement_round_trip(tmp_path: Path) -> None:
    model = {
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3]}],
    }
    expected = np.arange(12, dtype=float).reshape((4, 3)) * 1.0e-6
    path = tmp_path / "field.vtu"

    write_tet4_displacement_vtu(path, model, expected)

    assert np.allclose(load_vtu_displacements(path, 4), expected)


def test_vtu_displacement_reader_rejects_missing_or_wrong_sized_field(tmp_path: Path) -> None:
    missing = tmp_path / "missing.vtu"
    missing.write_text("<VTKFile><PointData/></VTKFile>", encoding="utf-8")
    with pytest.raises(InputValidationError, match="no Displacement"):
        load_vtu_displacements(missing, 1)

    wrong = tmp_path / "wrong.vtu"
    wrong.write_text(
        "<VTKFile><PointData><DataArray Name=\"Displacement\">0 1</DataArray></PointData></VTKFile>",
        encoding="utf-8",
    )
    with pytest.raises(InputValidationError, match="size mismatch"):
        load_vtu_displacements(wrong, 1)


def test_exterior_tet4_faces_removes_shared_face() -> None:
    cells = np.array([[0, 1, 2, 3], [0, 2, 1, 4]], dtype=np.int64)

    faces, owners = exterior_tet4_faces(cells)

    assert faces.shape == (6, 3)
    assert np.bincount(owners, minlength=2).tolist() == [3, 3]
