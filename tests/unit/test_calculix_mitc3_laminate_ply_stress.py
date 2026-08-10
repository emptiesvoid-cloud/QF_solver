"""Focused contracts for the MITC3+ / CalculiX S6 ply-stress protocol."""

import numpy as np

from solveur.verification.calculix_mitc3_laminate_ply_stress import (
    _relative_vector,
    build_s6_mesh,
    parse_s6_composite_ply_stresses,
    write_s6_composite_input,
)
from solveur.verification.mitc3_models import rectangular_tri_mesh


def test_s6_upgrade_preserves_corner_triangles_and_builds_shared_midpoints(tmp_path) -> None:
    nodes, triangles, _ = rectangular_tri_mesh(1.0, 0.2, 2, 1)
    mesh = build_s6_mesh(nodes, triangles)
    assert len(mesh.elements) == 4
    assert all(len(element) == 6 for element in mesh.elements)
    assert len(mesh.nodes) == 15
    path = tmp_path / "patch.inp"
    write_s6_composite_input(path, mesh, 2, 1)
    text = path.read_text(encoding="ascii")
    assert "*ELEMENT,TYPE=S6" in text
    assert text.count("*SHELL SECTION,ELSET=E") == 4
    assert "*EL PRINT,ELSET=EALL" in text


def test_relative_stress_metric_is_explicit() -> None:
    assert _relative_vector([1.0, 2.0], [1.0, 2.0]) == 0.0
    assert _relative_vector(np.array([1.0, 0.0]), np.array([2.0, 0.0])) == 0.5


def test_s6_parser_retains_the_controlled_ply_identifier(tmp_path) -> None:
    result = tmp_path / "patch.dat"
    result.write_text(
        "  1  7  1.0E+02  2.0E+02  3.0E+02  4.0E+02  5.0E+02  6.0E+02 P2_shell_000000000\n",
        encoding="ascii",
    )
    records = parse_s6_composite_ply_stresses(result)
    assert records == [{"element": 1, "integration_point": 7, "ply_index": 2, "stress_output": [100.0, 200.0, 300.0, 400.0, 500.0, 600.0]}]
