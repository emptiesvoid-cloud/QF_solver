"""Prepared element-load checks: execution requires an explicit scientific authorization."""

import numpy as np
import pytest

from solveur.loads.integration import _solid_face_vector
from solveur.mesh.topology import HEX20_FACES

pytestmark = pytest.mark.skip(reason="PREPARED_NOT_AUTHORIZED: element face integration requires an Owner decision")


def _cube_nodes() -> np.ndarray:
    corners = np.asarray(
        [
            [0, -0.5, -0.5],
            [1, -0.5, -0.5],
            [1, 0.5, -0.5],
            [0, 0.5, -0.5],
            [0, -0.5, 0.5],
            [1, -0.5, 0.5],
            [1, 0.5, 0.5],
            [0, 0.5, 0.5],
        ],
        dtype=float,
    )
    edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    return np.vstack((corners, [(corners[a] + corners[b]) / 2 for a, b in edges]))


@pytest.mark.parametrize("face", range(6))
def test_hex20_planar_face_traction_against_exact_quad8_weights(face: int) -> None:
    nodes = _cube_nodes()
    traction = np.asarray([2.0, -3.0, 5.0])
    observed = _solid_face_vector(nodes, HEX20_FACES[face], traction, None, "global").reshape(-1, 3)
    expected = np.zeros((20, 3))
    for node in HEX20_FACES[face][:4]:
        expected[node] = -traction / 12
    for node in HEX20_FACES[face][4:]:
        expected[node] = traction / 3
    np.testing.assert_allclose(observed, expected, rtol=0, atol=1e-12)


@pytest.mark.parametrize("face", range(6))
def test_hex20_planar_pressure_has_expected_outward_normal(face: int) -> None:
    normals = ((0, 0, -1), (0, 0, 1), (0, -1, 0), (1, 0, 0), (0, 1, 0), (-1, 0, 0))
    nodes = _cube_nodes()
    pressure = 3.0
    observed = _solid_face_vector(nodes, HEX20_FACES[face], None, pressure, "global").reshape(-1, 3)
    traction = -pressure * np.asarray(normals[face])
    expected = np.zeros((20, 3))
    for node in HEX20_FACES[face][:4]:
        expected[node] = -traction / 12
    for node in HEX20_FACES[face][4:]:
        expected[node] = traction / 3
    np.testing.assert_allclose(observed, expected, rtol=0, atol=1e-12)


def test_linear_quad4_and_tri3_constant_traction_are_unchanged() -> None:
    traction = np.asarray([1.0, 2.0, 3.0])
    quad = np.asarray([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]], dtype=float)
    tri = quad[[0, 1, 3]]
    q = _solid_face_vector(quad, (0, 1, 2, 3), traction, None, "global").reshape(-1, 3)
    t = _solid_face_vector(tri, (0, 1, 2), traction, None, "global").reshape(-1, 3)
    np.testing.assert_allclose(q, np.tile(traction / 4, (4, 1)), rtol=0, atol=1e-12)
    np.testing.assert_allclose(t, np.tile(traction / 6, (3, 1)), rtol=0, atol=1e-12)
