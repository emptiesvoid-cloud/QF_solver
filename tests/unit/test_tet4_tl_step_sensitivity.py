"""Tests for total-Lagrangian load-step sensitivity evaluation."""

from __future__ import annotations

import pytest

from solveur.verification.tet4_total_lagrangian_steps import evaluate_step_sensitivity


def test_step_sensitivity_accepts_identical_converged_equilibria():
    rows = [
        {"increments": 3, "status": "NON_CONVERGED"},
        {"increments": 6, "status": "CONVERGED", "tip_displacement_z": -0.4},
        {"increments": 10, "status": "CONVERGED", "tip_displacement_z": -0.4},
        {"increments": 12, "status": "CONVERGED", "tip_displacement_z": -0.4},
        {"increments": 24, "status": "CONVERGED", "tip_displacement_z": -0.4},
    ]

    result = evaluate_step_sensitivity(rows)

    assert result["status"] == "PASS_STEP_SENSITIVITY"
    assert result["minimum_load_increments"] == 6
    assert result["default_load_increments"] == 10
    assert result["checks"][0]["value"] == 0.0


def test_step_sensitivity_rejects_missing_required_level():
    rows = [{"increments": 24, "status": "CONVERGED", "tip_displacement_z": -0.4}]

    assert evaluate_step_sensitivity(rows)["status"] == "FAIL"


def test_step_sensitivity_requires_a_converged_result():
    with pytest.raises(ValueError, match="at least one"):
        evaluate_step_sensitivity([{"increments": 3, "status": "NON_CONVERGED"}])
