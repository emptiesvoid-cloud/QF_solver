"""Prepared element-independent checks for isolated finite-strain material laws.

This NUMERICAL_UNIT module is intentionally unexecuted in the current task.
It imports only NumPy, pytest, and the material-point kernel; it does not
assemble elements or call a public solver route.
"""

from __future__ import annotations

import numpy as np
import pytest

from solveur.materials.finite_strain_elastic import (
    CompressibleNeoHookean,
    FiniteStrainElasticResponse,
    StVenantKirchhoff,
)


_LAMBDA_PA = 121.15384615384616e9
_MU_PA = 80.76923076923077e9
_FD_STEP = 1.0e-6
_PROPOSED_RELATIVE_FD_LIMIT = 2.0e-6


def _models() -> tuple[StVenantKirchhoff | CompressibleNeoHookean, ...]:
    return (
        StVenantKirchhoff(_LAMBDA_PA, _MU_PA),
        CompressibleNeoHookean(_LAMBDA_PA + (2.0 / 3.0) * _MU_PA, _MU_PA),
    )


def _material_scale() -> float:
    return max(abs(_LAMBDA_PA) + 2.0 * _MU_PA, 1.0)


def _assert_response_finite(response: FiniteStrainElasticResponse) -> None:
    arrays = (
        response.deformation_gradient,
        response.green_lagrange_strain,
        response.second_piola_kirchhoff_stress,
        response.first_piola_kirchhoff_stress,
        response.cauchy_stress,
        response.material_tangent_dS_dE,
        response.first_piola_tangent_dP_dF,
    )
    assert all(np.all(np.isfinite(array)) for array in arrays)
    assert np.isfinite(response.jacobian_determinant)
    assert np.isfinite(response.strain_energy_density)


@pytest.mark.parametrize("model", _models(), ids=["stvk", "isochoric-neo-hookean"])
def test_zero_deformation_is_stress_free(model: StVenantKirchhoff | CompressibleNeoHookean) -> None:
    response = model.evaluate(np.eye(3))
    _assert_response_finite(response)
    assert response.jacobian_determinant == pytest.approx(1.0, abs=0.0)
    assert response.strain_energy_density == pytest.approx(0.0, abs=1.0e-12)
    np.testing.assert_allclose(response.green_lagrange_strain, np.zeros((3, 3)), atol=0.0, rtol=0.0)
    np.testing.assert_allclose(response.second_piola_kirchhoff_stress, 0.0, atol=1.0e-12, rtol=0.0)
    np.testing.assert_allclose(response.first_piola_kirchhoff_stress, 0.0, atol=1.0e-12, rtol=0.0)
    np.testing.assert_allclose(response.cauchy_stress, 0.0, atol=1.0e-12, rtol=0.0)


@pytest.mark.parametrize("model", _models(), ids=["stvk", "isochoric-neo-hookean"])
def test_uniaxial_and_simple_shear_match_direct_tensor_references(
    model: StVenantKirchhoff | CompressibleNeoHookean,
) -> None:
    stretch = 1.12
    f_uniaxial = np.diag([stretch, 1.0, 1.0])
    response = model.evaluate(f_uniaxial)
    c = f_uniaxial.T @ f_uniaxial
    green = 0.5 * (c - np.eye(3))
    log_j = np.log(stretch)
    if isinstance(model, StVenantKirchhoff):
        second = _LAMBDA_PA * np.trace(green) * np.eye(3) + 2.0 * _MU_PA * green
        energy = 0.5 * _LAMBDA_PA * np.trace(green) ** 2 + _MU_PA * np.sum(green * green)
    else:
        inverse_c = np.linalg.inv(c)
        bulk = _LAMBDA_PA + (2.0 / 3.0) * _MU_PA
        isochoric_scale = stretch ** (-2.0 / 3.0)
        first_invariant = float(np.trace(c))
        second = (
            _MU_PA * isochoric_scale * (np.eye(3) - (first_invariant / 3.0) * inverse_c)
            + bulk * log_j * inverse_c
        )
        energy = (
            0.5 * _MU_PA * (isochoric_scale * first_invariant - 3.0)
            + 0.5 * bulk * log_j**2
        )
    first = f_uniaxial @ second
    np.testing.assert_allclose(response.green_lagrange_strain, green, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(response.second_piola_kirchhoff_stress, second, rtol=1.0e-14, atol=1.0e-5)
    np.testing.assert_allclose(response.first_piola_kirchhoff_stress, first, rtol=1.0e-14, atol=1.0e-5)
    assert response.strain_energy_density == pytest.approx(energy, rel=1.0e-14, abs=1.0e-5)

    shear = 0.18
    f_shear = np.array([[1.0, shear, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    shear_response = model.evaluate(f_shear)
    expected_green = 0.5 * (f_shear.T @ f_shear - np.eye(3))
    np.testing.assert_allclose(shear_response.green_lagrange_strain, expected_green, atol=0.0, rtol=0.0)
    assert shear_response.jacobian_determinant == pytest.approx(1.0, abs=1.0e-14)
    if isinstance(model, StVenantKirchhoff):
        expected_second_shear = _LAMBDA_PA * (shear**2 / 2.0) * np.eye(3)
        expected_second_shear[1, 1] += _MU_PA * shear
        expected_second_shear[0, 1] = expected_second_shear[1, 0] = _MU_PA * shear
        expected_shear_energy = (
            _LAMBDA_PA * shear**4 / 8.0
            + _MU_PA * (shear**4 / 4.0 + shear**2 / 2.0)
        )
    else:
        inverse_c_shear = np.array(
            [[1.0 + shear**2, -shear, 0.0], [-shear, 1.0, 0.0], [0.0, 0.0, 1.0]]
        )
        shear_first_invariant = 3.0 + shear**2
        expected_second_shear = _MU_PA * (
            np.eye(3) - (shear_first_invariant / 3.0) * inverse_c_shear
        )
        expected_shear_energy = 0.5 * _MU_PA * shear**2
    np.testing.assert_allclose(
        shear_response.second_piola_kirchhoff_stress,
        expected_second_shear,
        rtol=1.0e-14,
        atol=1.0e-5,
    )
    np.testing.assert_allclose(
        shear_response.first_piola_kirchhoff_stress,
        f_shear @ expected_second_shear,
        rtol=1.0e-14,
        atol=1.0e-5,
    )
    assert shear_response.strain_energy_density == pytest.approx(
        expected_shear_energy, rel=1.0e-14, abs=1.0e-5
    )


@pytest.mark.parametrize("model", _models(), ids=["stvk", "isochoric-neo-hookean"])
def test_rigid_rotation_and_rotation_plus_stretch_are_objective(
    model: StVenantKirchhoff | CompressibleNeoHookean,
) -> None:
    angle = 0.61
    rotation = np.array(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    rotated = model.evaluate(rotation)
    assert rotated.strain_energy_density == pytest.approx(0.0, abs=1.0e-11)
    roundoff_stress_tolerance = 1.0e-14 * _material_scale()
    np.testing.assert_allclose(
        rotated.second_piola_kirchhoff_stress, 0.0, atol=roundoff_stress_tolerance, rtol=0.0
    )
    np.testing.assert_allclose(
        rotated.first_piola_kirchhoff_stress, 0.0, atol=roundoff_stress_tolerance, rtol=0.0
    )

    stretch = np.diag([1.15, 0.94, 1.07])
    reference = model.evaluate(stretch)
    rotated_stretch = model.evaluate(rotation @ stretch)
    np.testing.assert_allclose(
        rotated_stretch.green_lagrange_strain,
        reference.green_lagrange_strain,
        rtol=2.0e-14,
        atol=2.0e-14,
    )
    np.testing.assert_allclose(
        rotated_stretch.second_piola_kirchhoff_stress,
        reference.second_piola_kirchhoff_stress,
        rtol=2.0e-13,
        atol=2.0e-5,
    )
    np.testing.assert_allclose(
        rotated_stretch.first_piola_kirchhoff_stress,
        rotation @ reference.first_piola_kirchhoff_stress,
        rtol=2.0e-13,
        atol=2.0e-5,
    )
    np.testing.assert_allclose(
        rotated_stretch.cauchy_stress,
        rotation @ reference.cauchy_stress @ rotation.T,
        rtol=2.0e-13,
        atol=2.0e-5,
    )
    assert rotated_stretch.strain_energy_density == pytest.approx(
        reference.strain_energy_density, rel=2.0e-13, abs=1.0e-5
    )


@pytest.mark.parametrize("model", _models(), ids=["stvk", "isochoric-neo-hookean"])
def test_energy_gradient_and_first_piola_tangent_match_centered_differences(
    model: StVenantKirchhoff | CompressibleNeoHookean,
) -> None:
    deformation = np.array([[1.08, 0.11, -0.02], [0.03, 0.96, 0.04], [0.01, -0.05, 1.04]])
    base = model.evaluate(deformation)
    energy_gradient = np.zeros((3, 3))
    tangent_fd = np.zeros((3, 3, 3, 3))
    for k in range(3):
        for ell in range(3):
            direction = np.zeros((3, 3))
            direction[k, ell] = _FD_STEP
            plus = model.evaluate(deformation + direction)
            minus = model.evaluate(deformation - direction)
            energy_gradient[k, ell] = (
                plus.strain_energy_density - minus.strain_energy_density
            ) / (2.0 * _FD_STEP)
            tangent_fd[:, :, k, ell] = (
                plus.first_piola_kirchhoff_stress - minus.first_piola_kirchhoff_stress
            ) / (2.0 * _FD_STEP)

    stress_scale = _material_scale()
    gradient_error = float(
        np.linalg.norm(energy_gradient - base.first_piola_kirchhoff_stress, ord="fro") / stress_scale
    )
    tangent_error = float(
        np.linalg.norm(tangent_fd - base.first_piola_tangent_dP_dF)
        / (stress_scale * np.sqrt(81.0))
    )
    assert gradient_error <= _PROPOSED_RELATIVE_FD_LIMIT
    assert tangent_error <= _PROPOSED_RELATIVE_FD_LIMIT


@pytest.mark.parametrize("model", _models(), ids=["stvk", "isochoric-neo-hookean"])
def test_material_tangent_symmetries_and_dS_dE_finite_difference(
    model: StVenantKirchhoff | CompressibleNeoHookean,
) -> None:
    deformation = np.array([[1.08, 0.11, -0.02], [0.03, 0.96, 0.04], [0.01, -0.05, 1.04]])
    response = model.evaluate(deformation)
    c = deformation.T @ deformation
    tangent = response.material_tangent_dS_dE
    assert np.linalg.norm(response.cauchy_stress - response.cauchy_stress.T) / _material_scale() <= 1.0e-12
    symmetry_tolerance = 2.0e-12 * _material_scale()
    np.testing.assert_allclose(tangent, tangent.swapaxes(0, 1), rtol=0.0, atol=symmetry_tolerance)
    np.testing.assert_allclose(tangent, tangent.swapaxes(2, 3), rtol=0.0, atol=symmetry_tolerance)
    np.testing.assert_allclose(
        tangent, tangent.transpose(2, 3, 0, 1), rtol=2.0e-14, atol=symmetry_tolerance
    )
    first_tangent = response.first_piola_tangent_dP_dF
    np.testing.assert_allclose(
        first_tangent,
        first_tangent.transpose(2, 3, 0, 1),
        rtol=2.0e-13,
        atol=symmetry_tolerance,
    )

    symmetric_directions = []
    for i in range(3):
        direction = np.zeros((3, 3))
        direction[i, i] = 1.0
        symmetric_directions.append(direction)
    for i, j in ((0, 1), (1, 2), (0, 2)):
        direction = np.zeros((3, 3))
        direction[i, j] = direction[j, i] = 0.5
        symmetric_directions.append(direction)

    for direction in symmetric_directions:
        c_plus = c + 2.0 * _FD_STEP * direction
        c_minus = c - 2.0 * _FD_STEP * direction
        f_plus = np.linalg.cholesky(c_plus).T
        f_minus = np.linalg.cholesky(c_minus).T
        numerical = (
            model.evaluate(f_plus).second_piola_kirchhoff_stress
            - model.evaluate(f_minus).second_piola_kirchhoff_stress
        ) / (2.0 * _FD_STEP)
        analytic = np.einsum("IJKL,KL->IJ", tangent, direction)
        assert np.linalg.norm(numerical - analytic, ord="fro") / _material_scale() <= _PROPOSED_RELATIVE_FD_LIMIT


def test_isochoric_neo_hookean_has_the_correct_small_strain_limit() -> None:
    bulk = _LAMBDA_PA + (2.0 / 3.0) * _MU_PA
    model = CompressibleNeoHookean(bulk, _MU_PA)
    infinitesimal = np.array([[2.0e-7, 0.7e-7, -0.2e-7], [0.7e-7, -1.0e-7, 0.4e-7], [-0.2e-7, 0.4e-7, 0.5e-7]])
    response = model.evaluate(np.eye(3) + infinitesimal)
    lambda_from_bulk = bulk - (2.0 / 3.0) * _MU_PA
    expected = lambda_from_bulk * np.trace(infinitesimal) * np.eye(3) + 2.0 * _MU_PA * infinitesimal
    assert np.linalg.norm(response.first_piola_kirchhoff_stress - expected, ord="fro") / _material_scale() <= 1.0e-6


@pytest.mark.parametrize("model", _models(), ids=["stvk", "isochoric-neo-hookean"])
@pytest.mark.parametrize(
    "invalid_f",
    [np.diag([-1.0, 1.0, 1.0]), np.zeros((3, 3)), np.full((3, 3), np.nan)],
    ids=["inverted", "singular", "nonfinite"],
)
def test_invalid_or_orientation_reversing_deformation_is_refused(
    model: StVenantKirchhoff | CompressibleNeoHookean,
    invalid_f: np.ndarray,
) -> None:
    with pytest.raises(ValueError):
        model.evaluate(invalid_f)
