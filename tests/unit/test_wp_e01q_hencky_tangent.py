"""Prepared material-point diagnostics for the experimental Hencky tangent.

This module is intentionally not executed or collected under WP-E01-Q.  The
candidate tolerances are diagnostic gates for a later exact-path Owner GO;
they are not frozen scientific acceptance criteria.  It uses only NumPy,
pytest, and the isolated Hencky material-point interfaces.  Static AST
inventory: 13 test functions and 35 parameter-expanded cases.
"""

from __future__ import annotations

from decimal import Decimal, localcontext

import numpy as np
import pytest

from solveur.materials.finite_strain_hencky import ExperimentalHenckyElastic
from solveur.materials.finite_strain_hencky_tangent import hencky_directional_tangent_3d


MU = 80.0e9
KAPPA = 160.0e9
BASE = ExperimentalHenckyElastic(mu=MU, kappa=KAPPA)
NEARLY_INCOMPRESSIBLE = ExperimentalHenckyElastic(mu=MU, kappa=1.0e3 * KAPPA)
IDENTITY = np.eye(3)
FD_STEPS = (2.0e-3, 1.0e-3, 5.0e-4, 2.5e-4, 1.25e-4, 6.25e-5, 3.125e-5)
_EPS = np.finfo(np.float64).eps


def _rotation(axis: tuple[float, float, float], angle: float) -> np.ndarray:
    vector = np.asarray(axis, dtype=np.float64)
    vector /= np.linalg.norm(vector)
    x, y, z = vector
    skew = np.array(((0.0, -z, y), (z, 0.0, -x), (-y, x, 0.0)))
    return IDENTITY + np.sin(angle) * skew + (1.0 - np.cos(angle)) * (skew @ skew)


def _normalized(value: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(value, ord="fro"))
    if not np.isfinite(norm) or norm <= 128.0 * _EPS:
        raise ValueError("Diagnostic direction is zero or numerically degenerate.")
    return np.asarray(value, dtype=np.float64) / norm


def _diag_decimal_oracle(
    mu_text: str,
    kappa_text: str,
    stretches_text: tuple[str, str, str],
    direction_text: tuple[str, str, str],
) -> tuple[np.ndarray, np.ndarray]:
    """Independent closed-form Decimal P and dP for diagonal F and dF.

    Inputs are decimal strings by design.  The oracle does not obtain extra
    digits by converting already-rounded binary64 production outputs.
    """
    with localcontext() as context:
        context.prec = 70
        mu = Decimal(mu_text)
        kappa = Decimal(kappa_text)
        stretches = tuple(Decimal(item) for item in stretches_text)
        increments = tuple(Decimal(item) for item in direction_text)
        logs = tuple(value.ln() for value in stretches)
        log_trace = sum(logs, Decimal(0))
        dlog = tuple(increment / value for increment, value in zip(increments, stretches))
        dlog_trace = sum(dlog, Decimal(0))
        conjugate = tuple(
            2 * mu * (value - log_trace / 3) + kappa * log_trace
            for value in logs
        )
        dconjugate = tuple(
            2 * mu * (value - dlog_trace / 3) + kappa * dlog_trace
            for value in dlog
        )
        pk1 = tuple(value / stretch for value, stretch in zip(conjugate, stretches))
        tangent = tuple(
            dvalue / stretch - value * increment / (stretch * stretch)
            for value, dvalue, stretch, increment in zip(
                conjugate, dconjugate, stretches, increments
            )
        )
        return (
            np.diag([float(value) for value in pk1]),
            np.diag([float(value) for value in tangent]),
        )


def _diag_decimal_energy_hessian(
    mu_text: str,
    kappa_text: str,
    stretches_text: tuple[str, str, str],
    direction_text: tuple[str, str, str],
) -> Decimal:
    """Differentiate the closed-form diagonal energy twice in Decimal."""
    with localcontext() as context:
        context.prec = 70
        mu = Decimal(mu_text)
        kappa = Decimal(kappa_text)
        stretches = tuple(Decimal(item) for item in stretches_text)
        increments = tuple(Decimal(item) for item in direction_text)
        logarithms = tuple(value.ln() for value in stretches)
        first = tuple(step / value for step, value in zip(increments, stretches))
        second = tuple(-(step / value) ** 2 for step, value in zip(increments, stretches))
        trace = sum(logarithms, Decimal(0))
        trace_first = sum(first, Decimal(0))
        trace_second = sum(second, Decimal(0))
        volumetric_coefficient = kappa / 2 - mu / 3
        return (
            2 * mu * sum(
                (d1 * d1 + value * d2 for value, d1, d2 in zip(logarithms, first, second)),
                Decimal(0),
            )
            + 2
            * volumetric_coefficient
            * (trace_first * trace_first + trace * trace_second)
        )


def _difference_action(
    material: ExperimentalHenckyElastic,
    deformation: np.ndarray,
    direction: np.ndarray,
    step: float,
) -> np.ndarray:
    plus = material.evaluate(deformation + step * direction).first_piola_kirchhoff_stress
    minus = material.evaluate(deformation - step * direction).first_piola_kirchhoff_stress
    return (plus - minus) / (2.0 * step)


_FD_CASES = (
    pytest.param(
        BASE,
        np.diag((1.18, 0.91, 1.07)),
        np.array(((0.3, -0.2, 0.1), (0.2, 0.1, -0.25), (0.0, 0.15, -0.1))),
        id="general-stretch",
    ),
    pytest.param(
        BASE,
        np.diag((1.1, 1.1, 0.9)),
        np.array(((0.2, 0.1, 0.0), (-0.1, -0.15, 0.2), (0.1, 0.0, -0.05))),
        id="repeated-stretches",
    ),
    pytest.param(
        BASE,
        np.diag((1.2, 1.2 * (1.0 + 1.0e-10), 0.85)),
        np.array(((0.1, -0.2, 0.1), (0.2, 0.05, -0.1), (-0.1, 0.2, 0.0))),
        id="near-clustered-stretches",
    ),
    pytest.param(
        BASE,
        _rotation((1.0, -2.0, 0.5), 0.41) @ np.diag((1.16, 0.94, 1.03)),
        np.array(((0.1, 0.2, -0.1), (-0.2, 0.05, 0.15), (0.1, -0.1, 0.2))),
        id="rotated-stretch",
    ),
    pytest.param(
        BASE,
        np.array(((1.0, 0.32, 0.08), (0.0, 1.0, -0.11), (0.0, 0.0, 1.0))),
        np.array(((0.1, -0.2, 0.1), (0.2, 0.05, -0.1), (-0.1, 0.2, 0.0))),
        id="three-dimensional-shear",
    ),
    pytest.param(
        NEARLY_INCOMPRESSIBLE,
        np.diag((1.2, 1.2**-0.5, 1.2**-0.5)),
        np.array(((0.1, -0.2, 0.1), (0.2, 0.05, -0.1), (-0.1, 0.2, 0.0))),
        id="near-incompressible-isochoric",
    ),
)

_OBJECTIVITY_CASES = (
    pytest.param(BASE, np.diag((1.1, 1.1, 0.9)), id="repeated"),
    pytest.param(BASE, np.diag((1.2, 1.2 * (1.0 + 1.0e-10), 0.85)), id="clustered"),
    pytest.param(BASE, np.array(((1.0, 0.3, 0.0), (0.0, 1.0, 0.1), (0.0, 0.0, 1.0))), id="shear"),
    pytest.param(
        NEARLY_INCOMPRESSIBLE,
        np.diag((1.2, 1.2**-0.5, 1.2**-0.5)),
        id="near-incompressible",
    ),
)


def test_identity_state_has_analytic_linear_elastic_tangent_action() -> None:
    direction = np.array(((0.2, -0.3, 0.1), (0.5, -0.1, 0.2), (-0.2, 0.4, -0.1)))
    symmetric = 0.5 * (direction + direction.T)
    trace = float(np.trace(symmetric))
    expected = 2.0 * MU * (symmetric - trace * IDENTITY / 3.0) + KAPPA * trace * IDENTITY
    actual = hencky_directional_tangent_3d(BASE, IDENTITY, direction)
    scale_floor = 128.0 * _EPS * max(MU, KAPPA) * np.linalg.norm(direction, ord="fro")
    np.testing.assert_allclose(actual, expected, rtol=3.0e-13, atol=scale_floor)


def test_identity_state_maps_an_infinitesimal_rigid_spin_to_zero() -> None:
    spin = np.array(((0.0, -0.4, 0.2), (0.4, 0.0, -0.1), (-0.2, 0.1, 0.0)))
    actual = hencky_directional_tangent_3d(BASE, IDENTITY, spin)
    floor = 128.0 * _EPS * max(MU, KAPPA) * np.linalg.norm(spin, ord="fro")
    np.testing.assert_allclose(actual, np.zeros((3, 3)), rtol=0.0, atol=floor)


@pytest.mark.parametrize("stretch", (0.82, 1.0, 1.23), ids=("compression", "identity", "extension"))
def test_isotropic_volumetric_state_matches_closed_form_tangent(stretch: float) -> None:
    amplitude = 0.37
    deformation = stretch * IDENTITY
    direction = amplitude * IDENTITY
    expected = 3.0 * KAPPA * (1.0 - np.log(stretch)) * amplitude / (stretch**2) * IDENTITY
    actual = hencky_directional_tangent_3d(BASE, deformation, direction)
    floor = 128.0 * _EPS * KAPPA * np.linalg.norm(direction, ord="fro")
    np.testing.assert_allclose(actual, expected, rtol=4.0e-13, atol=floor)


@pytest.mark.parametrize(
    "mu_text,kappa_text,material,stretches,direction",
    (
        pytest.param(
            "80000000000", "160000000000", BASE,
            ("1.18", "0.91", "1.07"), ("0.3", "-0.2", "0.1"),
            id="base-moduli",
        ),
        pytest.param(
            "80000000000", "160000000000000", NEARLY_INCOMPRESSIBLE,
            ("1.2", "0.91287092917527685576", "0.91287092917527685576"),
            ("0.1", "-0.05", "-0.05"),
            id="high-bulk-modulus",
        ),
    ),
)
def test_diagonal_tangent_matches_independent_decimal_closed_form(
    mu_text: str,
    kappa_text: str,
    material: ExperimentalHenckyElastic,
    stretches: tuple[str, str, str],
    direction: tuple[str, str, str],
) -> None:
    deformation = np.diag(tuple(float(value) for value in stretches))
    delta = np.diag(tuple(float(value) for value in direction))
    expected_pk1, expected_action = _diag_decimal_oracle(
        mu_text, kappa_text, stretches, direction
    )
    expected_energy_hessian = float(
        _diag_decimal_energy_hessian(mu_text, kappa_text, stretches, direction)
    )
    response = material.evaluate(deformation)
    actual_action = hencky_directional_tangent_3d(material, deformation, delta)
    modulus = max(material.mu, material.kappa)
    scale_floor = 128.0 * _EPS * modulus * np.linalg.norm(delta, ord="fro")
    np.testing.assert_allclose(response.first_piola_kirchhoff_stress, expected_pk1, rtol=8.0e-14, atol=scale_floor)
    np.testing.assert_allclose(actual_action, expected_action, rtol=8.0e-13, atol=scale_floor)
    energy_hessian = float(np.sum(delta * actual_action))
    assert energy_hessian == pytest.approx(
        expected_energy_hessian,
        rel=1.0e-12,
        abs=scale_floor * np.linalg.norm(delta, ord="fro"),
    )


@pytest.mark.parametrize("material,deformation,direction", _FD_CASES)
def test_directional_tangent_matches_multistep_centered_pk1_difference(
    material: ExperimentalHenckyElastic,
    deformation: np.ndarray,
    direction: np.ndarray,
) -> None:
    delta = _normalized(direction)
    analytic = hencky_directional_tangent_3d(material, deformation, delta)
    action_scale = max(
        float(np.linalg.norm(analytic, ord="fro")),
        128.0 * _EPS * max(material.mu, material.kappa),
    )
    errors: list[float] = []
    for step in FD_STEPS:
        numeric = _difference_action(material, deformation, delta, step)
        absolute = float(np.linalg.norm(numeric - analytic, ord="fro"))
        errors.append(absolute)
        print(
            f"HENCKY_A_FD case={material.kappa / material.mu:.9g} h={step:.9e} "
            f"analytic_norm_Pa={np.linalg.norm(analytic):.12e} "
            f"numeric_norm_Pa={np.linalg.norm(numeric):.12e} abs_error_Pa={absolute:.9e} "
            f"normalized_error={absolute / action_scale:.9e}"
        )
    candidate_relative = 2.0e-7
    candidate_absolute = 256.0 * _EPS * max(material.mu, material.kappa)
    assert min(errors) <= candidate_absolute + candidate_relative * action_scale


@pytest.mark.parametrize("material,deformation", _OBJECTIVITY_CASES)
def test_directional_tangent_is_covariant_under_superposed_rotation(
    material: ExperimentalHenckyElastic,
    deformation: np.ndarray,
) -> None:
    rotation = _rotation((2.0, -1.0, 3.0), 0.63)
    direction = _normalized(np.array(((0.1, 0.3, -0.2), (0.05, -0.1, 0.2), (-0.3, 0.1, 0.2))))
    original = hencky_directional_tangent_3d(material, deformation, direction)
    rotated = hencky_directional_tangent_3d(
        material, rotation @ deformation, rotation @ direction
    )
    expected = rotation @ original
    scale = max(float(np.linalg.norm(expected, ord="fro")), 128.0 * _EPS * material.kappa)
    floor = 256.0 * _EPS * max(material.mu, material.kappa)
    np.testing.assert_allclose(rotated, expected, rtol=8.0e-12, atol=floor + 8.0e-12 * scale)


@pytest.mark.parametrize("material,deformation,direction", _FD_CASES[:4])
def test_tangent_has_major_hessian_symmetry(
    material: ExperimentalHenckyElastic,
    deformation: np.ndarray,
    direction: np.ndarray,
) -> None:
    first = _normalized(direction)
    second = _normalized(np.array(((0.0, 0.2, -0.1), (-0.3, 0.0, 0.15), (0.1, -0.2, 0.0))))
    first_action = hencky_directional_tangent_3d(material, deformation, first)
    second_action = hencky_directional_tangent_3d(material, deformation, second)
    left = float(np.sum(first * second_action))
    right = float(np.sum(second * first_action))
    scale = max(abs(left), abs(right), 128.0 * _EPS * max(material.mu, material.kappa))
    assert abs(left - right) <= 1.0e-11 * scale + 512.0 * _EPS * max(material.mu, material.kappa)


@pytest.mark.parametrize(
    "deformation",
    (
        np.diag((1.1, 1.1, 1.1)),
        np.diag((1.1, 1.1, 0.9)),
        np.diag((1.1, 1.1 * (1.0 + 1.0e-12), 0.9)),
    ),
    ids=("all-repeated", "pair-repeated", "near-repeat"),
)
def test_repeated_and_nearly_repeated_spectral_nodes_remain_finite(
    deformation: np.ndarray,
) -> None:
    direction = np.array(((0.2, -0.1, 0.0), (0.15, -0.05, 0.2), (0.0, -0.1, 0.1)))
    action = hencky_directional_tangent_3d(BASE, deformation, direction)
    assert action.shape == (3, 3)
    assert np.all(np.isfinite(action))


@pytest.mark.parametrize(
    "deformation",
    (
        np.zeros((3, 3)),
        np.diag((-1.0, 1.0, 1.0)),
        np.diag((1.0, 1.0, 1.0e-9)),
    ),
    ids=("singular", "inverted", "spectrally-unresolved"),
)
def test_inadmissible_base_deformation_is_rejected(deformation: np.ndarray) -> None:
    with pytest.raises(ValueError):
        hencky_directional_tangent_3d(BASE, deformation, IDENTITY)


@pytest.mark.parametrize(
    "direction",
    (np.full((3, 3), np.nan), np.full((2, 2), 1.0), np.full((3, 3), np.inf)),
    ids=("nan", "wrong-shape", "infinite"),
)
def test_invalid_tangent_direction_is_rejected(direction: np.ndarray) -> None:
    with pytest.raises(ValueError):
        hencky_directional_tangent_3d(BASE, IDENTITY, direction)


def test_material_response_still_does_not_claim_a_verified_tangent() -> None:
    assert BASE.evaluate(np.diag((1.1, 0.95, 1.02))).tangent_status == "NOT_IMPLEMENTED"


def test_directional_action_is_read_only_and_does_not_change_response() -> None:
    deformation = np.diag((1.14, 0.93, 1.04))
    direction = np.array(((0.1, 0.2, 0.0), (-0.1, 0.05, 0.1), (0.0, -0.2, 0.1)))
    before = BASE.evaluate(deformation)
    action = hencky_directional_tangent_3d(BASE, deformation, direction)
    after = BASE.evaluate(deformation)
    assert not action.flags.writeable
    np.testing.assert_array_equal(after.first_piola_kirchhoff_stress, before.first_piola_kirchhoff_stress)
    assert after.tangent_status == "NOT_IMPLEMENTED"


@pytest.mark.parametrize("material,deformation,direction", _FD_CASES[:3])
def test_directional_energy_hessian_matches_tangent_action(
    material: ExperimentalHenckyElastic,
    deformation: np.ndarray,
    direction: np.ndarray,
) -> None:
    delta = _normalized(direction)
    action = hencky_directional_tangent_3d(material, deformation, delta)
    tangent_energy = float(np.sum(delta * action))
    step = 2.0e-4
    plus = material.evaluate(deformation + step * delta).strain_energy_density
    center = material.evaluate(deformation).strain_energy_density
    minus = material.evaluate(deformation - step * delta).strain_energy_density
    second_difference = (plus - 2.0 * center + minus) / (step * step)
    scale = max(abs(tangent_energy), 128.0 * _EPS * max(material.mu, material.kappa))
    error = abs(second_difference - tangent_energy)
    print(
        f"HENCKY_ENERGY_HESSIAN h={step:.9e} tangent_Pa={tangent_energy:.12e} "
        f"difference_Pa={second_difference:.12e} abs_error_Pa={error:.9e} "
        f"normalized_error={error / scale:.9e}"
    )
    assert error <= 2.0e-5 * scale + 1024.0 * _EPS * max(material.mu, material.kappa)
