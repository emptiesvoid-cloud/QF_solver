"""J11 production/global HEX8-SRI reconstruction and same-system comparisons."""

from __future__ import annotations

import math

from research.j11_hex8.hex8_j7_reconstruction import ALPHAS, run_diagnostic


def test_j11_hex8_global_and_independent_reconstruction() -> None:
    result = run_diagnostic()
    assert result["execution_status"] == "COMPLETED_EXPLORATORY"
    assert result["interpretation"]["mechanical_reference"] == "none; a second solve of the same matrix is not an independent continuum or formulation reference"
    levels = result["results"]
    assert [row["alpha"] for row in levels] == list(ALPHAS)
    assert all(row["production_global_status"] == "PASS" for row in levels)
    assert levels[0]["global_vs_archived_j10_matrix_relative_frobenius"] < 1.0e-12
    assert levels[0]["mpmath_80_digit_qf_state_reconstruction_alpha0"]["precision_decimal_digits"] == 80
    assert levels[0]["mpmath_80_digit_same_matrix_solve_alpha0"]["precision_decimal_digits"] == 80
    assert (
        levels[0]["mpmath_80_digit_same_matrix_solve_alpha0"]["free_residual_l2_n"]
        < levels[0]["mpmath_80_digit_qf_state_reconstruction_alpha0"]["free_residual_l2_n"]
    )
    assert all(math.isfinite(row["condition_number_2_raw"]) for row in levels)
    assert result["same_system_definition"]["force_and_fixed_dof_inputs"] == "archived J7 arrays reused bit-for-bit"
