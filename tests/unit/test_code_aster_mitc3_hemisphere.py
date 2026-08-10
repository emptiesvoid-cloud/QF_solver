from __future__ import annotations

import numpy as np
import pytest

from solveur.verification.code_aster_mitc3_hemisphere import (
    _full_surface,
    _groups,
    code_aster_hemisphere_comm,
    code_aster_hemisphere_mesh,
)
from solveur.verification.mitc3_models import pinched_hemisphere_model


def test_pinched_hemisphere_geometry_loads_and_symmetry_constraints() -> None:
    model, triangles, probes = pinched_hemisphere_model(4)
    assert len(triangles) == 32
    assert np.linalg.norm(model.nodes, axis=1) == pytest.approx(np.full(model.node_count, 10.0))
    assert sum(load.value for load in model.loads) == pytest.approx(0.0)
    assert model.loads[0].node == probes["point_x"]
    assert model.loads[1].node == probes["point_y"]
    assert any(item.node == probes["point_x"] and "UZ" in item.dofs for item in model.fixed_dofs)


def test_code_aster_hemisphere_deck_preserves_mesh_groups_and_half_loads() -> None:
    model, triangles, _ = pinched_hemisphere_model(4)
    mesh = code_aster_hemisphere_mesh(model.nodes, triangles, _groups(model.nodes, 4))
    command = code_aster_hemisphere_comm()
    assert mesh.count("\nM") >= len(triangles)
    for group in ("SHELL", "YZERO", "XZERO", "POINTX", "POINTY", "NALL"):
        assert group in mesh
    assert 'MODELISATION="DKT"' in command
    assert 'GROUP_NO="POINTX", FX=-1.0' in command
    assert 'GROUP_NO="POINTY", FY=1.0' in command


def test_four_quadrant_reconstruction_preserves_vector_symmetry() -> None:
    model, triangles, _ = pinched_hemisphere_model(3)
    displacement = 0.01 * model.nodes
    nodes, full_triangles, full_displacement = _full_surface(
        model.nodes, triangles, displacement
    )
    assert len(nodes) == 4 * model.node_count
    assert len(full_triangles) == 4 * len(triangles)
    assert np.max(np.abs(np.linalg.norm(nodes, axis=1) - 10.0)) < 1.0e-12
    assert np.linalg.norm(full_displacement, axis=1) == pytest.approx(
        np.linalg.norm(displacement, axis=1).tolist() * 4
    )
