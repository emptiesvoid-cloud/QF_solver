from __future__ import annotations

import numpy as np
import pytest

from solveur.elements.solid.hex8 import Hex8Element
from solveur.materials.solid import SolidMaterial
from solveur.loads.integration import _solid_face_vector
from solveur.mesh.topology import HEX8_FACES


def unit_hex() -> np.ndarray:
    return np.asarray(
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


def element() -> Hex8Element:
    return Hex8Element(SolidMaterial(E=210.0e9, nu=0.3, density=7800.0))


def test_hex8_shape_functions_and_jacobian_are_exact_on_unit_cube() -> None:
    assert np.isclose(np.sum(Hex8Element.shape_functions((0.0, 0.0, 0.0))), 1.0)
    assert np.allclose(Hex8Element.shape_functions((-1.0, -1.0, -1.0)), [1, 0, 0, 0, 0, 0, 0, 0])
    assert all(np.isclose(Hex8Element.jacobian_determinant(unit_hex(), point), 0.125) for point in Hex8Element.integration_points)


def test_hex8_stiffness_mass_and_rigid_modes() -> None:
    stiffness = element().stiffness(unit_hex())
    mass = element().mass(unit_hex())
    lumped = element().mass_lumped(unit_hex())
    assert stiffness.shape == (24, 24)
    assert mass.shape == (24, 24)
    assert np.allclose(stiffness, stiffness.T)
    assert np.allclose(mass, mass.T)
    assert np.allclose(lumped, np.diag(np.diag(lumped)))
    assert np.isclose(np.sum(lumped), np.sum(mass))
    assert np.isclose(np.sum(mass), 3.0 * 7800.0)
    scale = max(np.linalg.norm(stiffness, ord=np.inf), 1.0)
    modes = []
    for axis in range(3):
        mode = np.zeros(24)
        mode[axis::3] = 1.0
        modes.append(mode)
    for axis in np.eye(3):
        mode = np.zeros(24)
        for node, point in enumerate(unit_hex()):
            mode[3 * node : 3 * node + 3] = np.cross(axis, point)
        modes.append(mode)
    assert max(np.linalg.norm(stiffness @ mode, ord=np.inf) / scale for mode in modes) < 1.0e-10


def test_hex8_affine_field_has_constant_strain_at_all_gauss_points() -> None:
    gradient = np.asarray([[0.01, 0.02, 0.03], [0.04, 0.05, 0.06], [0.07, 0.08, 0.09]])
    displacement = np.concatenate([gradient @ point for point in unit_hex()])
    strains = [element().strain_at(unit_hex(), displacement, point) for point in Hex8Element.integration_points]
    expected = np.asarray([gradient[0, 0], gradient[1, 1], gradient[2, 2], gradient[0, 1] + gradient[1, 0], gradient[1, 2] + gradient[2, 1], gradient[0, 2] + gradient[2, 0]])
    assert all(np.allclose(strain, expected) for strain in strains)


def test_hex8_rejects_inverted_geometry_and_invalid_reference_point() -> None:
    with pytest.raises(ValueError, match="Invalid HEX8 Jacobian"):
        element().stiffness(unit_hex()[[0, 3, 2, 1, 4, 7, 6, 5]])
    with pytest.raises(ValueError, match="reference coordinates"):
        Hex8Element.shape_functions((1.1, 0.0, 0.0))


def test_hex8_quad4_face_pressure_and_traction_balance() -> None:
    coords = unit_hex()
    face = HEX8_FACES[1]
    traction = _solid_face_vector(coords, face, np.asarray([0.0, 0.0, 2.0]), None, "global")
    pressure = _solid_face_vector(coords, face, None, 2.0, "global")
    assert np.allclose(np.sum(traction.reshape((-1, 3)), axis=0), [0.0, 0.0, 2.0])
    assert np.allclose(np.sum(pressure.reshape((-1, 3)), axis=0), [0.0, 0.0, -2.0])
