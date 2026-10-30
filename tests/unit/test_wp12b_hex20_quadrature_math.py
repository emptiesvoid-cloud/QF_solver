"""Pure polynomial checks: no element assembly or FEM solve is executed."""

import math
import numpy as np
import pytest

from solveur.loads.integration import _quad8_shape_data, _quadrilateral_face_gauss_rule


@pytest.mark.parametrize("nodes,maximum_degree", [(4, 3), (8, 5)])
def test_face_gauss_rule_integrates_polynomial_moments(nodes: int, maximum_degree: int) -> None:
    rule = _quadrilateral_face_gauss_rule(nodes)
    for power in range(maximum_degree + 1):
        observed = sum(weight * point**power for point, weight in rule)
        expected = 0.0 if power % 2 else 2.0 / (power + 1)
        assert observed == pytest.approx(expected, abs=1e-14)


def test_quad8_shape_integrals_match_independent_planar_oracle() -> None:
    # The integral on [-1,1]^2 is -1/3 per corner and 4/3 per edge.
    rule = _quadrilateral_face_gauss_rule(8)
    integrals = np.zeros(8)
    for xi, wx in rule:
        for eta, wy in rule:
            shape, _ = _quad8_shape_data(xi, eta)
            assert shape.sum() == pytest.approx(1.0, abs=1e-14)
            integrals += wx * wy * shape
    np.testing.assert_allclose(integrals, [-1 / 3] * 4 + [4 / 3] * 4, atol=1e-14, rtol=0)


def test_r1_abscissae_reproduce_the_wrong_reference_face_integrals() -> None:
    # Historical points ±1/√3 with three-point weights produce -17/27 and 44/27.
    point = 1.0 / math.sqrt(3.0)
    wrong_rule = ((-point, 5 / 9), (0.0, 8 / 9), (point, 5 / 9))
    integrals = np.zeros(8)
    for xi, wx in wrong_rule:
        for eta, wy in wrong_rule:
            shape, _ = _quad8_shape_data(xi, eta)
            integrals += wx * wy * shape
    np.testing.assert_allclose(integrals, [-17 / 27] * 4 + [44 / 27] * 4, atol=1e-14, rtol=0)


def test_face_gauss_rule_refuses_unregistered_order() -> None:
    with pytest.raises(ValueError, match="four or eight"):
        _quadrilateral_face_gauss_rule(6)
