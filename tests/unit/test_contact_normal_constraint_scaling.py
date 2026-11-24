from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.contact import support


@pytest.mark.parametrize(
    ("stiffness", "friction", "scale"),
    [(1e6, True, 1e3), (1, True, 1), (1e6, False, 1), (2.0**80, True, 2.0**40), (2.0**-60, True, 1)],
)
def test_normal_constraint_scaling_preserves_compression(stiffness, friction, scale, monkeypatch):
    matrix = csr_matrix([[stiffness, 0.0], [0.0, 1.0]])
    gap = 0.125 * min(1, 2.0**20 / stiffness)
    reduction = SimpleNamespace(
        matrix=matrix,
        rhs=np.array([stiffness * gap + 3, 1.0]),
        transform=csr_matrix(np.eye(2)),
        offset=np.zeros(2),
        independent=np.arange(2),
        expand=np.asarray,
    )
    plane = SimpleNamespace(vector=np.array([-1.0, 0.0]), initial_gap=gap, has_friction=friction)
    original = support._sparse_solve

    def check_scaled(system, rhs, label):
        assert system[0, 2] == system[2, 0] == -scale
        assert rhs[-1] == -gap * scale
        return original(system, rhs, label)

    monkeypatch.setattr(support, "_sparse_solve", check_scaled)
    displacement, multiplier = support._solve_active_set(reduction, [plane], (0,))
    np.testing.assert_allclose(displacement, [gap, 1])
    np.testing.assert_allclose(multiplier, [-3], atol=1e-10)
    np.testing.assert_allclose(matrix @ displacement + plane.vector * multiplier[0], reduction.rhs)
