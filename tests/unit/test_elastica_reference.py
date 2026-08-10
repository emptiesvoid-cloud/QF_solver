"""Tests for the cantilever elastica verification oracle."""

from __future__ import annotations

import pytest

from solveur.verification.elastica import solve_cantilever_elastica


def test_elastica_tends_to_linear_euler_bernoulli_at_small_load():
    young = 210.0e9
    inertia = 8.0e-6
    length = 2.0
    load = 10.0
    result = solve_cantilever_elastica(
        young=young, inertia=inertia, length=length, transverse_load=load
    )
    linear_tip = -load * length**3 / (3.0 * young * inertia)

    assert result.converged
    assert result.tip_z == pytest.approx(linear_tip, rel=1.0e-8)
    assert result.tip_x == pytest.approx(length, rel=1.0e-9)


@pytest.mark.parametrize("parameter", ["young", "inertia", "length", "transverse_load"])
def test_elastica_rejects_non_positive_parameters(parameter):
    values = {"young": 1.0, "inertia": 1.0, "length": 1.0, "transverse_load": 1.0}
    values[parameter] = 0.0

    with pytest.raises(ValueError, match="strictly positive"):
        solve_cantilever_elastica(**values)
