import numpy as np
import pytest

from solveur.elements.solid.tet4 import Tet4Element
from solveur.materials.solid import SolidMaterial


def unit_tet_coords():
    return np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def test_tet4_stiffness_is_symmetric():
    element = Tet4Element(SolidMaterial(E=210.0e9, nu=0.3))
    stiffness = element.stiffness(unit_tet_coords())
    assert stiffness.shape == (12, 12)
    assert np.allclose(stiffness, stiffness.T)


def test_tet4_has_six_rigid_body_modes():
    element = Tet4Element(SolidMaterial(E=210.0e9, nu=0.3))
    coords = unit_tet_coords()
    stiffness = element.stiffness(coords)
    norm = max(np.linalg.norm(stiffness, ord=np.inf), 1.0)
    modes = []
    for axis in range(3):
        mode = np.zeros(12)
        mode[axis::3] = 1.0
        modes.append(mode)
    for axis in np.eye(3):
        mode = np.zeros(12)
        for i, point in enumerate(coords):
            mode[3 * i : 3 * i + 3] = np.cross(axis, point)
        modes.append(mode)
    residual = max(np.linalg.norm(stiffness @ mode, ord=np.inf) / norm for mode in modes)
    assert residual < 1.0e-10


def test_tet4_rejects_inverted_or_degenerate_element():
    element = Tet4Element(SolidMaterial(E=210.0e9, nu=0.3))
    with pytest.raises(ValueError):
        element.stiffness(unit_tet_coords()[[0, 2, 1, 3]])
    with pytest.raises(ValueError):
        element.stiffness(np.zeros((4, 3)))
