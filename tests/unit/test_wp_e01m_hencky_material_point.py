"""Prepared, unexecuted material-point checks for WP-E01-M Hencky kernels.

These cases call isolated kinematics/material-point helpers only. They do not
assemble elements, invoke a nonlinear solver, or enter native FEM routes.
All numerical tolerances below are proposed test tolerances, not Owner-frozen
scientific acceptance criteria.
"""

from __future__ import annotations

import numpy as np
import pytest

from solveur.materials.finite_strain_hencky import (
    ExperimentalHenckyElastic,
    hencky_kinematics_3d,
    hex8_deformation_gradients,
    hex8_hencky_internal_force,
    tet4_deformation_gradients,
    tet4_hencky_internal_force,
)

MU = 80.0e9
KAPPA = 160.0e9
MATERIAL = ExperimentalHenckyElastic(mu=MU, kappa=KAPPA)
NEARLY_INCOMPRESSIBLE_MATERIAL = ExperimentalHenckyElastic(mu=MU, kappa=1.0e3 * KAPPA)
IDENTITY = np.eye(3)
_STRESS_ATOL = 2.0e-3  # Pa; proposed binary64 roundoff allowance for zero stress.
_STRAIN_ATOL = 2.0e-13  # dimensionless; proposed analytic kinematics comparison.
_OBJECTIVITY_RTOL = 2.0e-13  # Existing relative tolerance, now applied normwise.
_OBJECTIVITY_ROUNDOFF_FACTOR = 64.0
_ENERGY_FD_STEPS = (
    1.024e-3,
    5.12e-4,
    2.56e-4,
    1.28e-4,
    6.4e-5,
    3.2e-5,
    1.6e-5,
    8.0e-6,
    4.0e-6,
    2.0e-6,
)

_OBJECTIVITY_CASES = (
    pytest.param(
        "general-stretch",
        np.diag((1.25, 0.92, 1.08)),
        MATERIAL,
        id="general-stretch",
    ),
    pytest.param(
        "repeated-stretch",
        np.diag((1.1, 1.1, 0.9)),
        MATERIAL,
        id="repeated-stretch",
    ),
    pytest.param(
        "near-clustered-stretch",
        np.diag((1.2, 1.2 * (1.0 + 1.0e-10), 0.85)),
        MATERIAL,
        id="near-clustered-stretch",
    ),
    pytest.param(
        "simple-shear",
        np.array(((1.0, 0.4, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))),
        MATERIAL,
        id="simple-shear",
    ),
    pytest.param(
        "general-3d-shear",
        np.array(((1.13, 0.17, 0.02), (0.03, 0.94, -0.04), (0.01, 0.06, 1.07))),
        MATERIAL,
        id="general-3d-shear",
    ),
    pytest.param(
        "near-incompressible-isochoric",
        np.diag((1.2, 1.2**-0.5, 1.2**-0.5)),
        NEARLY_INCOMPRESSIBLE_MATERIAL,
        id="near-incompressible-isochoric",
    ),
)


def _rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    unit = np.asarray(axis, dtype=float)
    unit /= np.linalg.norm(unit)
    x, y, z = unit
    skew = np.array(((0.0, -z, y), (z, 0.0, -x), (-y, x, 0.0)))
    return IDENTITY + np.sin(angle) * skew + (1.0 - np.cos(angle)) * (skew @ skew)


def _c_spectral_metrics(deformation: np.ndarray) -> tuple[float, float, float, float]:
    right_cauchy_green = deformation.T @ deformation
    eigenvalues = np.linalg.eigvalsh(right_cauchy_green)
    relative_gap = float(np.min(np.diff(eigenvalues)) / eigenvalues[-1])
    return (
        float(eigenvalues[-1] / eigenvalues[0]),
        float(eigenvalues[0]),
        float(eigenvalues[-1]),
        relative_gap,
    )


def _assert_stress_objective(
    actual: np.ndarray,
    expected: np.ndarray,
    material: ExperimentalHenckyElastic,
    *,
    measure: str,
) -> tuple[float, float]:
    """Compare stress tensors with a modulus-scaled, normwise roundoff floor.

    The absolute floor is 64 binary64 epsilons times the largest constitutive
    modulus.  This is a proposed allowance for the small matrix products,
    symmetric eigensolve, spectral reconstruction, and stress push-forward in
    this well-resolved 3D test domain; it is not a universal error guarantee.
    The pre-existing 2e-13 relative tolerance is retained, now applied to a
    Frobenius-norm comparison so exact-zero tensor components are not given a
    zero error allowance.
    """
    difference = float(np.linalg.norm(actual - expected, ord="fro"))
    stress_scale = float(
        max(
            np.linalg.norm(actual, ord="fro"),
            np.linalg.norm(expected, ord="fro"),
        )
    )
    absolute_tolerance = (
        _OBJECTIVITY_ROUNDOFF_FACTOR
        * np.finfo(np.float64).eps
        * max(material.mu, material.kappa)
    )
    allowed = absolute_tolerance + _OBJECTIVITY_RTOL * stress_scale
    assert difference <= allowed, (
        f"{measure} objectivity norm error {difference:.17g} Pa exceeds "
        f"{allowed:.17g} Pa (stress scale {stress_scale:.17g} Pa, "
        f"modulus floor {absolute_tolerance:.17g} Pa)"
    )
    return difference, allowed


def _affine_displacements(coordinates: np.ndarray, deformation: np.ndarray) -> np.ndarray:
    return coordinates @ (deformation - IDENTITY).T


def _standard_hex8_coordinates() -> np.ndarray:
    return np.array(
        (
            (0.0, 0.0, 0.0),
            (1.0, 0.0, 0.0),
            (1.0, 1.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, 0.0, 1.0),
            (1.0, 0.0, 1.0),
            (1.0, 1.0, 1.0),
            (0.0, 1.0, 1.0),
        )
    )


def test_identity_deformation_has_zero_energy_and_all_stresses() -> None:
    response = MATERIAL.evaluate(IDENTITY)
    np.testing.assert_allclose(response.logarithmic_strain, 0.0, atol=_STRAIN_ATOL, rtol=0.0)
    assert response.strain_energy_density == 0.0
    for stress in (
        response.logarithmic_strain_conjugate_stress,
        response.second_piola_kirchhoff_stress,
        response.first_piola_kirchhoff_stress,
        response.cauchy_stress,
    ):
        np.testing.assert_allclose(stress, 0.0, atol=_STRESS_ATOL, rtol=0.0)


@pytest.mark.parametrize("mu, kappa", ((0.0, KAPPA), (MU, 0.0), (-MU, KAPPA), (MU, np.nan)))
def test_nonpositive_or_nonfinite_moduli_are_rejected(mu: float, kappa: float) -> None:
    with pytest.raises(ValueError):
        ExperimentalHenckyElastic(mu=mu, kappa=kappa)


@pytest.mark.parametrize("axis, angle", [((1.0, 2.0, -1.0), 0.37), ((0.0, 1.0, 0.0), 1.5707963267948966)])
def test_proper_rigid_rotation_is_stress_free(axis: tuple[float, ...], angle: float) -> None:
    response = MATERIAL.evaluate(_rotation(np.asarray(axis), angle))
    np.testing.assert_allclose(response.logarithmic_strain, 0.0, atol=3.0e-15, rtol=0.0)
    assert response.strain_energy_density <= 1.0e-8  # J/m^3; proposed roundoff-scale allowance.
    np.testing.assert_allclose(response.cauchy_stress, 0.0, atol=5.0e-4, rtol=0.0)


def test_uniaxial_stretch_has_analytic_principal_strain_energy_and_pk2() -> None:
    stretch = 1.17
    logarithm = np.log(stretch)
    response = MATERIAL.evaluate(np.diag((stretch, 1.0, 1.0)))
    expected_energy = (2.0 * MU / 3.0 + KAPPA / 2.0) * logarithm**2
    expected_conjugate = np.array(
        (
            4.0 * MU * logarithm / 3.0 + KAPPA * logarithm,
            KAPPA * logarithm - 2.0 * MU * logarithm / 3.0,
            KAPPA * logarithm - 2.0 * MU * logarithm / 3.0,
        )
    )
    expected_pk2 = np.diag(expected_conjugate / np.array((stretch**2, 1.0, 1.0)))
    expected_pk1_axial = (4.0 * MU / 3.0 + KAPPA) * logarithm / stretch
    np.testing.assert_allclose(response.principal_logarithmic_strains, (0.0, 0.0, logarithm), atol=2.0e-15)
    assert response.strain_energy_density == pytest.approx(expected_energy, rel=2.0e-14)
    np.testing.assert_allclose(response.second_piola_kirchhoff_stress, expected_pk2, rtol=2.0e-14, atol=1.0e-4)
    assert response.first_piola_kirchhoff_stress[0, 0] == pytest.approx(expected_pk1_axial, rel=2.0e-14)

    # Independent directional reference from the closed-form uniaxial energy
    # derivative, dW/dlambda = (4 mu/3 + kappa) log(lambda)/lambda.
    independent_work_scale = max(abs(expected_pk1_axial), 64.0 * np.finfo(np.float64).eps * max(MU, KAPPA))
    for step in _ENERGY_FD_STEPS:
        plus_energy = MATERIAL.evaluate(np.diag((stretch + step, 1.0, 1.0))).strain_energy_density
        minus_energy = MATERIAL.evaluate(np.diag((stretch - step, 1.0, 1.0))).strain_energy_density
        centered = (plus_energy - minus_energy) / (2.0 * step)
        absolute_error = abs(centered - expected_pk1_axial)
        print(
            f"PK1_UNIAXIAL_INDEPENDENT_SWEEP h={step:.9e} centered_Pa={centered:.12e} "
            f"abs_error_Pa={absolute_error:.9e} "
            f"normalized_error={absolute_error / independent_work_scale:.9e} "
            f"work_scale_Pa={independent_work_scale:.9e} reference=closed_form_energy_derivative"
        )


def test_isotropic_volumetric_stretch_has_analytic_response() -> None:
    stretch = 1.08
    logarithm = np.log(stretch)
    response = MATERIAL.evaluate(stretch * IDENTITY)
    assert response.strain_energy_density == pytest.approx(4.5 * KAPPA * logarithm**2, rel=2.0e-14)
    np.testing.assert_allclose(
        response.second_piola_kirchhoff_stress,
        (3.0 * KAPPA * logarithm / stretch**2) * IDENTITY,
        rtol=2.0e-14,
        atol=1.0e-4,
    )


def test_isochoric_principal_stretches_have_analytic_energy() -> None:
    logarithm = np.log(2.0)
    response = MATERIAL.evaluate(np.diag((2.0, 0.5, 1.0)))
    np.testing.assert_allclose(response.principal_logarithmic_strains, (-logarithm, 0.0, logarithm), atol=2.0e-15)
    assert abs(float(np.trace(response.logarithmic_strain))) <= _STRAIN_ATOL
    assert response.strain_energy_density == pytest.approx(2.0 * MU * logarithm**2, rel=2.0e-14)


def test_simple_shear_principal_strains_match_closed_form() -> None:
    shear = 0.4
    deformation = IDENTITY.copy()
    deformation[0, 1] = shear
    response = MATERIAL.evaluate(deformation)
    discriminant = np.sqrt((2.0 + shear**2) ** 2 - 4.0)
    eigenvalues = np.array(((2.0 + shear**2 - discriminant) / 2.0, 1.0, (2.0 + shear**2 + discriminant) / 2.0))
    expected = 0.5 * np.log(eigenvalues)
    np.testing.assert_allclose(response.principal_logarithmic_strains, expected, rtol=2.0e-14, atol=2.0e-15)
    assert response.jacobian_determinant == pytest.approx(1.0, abs=2.0e-15)


@pytest.mark.parametrize("case_name,deformation,material", _OBJECTIVITY_CASES)
def test_left_rotation_of_stretch_is_objective_for_all_stress_measures(
    case_name: str,
    deformation: np.ndarray,
    material: ExperimentalHenckyElastic,
) -> None:
    rotation = _rotation(np.array((1.0, -2.0, 0.5)), 0.81)
    base = material.evaluate(deformation)
    rotated = material.evaluate(rotation @ deformation)
    rotation_error = float(np.linalg.norm(rotation.T @ rotation - IDENTITY, ord="fro"))
    determinant_error = abs(float(np.linalg.det(rotation)) - 1.0)
    assert rotation_error <= 128.0 * np.finfo(np.float64).eps
    assert determinant_error <= 128.0 * np.finfo(np.float64).eps
    np.testing.assert_allclose(rotated.logarithmic_strain, base.logarithmic_strain, rtol=2.0e-13, atol=2.0e-14)
    assert rotated.strain_energy_density == pytest.approx(base.strain_energy_density, rel=2.0e-13)
    conjugate_error, conjugate_limit = _assert_stress_objective(
        rotated.logarithmic_strain_conjugate_stress,
        base.logarithmic_strain_conjugate_stress,
        material,
        measure="logarithmic-conjugate",
    )
    pk2_error, pk2_limit = _assert_stress_objective(
        rotated.second_piola_kirchhoff_stress,
        base.second_piola_kirchhoff_stress,
        material,
        measure="PK2",
    )
    pk1_error, pk1_limit = _assert_stress_objective(
        rotated.first_piola_kirchhoff_stress,
        rotation @ base.first_piola_kirchhoff_stress,
        material,
        measure="PK1",
    )
    cauchy_error, cauchy_limit = _assert_stress_objective(
        rotated.cauchy_stress,
        rotation @ base.cauchy_stress @ rotation.T,
        material,
        measure="Cauchy",
    )
    cond_c, lambda_min, lambda_max, spectral_gap = _c_spectral_metrics(deformation)
    cond_c_rotated, _, _, rotated_spectral_gap = _c_spectral_metrics(rotation @ deformation)
    assert lambda_min > 0.0 and lambda_max >= lambda_min
    assert rotated.jacobian_determinant == pytest.approx(base.jacobian_determinant, rel=2.0e-13)
    print(
        f"OBJECTIVITY case={case_name} cond_C={max(cond_c, cond_c_rotated):.9e} "
        f"relative_spectral_gap_C={min(spectral_gap, rotated_spectral_gap):.9e} "
        f"lambda_C=[{lambda_min:.9e},{lambda_max:.9e}] "
        f"PK2_norm_Pa={np.linalg.norm(base.second_piola_kirchhoff_stress, ord='fro'):.9e} "
        f"errors_Pa=(M_H:{conjugate_error:.9e}/{conjugate_limit:.9e}, "
        f"S:{pk2_error:.9e}/{pk2_limit:.9e}, P:{pk1_error:.9e}/{pk1_limit:.9e}, "
        f"sigma:{cauchy_error:.9e}/{cauchy_limit:.9e})"
    )


@pytest.mark.parametrize("amplitude", (1.0e-3, 5.0e-4, 2.5e-4))
def test_hencky_strain_has_infinitesimal_symmetric_gradient_limit(amplitude: float) -> None:
    displacement_gradient = np.array(((0.02, 0.03, -0.01), (-0.01, -0.015, 0.04), (0.02, 0.005, 0.01)))
    infinitesimal = 0.5 * (displacement_gradient + displacement_gradient.T)
    response = MATERIAL.evaluate(IDENTITY + amplitude * displacement_gradient)
    error = np.linalg.norm(response.logarithmic_strain - amplitude * infinitesimal)
    assert error <= 2.0 * amplitude**2 * np.linalg.norm(displacement_gradient, ord=2) ** 2


def test_repeated_principal_stretches_have_finite_symmetric_response() -> None:
    response = MATERIAL.evaluate(np.diag((1.1, 1.1, 0.9)))
    assert np.all(np.isfinite(response.second_piola_kirchhoff_stress))
    np.testing.assert_allclose(response.second_piola_kirchhoff_stress, response.second_piola_kirchhoff_stress.T, atol=1.0e-7)
    np.testing.assert_allclose(response.principal_logarithmic_strains, (np.log(0.9), np.log(1.1), np.log(1.1)), atol=2.0e-15)


def test_nearly_repeated_positive_stretches_remain_resolved() -> None:
    stretch = 1.2
    response = MATERIAL.evaluate(np.diag((stretch, stretch * (1.0 + 1.0e-10), 0.85)))
    assert np.all(np.isfinite(response.logarithmic_strain))
    assert np.all(np.isfinite(response.second_piola_kirchhoff_stress))
    assert response.strain_energy_density >= 0.0


@pytest.mark.parametrize(
    "deformation",
    (
        np.diag((1.0, 1.0, 0.0)),
        np.diag((-1.0, 1.0, 1.0)),
        np.diag((1.0, 1.0, 1.0e-8)),  # C has a positive but unresolved eigenvalue at float64 scale.
        np.array(((1.0, 0.0, 0.0), (0.0, np.nan, 0.0), (0.0, 0.0, 1.0))),
        np.array(((1.0 + 0.0j, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))),
    ),
)
def test_singular_inverted_nonfinite_or_complex_f_fails_closed(deformation: np.ndarray) -> None:
    with pytest.raises(ValueError):
        hencky_kinematics_3d(deformation)


def test_principal_strains_reconstruct_right_cauchy_green() -> None:
    deformation = np.array(((1.13, 0.17, 0.02), (0.03, 0.94, -0.04), (0.01, 0.06, 1.07)))
    kinematics = hencky_kinematics_3d(deformation)
    values, vectors = np.linalg.eigh(kinematics.logarithmic_strain)
    reconstructed = (vectors * np.exp(2.0 * values)) @ vectors.T
    np.testing.assert_allclose(reconstructed, kinematics.right_cauchy_green, rtol=3.0e-14, atol=3.0e-14)


def test_energy_matches_definition_for_general_three_dimensional_f() -> None:
    deformation = np.array(((1.13, 0.17, 0.02), (0.03, 0.94, -0.04), (0.01, 0.06, 1.07)))
    response = MATERIAL.evaluate(deformation)
    strain = response.logarithmic_strain
    deviator = strain - np.trace(strain) / 3.0 * IDENTITY
    expected = MU * np.sum(deviator * deviator) + 0.5 * KAPPA * np.trace(strain) ** 2
    assert response.strain_energy_density == pytest.approx(float(expected), rel=2.0e-14, abs=1.0e-12)


@pytest.mark.parametrize(
    "direction_name,direction",
    (
        pytest.param("axial-entry", np.diag((1.0, 0.0, 0.0)), id="axial-entry"),
        pytest.param(
            "simple-shear-entry",
            np.array(((0.0, 1.0, 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0))),
            id="simple-shear-entry",
        ),
        pytest.param(
            "mixed-3d",
            np.array(((0.2, -0.3, 0.1), (0.4, -0.1, 0.2), (-0.2, 0.3, 0.1))),
            id="mixed-3d",
        ),
    ),
)
def test_pk1_is_directional_derivative_of_energy(direction_name: str, direction: np.ndarray) -> None:
    """Run a finite-difference self-consistency sweep against the returned PK1 stress."""
    deformation = np.array(((1.12, 0.08, 0.01), (0.03, 0.94, 0.02), (-0.01, 0.02, 1.06)))
    direction = direction / np.linalg.norm(direction)
    response = MATERIAL.evaluate(deformation)
    analytic = float(np.sum(response.first_piola_kirchhoff_stress * direction))
    work_scale = max(
        abs(analytic),
        float(np.linalg.norm(response.first_piola_kirchhoff_stress, ord="fro") * np.linalg.norm(direction)),
        64.0 * np.finfo(np.float64).eps * max(MU, KAPPA),
    )
    rows: list[dict[str, float | bool]] = []
    for step in _ENERGY_FD_STEPS:
        plus_f = deformation + step * direction
        minus_f = deformation - step * direction
        plus_response = MATERIAL.evaluate(plus_f)
        minus_response = MATERIAL.evaluate(minus_f)
        centered = (
            plus_response.strain_energy_density - minus_response.strain_energy_density
        ) / (2.0 * step)
        absolute_error = abs(centered - analytic)
        roundoff_estimate = (
            np.finfo(np.float64).eps
            * (abs(plus_response.strain_energy_density) + abs(minus_response.strain_energy_density))
            / (2.0 * step)
        )
        cond_plus, lambda_min_plus, _, gap_plus = _c_spectral_metrics(plus_f)
        cond_minus, lambda_min_minus, _, gap_minus = _c_spectral_metrics(minus_f)
        rows.append(
            {
                "step": step,
                "centered": centered,
                "absolute_error": absolute_error,
                "normalized_error": absolute_error / work_scale,
                "roundoff_estimate": roundoff_estimate,
                "condition_c": max(cond_plus, cond_minus),
                "relative_spectral_gap_c": min(gap_plus, gap_minus),
                "lambda_min_c": min(lambda_min_plus, lambda_min_minus),
                "jacobian_min": min(plus_response.jacobian_determinant, minus_response.jacobian_determinant),
                "admissible": (
                    plus_response.jacobian_determinant > 0.0
                    and minus_response.jacobian_determinant > 0.0
                    and lambda_min_plus > 0.0
                    and lambda_min_minus > 0.0
                ),
            }
        )

    assert all(bool(row["admissible"]) for row in rows)
    finite_keys = (
        "centered",
        "absolute_error",
        "normalized_error",
        "roundoff_estimate",
        "condition_c",
        "relative_spectral_gap_c",
        "lambda_min_c",
        "jacobian_min",
    )
    assert all(np.all(np.isfinite([float(row[key]) for key in finite_keys])) for row in rows)
    richardson_rows: list[tuple[float, float, float, float, bool]] = []
    for coarse, fine in zip(rows, rows[1:]):
        richardson = (4.0 * float(fine["centered"]) - float(coarse["centered"])) / 3.0
        richardson_error = abs(richardson - analytic)
        center_delta = abs(float(coarse["centered"]) - float(fine["centered"]))
        estimated_roundoff = float(coarse["roundoff_estimate"]) + float(fine["roundoff_estimate"])
        coarse_error = float(coarse["absolute_error"])
        fine_error = float(fine["absolute_error"])
        observed_order = (
            np.log(coarse_error / fine_error) / np.log(2.0)
            if coarse_error > estimated_roundoff and fine_error > estimated_roundoff and fine_error > 0.0
            else float("nan")
        )
        plateau = center_delta <= estimated_roundoff
        richardson_rows.append((float(coarse["step"]), richardson_error, observed_order, center_delta, plateau))
    for index, row in enumerate(rows):
        richardson_error = (
            richardson_rows[index][1]
            if index < len(richardson_rows)
            else float("nan")
        )
        order = richardson_rows[index][2] if index < len(richardson_rows) else float("nan")
        plateau = richardson_rows[index][4] if index < len(richardson_rows) else False
        print(
            f"PK1_ENERGY_SWEEP direction={direction_name} h={float(row['step']):.9e} "
            f"centered_Pa={float(row['centered']):.12e} "
            f"abs_error_Pa={float(row['absolute_error']):.9e} "
            f"normalized_error={float(row['normalized_error']):.9e} "
            f"richardson_error_Pa={richardson_error:.9e} "
            f"order_if_resolved={order:.6g} roundoff_estimate_Pa={float(row['roundoff_estimate']):.9e} "
            f"cond_C={float(row['condition_c']):.9e} lambda_min_C={float(row['lambda_min_c']):.9e} "
            f"relative_spectral_gap_C={float(row['relative_spectral_gap_c']):.9e} "
            f"minimum_J={float(row['jacobian_min']):.9e} plateau_estimate={plateau}"
        )
    legacy_row = next(row for row in rows if float(row["step"]) == 2.0e-6)
    legacy_relative_error = float(legacy_row["absolute_error"]) / max(abs(analytic), 1.0)
    print(
        f"PK1_ENERGY_REFERENCE returned_PK1_work_Pa={analytic:.12e} work_scale_Pa={work_scale:.12e} "
        f"reference=kernel_stress_energy_self_consistency direction={direction_name} "
        f"legacy_relative_error={legacy_relative_error:.9e} legacy_limit=2.0e-7"
    )
    # Preserve the prior proposed threshold at its exact h=2e-6 point.
    assert legacy_relative_error <= 2.0e-7


def test_pk_stress_transformations_are_explicit_and_cauchy_is_symmetric() -> None:
    deformation = np.array(((1.1, 0.12, 0.0), (0.02, 0.96, 0.03), (0.0, 0.01, 1.04)))
    response = MATERIAL.evaluate(deformation)
    np.testing.assert_allclose(
        response.first_piola_kirchhoff_stress,
        deformation @ response.second_piola_kirchhoff_stress,
        rtol=2.0e-14,
        atol=1.0e-6,
    )
    expected_cauchy = (
        deformation @ response.second_piola_kirchhoff_stress @ deformation.T
        / response.jacobian_determinant
    )
    np.testing.assert_allclose(response.cauchy_stress, expected_cauchy, rtol=2.0e-14, atol=1.0e-6)
    np.testing.assert_allclose(response.cauchy_stress, response.cauchy_stress.T, atol=2.0e-6)


def test_consistent_tangent_is_explicitly_unavailable() -> None:
    response = MATERIAL.evaluate(IDENTITY)
    assert response.tangent_status == "NOT_IMPLEMENTED"
    assert not hasattr(response, "material_tangent_dS_dE")
    assert not hasattr(response, "first_piola_tangent_dP_dF")


def test_tet4_affine_displacement_recovers_constant_f() -> None:
    coordinates = np.array(((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.2, 1.5, 0.0), (0.1, 0.2, 1.2)))
    deformation = np.array(((1.1, 0.08, 0.02), (0.03, 0.94, 0.01), (0.0, 0.04, 1.03)))
    gradients = tet4_deformation_gradients(coordinates, _affine_displacements(coordinates, deformation))
    assert gradients.shape == (1, 3, 3)
    np.testing.assert_allclose(gradients[0], deformation, rtol=2.0e-13, atol=2.0e-13)


def test_hex8_affine_displacement_recovers_f_at_all_existing_gauss_points() -> None:
    coordinates = _standard_hex8_coordinates()
    deformation = np.array(((1.1, 0.08, 0.02), (0.03, 0.94, 0.01), (0.0, 0.04, 1.03)))
    gradients = hex8_deformation_gradients(coordinates, _affine_displacements(coordinates, deformation))
    assert gradients.shape == (8, 3, 3)
    for value in gradients:
        np.testing.assert_allclose(value, deformation, rtol=2.0e-13, atol=2.0e-13)


def test_tet4_force_adapter_matches_uniform_pk1_reference() -> None:
    coordinates = np.array(((0.0, 0.0, 0.0), (2.0, 0.0, 0.0), (0.2, 1.5, 0.0), (0.1, 0.2, 1.2)))
    stretch = 1.17
    deformation = np.diag((stretch, 1.0, 1.0))
    displacement = _affine_displacements(coordinates, deformation)
    logarithm = np.log(stretch)
    pk1 = np.diag(
        (
            (4.0 * MU / 3.0 + KAPPA) * logarithm / stretch,
            (KAPPA - 2.0 * MU / 3.0) * logarithm,
            (KAPPA - 2.0 * MU / 3.0) * logarithm,
        )
    )
    edges = coordinates[1:] - coordinates[0]
    gradients = np.vstack((-np.sum(np.linalg.inv(edges).T, axis=0), np.linalg.inv(edges).T))
    volume = np.linalg.det(edges) / 6.0
    expected = volume * (gradients @ pk1.T).reshape(12)
    actual = tet4_hencky_internal_force(MATERIAL, coordinates, displacement)
    np.testing.assert_allclose(actual, expected, rtol=3.0e-13, atol=2.0e-4)
    np.testing.assert_allclose(actual.reshape(4, 3).sum(axis=0), 0.0, atol=2.0e-4)


def test_hex8_force_adapter_matches_unit_cube_uniform_pk1_reference() -> None:
    coordinates = _standard_hex8_coordinates()
    stretch = 1.17
    displacement = _affine_displacements(coordinates, np.diag((stretch, 1.0, 1.0)))
    logarithm = np.log(stretch)
    pk1 = np.diag(
        (
            (4.0 * MU / 3.0 + KAPPA) * logarithm / stretch,
            (KAPPA - 2.0 * MU / 3.0) * logarithm,
            (KAPPA - 2.0 * MU / 3.0) * logarithm,
        )
    )
    signs = 2.0 * coordinates - 1.0
    integrated_shape_gradients = signs / 4.0  # Exact unit-cube integral of grad_X N_a.
    expected = (integrated_shape_gradients @ pk1.T).reshape(24)
    actual = hex8_hencky_internal_force(MATERIAL, coordinates, displacement)
    np.testing.assert_allclose(actual, expected, rtol=3.0e-13, atol=2.0e-4)
    np.testing.assert_allclose(actual.reshape(8, 3).sum(axis=0), 0.0, atol=2.0e-4)


@pytest.mark.parametrize(
    "coordinates",
    (
        np.array(((0.0, 0.0, 0.0), (0.0, 1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))),
        np.array(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 0.0))),
    ),
)
def test_tet4_inverted_or_degenerate_reference_geometry_is_rejected(coordinates: np.ndarray) -> None:
    with pytest.raises(ValueError):
        tet4_deformation_gradients(coordinates, np.zeros((4, 3)))


def test_hex8_inverted_reference_geometry_is_rejected() -> None:
    coordinates = _standard_hex8_coordinates()
    coordinates[:, 0] = 1.0 - coordinates[:, 0]
    with pytest.raises(ValueError):
        hex8_deformation_gradients(coordinates, np.zeros((8, 3)))
