from __future__ import annotations

import numpy as np

from solveur.verification.calculix_composite import (
    build_s8r_mesh,
    parse_original_frd_displacement,
    write_calculix_composite_input,
)


def test_s8r_mesh_has_shared_edges_and_center_tip() -> None:
    mesh = build_s8r_mesh(4, 2)
    assert len(mesh.elements) == 8
    assert len(mesh.nodes) == (2 * 4 + 1) * (2 * 2 + 1) - 4 * 2
    assert mesh.nodes[mesh.tip_node - 1].tolist() == [1.0, 0.0, 0.0]
    assert len(mesh.fixed_nodes) == 5


def test_calculix_composite_deck_contains_controlled_layup(tmp_path) -> None:
    path = write_calculix_composite_input(tmp_path / "case.inp", build_s8r_mesh(2, 2))
    text = path.read_text(encoding="ascii")
    assert "*ELEMENT,TYPE=S8R" in text
    assert "*SHELL SECTION,ELSET=EALL,COMPOSITE" in text
    assert text.count("2.5e-3,,LAMINA") == 4
    assert "*ELASTIC,TYPE=ENGINEERING CONSTANTS" in text
    assert "*NODE FILE,OUTPUT=2D" in text


def test_composite_frd_parser_ignores_generated_layer_nodes(tmp_path) -> None:
    path = tmp_path / "expanded.frd"
    path.write_text(
        " -4  DISP        4    1\n"
        " -1         1 1.00000E+00 2.00000E+00 3.00000E+00\n"
        " -1         2 4.00000E+00 5.00000E+00 6.00000E+00\n"
        " -1       101 7.00000E+00 8.00000E+00 9.00000E+00\n"
        " -3\n",
        encoding="ascii",
    )
    displacement = parse_original_frd_displacement(path, 2)
    np.testing.assert_allclose(displacement, [[1.0, 2.0, 3.0], [4.0, 5.0, 6.0]])
