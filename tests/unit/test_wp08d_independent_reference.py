"""Targeted tests for the independent NumPy KKT/reference harness."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np

from scripts.wp08d_independent_kkt_reference import (
    KktReferenceProblem,
    ReferenceContact,
    solve_kkt_return_map,
)


REFERENCE = Path(__file__).resolve().parents[2] / "scripts" / "wp08d_independent_kkt_reference.py"


def _problem(force_x: float, *, tangential_stiffness: float = 1.0e4) -> KktReferenceProblem:
    stiffness = np.diag([1.0e6, 1.0e6, 1.0e3])
    normal = np.array([0.0, 0.0, 1.0])
    tangent_x = np.array([1.0, 0.0, 0.0])
    tangent_y = np.array([0.0, 1.0, 0.0])
    contact = ReferenceContact(
        normal=normal,
        tangent_basis=np.vstack((tangent_x, tangent_y)),
        friction_coefficient=0.3,
        tangential_stiffness=tangential_stiffness,
    )
    return KktReferenceProblem(
        stiffness=stiffness,
        force=np.array([force_x, 0.0, -200.0]),
        constraints=np.zeros((0, 3), dtype=float),
        constraint_values=np.zeros(0, dtype=float),
        contacts=(contact,),
    )


def test_reference_module_has_no_solver_package_or_production_contact_imports() -> None:
    tree = ast.parse(REFERENCE.read_text(encoding="utf-8"))
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    imported_names = {
        alias.name
        for node in imports
        for alias in node.names
    }
    assert not any(name.startswith("solveur") for name in imported_names)
    assert "_friction_update" not in REFERENCE.read_text(encoding="utf-8")


def test_independent_reference_reaches_a_finite_sliding_return_map() -> None:
    result = solve_kkt_return_map(_problem(50_000.0))
    assert result.contact_states in (("stick",), ("slip",))
    assert np.all(np.isfinite(result.displacement))
    assert result.cumulative_dissipation > 0.0
    assert np.linalg.norm(result.displacement[[1, 2]]) == 0.0


def test_independent_reference_sticks_inside_coulomb_limit() -> None:
    result = solve_kkt_return_map(_problem(100.0))
    assert result.contact_states == ("stick",)
    assert result.cumulative_dissipation == 0.0
    assert result.tangential_forces[0, 0] > 0.0


def test_reference_rejects_non_symmetric_stiffness() -> None:
    problem = _problem(100.0)
    nonsymmetric = np.asarray(problem.stiffness, dtype=float).copy()
    nonsymmetric[0, 1] = 1.0
    invalid = KktReferenceProblem(
        stiffness=nonsymmetric,
        force=problem.force,
        constraints=problem.constraints,
        constraint_values=problem.constraint_values,
        contacts=problem.contacts,
    )
    try:
        solve_kkt_return_map(invalid)
    except ValueError as error:
        assert "symmetric" in str(error)
    else:
        raise AssertionError("non-symmetric reference stiffness was accepted")
