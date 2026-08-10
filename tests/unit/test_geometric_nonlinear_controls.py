"""Tests for finite-kinematics load-control policy."""

from __future__ import annotations

import pytest

from solveur.core.geometric_nonlinear_controls import (
    DEFAULT_LOAD_INCREMENTS,
    MINIMUM_LOAD_INCREMENTS,
    GeometricNonlinearControls,
)


def test_geometric_nonlinear_controls_default_to_ten_increments():
    controls = GeometricNonlinearControls()

    assert controls.load_increments == DEFAULT_LOAD_INCREMENTS == 10
    assert MINIMUM_LOAD_INCREMENTS == 6


def test_geometric_nonlinear_controls_accept_minimum():
    assert GeometricNonlinearControls(load_increments=6).load_increments == 6


@pytest.mark.parametrize("value", [0, 3, 5, True, 6.0])
def test_geometric_nonlinear_controls_reject_invalid_increment_count(value):
    with pytest.raises(ValueError, match="load_increments"):
        GeometricNonlinearControls(load_increments=value)
