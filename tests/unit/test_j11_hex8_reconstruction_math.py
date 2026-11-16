"""Small algebraic controls for J11 high-precision HEX8 diagnostics."""

from __future__ import annotations

import math

import numpy as np

from research.j11_hex8.hex8_j7_reconstruction import (
    _mpmath_residual_and_closure,
    _mpmath_solve,
)


def test_mpmath_solve_and_reconstructed_support_wrench_use_same_system() -> None:
    coordinates = np.asarray(((0.0, 0.0, 0.0), (20.0, 0.0, 0.0)))
    stiffness = np.diag((2.0, 1.0, 1.0, 2.0, 2.0, 2.0))
    stiffness[0, 3] = -2.0
    stiffness[3, 0] = -2.0
    force = np.asarray((0.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    fixed = np.asarray((0, 1, 2), dtype=np.int64)
    free = np.asarray((3, 4, 5), dtype=np.int64)
    solution_free = _mpmath_solve(stiffness[np.ix_(free, free)], force[free], digits=80)
    solution = [solution_free[0] * 0, solution_free[0] * 0, solution_free[0] * 0, *solution_free]

    exact = _mpmath_residual_and_closure(coordinates, stiffness, force, solution, fixed, free)
    assert exact["precision_decimal_digits"] == 80
    assert exact["free_residual_l2_n"] == 0.0
    assert exact["force_closure_relative"] == 0.0
    assert exact["moment_closure_relative"] == 0.0

    perturbed = np.asarray((0.0, 0.0, 0.0, 0.5000001, 0.0, 0.0))
    rounded = _mpmath_residual_and_closure(coordinates, stiffness, force, perturbed, fixed, free)
    assert math.isclose(rounded["free_residual_l2_n"], 2.0e-7, rel_tol=1.0e-8)
    assert rounded["force_closure_relative"] > 0.0
