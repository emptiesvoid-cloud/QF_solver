"""Contracts for the curved projected-axis MITC3+ correlation deck."""

import numpy as np

from solveur.verification.calculix_mitc3_curved_composite import (
    LAYUP,
    REFERENCE_DIRECTION,
    build_curved_s6_mesh,
    write_s6_input,
)
from solveur.verification.calculix_mitc3_curved_composite import _qf_model
from solveur.verification.mitc3_models import LAMINATE_MATERIAL


def test_curved_mesh_has_shared_quadratic_edges_and_projected_frames() -> None:
    mesh = build_curved_s6_mesh(4, 2)

    assert len(mesh.triangles) == 16
    assert len(mesh.elements) == len(mesh.triangles)
    assert all(len(element) == 6 for element in mesh.elements)
    assert len(set(mesh.elements)) == len(mesh.elements)
    assert np.isclose(np.sum(mesh.tip_weights), 1.0)
    assert all(np.isfinite(frame).all() for frame in mesh.orientations)

    for frame in mesh.orientations:
        assert np.allclose(frame.T @ frame, np.eye(3), atol=1.0e-12)
        assert np.isclose(np.linalg.det(frame), 1.0, atol=1.0e-12)
        assert np.isclose(np.linalg.norm(frame[:, 2]), 1.0)

    assert np.linalg.norm(REFERENCE_DIRECTION) > 0.0


def test_curved_s6_input_preserves_per_ply_orientation_projection(tmp_path) -> None:
    mesh = build_curved_s6_mesh(2, 1)
    path = write_s6_input(tmp_path / "curved.inp", mesh)
    text = path.read_text(encoding="ascii")

    assert text.count("*ELEMENT,TYPE=S6") == 1
    assert text.count("*SHELL SECTION,ELSET=E") == len(mesh.elements)
    for element_index in (1, len(mesh.elements)):
        for ply_index, angle in enumerate(LAYUP, start=1):
            assert f"*ORIENTATION,NAME=ORI{element_index}_{ply_index}" in text
            assert f"3,{angle:.16g}" in text
            assert f"0.002,,LAMINA,ORI{element_index}_{ply_index}" in text


def test_curved_mesh_uses_same_corner_geometry_for_qf_and_s6() -> None:
    mesh = build_curved_s6_mesh(3, 2)
    corner_count = (3 + 1) * (2 + 1)

    assert all(0 <= node < corner_count for triangle in mesh.triangles for node in triangle)
    assert all(node > corner_count for element in mesh.elements for node in element[3:])
    for element in mesh.elements:
        corners = [mesh.nodes[node - 1] for node in element[:3]]
        midsides = [mesh.nodes[node - 1] for node in element[3:]]
        assert np.allclose(midsides[0], 0.5 * (corners[0] + corners[1]))
        assert np.allclose(midsides[1], 0.5 * (corners[1] + corners[2]))
        assert np.allclose(midsides[2], 0.5 * (corners[2] + corners[0]))


def test_curved_qf_model_supports_independent_axial_loading() -> None:
    model, _ = _qf_model(2, 1, load_case="axial")

    values = {load.dof: float(load.value) for load in model.loads}
    assert values["UX"] > 0.0
    assert values["UZ"] == 0.0


def test_calculix_curved_deck_uses_the_qf_laminate_constants(tmp_path) -> None:
    mesh = build_curved_s6_mesh(2, 1)
    text = write_s6_input(tmp_path / "curved.inp", mesh).read_text(encoding="ascii")

    assert f"{LAMINATE_MATERIAL['E1']:.16g}" in text
    assert f"{LAMINATE_MATERIAL['E2']:.16g}" in text
    assert f"{LAMINATE_MATERIAL['G13']:.16g}" in text
    assert f"{LAMINATE_MATERIAL['G23']:.16g}" in text
    assert f"{LAMINATE_MATERIAL['density']:.16g}" in text
