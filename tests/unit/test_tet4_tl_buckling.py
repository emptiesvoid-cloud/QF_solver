"""Tests for total-Lagrangian tangent buckling helpers."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.materials.solid import SolidMaterial
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh
from solveur.verification.tet4_total_lagrangian_buckling import (
    euler_cantilever_critical_load,
    refine_sign_change,
)
from solveur.verification.total_lagrangian_structural import solve_proportional_dead_load


def test_euler_cantilever_critical_load():
    value = euler_cantilever_critical_load(210.0e9, 8.0e-6, 3.0)
    assert value == pytest.approx(np.pi**2 * 210.0e9 * 8.0e-6 / 36.0)


@pytest.mark.parametrize("values", [(0.0, 1.0, 1.0), (1.0, 0.0, 1.0), (1.0, 1.0, 0.0)])
def test_euler_cantilever_rejects_nonpositive_parameters(values):
    with pytest.raises(ValueError, match="strictly positive"):
        euler_cantilever_critical_load(*values)


def test_refine_sign_change_finds_linear_root():
    def function(value):
        return 3.25 - value

    bracket = refine_sign_change(function, 0.0, 5.0, function(0.0), function(5.0), tolerance=1.0e-8)
    assert bracket[0] <= 3.25 <= bracket[1]
    assert bracket[1] - bracket[0] < 1.0e-6


def test_refine_sign_change_rejects_invalid_bracket():
    with pytest.raises(ValueError, match="positive-to-negative"):
        refine_sign_change(lambda value: value, 0.0, 1.0, -1.0, 1.0, tolerance=1.0e-3)


def test_dead_load_helper_converges_small_compression():
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 0.5, 0.5)
    assembly = TotalLagrangianTet4Assembly(nodes, elements, SolidMaterial(E=1.0e6, nu=0.3))
    fixed_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    fixed = (3 * fixed_nodes[:, None] + np.arange(3)).reshape(-1)
    tip_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 2.0))
    load = np.zeros(assembly.ndof)
    load[3 * tip_nodes] = -10.0 / tip_nodes.size

    result = solve_proportional_dead_load(assembly, load, fixed, increments=6)

    assert result.relative_residual < 1.0e-9
    assert result.minimum_det_f > 0.99
    assert np.mean(result.displacement[3 * tip_nodes]) < 0.0
