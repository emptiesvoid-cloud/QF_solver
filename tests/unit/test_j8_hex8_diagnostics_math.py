import numpy as np
import pytest

from research.j8_hex8.diagnostics import (
    backward_error_inf,
    energy_diagnostics,
    partitioned_residuals,
)


def test_partitioned_residual_and_reaction_include_nonzero_prescribed_values():
    stiffness = np.array([[4.0, 1.0], [1.0, 3.0]])
    force = np.array([5.0, 0.0])
    displacement = np.array([0.75, 2.0])
    fixed = np.array([False, True])

    result = partitioned_residuals(stiffness, force, displacement, fixed)

    assert result["effective_free_rhs"][0] == pytest.approx(3.0)
    assert result["free_matrix"][0, 0] == 4.0
    assert result["raw_residual"].tolist() == pytest.approx([0.0, 6.75])
    assert result["reactions"].tolist() == pytest.approx([0.0, 6.75])
    assert result["equilibrium_residual"].tolist() == pytest.approx([0.0, 0.0])


def test_energy_indicator_is_unit_covariant_and_legacy_floor_is_not():
    stiffness = np.diag([2.0, 3.0])
    displacement = np.array([0.1, 0.0])
    force = np.array([1.0, 0.0])

    energy = energy_diagnostics(stiffness, force, displacement, stiffness @ displacement)

    assert energy["strain_energy_j"] == pytest.approx(0.01)
    assert energy["external_work_j"] == pytest.approx(0.05)
    assert energy["legacy_metric_si"] == pytest.approx(0.04)
    assert energy["legacy_metric_nmm"] == pytest.approx(0.8)
    assert energy["prospective_unit_covariant_indicator"] == pytest.approx(0.8)


def test_backward_error_uses_dimensionless_componentwise_scale():
    matrix = np.array([[4.0, 1.0], [1.0, 3.0]])
    solution = np.array([1.0, 2.0])
    rhs = matrix @ solution

    result = backward_error_inf(matrix, solution, rhs)

    assert result["backward_error_inf"] == 0.0
    assert result["within_backward_error_indicator"] is True
    assert result["indicator_limit"] > 0.0
