"""Verification of RBE-style link kinematics and static integration."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from solveur.core.assembler import GlobalAssembler
from solveur.core.constraints import ConstraintReduction
from solveur.core.rbe import Rbe2Definition, Rbe3Definition, rbe2_constraints, rbe3_constraints
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.model_writer import JsonModelWriter


def _coefficients(constraint: object) -> dict[tuple[int, str], float]:
    return {(term.node, term.dof): term.coefficient for term in constraint.terms}


def test_rbe2_generates_rigid_offset_kinematics() -> None:
    constraints = rbe2_constraints(
        np.array([[0.0, 0.0, 0.0], [0.0, 2.0, 3.0]]), Rbe2Definition(master=0, slaves=(1,), name="arm")
    )

    assert len(constraints) == 3
    assert _coefficients(constraints[0]) == {(1, "UX"): 1.0, (0, "UX"): -1.0, (0, "RY"): -3.0, (0, "RZ"): 2.0}
    assert _coefficients(constraints[1]) == {(1, "UY"): 1.0, (0, "UY"): -1.0, (0, "RX"): 3.0}
    assert _coefficients(constraints[2]) == {(1, "UZ"): 1.0, (0, "UZ"): -1.0, (0, "RX"): -2.0}


def test_rbe3_normalizes_weights_without_artificial_stiffness() -> None:
    constraints = rbe3_constraints(
        None,
        Rbe3Definition(
            reference=0,
            independents=((1, 2.0), (2, 1.0)),
            dofs=("UX",),
            mode="weighted",
            name="average",
        ),
    )

    assert len(constraints) == 1
    assert _coefficients(constraints[0]) == {(0, "UX"): 1.0, (1, "UX"): -2.0 / 3.0, (2, "UX"): -1.0 / 3.0}


def test_rbe2_static_solution_obeys_offset_relation_and_round_trips(tmp_path: Path) -> None:
    data = {
        "nodes": [[0.0, 0.0, 0.0], [0.0, 2.0, 0.0]],
        "elements": [],
        "materials": {},
        "springs": [{"node_a": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"], "stiffness": 1000.0}],
        "fixed_dofs": [{"node": 0, "dofs": ["UY", "UZ", "RX", "RY", "RZ"]}],
        "loads": [{"node": 1, "dof": "UX", "value": 20.0}],
        "rbe2": [{"name": "rigid_arm", "master": 0, "slaves": [1]}],
    }
    model = JsonModelReader().from_dict(data)
    result = LinearStaticSolver().solve(model)
    dofs = result.dofs

    master_ux = result.displacements[dofs.index(0, "UX")]
    master_rz = result.displacements[dofs.index(0, "RZ")]
    slave_ux = result.displacements[dofs.index(1, "UX")]
    assert slave_ux == pytest.approx(master_ux - 2.0 * master_rz)
    assert result.solver["multipoint_constraints"]["mpc_count"] == 3
    assert result.to_dict()["qualification_summary"]["maturity"]["discrete_entities"]["rbe2"] == "experimental"
    constraints = result.audit.equilibrium["constraint_forces"] if result.audit is not None else {}
    assert constraints["constraint_violation_norm"] < 1.0e-12
    assert constraints["equilibrium_relative_error"] < 1.0e-12
    assert constraints["resultant"] == pytest.approx([0.0, 0.0, 0.0])
    assert constraints["moment_about_origin"] == pytest.approx([0.0, 0.0, -40.0])
    assert constraints["global_force_closure_relative_error"] < 1.0e-12
    assert constraints["global_moment_closure_relative_error"] < 1.0e-12
    assert result.audit.equilibrium["linear_energy_identity_relative_error"] < 1.0e-12
    checks = {entry["name"]: entry["status"] for entry in result.to_dict()["audit"]["checks"]}
    assert checks["equilibrium:constraint_compatibility"] == "PASS"
    assert checks["equilibrium:constraint_force_closure"] == "PASS"
    assert checks["equilibrium:constraint_global_force_closure"] == "PASS"
    assert checks["equilibrium:constraint_global_moment_closure"] == "PASS"
    stiffness = GlobalAssembler().assemble_stiffness(model, dofs)
    loads = GlobalAssembler().assemble_loads(model, dofs)
    fixed = GlobalAssembler().fixed_indices(model, dofs)
    reduction = ConstraintReduction.from_system(dofs, stiffness, loads, model.linear_constraints(), fixed)
    lagrange = reduction.lagrange_solution(stiffness, loads, dofs, model.linear_constraints(), fixed)
    assert result.displacements == pytest.approx(lagrange)
    target = tmp_path / "rbe2.json"
    JsonModelWriter().write(model, target)
    assert JsonModelReader().read(target).rbe2 == model.rbe2


def test_rbe3_static_solution_distributes_load_through_existing_springs() -> None:
    data = {
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
        "elements": [],
        "materials": {},
        "springs": [
            {"node_a": 1, "dofs": ["UX"], "stiffness": 1000.0},
            {"node_a": 2, "dofs": ["UX"], "stiffness": 1000.0},
        ],
        "loads": [{"node": 0, "dof": "UX", "value": 20.0}],
        "rbe3": [
            {
                "name": "weighted_reference",
                "reference": 0,
                "independents": [{"node": 1, "weight": 2.0}, {"node": 2, "weight": 1.0}],
                "dofs": ["UX"],
                "mode": "weighted",
            }
        ],
    }
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    dofs = result.dofs

    assert result.displacements[dofs.index(1, "UX")] == pytest.approx(20.0 / 1000.0 * 2.0 / 3.0)
    assert result.displacements[dofs.index(2, "UX")] == pytest.approx(20.0 / 1000.0 / 3.0)
    assert result.displacements[dofs.index(0, "UX")] == pytest.approx(20.0 / 1000.0 * 5.0 / 9.0)
    assert result.solver["multipoint_constraints"]["mpc_count"] == 1


def test_rbe3_rigid_body_projection_reproduces_motion_and_transfers_wrench() -> None:
    nodes = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 3.0]]
    )
    constraints = rbe3_constraints(
        nodes,
        Rbe3Definition(reference=0, independents=((1, 1.0), (2, 2.0), (3, 3.0)), name="projector"),
    )
    rigid = np.array([0.2, -0.3, 0.4, 0.1, -0.2, 0.3])
    independent = np.concatenate(
        [
            np.array([rigid[0], rigid[1] + 0.3, rigid[2] + 0.2]),
            np.array([rigid[0] - 0.6, rigid[1], rigid[2] + 0.2]),
            np.array([rigid[0] - 0.6, rigid[1] - 0.3, rigid[2]]),
        ]
    )
    values = {(0, name): rigid[index] for index, name in enumerate(("UX", "UY", "UZ", "RX", "RY", "RZ"))}
    for node, vector in zip((1, 2, 3), independent.reshape(3, 3)):
        values.update({(node, name): vector[index] for index, name in enumerate(("UX", "UY", "UZ"))})
    assert [sum(values[(term.node, term.dof)] * term.coefficient for term in row.terms) for row in constraints] == pytest.approx([0.0] * 6, abs=1.0e-12)

    wrench = np.array([4.0, -2.0, 3.0, 5.0, 7.0, -11.0])
    nodal_forces = np.zeros((3, 3))
    for row, generalized in zip(constraints, wrench):
        for term in row.terms[1:]:
            if term.dof in {"UX", "UY", "UZ"}:
                nodal_forces[term.node - 1, ("UX", "UY", "UZ").index(term.dof)] -= term.coefficient * generalized
    offsets = nodes[1:] - nodes[0]
    assert np.sum(nodal_forces, axis=0) == pytest.approx(wrench[:3])
    assert np.sum(np.cross(offsets, nodal_forces), axis=0) == pytest.approx(wrench[3:])


def test_rbe3_rigid_body_projection_solves_and_closes_global_equilibrium() -> None:
    data = {
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 2.0, 0.0], [0.0, 0.0, 3.0]],
        "elements": [],
        "materials": {},
        "springs": [
            {"node_a": node, "dofs": ["UX", "UY", "UZ"], "stiffness": 1000.0}
            for node in (1, 2, 3)
        ],
        "loads": [{"node": 0, "dof": "UX", "value": 4.0}, {"node": 0, "dof": "RZ", "value": -5.0}],
        "rbe3": [
            {"name": "spatial_distribution", "reference": 0, "independents": [
                {"node": 1, "weight": 1.0}, {"node": 2, "weight": 2.0}, {"node": 3, "weight": 3.0}
            ]}
        ],
    }
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    assert result.audit is not None
    constraints = result.audit.equilibrium["constraint_forces"]
    assert constraints["kinematic_equation_count"] == 6
    assert constraints["constraint_violation_norm"] < 1.0e-12
    assert constraints["global_force_closure_relative_error"] < 1.0e-12
    assert constraints["global_moment_closure_relative_error"] < 1.0e-12


def test_rbe3_rigid_body_projection_rejects_degenerate_geometry() -> None:
    with pytest.raises(ValueError, match="span six rigid-body"):
        rbe3_constraints(
            np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]),
            Rbe3Definition(reference=0, independents=((1, 1.0), (2, 1.0))),
        )


def test_schema_rejects_invalid_rbe_references() -> None:
    with pytest.raises(ValueError, match="must differ from master"):
        JsonModelReader().from_dict(
            {
                "nodes": [[0.0, 0.0, 0.0]],
                "elements": [],
                "materials": {},
                "springs": [{"node_a": 0, "dofs": ["UX"], "stiffness": 1.0}],
                "rbe2": [{"master": 0, "slaves": [0]}],
            }
        )
