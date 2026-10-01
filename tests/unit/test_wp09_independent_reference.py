"""Tests for the source-independent WP09 NumPy reference."""

from __future__ import annotations

import inspect

import numpy as np

from solveur.verification import wp09_independent_reference as reference


def test_reference_module_has_no_production_solver_imports() -> None:
    source = inspect.getsource(reference)
    assert "solveur.elements" not in source
    assert "solveur.materials" not in source
    assert "solveur.core" not in source


def test_rigid_rotation_has_zero_corotational_strain_and_stress() -> None:
    angle = np.deg2rad(50.0)
    rotation = np.asarray(
        [
            [np.cos(angle), -np.sin(angle), 0.0],
            [np.sin(angle), np.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    history = reference.evaluate_corotational_history(
        [rotation],
        young=1_000.0,
        poisson=0.3,
        yield_stress=2.0,
        hardening_modulus=20.0,
    )
    row = history[0]
    np.testing.assert_allclose(row["local_strain"], np.zeros(6), atol=1.0e-12)
    np.testing.assert_allclose(row["local_stress"], np.zeros(6), atol=1.0e-12)
    np.testing.assert_allclose(row["cauchy_stress"], np.zeros((3, 3)), atol=1.0e-12)
    assert row["equivalent_plastic_strain"] == 0.0


def test_radial_return_reaches_hardening_surface_and_preserves_history() -> None:
    state = reference.initial_state()
    first_stress, first_state = reference.integrate_j2(
        [0.02, -0.01, 0.0, 0.0, 0.0, 0.0],
        state,
        young=1_000.0,
        poisson=0.3,
        yield_stress=2.0,
        hardening_modulus=20.0,
    )
    assert np.all(np.isfinite(first_stress))
    assert first_state["equivalent_plastic_strain"] > 0.0
    assert abs(float(first_state["yield_function"])) < 1.0e-12
    assert state["equivalent_plastic_strain"] == 0.0

    second_stress, second_state = reference.integrate_j2(
        [0.03, -0.015, 0.0, 0.0, 0.0, 0.0],
        first_state,
        young=1_000.0,
        poisson=0.3,
        yield_stress=2.0,
        hardening_modulus=20.0,
    )
    assert np.all(np.isfinite(second_stress))
    assert second_state["equivalent_plastic_strain"] > first_state["equivalent_plastic_strain"]
    assert abs(float(second_state["yield_function"])) < 1.0e-12


def test_rotation_transport_preserves_tensor_invariants() -> None:
    state = reference.initial_state()
    state["stress"] = np.asarray([3.0, -1.0, 0.5, 0.25, -0.1, 0.4])
    state["plastic_strain"] = np.asarray([0.01, -0.003, 0.0, 0.002, 0.0, -0.001])
    old_rotation = np.eye(3)
    angle = np.deg2rad(35.0)
    new_rotation = np.asarray(
        [
            [np.cos(angle), 0.0, np.sin(angle)],
            [0.0, 1.0, 0.0],
            [-np.sin(angle), 0.0, np.cos(angle)],
        ]
    )
    state["corotation"] = old_rotation
    transported = reference.transport_state(state, new_rotation)
    assert transported is not None
    original_stress = reference.stress_tensor(state["stress"])
    moved_stress = reference.stress_tensor(transported["stress"])
    np.testing.assert_allclose(np.trace(original_stress), np.trace(moved_stress), atol=1.0e-12)
    np.testing.assert_allclose(
        np.linalg.eigvalsh(original_stress),
        np.linalg.eigvalsh(moved_stress),
        atol=1.0e-12,
    )

