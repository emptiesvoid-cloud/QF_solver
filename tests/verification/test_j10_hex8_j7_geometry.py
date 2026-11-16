"""J10 controlled interior distortion replay on the archived J7 HEX8-SRI case."""

from __future__ import annotations

import math

from research.j10_hex8.hex8_j7_diagnostic import ALPHA_LEVELS, run_diagnostic


def test_j10_hex8_j7_domain_preserving_distortion() -> None:
    result = run_diagnostic()
    assert result["execution_status"] == "COMPLETED_EXPLORATORY"
    assert result["contract_id"] == "J10-HEX8-J7-DOMAIN-PRESERVING-DISTORTION-CORRECTIVE-003"
    assert result["attempt_id"] == "J10-HEX8-J7-DISTORTION-ATTEMPT-003"
    assert result["development_attempt_number"] == 3
    assert result["historical_j7_status"] == "FAIL"
    assert [row["alpha"] for row in result["levels"]] == list(ALPHA_LEVELS)
    assert all(row["exterior_node_coordinates_unchanged"] for row in result["levels"])
    assert all(row["minimum_gauss_jacobian_m3"] > 0.0 for row in result["levels"])
    assert all(math.isfinite(row["condition_number_2_estimate"]) for row in result["levels"])
    assert all(math.isfinite(row["free_residual_backward_error"]) for row in result["levels"])
    assert result["levels"][0]["relative_matrix_difference_from_archived_j7_alpha0"] <= 1.0e-12
    assert result["levels"][0]["relative_displacement_difference_from_archived_j7_alpha0"] <= 1.0e-10
    assert set(result["figures"]) == {"site_hex8_j7_distortion.png", "hex8_j7_distortion_indicators.png"}
