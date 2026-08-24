"""Common element-level contract checks for the small-strain J2 adapter."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.hex20 import Hex20Element
from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet10 import Tet10Element
from solveur.materials.solid import VonMisesElastoplasticMaterial


def _tet4_coords() -> np.ndarray:
    return np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])


def _tet10_coords() -> np.ndarray:
    corners = _tet4_coords()
    edges = ((0, 1), (1, 2), (2, 0), (0, 3), (1, 3), (2, 3))
    return np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])


def _hex8_coords() -> np.ndarray:
    return np.asarray(
        [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]],
        dtype=float,
    )


def _hex20_coords() -> np.ndarray:
    corners = _hex8_coords()
    edges = ((0, 1), (0, 3), (0, 4), (1, 2), (1, 5), (2, 3), (2, 6), (3, 7), (4, 5), (4, 7), (5, 6), (6, 7))
    return np.vstack([corners, [(corners[first] + corners[second]) / 2.0 for first, second in edges]])


@pytest.mark.parametrize(
    ("element_type", "coords", "dof_count"),
    [
        (Tet4Element, _tet4_coords(), 12),
        (Tet10Element, _tet10_coords(), 30),
        (Hex8Element, _hex8_coords(), 24),
        (Hex20Element, _hex20_coords(), 60),
    ],
)
def test_solid_elements_share_stateful_internal_force_tangent_contract(element_type, coords, dof_count) -> None:
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=100.0)
    element = element_type(material)
    displacement = np.asarray([[0.08 * point[0], 0.0, 0.0] for point in coords]).reshape(-1)

    internal, tangent, states = element.internal_force_tangent_state(coords, displacement)

    assert internal.shape == (dof_count,)
    assert tangent.shape == (dof_count, dof_count)
    assert len(states) == element.integration_point_count
    assert np.all(np.isfinite(internal))
    assert np.all(np.isfinite(tangent))
    assert all(float(state["equivalent_plastic_strain"]) > 0.0 for state in states)


@pytest.mark.parametrize("element_type", [Tet4Element, Tet10Element])
def test_low_order_tetra_element_tangent_matches_internal_force_finite_difference(element_type) -> None:
    """Check the element tangent against the committed-state force derivative."""
    coords = _tet4_coords() if element_type is Tet4Element else _tet10_coords()
    material = VonMisesElastoplasticMaterial(E=1000.0, nu=0.25, yield_stress=5.0, hardening_modulus=100.0)
    element = element_type(material)
    displacement = np.asarray([[0.08 * x, 0.02 * y, -0.01 * z] for x, y, z in coords]).reshape(-1)

    _, tangent, _ = element.internal_force_tangent_state(coords, displacement)
    finite_difference = np.zeros_like(tangent)
    step = 1.0e-6
    for column in range(displacement.size):
        plus = displacement.copy()
        minus = displacement.copy()
        plus[column] += step
        minus[column] -= step
        force_plus, _, _ = element.internal_force_tangent_state(coords, plus)
        force_minus, _, _ = element.internal_force_tangent_state(coords, minus)
        finite_difference[:, column] = (force_plus - force_minus) / (2.0 * step)

    relative_error = np.linalg.norm(tangent - finite_difference) / max(1.0, np.linalg.norm(finite_difference))
    assert relative_error < 1.0e-7
