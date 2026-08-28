from __future__ import annotations

import numpy as np

from solveur.elements.solid.hex8_total_lagrangian_batch import TotalLagrangianHex8Assembly
from solveur.materials.solid import SolidMaterial


REFERENCE_HEX = np.array(
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


def assembly() -> TotalLagrangianHex8Assembly:
    return TotalLagrangianHex8Assembly(
        REFERENCE_HEX,
        np.array([[0, 1, 2, 3, 4, 5, 6, 7]]),
        SolidMaterial(E=210.0e3, nu=0.3),
    )


def affine_displacement(deformation: np.ndarray) -> np.ndarray:
    return (REFERENCE_HEX @ (deformation - np.eye(3)).T).reshape(24)


def test_hex8_total_lagrangian_reference_matches_zero_force_and_positive_energy() -> None:
    element = assembly()
    internal, tangent = element.assemble(np.zeros(24))

    np.testing.assert_allclose(internal, 0.0, atol=1.0e-10)
    assert tangent is not None
    np.testing.assert_allclose(tangent.toarray(), tangent.toarray().T, atol=1.0e-8)


def test_hex8_total_lagrangian_rigid_rotation_is_objective() -> None:
    angle = np.deg2rad(41.0)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    element = assembly()
    displacement = affine_displacement(rotation)
    internal, _ = element.assemble(displacement)

    assert np.linalg.norm(internal) < 1.0e-7
    assert element.strain_energy(displacement) < 1.0e-8


def test_hex8_total_lagrangian_tangent_matches_finite_difference() -> None:
    element = assembly()
    displacement = np.linspace(-2.0e-4, 3.0e-4, 24)
    _, tangent = element.assemble(displacement)
    assert tangent is not None
    step = 1.0e-7
    numerical = np.zeros((24, 24))
    for column in range(24):
        perturbation = np.zeros(24)
        perturbation[column] = step
        plus = element.assemble(displacement + perturbation, tangent_required=False)[0]
        minus = element.assemble(displacement - perturbation, tangent_required=False)[0]
        numerical[:, column] = (plus - minus) / (2.0 * step)

    relative_error = np.linalg.norm(tangent.toarray() - numerical) / np.linalg.norm(numerical)
    assert relative_error < 1.0e-7


def test_hex8_total_lagrangian_accepts_a_distorted_positive_jacobian_mesh() -> None:
    distorted = REFERENCE_HEX.copy()
    distorted[2] = [1.12, 0.94, 0.08]
    distorted[6] = [1.08, 1.06, 1.14]
    element = TotalLagrangianHex8Assembly(
        distorted,
        np.array([[0, 1, 2, 3, 4, 5, 6, 7]]),
        SolidMaterial(E=210.0e3, nu=0.3),
    )

    determinants = element.deformation_determinants(np.zeros(24))
    assert np.all(determinants > 0.0)
    displacement = np.linspace(-1.0e-5, 1.5e-5, 24)
    internal, tangent = element.assemble(displacement)
    assert np.all(np.isfinite(internal))
    assert tangent is not None
    assert np.all(np.isfinite(tangent.data))
