"""Mechanical verification of the finite-kinematics TET4 kernel."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.elements.solid.tet4 import Tet4Element
from solveur.elements.solid.tet4_total_lagrangian import TotalLagrangianTet4Kernel
from solveur.materials.solid import SolidMaterial


REFERENCE_TETRA = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])


def kernel() -> TotalLagrangianTet4Kernel:
    return TotalLagrangianTet4Kernel(SolidMaterial(E=210.0e9, nu=0.3))


def affine_displacement(deformation: np.ndarray) -> np.ndarray:
    return (REFERENCE_TETRA @ (deformation - np.eye(3)).T).reshape(12)


def test_total_lagrangian_tangent_matches_linear_tet4_at_reference_state():
    material = SolidMaterial(E=70.0e9, nu=0.28)
    nonlinear = TotalLagrangianTet4Kernel(material)

    internal, tangent = nonlinear.internal_force_and_tangent(REFERENCE_TETRA, np.zeros(12))

    np.testing.assert_allclose(internal, 0.0, atol=1.0e-12)
    np.testing.assert_allclose(tangent, Tet4Element(material).stiffness(REFERENCE_TETRA), rtol=1.0e-13)


def test_total_lagrangian_rigid_rotation_is_stress_and_energy_free():
    angle = np.deg2rad(73.0)
    rotation = np.array(
        [[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]]
    )
    local_u = affine_displacement(rotation)

    internal, tangent = kernel().internal_force_and_tangent(REFERENCE_TETRA, local_u)

    assert np.linalg.norm(internal) < 1.0e-4
    assert kernel().strain_energy(REFERENCE_TETRA, local_u) < 1.0e-6
    np.testing.assert_allclose(tangent, tangent.T, rtol=1.0e-13, atol=1.0e-4)


def test_total_lagrangian_homogeneous_extension_matches_analytical_energy():
    stretch = 1.2
    deformation = np.diag([stretch, 1.0, 1.0])
    strain_x = 0.5 * (stretch**2 - 1.0)
    lam, mu = kernel().lame_constants
    expected_density = 0.5 * lam * strain_x**2 + mu * strain_x**2
    expected_energy = Tet4Element.signed_volume(REFERENCE_TETRA) * expected_density

    energy = kernel().strain_energy(REFERENCE_TETRA, affine_displacement(deformation))

    assert energy == pytest.approx(expected_energy, rel=1.0e-14)


def test_total_lagrangian_consistent_tangent_matches_finite_differences():
    deformation = np.array([[1.12, 0.08, 0.0], [0.03, 0.94, 0.04], [0.02, -0.01, 1.06]])
    local_u = affine_displacement(deformation)
    element = kernel()
    _, tangent = element.internal_force_and_tangent(REFERENCE_TETRA, local_u)
    numerical = np.zeros_like(tangent)
    step = 1.0e-7
    for column in range(12):
        perturbation = np.zeros(12)
        perturbation[column] = step
        plus = element.internal_force_and_tangent(REFERENCE_TETRA, local_u + perturbation)[0]
        minus = element.internal_force_and_tangent(REFERENCE_TETRA, local_u - perturbation)[0]
        numerical[:, column] = (plus - minus) / (2.0 * step)

    error = np.linalg.norm(tangent - numerical) / np.linalg.norm(numerical)
    assert error < 1.0e-8


def test_internal_force_only_matches_full_kernel():
    kernel = TotalLagrangianTet4Kernel(SolidMaterial(E=70.0e9, nu=0.29))
    displacement = np.linspace(-2.0e-4, 3.0e-4, 12)

    force_only = kernel.internal_force(REFERENCE_TETRA, displacement)
    force_full, _ = kernel.internal_force_and_tangent(REFERENCE_TETRA, displacement)

    np.testing.assert_allclose(force_only, force_full, rtol=0.0, atol=1.0e-12)


def test_total_lagrangian_rejects_inverted_current_configuration():
    deformation = np.diag([-0.1, 1.0, 1.0])

    with pytest.raises(ValueError, match="deformation gradient determinant"):
        kernel().internal_force_and_tangent(REFERENCE_TETRA, affine_displacement(deformation))
