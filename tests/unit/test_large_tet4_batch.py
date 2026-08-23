from __future__ import annotations

import numpy as np
import pytest

from solveur.elements.solid.tet4 import Tet4Element
from solveur.large.tet4_batch import (
    _tet4_geometry_batch,
    apply_homogeneous_constraints_batch,
    element_dofs_batch,
    petsc_block_values_batch,
    tet4_stiffness_batch,
)
from solveur.materials.solid import SolidMaterial


def test_batched_tet4_stiffness_matches_element_reference() -> None:
    material = SolidMaterial(E=210.0e9, nu=0.3)
    base = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float)
    transforms = [
        np.diag([1.0 + 0.1 * i, 0.8 + 0.03 * i, 1.2 + 0.02 * i])
        for i in range(8)
    ]
    coordinates = np.asarray([base @ transform.T + i for i, transform in enumerate(transforms)])

    batched = tet4_stiffness_batch(coordinates, material.elasticity_matrix)
    reference = np.asarray([Tet4Element(material).stiffness(coords) for coords in coordinates])

    assert np.allclose(batched, reference, rtol=2.0e-14, atol=1.0e-5)
    assert np.allclose(batched, batched.transpose(0, 2, 1))


def test_batched_tet4_geometry_uses_barycentric_gradient_contract() -> None:
    coordinates = np.asarray(
        [
            [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            [[2.0, -1.0, 0.5], [4.0, -1.0, 0.5], [2.0, 2.0, 0.5], [2.0, -1.0, 5.5]],
        ],
        dtype=float,
    )

    _, volumes, gradients = _tet4_geometry_batch(coordinates)

    assert np.all(volumes > 0.0)
    assert np.allclose(gradients.sum(axis=1), 0.0)
    assert np.allclose(gradients[0], [[-1.0, -1.0, -1.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    assert np.allclose(gradients[1], [[-0.5, -1.0 / 3.0, -1.0 / 5.0], [0.5, 0.0, 0.0], [0.0, 1.0 / 3.0, 0.0], [0.0, 0.0, 1.0 / 5.0]])


def test_batched_dofs_and_constraints() -> None:
    nodes = np.asarray([[0, 1, 2, 3], [1, 4, 2, 3]], dtype=np.int64)
    dofs = element_dofs_batch(nodes)
    stiffness = np.ones((2, 12, 12), dtype=float)
    fixed = np.zeros(15, dtype=bool)
    fixed[[0, 1, 2]] = True

    constrained = apply_homogeneous_constraints_batch(stiffness, dofs, fixed)

    assert np.all(constrained[0, :3, :] == 0.0)
    assert np.all(constrained[0, :, :3] == 0.0)
    assert np.all(constrained[1] == 1.0)


def test_batched_tet4_rejects_inverted_element() -> None:
    coords = np.asarray([[[0, 0, 0], [0, 1, 0], [1, 0, 0], [0, 0, 1]]], dtype=float)
    with pytest.raises(ValueError, match="Invalid batched TET4 volume"):
        tet4_stiffness_batch(coords, np.eye(6))


def test_petsc_block_order_reconstructs_scalar_matrix() -> None:
    scalar = np.arange(144, dtype=float).reshape((1, 12, 12))
    blocked = petsc_block_values_batch(scalar)

    assert blocked.flags.c_contiguous
    assert np.array_equal(blocked, scalar)
