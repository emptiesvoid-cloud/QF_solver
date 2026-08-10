from __future__ import annotations

import numpy as np

from solveur.materials.solid import SolidMaterial
from solveur.verification.torsion_stress_probe import (
    H8_MESH_SIZE,
    TARGET_ELEMENT_MULTIPLIER,
    TARGET_MESH_SIZE,
    recover_tet4_stresses,
)


def test_target_size_uses_three_dimensional_fourfold_refinement() -> None:
    assert np.isclose((H8_MESH_SIZE / TARGET_MESH_SIZE) ** 3, TARGET_ELEMENT_MULTIPLIER)


def test_chunked_tet4_stress_recovery_reproduces_affine_field() -> None:
    nodes = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
        ]
    )
    cells = np.array([[0, 1, 2, 3], [4, 2, 1, 3]], dtype=np.int64)
    gradient = np.array([[0.01, 0.02, -0.01], [0.03, -0.02, 0.04], [0.02, 0.01, 0.03]])
    displacements = nodes @ gradient.T
    material = SolidMaterial(E=70.0e9, nu=0.3)
    strain = np.array(
        [
            gradient[0, 0],
            gradient[1, 1],
            gradient[2, 2],
            gradient[0, 1] + gradient[1, 0],
            gradient[1, 2] + gradient[2, 1],
            gradient[0, 2] + gradient[2, 0],
        ]
    )
    expected = material.elasticity_matrix @ strain

    stresses = recover_tet4_stresses(nodes, cells, displacements, material.elasticity_matrix, chunk_size=1)

    assert np.allclose(stresses, expected[None, :], rtol=1.0e-12, atol=1.0e-6)
