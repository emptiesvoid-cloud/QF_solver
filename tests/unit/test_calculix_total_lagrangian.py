"""Tests for the CalculiX TET4 finite-kinematics correlation."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.verification.calculix_total_lagrangian import (
    parse_last_frd_displacement,
    write_calculix_input,
)
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh


def test_calculix_input_preserves_tet4_mesh_and_load(tmp_path):
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 4.0, 0.5, 0.5)
    path = write_calculix_input(tmp_path / "case.inp", nodes, elements)
    text = path.read_text(encoding="ascii")

    assert "*ELEMENT,TYPE=C3D4,ELSET=EALL" in text
    assert "*STEP,NLGEOM=YES" in text
    assert text.count("-37.5") == 4
    for index, element in enumerate(elements):
        connectivity = ",".join(str(int(node) + 1) for node in element)
        assert f"{index + 1},{connectivity}" in text


def test_frd_parser_returns_last_complete_displacement_block(tmp_path):
    path = tmp_path / "case.frd"
    path.write_text(
        "\n".join(
            (
                " -4  DISP        4    1",
                " -1         1 1.00000E-01 2.00000E-01-3.00000E-01",
                " -1         2 4.00000E-01 5.00000E-01-6.00000E-01",
                " -3",
                " -4  DISP        4    1",
                " -1         1 7.00000E-01 8.00000E-01-9.00000E-01",
                " -1         2 1.00000E+00 1.10000E+00-1.20000E+00",
                " -3",
            )
        ),
        encoding="ascii",
    )

    result = parse_last_frd_displacement(path, 2)

    np.testing.assert_allclose(result, [[0.7, 0.8, -0.9], [1.0, 1.1, -1.2]])


def test_frd_parser_rejects_incomplete_block(tmp_path):
    path = tmp_path / "case.frd"
    path.write_text(" -4  DISP        4    1\n -1         1 0.0E+00 0.0E+00 0.0E+00\n -3\n")

    with pytest.raises(ValueError, match="Expected 2"):
        parse_last_frd_displacement(path, 2)
