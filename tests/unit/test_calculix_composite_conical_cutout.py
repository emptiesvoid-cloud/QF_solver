"""Mesh and deck contracts for the exploratory curved-composite correlation."""

from __future__ import annotations

import numpy as np

from solveur.core.assembler import GlobalAssembler
from solveur.verification.calculix_composite_conical_cutout import (
    _qf_pressure_cloads,
    build_conical_s8r_mesh,
    build_loaded_qf_model,
    parse_calculix_composite_ply_stresses,
    write_conical_s8r_input,
)
from solveur.verification.mitc4_conical_cutout import build_conical_cutout_model


def test_s8r_conical_corner_nodes_match_the_qf_conical_mesh() -> None:
    qf, _ = build_conical_cutout_model(4, 16)
    s8r = build_conical_s8r_mesh(4, 16)
    assert len(s8r.elements) == len(qf.elements)
    assert np.allclose(s8r.nodes[s8r.qf_node_ids], qf.nodes, rtol=0.0, atol=1.0e-14)


def test_s8r_conical_deck_has_one_composite_section_per_element(tmp_path) -> None:
    mesh = build_conical_s8r_mesh(2, 8)
    model, _ = build_loaded_qf_model(2, 8)
    deck = write_conical_s8r_input(tmp_path / "cone.inp", mesh, model).read_text(encoding="ascii")
    assert "*ELEMENT,TYPE=S8R,ELSET=EALL" in deck
    assert deck.count("*SHELL SECTION,ELSET=E") == len(mesh.elements)
    assert "*CLOAD" in deck


def test_s8r_conical_deck_can_request_integration_point_ply_stresses(tmp_path) -> None:
    mesh = build_conical_s8r_mesh(2, 8)
    model, _ = build_loaded_qf_model(2, 8)
    deck = write_conical_s8r_input(
        tmp_path / "cone_stresses.inp", mesh, model, include_ply_stress_output=True
    ).read_text(encoding="ascii")
    assert "*EL PRINT,ELSET=EALL" in deck
    assert "\nS\n*END STEP" in deck


def test_parse_s8r_ply_stresses_keeps_element_point_and_layer(tmp_path) -> None:
    output = tmp_path / "cone.dat"
    output.write_text(
        " stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz)\n"
        "  12  17 1.0E+00 -2.0E+00 3.0E+00 4.0E+00 -5.0E+00 6.0E+00 E12P3_shell_000\n",
        encoding="utf-8",
    )
    assert parse_calculix_composite_ply_stresses(output) == [
        {
            "element": 12,
            "integration_point": 17,
            "ply_index": 3,
            "stress_output": [1.0, -2.0, 3.0, 4.0, -5.0, 6.0],
        }
    ]


def test_s8r_pressure_loads_are_the_qf_consistent_load_vector() -> None:
    model, _ = build_loaded_qf_model(2, 8)
    mesh = build_conical_s8r_mesh(2, 8)
    dofs = model.dof_manager()
    qf_loads = GlobalAssembler().assemble_loads(model, dofs)
    transferred = {(node - 1, component): value for node, component, value in _qf_pressure_cloads(model, mesh)}

    for qf_node, s8r_node in enumerate(mesh.qf_node_ids):
        for component, name in enumerate(("UX", "UY", "UZ"), start=1):
            expected = float(qf_loads[dofs.index(qf_node, name)])
            assert np.isclose(transferred.get((int(s8r_node), component), 0.0), expected, rtol=0.0, atol=1.0e-14)
