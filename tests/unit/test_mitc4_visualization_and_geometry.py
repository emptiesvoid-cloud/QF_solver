from __future__ import annotations

import numpy as np

from solveur.compat.mitc4.geometry import block_rotation_transform, element_dofs, node_dofs, polygon_area_xy, rotation_matrix_xyz
from solveur.elements.shell.mitc4.geometry import element_dofs as relocated_element_dofs
from solveur.elements.shell.mitc4.mesh import MeshFactory
from solveur.materials.shell import ShellMaterial
from solveur.mesh.entities import MeshIssue
from solveur.post.mitc4_visualization import DeformationPlotter


def test_mitc4_geometry_facade_and_mesh_factories() -> None:
    rotation = rotation_matrix_xyz(0.1, 0.2, 0.3)
    assert np.allclose(rotation.T @ rotation, np.eye(3), atol=1.0e-12)
    assert np.array_equal(node_dofs(2), np.arange(12, 18))
    assert np.array_equal(element_dofs([0, 1]), relocated_element_dofs([0, 1]))
    transform = block_rotation_transform(rotation, 2)
    assert transform.shape == (12, 12)
    assert polygon_area_xy(np.asarray([[0.0, 0.0], [2.0, 0.0], [2.0, 1.0], [0.0, 1.0]])) == 2.0

    plate = MeshFactory.rectangular_plate(2, 1, 2.0, 1.0)
    curved = MeshFactory.scordelis_lo(2, 2)
    distorted = MeshFactory.distorted_patch_2x2()
    assert plate.nodes.shape == (6, 3)
    assert curved.quads.shape == (4, 4)
    assert distorted.quads.shape == (4, 4)
    assert isinstance(MeshIssue("warning", "quality"), MeshIssue)
    assert ShellMaterial is not None


def test_mitc4_deformation_plotter_writes_colored_field(tmp_path) -> None:
    nodes = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0]])
    quads = np.asarray([[0, 1, 2, 3]], dtype=int)
    displacements = np.zeros(24, dtype=float)
    displacements[2::6] = [0.0, 0.1, 0.2, 0.3]
    output = tmp_path / "deformation.png"
    DeformationPlotter(scale=2.0).plot(nodes, quads, displacements, title="test field", png=output)
    assert output.is_file()
    assert output.stat().st_size > 0
