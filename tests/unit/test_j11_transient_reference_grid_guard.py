"""Regression checks for time-grid-aware continuum reference consistency."""

from __future__ import annotations

import numpy as np
import pytest

from research.j11_transient.tet10_axial_transient import _assert_shared_reference_consistency


def test_coarse_time_grid_is_not_compared_elementwise_to_fine_grid() -> None:
    coarse_times = np.asarray((1.0e-4, 2.0e-4))
    coarse_values = np.asarray((0.1, 0.2))
    fine_times = np.asarray((2.5e-5, 5.0e-5, 7.5e-5, 1.0e-4))
    fine_values = np.asarray((0.025, 0.05, 0.075, 0.1))

    _assert_shared_reference_consistency(
        coarse_times,
        coarse_values,
        fine_times,
        fine_values,
        tolerance=1.0e-12,
    )


def test_identical_time_grid_still_checks_cached_reference_values() -> None:
    times = np.asarray((1.0e-4, 2.0e-4))
    reference = np.asarray((0.1, 0.2))
    _assert_shared_reference_consistency(times, reference.copy(), times, reference, tolerance=1.0e-12)

    with pytest.raises(RuntimeError, match="identical physical observation times"):
        _assert_shared_reference_consistency(
            times,
            np.asarray((0.1, 0.21)),
            times,
            reference,
            tolerance=1.0e-12,
        )
