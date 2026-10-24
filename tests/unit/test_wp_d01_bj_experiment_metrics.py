"""Pure tests for the non-qualifying WP-D01-BJ diagnostic ratio."""

from __future__ import annotations

import math

import pytest

from experiments.wp_d01_bj_experiment_metrics import correction_error_ratio


@pytest.mark.parametrize(
    ("corrected", "uncorrected", "expected_ratio", "expected_status"),
    [
        (0.5, 1.0, 0.5, "DEFINED"),
        (2.0, 1.0, 2.0, "DEFINED"),
        (0.0, 0.0, None, "BOTH_ERRORS_ZERO"),
        (0.25, 0.0, None, "UNCORRECTED_ZERO_CORRECTED_NONZERO"),
    ],
)
def test_correction_error_ratio_reports_defined_and_zero_cases(
    corrected: float,
    uncorrected: float,
    expected_ratio: float | None,
    expected_status: str,
) -> None:
    ratio, status = correction_error_ratio(corrected, uncorrected)
    assert ratio == expected_ratio
    assert status == expected_status
    if ratio is not None:
        assert ratio >= 0.0 and math.isfinite(ratio)


@pytest.mark.parametrize(
    ("corrected", "uncorrected"),
    [(math.nan, 1.0), (1.0, math.inf), (-1.0, 1.0), (1.0, -1.0)],
)
def test_correction_error_ratio_rejects_invalid_norms(corrected: float, uncorrected: float) -> None:
    with pytest.raises(ValueError):
        correction_error_ratio(corrected, uncorrected)
