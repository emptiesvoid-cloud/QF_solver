from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import numpy as np
import pytest

from solveur.core.assembly.nonlinear import (
    assemble_internal_tangent,
    build_nonlinear_assembly_plan,
    validate_corotational_formulation,
)
from solveur.core.errors import InputValidationError
from solveur.core.nonlinear.material_state import StateTransaction, state_digest
from solveur.elements.solid.corotational_j2 import (
    CORRECTED_COROTATIONAL_J2,
    LEGACY_COROTATIONAL_J2,
    CorotationalJ2Hex8Element,
    CorotationalJ2Hex20Element,
    CorotationalJ2Tet4Element,
    CorotationalJ2Tet10Element,
    _corrected_first_piola_from_biot_stress,
    _corrected_material_identity,
    _corrected_polar_kinematics,
    _corrected_stress_measures,
    _evaluate_corrected_material_state,
    _polar_stretch_directional_derivative,
)
from solveur.materials.solid import VonMisesElastoplasticMaterial
from solveur.verification.robustness_nonlinear_solids import _refinement_model


def _material() -> VonMisesElastoplasticMaterial:
    return VonMisesElastoplasticMaterial(
        E=2100.0,
        nu=0.3,
        yield_stress=2.5,
        hardening_modulus=18.0,
    )


def _dev(tensor: np.ndarray) -> np.ndarray:
    return tensor - np.trace(tensor) / 3.0 * np.eye(3)


def _independent_j2_return(
    strain: np.ndarray,
    plastic_strain: np.ndarray,
    alpha: float,
    material: VonMisesElastoplasticMaterial,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Tensor reference written independently of the production Voigt return."""

    elastic_trial = strain - plastic_strain
    lam = material.E * material.nu / ((1.0 + material.nu) * (1.0 - 2.0 * material.nu))
    mu = material.E / (2.0 * (1.0 + material.nu))
    trial = 2.0 * mu * _dev(elastic_trial) + lam * np.trace(elastic_trial) * np.eye(3)
    deviator = _dev(trial)
    q_trial = float(np.sqrt(1.5 * np.sum(deviator * deviator)))
    f_trial = q_trial - (material.yield_stress + material.hardening_modulus * alpha)
    if f_trial <= 0.0:
        return trial, plastic_strain.copy(), alpha, f_trial
    delta_gamma = f_trial / (3.0 * mu + material.hardening_modulus)
    flow = deviator / q_trial
    plastic_new = plastic_strain + 1.5 * delta_gamma * flow
    alpha_new = alpha + delta_gamma
    bulk = lam + 2.0 * mu / 3.0
    stress = bulk * np.trace(strain - plastic_strain) * np.eye(3) + (1.0 - 3.0 * mu * delta_gamma / q_trial) * deviator
    return stress, plastic_new, alpha_new, f_trial


def _independent_polar(deformation: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    left, singular_values, right_transpose = np.linalg.svd(deformation)
    rotation = left @ right_transpose
    stretch = right_transpose.T @ np.diag(singular_values) @ right_transpose
    return rotation, stretch, float(np.linalg.det(deformation))


def _independent_incremental_potential(
    deformation: np.ndarray,
    accepted_state: dict[str, object],
    material: VonMisesElastoplasticMaterial,
) -> float:
    _, stretch, _ = _independent_polar(deformation)
    strain = stretch - np.eye(3)
    plastic_old = _voigt_strain_tensor(np.asarray(accepted_state["plastic_strain"], dtype=float))
    alpha_old = float(accepted_state["equivalent_plastic_strain"])
    _, plastic_new, alpha_new, _ = _independent_j2_return(strain, plastic_old, alpha_old, material)
    elastic = strain - plastic_new
    lam = material.E * material.nu / ((1.0 + material.nu) * (1.0 - 2.0 * material.nu))
    mu = material.E / (2.0 * (1.0 + material.nu))
    elastic_energy = mu * np.sum(elastic * elastic) + 0.5 * lam * np.trace(elastic) ** 2
    hardening_change = 0.5 * material.hardening_modulus * (alpha_new**2 - alpha_old**2)
    plastic_dissipation = material.yield_stress * (alpha_new - alpha_old)
    return float(elastic_energy + hardening_change + plastic_dissipation)


def _independent_total_incremental_potential(
    element,
    coords: np.ndarray,
    displacement: np.ndarray,
    accepted_states: list[dict[str, object]],
    material: VonMisesElastoplasticMaterial,
) -> float:
    """Integrate an independently coded material potential over the fixed rule."""

    total = 0.0
    local = displacement.reshape(element.node_count, 3)
    for index, (weight, gradients) in enumerate(element._cached_reference_data(coords)):
        deformation = np.eye(3) + local.T @ gradients
        total += float(weight) * _independent_incremental_potential(deformation, accepted_states[index], material)
    return total


def _voigt_strain_tensor(values: np.ndarray) -> np.ndarray:
    ex, ey, ez, gxy, gyz, gxz = values
    return np.array(
        [[ex, 0.5 * gxy, 0.5 * gxz], [0.5 * gxy, ey, 0.5 * gyz], [0.5 * gxz, 0.5 * gyz, ez]],
        dtype=float,
    )


def _voigt_stress_tensor(values: np.ndarray) -> np.ndarray:
    sx, sy, sz, txy, tyz, txz = values
    return np.array([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]], dtype=float)


def _tet4_coordinates() -> np.ndarray:
    return np.asarray(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        dtype=float,
    )


def _tet10_coordinates() -> np.ndarray:
    return np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.5, 0.0, 0.0],
            [0.5, 0.5, 0.0],
            [0.0, 0.5, 0.0],
            [0.0, 0.0, 0.5],
            [0.5, 0.0, 0.5],
            [0.0, 0.5, 0.5],
        ],
        dtype=float,
    )


def _hex8_coordinates() -> np.ndarray:
    return np.asarray(
        [
            [-1.0, -1.0, -1.0],
            [1.0, -1.0, -1.0],
            [1.0, 1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [-1.0, -1.0, 1.0],
            [1.0, -1.0, 1.0],
            [1.0, 1.0, 1.0],
            [-1.0, 1.0, 1.0],
        ],
        dtype=float,
    )


def _hex20_coordinates() -> np.ndarray:
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
        ],
        dtype=float,
    )
    edge_pairs = (
        (0, 1),
        (0, 3),
        (0, 4),
        (1, 2),
        (1, 5),
        (2, 3),
        (2, 6),
        (3, 7),
        (4, 5),
        (4, 7),
        (5, 6),
        (6, 7),
    )
    return np.vstack([corners, [(corners[i] + corners[j]) / 2.0 for i, j in edge_pairs]])


def _affine_displacement(coords: np.ndarray, deformation: np.ndarray) -> np.ndarray:
    return ((deformation - np.eye(3)) @ coords.T).T.reshape(-1)


def _proper_rotation(axis: np.ndarray, angle: float) -> np.ndarray:
    unit = np.asarray(axis, dtype=float)
    unit /= np.linalg.norm(unit)
    cross = np.array([[0.0, -unit[2], unit[1]], [unit[2], 0.0, -unit[0]], [-unit[1], unit[0], 0.0]])
    return np.eye(3) + np.sin(angle) * cross + (1.0 - np.cos(angle)) * (cross @ cross)


def test_corrected_polar_kinematics_and_fail_closed_guards() -> None:
    angle = 0.37
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    stretch = np.array([[1.012, 0.003, 0.0], [0.003, 0.994, 0.001], [0.0, 0.001, 1.002]])
    deformation = rotation @ stretch
    observed_rotation, observed_stretch, determinant = _corrected_polar_kinematics(deformation, max_local_strain=0.05)
    np.testing.assert_allclose(observed_rotation @ observed_stretch, deformation, rtol=0.0, atol=1.0e-12)
    np.testing.assert_allclose(observed_stretch, observed_stretch.T, rtol=0.0, atol=1.0e-12)
    assert determinant > 1.0e-10
    with pytest.raises(ValueError, match="finite with shape"):
        _corrected_polar_kinematics(np.full((3, 3), np.nan), max_local_strain=0.05)
    with pytest.raises(ValueError, match="determinant"):
        _corrected_polar_kinematics(np.diag([-1.0, 1.0, 1.0]), max_local_strain=0.05)
    with pytest.raises(ValueError, match="small-strain bound"):
        _corrected_polar_kinematics(np.diag([1.08, 1.0, 1.0]), max_local_strain=0.05)


def test_corrected_state_matches_independent_tensor_j2_history() -> None:
    material = _material()
    element = CorotationalJ2Tet4Element(material, formulation_id=CORRECTED_COROTATIONAL_J2)
    accepted = element.corrected_initial_state()
    strain = np.array([[0.012, 0.003, 0.0], [0.003, -0.006, 0.001], [0.0, 0.001, -0.006]])
    observed_stress, observed_state, _ = _evaluate_corrected_material_state(material, strain, accepted)
    expected_stress, expected_plastic, expected_alpha, yield_trial = _independent_j2_return(
        strain, np.zeros((3, 3)), 0.0, material
    )
    assert yield_trial > 0.0
    np.testing.assert_allclose(observed_stress, expected_stress, rtol=1.0e-12, atol=1.0e-12)
    np.testing.assert_allclose(
        _voigt_strain_tensor(np.asarray(observed_state["plastic_strain"])),
        expected_plastic,
        rtol=1.0e-12,
        atol=1.0e-12,
    )
    assert observed_state["equivalent_plastic_strain"] == pytest.approx(expected_alpha, abs=1.0e-13)
    assert observed_state["plastic_dissipation"] == pytest.approx(material.yield_stress * expected_alpha, rel=1.0e-13)
    assert observed_state["hardening_energy"] == pytest.approx(
        0.5 * material.hardening_modulus * expected_alpha**2, rel=1.0e-13
    )
    assert observed_state["formulation_id"] == CORRECTED_COROTATIONAL_J2


def test_corrected_multistep_plastic_unload_and_noncoaxial_history_matches_reference() -> None:
    material = _material()
    element = CorotationalJ2Tet4Element(material, formulation_id=CORRECTED_COROTATIONAL_J2)
    accepted = element.corrected_initial_state()
    plastic_tensor = np.zeros((3, 3))
    alpha = 0.0
    histories = (
        np.diag([0.012, -0.006, -0.006]),
        np.diag([0.017, -0.0085, -0.0085]),
        np.diag([0.011, -0.0055, -0.0055]),
        np.array([[0.010, 0.002, 0.0], [0.002, -0.004, 0.001], [0.0, 0.001, -0.006]]),
        np.diag([-0.015, 0.0075, 0.0075]),
    )
    previous_dissipation = 0.0
    for strain in histories:
        observed_stress, updated, _ = _evaluate_corrected_material_state(material, strain, accepted)
        expected_stress, expected_plastic, expected_alpha, _ = _independent_j2_return(
            strain, plastic_tensor, alpha, material
        )
        np.testing.assert_allclose(observed_stress, expected_stress, rtol=1.0e-12, atol=1.0e-12)
        np.testing.assert_allclose(
            _voigt_strain_tensor(np.asarray(updated["plastic_strain"])),
            expected_plastic,
            rtol=1.0e-12,
            atol=1.0e-12,
        )
        assert updated["equivalent_plastic_strain"] == pytest.approx(expected_alpha, abs=1.0e-13)
        if updated["plastic_multiplier"] > 0.0:
            yield_scale = max(material.yield_stress, np.linalg.norm(observed_stress), 1.0)
            assert abs(float(updated["yield_function"])) / yield_scale <= 1.0e-10
        assert updated["plastic_dissipation"] >= previous_dissipation
        assert updated["hardening_energy"] == pytest.approx(
            0.5 * material.hardening_modulus * expected_alpha**2, rel=1.0e-13
        )
        plastic_tensor = expected_plastic
        alpha = expected_alpha
        previous_dissipation = float(updated["plastic_dissipation"])
        accepted = updated


def test_corrected_pure_spin_preserves_accepted_material_state() -> None:
    material = _material()
    element = CorotationalJ2Tet4Element(material, formulation_id=CORRECTED_COROTATIONAL_J2)
    coords = _tet4_coordinates()
    preload = np.array([[1.016, 0.003, 0.0], [0.0, 0.992, 0.0], [0.0, 0.0, 0.992]])
    force_1, state_1, points_1 = element.corrected_internal_force_state(coords, _affine_displacement(coords, preload))
    accepted = deepcopy(state_1)
    angle = 0.71
    q = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    force_2, state_2, points_2 = element.corrected_internal_force_state(
        coords, _affine_displacement(coords, q @ preload), state_1
    )
    np.testing.assert_allclose(state_2[0]["plastic_strain"], state_1[0]["plastic_strain"], rtol=0.0, atol=5.0e-12)
    assert state_2[0]["equivalent_plastic_strain"] == pytest.approx(
        state_1[0]["equivalent_plastic_strain"], abs=5.0e-13
    )
    np.testing.assert_allclose(points_2[0]["biot_stress"], points_1[0]["biot_stress"], rtol=5.0e-12, atol=1.0e-12)
    np.testing.assert_allclose(
        points_2[0]["first_piola_stress"], q @ np.asarray(points_1[0]["first_piola_stress"]), rtol=5.0e-11, atol=1.0e-11
    )
    np.testing.assert_allclose(
        points_2[0]["second_piola_stress"], points_1[0]["second_piola_stress"], rtol=5.0e-11, atol=1.0e-11
    )
    np.testing.assert_allclose(
        points_2[0]["cauchy_stress"], q @ np.asarray(points_1[0]["cauchy_stress"]) @ q.T, rtol=5.0e-11, atol=1.0e-11
    )
    assert np.all(np.isfinite(force_1)) and np.all(np.isfinite(force_2))
    assert accepted == state_1


def test_corrected_elastic_controls_and_rigid_rotation_have_no_plastic_update() -> None:
    material = VonMisesElastoplasticMaterial(
        E=2100.0,
        nu=0.3,
        yield_stress=1.0e6,
        hardening_modulus=18.0,
    )
    element = CorotationalJ2Tet4Element(material, formulation_id=CORRECTED_COROTATIONAL_J2)
    coords = _tet4_coordinates()
    angle = 0.42
    q = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    cases = [
        np.eye(3),
        q,
        np.diag([1.01, 0.995, 0.995]),
        np.diag([0.99, 1.005, 1.005]),
        np.array([[1.0, 0.008, 0.0], [0.008, 1.0, 0.0], [0.0, 0.0, 1.0]]),
        q @ np.diag([1.012, 0.994, 0.997]) @ q.T,
        q @ np.array([[1.01, 0.004, 0.0], [0.004, 0.995, 0.001], [0.0, 0.001, 0.998]]),
    ]
    for deformation in cases:
        _, states, points = element.corrected_internal_force_state(coords, _affine_displacement(coords, deformation))
        assert states[0]["equivalent_plastic_strain"] == 0.0
        assert np.linalg.norm(np.asarray(states[0]["plastic_strain"])) == 0.0
        cauchy = np.asarray(points[0]["cauchy_stress"])
        assert np.linalg.norm(cauchy - cauchy.T) / max(np.linalg.norm(cauchy), 1.0) <= 1.0e-10
    rigid_force, _, rigid_points = element.corrected_internal_force_state(coords, _affine_displacement(coords, q))
    np.testing.assert_allclose(rigid_force, 0.0, atol=1.0e-10)
    np.testing.assert_allclose(rigid_points[0]["biot_stress"], 0.0, atol=1.0e-12)


def test_corrected_noncoaxial_history_changes_legacy_force_without_rewriting_legacy() -> None:
    material = VonMisesElastoplasticMaterial(
        E=210.0e9,
        nu=0.3,
        yield_stress=250.0e6,
        hardening_modulus=1.0e9,
    )
    coords = _tet4_coordinates()
    a = 0.016
    first_f = np.diag([1.0 + a, 1.0 - a / 2.0, 1.0 - a / 2.0])
    angle = 0.42
    q = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    second_f = q @ np.diag([1.0 + 0.85 * a, 1.0 - 0.45 * a, 1.0 - 0.40 * a]) @ q.T

    legacy = CorotationalJ2Tet4Element(material)
    _, legacy_state, _ = legacy._force_and_states(
        coords, _affine_displacement(coords, first_f), [material.initial_state()]
    )
    legacy_force, _, legacy_points = legacy._force_and_states(
        coords, _affine_displacement(coords, second_f), legacy_state
    )

    corrected = CorotationalJ2Tet4Element(material, formulation_id=CORRECTED_COROTATIONAL_J2)
    _, corrected_state, _ = corrected.corrected_internal_force_state(coords, _affine_displacement(coords, first_f))
    corrected_force, _, corrected_points = corrected.corrected_internal_force_state(
        coords, _affine_displacement(coords, second_f), corrected_state
    )
    legacy_cauchy = np.asarray(legacy_points[0]["cauchy_stress"])
    corrected_cauchy = np.asarray(corrected_points[0]["cauchy_stress"])
    legacy_skew = np.linalg.norm(legacy_cauchy - legacy_cauchy.T) / max(np.linalg.norm(legacy_cauchy), 1.0)
    corrected_skew = np.linalg.norm(corrected_cauchy - corrected_cauchy.T) / max(np.linalg.norm(corrected_cauchy), 1.0)
    assert legacy_skew > 1.0e-5
    assert corrected_skew <= 1.0e-10
    expected_change = np.linalg.norm(corrected_force - legacy_force) / max(
        np.linalg.norm(corrected_force), np.linalg.norm(legacy_force), 1.0
    )
    assert expected_change > 1.0e-5
    # The legacy element still emits its original local tensor under the historical field.
    np.testing.assert_allclose(
        legacy_points[0]["second_piola_stress"],
        _voigt_stress_tensor(np.asarray(legacy_points[0]["local_stress"])),
    )


def test_corrected_superposed_rotation_covariance_and_origin_invariance() -> None:
    material = _material()
    element = CorotationalJ2Tet4Element(material, formulation_id=CORRECTED_COROTATIONAL_J2)
    coords = _tet4_coordinates()
    first = np.array([[1.013, 0.002, 0.0], [0.0, 0.994, 0.0], [0.0, 0.0, 0.993]])
    second = np.array([[1.011, 0.004, 0.0], [0.004, 0.994, 0.0], [0.0, 0.0, 0.995]])
    _, state_a, _ = element.corrected_internal_force_state(coords, _affine_displacement(coords, first))
    force_a, state_a, point_a = element.corrected_internal_force_state(
        coords, _affine_displacement(coords, second), state_a
    )
    q = _proper_rotation(np.array([0.3, 0.5, -0.2]), -0.52)
    _, state_b, _ = element.corrected_internal_force_state(coords, _affine_displacement(coords, q @ first))
    force_b, state_b, point_b = element.corrected_internal_force_state(
        coords, _affine_displacement(coords, q @ second), state_b
    )
    np.testing.assert_allclose(state_b[0]["plastic_strain"], state_a[0]["plastic_strain"], rtol=5.0e-11, atol=1.0e-12)
    assert state_b[0]["equivalent_plastic_strain"] == pytest.approx(
        state_a[0]["equivalent_plastic_strain"], rel=5.0e-11
    )
    np.testing.assert_allclose(
        point_b[0]["first_piola_stress"], q @ np.asarray(point_a[0]["first_piola_stress"]), rtol=5.0e-11, atol=1.0e-10
    )
    np.testing.assert_allclose(force_b.reshape(4, 3), (q @ force_a.reshape(4, 3).T).T, rtol=5.0e-11, atol=1.0e-10)

    shift = np.array([700.0, -400.0, 100.0])
    translated = coords + shift
    force_shifted, state_shifted, points_shifted = element.corrected_internal_force_state(
        translated, _affine_displacement(translated, second), state_a
    )
    np.testing.assert_allclose(force_shifted, force_a, rtol=1.0e-9, atol=1.0e-10)
    np.testing.assert_allclose(
        points_shifted[0]["first_piola_stress"], point_a[0]["first_piola_stress"], rtol=1.0e-9, atol=1.0e-10
    )
    assert state_shifted[0]["equivalent_plastic_strain"] == pytest.approx(
        state_a[0]["equivalent_plastic_strain"], rel=1.0e-9
    )


def test_polar_directional_derivative_matches_independent_sylvester_and_fd() -> None:
    angle = 0.27
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    # Repeated stretches exercise the stable lambda_i + lambda_j Sylvester denominator.
    stretch = np.diag([1.01, 1.01, 0.995])
    deformation = rotation @ stretch
    delta = np.array([[0.2, -0.3, 0.1], [0.4, 0.15, -0.2], [-0.1, 0.35, 0.05]])
    derivative = _polar_stretch_directional_derivative(rotation, stretch, delta)
    a = rotation.T @ delta
    omega = np.zeros((3, 3))
    for i in range(3):
        for j in range(i + 1, 3):
            omega[i, j] = (a[i, j] - a[j, i]) / (stretch[i, i] + stretch[j, j])
            omega[j, i] = -omega[i, j]
    independent = 0.5 * ((a - omega @ stretch) + (a - omega @ stretch).T)
    np.testing.assert_allclose(derivative, independent, rtol=1.0e-12, atol=1.0e-12)
    errors = []
    for step in (1.0e-4, 3.0e-5, 1.0e-5, 3.0e-6):
        _, plus, _ = _independent_polar(deformation + step * delta)
        _, minus, _ = _independent_polar(deformation - step * delta)
        fd = (plus - minus) / (2.0 * step)
        errors.append(np.linalg.norm(fd - derivative) / max(np.linalg.norm(derivative), 1.0))
    assert min(errors) <= 2.0e-7


def test_polar_adjoint_satisfies_virtual_work_and_angular_identity() -> None:
    rng = np.random.default_rng(71208)
    left = rng.normal(size=(3, 3))
    rotation, _ = np.linalg.qr(left)
    if np.linalg.det(rotation) < 0.0:
        rotation[:, 0] *= -1.0
    basis, _ = np.linalg.qr(rng.normal(size=(3, 3)))
    stretch = basis @ np.diag([0.985, 1.008, 1.021]) @ basis.T
    local = rng.normal(size=(3, 3))
    stress = 0.5 * (local + local.T) * 4.0
    first_piola, nominal_material = _corrected_first_piola_from_biot_stress(rotation, stretch, stress)
    delta = rng.normal(size=(3, 3))
    delta_stretch = _polar_stretch_directional_derivative(rotation, stretch, delta)
    lhs = float(np.sum(first_piola * delta))
    rhs = float(np.sum(stress * delta_stretch))
    work_scale = max(
        np.linalg.norm(first_piola) * np.linalg.norm(delta),
        np.linalg.norm(stress) * np.linalg.norm(delta_stretch),
        max(np.linalg.norm(delta), np.linalg.norm(delta_stretch)),
        1.0e-30,
    )
    assert abs(lhs - rhs) / work_scale <= 5.0e-12
    angular = nominal_material @ stretch
    assert np.linalg.norm(angular - angular.T) / max(np.linalg.norm(angular), 1.0) <= 1.0e-12


def test_corrected_pk2_and_cauchy_match_independent_transforms_without_symmetrizing() -> None:
    angle = 0.31
    rotation = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
    stretch = np.array([[1.014, 0.003, 0.001], [0.003, 0.991, -0.002], [0.001, -0.002, 1.002]])
    deformation = rotation @ stretch
    rotation_p, stretch_p, determinant = _corrected_polar_kinematics(deformation, max_local_strain=0.05)
    stress = np.array([[8.0, 1.5, -0.7], [1.5, -3.0, 0.4], [-0.7, 0.4, -5.0]])
    first, nominal = _corrected_first_piola_from_biot_stress(rotation_p, stretch_p, stress)
    second, cauchy = _corrected_stress_measures(deformation, first, determinant)
    independent_second = np.linalg.solve(deformation, first)
    independent_cauchy = first @ deformation.T / determinant
    np.testing.assert_allclose(second, independent_second, rtol=1.0e-12, atol=1.0e-12)
    np.testing.assert_allclose(cauchy, independent_cauchy, rtol=1.0e-12, atol=1.0e-12)
    assert np.linalg.norm(second - second.T) / max(np.linalg.norm(second), 1.0) <= 1.0e-10
    assert np.linalg.norm(cauchy - cauchy.T) / max(np.linalg.norm(cauchy), 1.0) <= 1.0e-10


@pytest.mark.parametrize("history_case", ["elastic", "active_plastic", "noncoaxial_plastic"])
def test_corrected_element_force_matches_independent_incremental_potential_gradient(
    history_case: str,
) -> None:
    material = (
        VonMisesElastoplasticMaterial(E=2100.0, nu=0.3, yield_stress=100.0, hardening_modulus=18.0)
        if history_case == "elastic"
        else _material()
    )
    element = CorotationalJ2Tet4Element(material, formulation_id=CORRECTED_COROTATIONAL_J2)
    coords = _tet4_coordinates()
    volume = 1.0 / 6.0
    deformation = np.array([[1.012, 0.006, 0.0], [0.006, 0.994, 0.0], [0.0, 0.0, 0.998]])
    displacement = _affine_displacement(coords, deformation)
    accepted = element.corrected_initial_state()
    accepted_for_reference: list[dict[str, object]] = [accepted]
    if history_case == "noncoaxial_plastic":
        prior_f = np.diag([1.016, 0.992, 0.992])
        _, prior_u, _ = _independent_polar(prior_f)
        prior_strain = prior_u - np.eye(3)
        prior_stress, prior_plastic, prior_alpha, _ = _independent_j2_return(
            prior_strain, np.zeros((3, 3)), 0.0, material
        )
        accepted = {
            **accepted,
            "plastic_strain": _tensor_to_strain_voigt(prior_plastic).tolist(),
            "equivalent_plastic_strain": prior_alpha,
            "plastic_dissipation": material.yield_stress * prior_alpha,
            "hardening_energy": 0.5 * material.hardening_modulus * prior_alpha**2,
            "strain": _tensor_to_strain_voigt(prior_strain).tolist(),
            "stress": _tensor_to_stress_voigt(prior_stress).tolist(),
        }
        angle = 0.39
        q = np.array([[np.cos(angle), -np.sin(angle), 0.0], [np.sin(angle), np.cos(angle), 0.0], [0.0, 0.0, 1.0]])
        deformation = q @ np.diag([1.018, 0.991, 0.991]) @ q.T
        displacement = _affine_displacement(coords, deformation)
        accepted_for_reference = [accepted]
    force, states, points = element.corrected_internal_force_state(coords, displacement, [accepted])
    if history_case == "active_plastic":
        assert states[0]["plastic_multiplier"] > 0.0
    elif history_case == "elastic":
        assert states[0]["plastic_multiplier"] == 0.0
    else:
        assert accepted["equivalent_plastic_strain"] > 0.0
        assert states[0]["plastic_multiplier"] > 0.0
    assert points[0]["public_result_availability"]["status"] == "UNAVAILABLE"
    char_stress = max(
        np.linalg.norm(np.asarray(points[0]["biot_stress"])),
        material.E * np.linalg.norm(np.asarray(points[0]["biot_strain"])),
        material.yield_stress,
        1.0,
    )
    force_char = char_stress * volume ** (2.0 / 3.0)

    def potential(nodal: np.ndarray) -> float:
        return _independent_total_incremental_potential(element, coords, nodal, accepted_for_reference, material)

    errors = []
    gradients_by_step = []
    characteristic_length = volume ** (1.0 / 3.0)
    for relative_step in (1.0e-4, 3.0e-5, 1.0e-5, 3.0e-6):
        step = relative_step * characteristic_length
        reference = np.empty(12)
        for dof in range(12):
            plus = displacement.copy()
            minus = displacement.copy()
            plus[dof] += step
            minus[dof] -= step
            reference[dof] = (potential(plus) - potential(minus)) / (2.0 * step)
        scale = max(np.linalg.norm(reference), np.linalg.norm(force), force_char)
        errors.append(np.linalg.norm(reference - force) / scale)
        gradients_by_step.append(reference)
    assert min(errors) <= 2.0e-6
    plateau = [
        np.linalg.norm(gradients_by_step[i] - gradients_by_step[i + 1]) / max(np.linalg.norm(force), force_char)
        for i in range(len(gradients_by_step) - 1)
    ]
    assert min(plateau) <= 2.0e-6
    current = coords + displacement.reshape(4, 3)
    centered = current - np.mean(current, axis=0)
    torque = np.sum(np.cross(centered, force.reshape(4, 3)), axis=0)
    torque_scale = max(char_stress * volume, 1.0e-30)
    assert np.linalg.norm(torque) / torque_scale <= 1.0e-9


def _tensor_to_strain_voigt(tensor: np.ndarray) -> np.ndarray:
    return np.asarray(
        [tensor[0, 0], tensor[1, 1], tensor[2, 2], 2.0 * tensor[0, 1], 2.0 * tensor[1, 2], 2.0 * tensor[0, 2]],
        dtype=float,
    )


def _tensor_to_stress_voigt(tensor: np.ndarray) -> np.ndarray:
    return np.asarray(
        [tensor[0, 0], tensor[1, 1], tensor[2, 2], tensor[0, 1], tensor[1, 2], tensor[0, 2]],
        dtype=float,
    )


@pytest.mark.parametrize(
    "element_type,coordinates",
    [
        (CorotationalJ2Tet4Element, _tet4_coordinates),
        (CorotationalJ2Tet10Element, _tet10_coordinates),
        (CorotationalJ2Hex8Element, _hex8_coordinates),
        (CorotationalJ2Hex20Element, _hex20_coordinates),
    ],
)
def test_corrected_force_kernel_supported_element_families(element_type, coordinates) -> None:
    material = _material()
    element = element_type(material, formulation_id=CORRECTED_COROTATIONAL_J2)
    coords = coordinates()
    deformation = np.array([[1.008, 0.002, 0.0], [0.0, 0.995, 0.001], [0.0, 0.0, 0.997]])
    force, states, points = element.corrected_internal_force_state(coords, _affine_displacement(coords, deformation))
    expected_force = np.zeros_like(force)
    for index, (weight, gradients) in enumerate(element._cached_reference_data(coords)):
        local_f = np.eye(3) + _affine_displacement(coords, deformation).reshape(element.node_count, 3).T @ gradients
        _, local_u, _ = _independent_polar(local_f)
        local_stress, _, _, _ = _independent_j2_return(local_u - np.eye(3), np.zeros((3, 3)), 0.0, material)
        left, singular_values, right_transpose = np.linalg.svd(local_f)
        local_r = left @ right_transpose
        eigenvalues, basis = np.linalg.eigh(local_u)
        stress_basis = basis.T @ local_stress @ basis
        pbar_basis = np.empty((3, 3))
        for row in range(3):
            for column in range(3):
                pbar_basis[row, column] = (
                    stress_basis[row, column]
                    if row == column
                    else 2.0 * eigenvalues[row] * stress_basis[row, column] / (eigenvalues[row] + eigenvalues[column])
                )
        p = local_r @ basis @ pbar_basis @ basis.T
        expected_force += float(weight) * np.einsum("iJ,aJ->ai", p, gradients).reshape(-1)
    force_scale = max(np.linalg.norm(expected_force), np.linalg.norm(force), 1.0)
    assert np.linalg.norm(force - expected_force) / force_scale <= 1.0e-10
    reference_data = element._cached_reference_data(coords)
    accepted_states = [element.corrected_initial_state() for _ in reference_data]
    direction = np.random.default_rng(81500 + len(coords)).normal(size=force.shape)
    direction /= np.linalg.norm(direction)
    total_volume = sum(float(weight) for weight, _ in reference_data)
    characteristic_length = total_volume ** (1.0 / 3.0)

    def potential_at(values: np.ndarray) -> float:
        return _independent_total_incremental_potential(element, coords, values, accepted_states, material)

    directional_errors = []
    directional_references = []
    for relative_step in (1.0e-4, 3.0e-5, 1.0e-5, 3.0e-6):
        step = relative_step * characteristic_length
        reference = (
            potential_at(_affine_displacement(coords, deformation) + step * direction)
            - potential_at(_affine_displacement(coords, deformation) - step * direction)
        ) / (2.0 * step)
        observed = float(force @ direction)
        sigma_scale = max(
            max(float(np.linalg.norm(point["biot_stress"])) for point in points),
            material.E * max(float(np.linalg.norm(point["biot_strain"])) for point in points),
            material.yield_stress,
            1.0,
        )
        force_char = sigma_scale * total_volume ** (2.0 / 3.0)
        directional_errors.append(abs(observed - reference) / max(abs(observed), abs(reference), force_char))
        directional_references.append(reference)
    assert min(directional_errors) <= 2.0e-6
    plateau_errors = [
        abs(directional_references[index] - directional_references[index + 1])
        / max(abs(float(force @ direction)), force_char)
        for index in range(len(directional_references) - 1)
    ]
    assert min(plateau_errors) <= 2.0e-6
    current = coords + _affine_displacement(coords, deformation).reshape(element.node_count, 3)
    centered = current - np.mean(current, axis=0)
    torque = np.sum(np.cross(centered, force.reshape(element.node_count, 3)), axis=0)
    assert np.linalg.norm(torque) / max(sigma_scale * total_volume, 1.0e-30) <= 1.0e-9
    assert force.shape == (3 * len(coords),)
    assert np.all(np.isfinite(force))
    assert len(states) == len(points) == element.integration_point_count
    assert all(state["formulation_id"] == CORRECTED_COROTATIONAL_J2 for state in states)
    for point in points:
        sigma = np.asarray(point["cauchy_stress"])
        pk2 = np.asarray(point["second_piola_stress"])
        assert np.linalg.norm(sigma - sigma.T) / max(np.linalg.norm(sigma), 1.0) <= 1.0e-10
        assert np.linalg.norm(pk2 - pk2.T) / max(np.linalg.norm(pk2), 1.0) <= 1.0e-10


def test_corrected_state_is_versioned_detached_and_transaction_safe() -> None:
    material = _material()
    element = CorotationalJ2Tet4Element(material, formulation_id=CORRECTED_COROTATIONAL_J2)
    coords = _tet4_coordinates()
    initial = element.corrected_initial_state()
    transaction = StateTransaction(initial)
    trial = transaction.begin_trial()
    before = transaction.committed_digest
    deformation = np.diag([1.015, 0.992, 0.993])
    _, states, _ = element.corrected_internal_force_state(coords, _affine_displacement(coords, deformation), [trial])
    assert transaction.committed_digest == before
    assert state_digest(transaction.committed) == before
    transaction.rollback()
    assert transaction.committed_digest == before
    transaction.begin_trial()
    accepted_after_evaluation = element.corrected_internal_force_state(
        coords,
        _affine_displacement(coords, np.diag([1.015, 0.992, 0.993])),
        [transaction.trial],
    )[1][0]
    transaction.trial = accepted_after_evaluation
    transaction.commit()
    assert transaction.committed["equivalent_plastic_strain"] > 0.0
    with pytest.raises(ValueError, match="refuses legacy or unidentified"):
        element.corrected_internal_force_state(coords, np.zeros(12), [material.initial_state()])
    other_material = VonMisesElastoplasticMaterial(E=2100.0, nu=0.3, yield_stress=3.0, hardening_modulus=18.0)
    other_element = CorotationalJ2Tet4Element(other_material, formulation_id=CORRECTED_COROTATIONAL_J2)
    with pytest.raises(ValueError, match="material identity"):
        other_element.corrected_internal_force_state(coords, np.zeros(12), [initial])
    malformed = deepcopy(initial)
    malformed["plastic_dissipation"] = float("nan")
    with pytest.raises(ValueError, match="finite and non-negative"):
        element.corrected_internal_force_state(coords, np.zeros(12), [malformed])
    assert states[0]["formulation_id"] == CORRECTED_COROTATIONAL_J2


def test_corrected_newton_entry_is_rejected_until_r3_and_legacy_default_is_unchanged() -> None:
    material = _material()
    coords = _tet4_coordinates()
    legacy = CorotationalJ2Tet4Element(material)
    corrected = CorotationalJ2Tet4Element(material, formulation_id=CORRECTED_COROTATIONAL_J2)
    assert legacy.formulation_id == LEGACY_COROTATIONAL_J2
    assert _corrected_material_identity(material) == corrected.corrected_initial_state()["material_identity"]
    with pytest.raises(RuntimeError, match="no production-compatible tangent"):
        corrected.internal_force_tangent_state(coords, np.zeros(12), [corrected.corrected_initial_state()])
    with pytest.raises(RuntimeError, match="post-processing"):
        corrected.integration_point_results(coords, np.zeros(12), [corrected.corrected_initial_state()])
    legacy_force, legacy_tangent, _ = legacy.internal_force_tangent_state(
        coords, np.zeros(12), [material.initial_state()]
    )
    np.testing.assert_allclose(legacy_force, np.zeros(12), atol=1.0e-12)
    assert np.all(np.isfinite(legacy_tangent))


def test_global_solver_rejects_corrected_route_without_a_validated_tangent() -> None:
    model = _refinement_model("TET4", 1)
    parameters = {
        **model.analysis.parameters,
        "kinematics": "corotational_j2",
        "corotational_formulation": CORRECTED_COROTATIONAL_J2,
    }
    model = replace(model, analysis=replace(model.analysis, parameters=parameters))
    with pytest.raises(InputValidationError, match="disabled until WP08-R3"):
        validate_corotational_formulation(model)
    dofs = model.dof_manager()
    with pytest.raises(InputValidationError, match="disabled until WP08-R3"):
        build_nonlinear_assembly_plan(model, dofs)
    with pytest.raises(InputValidationError, match="disabled until WP08-R3"):
        assemble_internal_tangent(model, dofs, np.zeros(dofs.ndof))
    legacy_model = replace(
        model,
        analysis=replace(
            model.analysis,
            parameters={key: value for key, value in parameters.items() if key != "corotational_formulation"},
        ),
    )
    assert validate_corotational_formulation(legacy_model) == LEGACY_COROTATIONAL_J2
    with pytest.raises(ValueError, match="strain cap"):
        CorotationalJ2Tet4Element(
            _material(),
            formulation_id=CORRECTED_COROTATIONAL_J2,
            max_corotational_strain=0.06,
        )
