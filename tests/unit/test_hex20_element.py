from __future__ import annotations

import numpy as np
import pytest

from solveur.elements.solid.hex20 import Hex20Element
from solveur.loads.integration import _hex20_body_vector, _solid_face_vector
from solveur.materials.solid import SolidMaterial
from solveur.mesh.topology import HEX20_FACES


NATURAL_NODES = np.asarray(
    [
        (-1, -1, -1),
        (1, -1, -1),
        (1, 1, -1),
        (-1, 1, -1),
        (-1, -1, 1),
        (1, -1, 1),
        (1, 1, 1),
        (-1, 1, 1),
        (0, -1, -1),
        (-1, 0, -1),
        (-1, -1, 0),
        (1, 0, -1),
        (1, -1, 0),
        (0, 1, -1),
        (1, 1, 0),
        (-1, 1, 0),
        (0, -1, 1),
        (-1, 0, 1),
        (1, 0, 1),
        (0, 1, 1),
    ],
    dtype=float,
)


def unit_hex20() -> np.ndarray:
    corners = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ]
    )
    edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    return np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])


def element(*, density: float = 7800.0) -> Hex20Element:
    return Hex20Element(SolidMaterial(E=210.0e9, nu=0.3, density=density))


def test_hex20_shape_functions_match_gmsh_nodes_and_partition() -> None:
    interpolation = np.vstack([Hex20Element.shape_functions(point) for point in NATURAL_NODES])
    assert np.allclose(interpolation, np.eye(20))
    assert max(abs(float(np.sum(Hex20Element.shape_functions(point))) - 1.0) for point in Hex20Element.integration_points) < 1.0e-14


def test_hex20_jacobian_stiffness_mass_and_rigid_modes() -> None:
    coords = unit_hex20()
    determinants = [Hex20Element.jacobian_determinant(coords, point) for point in Hex20Element.integration_points]
    assert min(determinants) == pytest.approx(0.125)
    stiffness = element().stiffness(coords)
    mass = element().mass(coords)
    lumped = element().mass_lumped(coords)
    assert stiffness.shape == (60, 60)
    assert mass.shape == (60, 60)
    assert np.allclose(stiffness, stiffness.T)
    assert np.allclose(mass, mass.T)
    assert np.allclose(lumped, np.diag(np.diag(lumped)))
    assert np.sum(mass) == pytest.approx(3.0 * 7800.0)
    scale = max(np.linalg.norm(stiffness, ord=np.inf), 1.0)
    modes = []
    for axis in range(3):
        mode = np.zeros(60)
        mode[axis::3] = 1.0
        modes.append(mode)
    for axis in np.eye(3):
        modes.append(np.concatenate([np.cross(axis, point) for point in coords]))
    assert max(np.linalg.norm(stiffness @ mode, ord=np.inf) / scale for mode in modes) < 1.0e-10


def test_hex20_affine_field_is_exact_at_all_gauss_points() -> None:
    gradient = np.asarray([[0.01, 0.02, 0.03], [0.04, 0.05, 0.06], [0.07, 0.08, 0.09]])
    coords = unit_hex20()
    displacement = np.concatenate([gradient @ point for point in coords])
    expected = np.asarray(
        [
            gradient[0, 0],
            gradient[1, 1],
            gradient[2, 2],
            gradient[0, 1] + gradient[1, 0],
            gradient[1, 2] + gradient[2, 1],
            gradient[0, 2] + gradient[2, 0],
        ]
    )
    strains = [element(density=0.0).strain_at(coords, displacement, point) for point in Hex20Element.integration_points]
    assert all(np.allclose(strain, expected, atol=1.0e-12) for strain in strains)


def test_hex20_body_and_quad8_face_loads_preserve_resultants() -> None:
    coords = unit_hex20()
    body = _hex20_body_vector(coords, np.asarray([1.0, 2.0, 3.0]))
    traction = _solid_face_vector(coords, HEX20_FACES[1], np.asarray([0.0, 0.0, 2.0]), None, "global")
    pressure = _solid_face_vector(coords, HEX20_FACES[1], None, 2.0, "global")
    assert np.sum(body.reshape((-1, 3)), axis=0) == pytest.approx([1.0, 2.0, 3.0])
    assert np.sum(traction.reshape((-1, 3)), axis=0) == pytest.approx([0.0, 0.0, 2.0])
    assert np.sum(pressure.reshape((-1, 3)), axis=0) == pytest.approx([0.0, 0.0, -2.0])


def test_hex20_rejects_inverted_geometry() -> None:
    with pytest.raises(ValueError, match="Invalid HEX20 Jacobian"):
        element().stiffness(unit_hex20()[[0, 3, 2, 1, 4, 7, 6, 5, 9, 13, 11, 8, 10, 15, 19, 17, 16, 18, 14, 12]])
