"""Unit checks for the sparse affine MPC reduction kernel."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.constraints import ConstraintReduction, ConstraintTerm, LinearConstraint
from solveur.core.dofs import DofManager
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.model_writer import JsonModelWriter


def _dofs() -> DofManager:
    return DofManager.from_node_requirements({0: {"UX"}, 1: {"UX"}, 2: {"UX"}})


def test_elimination_matches_lagrange_multiplier_solution() -> None:
    dofs = _dofs()
    stiffness = csr_matrix([[8.0, -2.0, 0.0], [-2.0, 5.0, -1.0], [0.0, -1.0, 3.0]])
    loads = np.array([0.0, 0.0, 12.0])
    constraints = [
        LinearConstraint(
            (ConstraintTerm(1, "UX", 1.0), ConstraintTerm(0, "UX", -1.0)),
            name="tie_1_to_0",
        )
    ]
    fixed = np.array([dofs.index(0, "UX")], dtype=int)
    reduction = ConstraintReduction.from_system(dofs, stiffness, loads, constraints, fixed)

    reduced = np.linalg.solve(reduction.matrix.toarray(), reduction.rhs)
    eliminated = reduction.expand(reduced)
    lagrange = reduction.lagrange_solution(stiffness, loads, dofs, constraints, fixed)

    np.testing.assert_allclose(eliminated, lagrange, atol=1.0e-12)
    assert eliminated[dofs.index(0, "UX")] == pytest.approx(0.0)
    assert eliminated[dofs.index(1, "UX")] == pytest.approx(0.0)


def test_affine_constraint_reconstructs_prescribed_relative_displacement() -> None:
    dofs = _dofs()
    stiffness = csr_matrix(np.eye(3))
    loads = np.zeros(3)
    constraints = [
        LinearConstraint(
            (ConstraintTerm(1, "UX", 2.0), ConstraintTerm(2, "UX", -2.0)),
            value=0.4,
            name="offset",
        )
    ]
    reduction = ConstraintReduction.from_system(dofs, stiffness, loads, constraints, np.array([], dtype=int))
    full = reduction.expand(np.array([0.0, 0.3]))

    assert full[dofs.index(1, "UX")] - full[dofs.index(2, "UX")] == pytest.approx(0.2)


@pytest.mark.parametrize(
    "constraints, message",
    [
        (
            [
                LinearConstraint((ConstraintTerm(0, "UX", 1.0), ConstraintTerm(1, "UX", -1.0))),
                LinearConstraint((ConstraintTerm(1, "UX", 1.0), ConstraintTerm(0, "UX", -1.0))),
            ],
            "cycle",
        ),
        (
            [
                LinearConstraint((ConstraintTerm(0, "UX", 1.0), ConstraintTerm(1, "UX", -1.0))),
                LinearConstraint((ConstraintTerm(0, "UX", 1.0), ConstraintTerm(2, "UX", -1.0))),
            ],
            "conflicts",
        ),
    ],
)
def test_mpc_reducer_rejects_cycles_and_conflicts(
    constraints: list[LinearConstraint],
    message: str,
) -> None:
    dofs = _dofs()
    with pytest.raises(ValueError, match=message):
        ConstraintReduction.from_system(dofs, csr_matrix(np.eye(3)), np.zeros(3), constraints, np.array([], dtype=int))


def test_static_solver_enforces_json_mpc_and_reports_reduction(tmp_path: object) -> None:
    data = {
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
        "elements": [],
        "materials": {},
        "springs": [{"node_a": 0, "dofs": ["UX"], "stiffness": 1000.0}],
        "loads": [{"node": 1, "dof": "UX", "value": 20.0}],
        "multipoint_constraints": [
            {
                "name": "rigid_translation",
                "terms": [
                    {"node": 1, "dof": "UX", "coefficient": 1.0},
                    {"node": 0, "dof": "UX", "coefficient": -1.0},
                ],
            }
        ],
    }
    model = JsonModelReader().from_dict(data)
    result = LinearStaticSolver().solve(model)

    np.testing.assert_allclose(result.displacements, [0.02, 0.02], atol=1.0e-12)
    assert result.solver["multipoint_constraints"]["mpc_count"] == 1
    assert result.audit is not None
    assert result.audit.equilibrium["free_residual_norm"] < 1.0e-10
    target = tmp_path / "mpc_model.json"
    JsonModelWriter().write(model, target)
    assert JsonModelReader().read(target).multipoint_constraints == model.multipoint_constraints


def test_rbe2_support_reaction_includes_transported_moment_in_global_audit() -> None:
    root = Path(__file__).resolve().parents[2]
    result = LinearStaticSolver().solve(JsonModelReader().read(root / "examples" / "rbe2_rigid_arm.json"))

    equilibrium = result.audit.equilibrium
    reaction = next(item for item in equilibrium["reactions"] if item["node"] == 0 and item["dof"] == "RZ")
    assert reaction["value"] == pytest.approx(40.0)
    assert equilibrium["moment_imbalance_about_origin"] == pytest.approx([0.0, 0.0, 0.0], abs=1.0e-12)
    assert equilibrium["moment_balance_relative_error"] <= 1.0e-12


def test_json_schema_rejects_invalid_mpc_terms() -> None:
    with pytest.raises(ValueError, match="dependent DOF"):
        JsonModelReader().from_dict(
            {
                "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]],
                "elements": [],
                "materials": {},
                "springs": [{"node_a": 0, "dofs": ["UX"], "stiffness": 1.0}],
                "multipoint_constraints": [
                    {
                        "terms": [
                            {"node": 1, "dof": "UX", "coefficient": 0.0},
                            {"node": 0, "dof": "UX", "coefficient": -1.0},
                        ]
                    }
                ],
            }
        )
