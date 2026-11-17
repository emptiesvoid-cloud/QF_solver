from __future__ import annotations

import pytest

from research.j16.residual_guard_analysis import _guard_row


def test_j16_guard_row_separates_computed_residual_and_roundoff_bound() -> None:
    record = {
        "frequency_hz": 2.375,
        "frequency_role": "dense_grid",
        "qf_route_status": "QF_GUARD_REJECTED",
        "qf_route_details": {
            "diagnostics": {
                "residual_norm": 2.0,
                "relative_residual": 2.0e-10,
                "matvec_roundoff_bound": 2.0e3,
                "norm_relative_roundoff_factor": 1.0e-12,
                "relative_residual_upper_bound": 2.002e-7,
                "residual_failure_tolerance": 1.0e-7,
            }
        },
        "diagnostic_reduced_relative_residual_l2": 1.0e-10,
        "diagnostic_reduced_backward_error_inf": 1.0e-16,
        "diagnostic_center_uz_amplitude_mm": 40.0,
        "condition_number_2": 2.0e6,
        "checkpoint_stage": "POSTPROCESSED",
    }

    row = _guard_row(record)

    assert row["qf_route_status"] == "QF_GUARD_REJECTED"
    assert row["qf_relative_residual_l2"] == 2.0e-10
    assert row["estimated_reference_norm_from_qf_residual"] == 1.0e10
    assert row["approx_relative_matvec_roundoff_contribution"] == pytest.approx(2.0e-7)
    assert row["upper_bound_to_relative_residual_ratio"] == pytest.approx(1001.0)
    assert row["spsolve_backward_error_eta_inf"] == 1.0e-16
    assert row["condition_number_2_if_sampled"] == 2.0e6


def test_j16_guard_row_names_missing_guard_diagnostics() -> None:
    with pytest.raises(ValueError, match="missing QF guard diagnostics"):
        _guard_row({"qf_route_details": {"diagnostics": {}}})
