import numpy as np
import pytest

from research.j8_hex8.diagnostics import (
    backward_error_inf,
    energy_diagnostics,
    method_checkpoint_snapshot,
    partitioned_residuals,
)
from research.j8_hex8.recovery import recompute_one_method


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


def test_method_checkpoint_retains_previous_records_across_start_and_failure():
    initial = {"methods": {}, "case": "frozen"}
    first = {"status": "COMPLETED", "metric": 1.0}
    start_next = method_checkpoint_snapshot(initial, {"first": first}, "METHOD_SECOND_STARTED")

    assert start_next["methods"] == {"first": first}

    second_failure = {"status": "FAILED", "error_type": "RuntimeError"}
    after_failure = method_checkpoint_snapshot(
        initial,
        {"first": first, "second": second_failure},
        "METHOD_SECOND_FAILED",
    )

    assert after_failure["methods"] == {"first": first, "second": second_failure}


def test_recovered_method_metrics_use_saved_displacement_without_solving():
    stiffness = np.diag([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    fixed = np.array([True, True, True, False, False, False])
    displacement = np.array([0.0, 0.0, 0.0, 0.1, 0.2, 0.3])
    force = stiffness @ displacement
    coordinates = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])

    metrics = recompute_one_method(
        stiffness,
        force,
        fixed,
        coordinates,
        displacement,
        displacement,
        1.0,
    )

    assert metrics["free_residual_norm_n"] == pytest.approx(0.0)
    assert metrics["backward_error"]["backward_error_inf"] == pytest.approx(0.0)
    assert metrics["energy"]["energy_delta_j"] == pytest.approx(0.0)
    assert metrics["relative_displacement_change_from_archived"] == pytest.approx(0.0)
