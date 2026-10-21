"""Verification of RBE-style link kinematics and static integration."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from solveur.core.assembler import GlobalAssembler
from solveur.core.constraints import ConstraintReduction
from solveur.core.rbe import Rbe2Definition, Rbe3Definition, rbe2_constraints, rbe3_constraints
from solveur.core.model import ElementDefinition, FiniteElementModel
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.io.model_writer import JsonModelWriter
from solveur.mesh.validation import MeshValidator


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


def test_rbe2_reproduces_arbitrary_rigid_motion_for_multiple_offsets_and_rotation_tie() -> None:
    nodes = np.array(
        [[2.3, -1.7, 4.2], [3.1, 0.6, 2.8], [-0.4, -2.2, 5.7]],
        dtype=np.float64,
    )
    rotation = np.array([0.37, -0.21, 0.48])
    master_translation = np.array([-0.13, 0.28, 0.71])
    values: dict[tuple[int, str], float] = {}
    for component, dof in enumerate(("UX", "UY", "UZ")):
        values[(0, dof)] = float(master_translation[component])
    for component, dof in enumerate(("RX", "RY", "RZ")):
        values[(0, dof)] = float(rotation[component])

    definition = Rbe2Definition(master=0, slaves=(1, 2), tie_rotations=True)
    constraints = rbe2_constraints(nodes, definition)
    assert len(constraints) == 12
    for slave in definition.slaves:
        slave_translation = master_translation + np.cross(rotation, nodes[slave] - nodes[0])
        for component, dof in enumerate(("UX", "UY", "UZ")):
            values[(slave, dof)] = float(slave_translation[component])
        for component, dof in enumerate(("RX", "RY", "RZ")):
            values[(slave, dof)] = float(rotation[component])

    residuals = [sum(values[(term.node, term.dof)] * term.coefficient for term in row.terms) for row in constraints]
    np.testing.assert_allclose(residuals, np.zeros(12), atol=2.0e-15, rtol=0.0)


def test_rbe2_dof_activation_for_solid_master_and_beam_or_shell_slave() -> None:
    model = FiniteElementModel(
        nodes=np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 1.0, 1.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [2.0, 0.0, 0.0],
                [3.0, 0.0, 0.0],
            ]
        ),
        elements=[
            ElementDefinition("TET4", (0, 1, 2, 3), "solid"),
            ElementDefinition("BEAM2", (4, 5), "beam"),
        ],
        materials={},
        rbe2=[
            Rbe2Definition(master=0, slaves=(1,)),
            Rbe2Definition(master=4, slaves=(5,), tie_rotations=True),
        ],
    )

    dofs = model.dof_manager()
    assert dofs.node_dofs[0] == ("UX", "UY", "UZ", "RX", "RY", "RZ")
    assert dofs.node_dofs[1] == ("UX", "UY", "UZ")
    assert dofs.node_dofs[4] == ("UX", "UY", "UZ", "RX", "RY", "RZ")
    assert dofs.node_dofs[5] == ("UX", "UY", "UZ", "RX", "RY", "RZ")


def test_mesh_rank_uses_rbe_reduction_instead_of_unconstrained_auxiliary_rotations() -> None:
    model = JsonModelReader().from_dict(
        {
            "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "elements": [],
            "materials": {},
            "springs": [
                {"node_a": node, "dofs": ["UX", "UY", "UZ"], "stiffness": 1000.0}
                for node in (1, 2, 3)
            ],
            "fixed_dofs": [{"node": 0, "dofs": ["UX", "UY"]}],
            "rbe2": [{"master": 0, "slaves": [1, 2, 3]}],
        }
    )

    report = MeshValidator().validate(model)
    rank = report.details["mechanical_rank"]
    assert rank["checked"] is True
    assert rank["rank_basis"] == "fixed_and_mpc_reduced"
    assert rank["free_dof_count"] == 4
    assert rank["rank"] == 4
    assert rank["zero_mode_count"] == 0
    assert report.details["isolated_nodes"] == []
    assert not any("near-zero modes" in warning for warning in report.warnings)


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


@pytest.mark.parametrize(
    "weights",
    [
        ((1, -1.0), (2, 2.0)),
        ((1, 0.0), (2, 1.0)),
        ((1, 1.0), (2, -1.0)),
        ((1, float("nan")), (2, 1.0)),
        ((1, float("inf")), (2, 1.0)),
    ],
)
def test_rbe3_rigid_projection_rejects_invalid_weights(weights: tuple[tuple[int, float], ...]) -> None:
    nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]])
    with pytest.raises(ValueError):
        rbe3_constraints(nodes, Rbe3Definition(reference=0, independents=weights))


def test_rbe3_weighted_mode_retains_documented_signed_extrapolation() -> None:
    constraints = rbe3_constraints(
        None,
        Rbe3Definition(
            reference=0,
            independents=((1, -1.0), (2, 2.0)),
            dofs=("UX",),
            mode="weighted",
        ),
    )
    assert _coefficients(constraints[0]) == {(0, "UX"): 1.0, (1, "UX"): 1.0, (2, "UX"): -2.0}


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


def test_rbe2_multiple_arms_transfer_combined_wrench_and_match_condensed_reference() -> None:
    nodes = np.array([[0.4, -0.2, 0.7], [1.2, 0.9, -0.1], [-0.6, 0.3, 1.5]], dtype=np.float64)
    node_stiffness = np.array(
        [[120.0, 150.0, 180.0, 14.0, 17.0, 19.0], [35.0, 42.0, 48.0, 5.0, 6.0, 7.0], [53.0, 59.0, 64.0, 8.0, 9.0, 10.0]]
    )
    nodal_loads = np.array(
        [
            [3.0, -4.0, 2.0, 0.7, -0.3, 0.5],
            [8.0, 1.0, -5.0, 0.2, 0.6, -0.4],
            [-2.0, 7.0, 4.0, -0.8, 0.1, 0.9],
        ]
    )
    dof_names = ("UX", "UY", "UZ", "RX", "RY", "RZ")
    springs = [
        {"node_a": node, "dofs": [dof], "stiffness": float(node_stiffness[node, component])}
        for node in range(3)
        for component, dof in enumerate(dof_names)
    ]
    loads = [
        {"node": node, "dof": dof, "value": float(nodal_loads[node, component])}
        for node in range(3)
        for component, dof in enumerate(dof_names)
    ]
    model = JsonModelReader().from_dict(
        {
            "nodes": nodes.tolist(),
            "elements": [],
            "materials": {},
            "springs": springs,
            "loads": loads,
            "rbe2": [{"master": 0, "slaves": [1, 2], "tie_rotations": True}],
        }
    )
    result = LinearStaticSolver().solve(model)

    # Independent condensed reference assembled directly from the rigid-arm
    # cross-product map and the declared diagonal nodal spring matrices.
    condensed_stiffness = np.diag(node_stiffness[0].copy())
    condensed_load = nodal_loads[0].copy()
    maps: list[np.ndarray] = []
    for node in (1, 2):
        x, y, z = nodes[node] - nodes[0]
        mapping = np.array(
            [
                [1.0, 0.0, 0.0, 0.0, z, -y],
                [0.0, 1.0, 0.0, -z, 0.0, x],
                [0.0, 0.0, 1.0, y, -x, 0.0],
                [0.0, 0.0, 0.0, 1.0, 0.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
                [0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
            ]
        )
        maps.append(mapping)
        slave_stiffness = np.diag(node_stiffness[node])
        condensed_stiffness += mapping.T @ slave_stiffness @ mapping
        condensed_load += mapping.T @ nodal_loads[node]
    expected_master = np.linalg.solve(condensed_stiffness, condensed_load)
    actual_master = np.array([result.displacements[result.dofs.index(0, dof)] for dof in dof_names])
    np.testing.assert_allclose(actual_master, expected_master, atol=2.0e-13, rtol=2.0e-13)

    for node, mapping in zip((1, 2), maps):
        actual_slave = np.array([result.displacements[result.dofs.index(node, dof)] for dof in dof_names])
        np.testing.assert_allclose(actual_slave, mapping @ expected_master, atol=2.0e-13, rtol=2.0e-13)

    external_force = np.sum(nodal_loads[:, :3], axis=0)
    external_moment = np.sum(np.cross(nodes, nodal_loads[:, :3]), axis=0) + np.sum(nodal_loads[:, 3:], axis=0)
    support_force = np.zeros(3)
    support_moment = np.zeros(3)
    for node in range(3):
        dofs_at_node = np.array([result.displacements[result.dofs.index(node, dof)] for dof in dof_names])
        spring_reaction = -node_stiffness[node] * dofs_at_node
        support_force += spring_reaction[:3]
        support_moment += np.cross(nodes[node], spring_reaction[:3]) + spring_reaction[3:]
    np.testing.assert_allclose(external_force + support_force, np.zeros(3), atol=2.0e-12, rtol=0.0)
    np.testing.assert_allclose(external_moment + support_moment, np.zeros(3), atol=2.0e-12, rtol=0.0)
    assert result.audit is not None
    assert result.audit.equilibrium["constraint_forces"]["constraint_violation_norm"] < 1.0e-12
    assert result.audit.equilibrium["constraint_forces"]["global_force_closure_relative_error"] < 1.0e-12
    assert result.audit.equilibrium["constraint_forces"]["global_moment_closure_relative_error"] < 1.0e-12


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


def test_rbe3_rigid_body_projection_on_symmetric_tetrahedron_reproduces_six_modes() -> None:
    nodes = np.array(
        [
            [0.0, 0.0, 0.0],
            [1.0, 1.0, 1.0],
            [1.0, -1.0, -1.0],
            [-1.0, 1.0, -1.0],
            [-1.0, -1.0, 1.0],
        ],
        dtype=np.float64,
    )
    independents = ((1, 1.0), (2, 1.0), (3, 1.0), (4, 1.0))
    constraints = rbe3_constraints(nodes, Rbe3Definition(reference=0, independents=independents))
    design = np.zeros((12, 6), dtype=np.float64)
    for index, (node, _) in enumerate(independents):
        x, y, z = nodes[node]
        design[3 * index : 3 * index + 3] = np.array(
            [
                [1.0, 0.0, 0.0, 0.0, z, -y],
                [0.0, 1.0, 0.0, -z, 0.0, x],
                [0.0, 0.0, 1.0, y, -x, 0.0],
            ]
        )
    projector = np.zeros((6, 12), dtype=np.float64)
    positions = {node: index for index, (node, _) in enumerate(independents)}
    for component, row in enumerate(constraints):
        for term in row.terms[1:]:
            projector[component, 3 * positions[term.node] + ("UX", "UY", "UZ").index(term.dof)] = -term.coefficient
    np.testing.assert_allclose(projector @ design, np.eye(6), atol=2.0e-13, rtol=2.0e-13)


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
    model = JsonModelReader().from_dict(data)
    result = LinearStaticSolver().solve(model)
    assert result.audit is not None
    constraints = result.audit.equilibrium["constraint_forces"]
    assert constraints["kinematic_equation_count"] == 6
    assert constraints["constraint_violation_norm"] < 1.0e-12
    assert constraints["global_force_closure_relative_error"] < 1.0e-12
    assert constraints["global_moment_closure_relative_error"] < 1.0e-12
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, result.dofs)
    loads = assembler.assemble_loads(model, result.dofs)
    fixed = assembler.fixed_indices(model, result.dofs)
    reduction = ConstraintReduction.from_system(result.dofs, stiffness, loads, model.linear_constraints(), fixed)
    lagrange = reduction.lagrange_solution(stiffness, loads, result.dofs, model.linear_constraints(), fixed)
    np.testing.assert_allclose(result.displacements, lagrange, atol=1.0e-12, rtol=1.0e-12)


def test_rbe3_rigid_body_projection_rejects_degenerate_geometry() -> None:
    with pytest.raises(ValueError, match="span six rigid-body"):
        rbe3_constraints(
            np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]]),
            Rbe3Definition(reference=0, independents=((1, 1.0), (2, 1.0))),
        )


def test_rbe3_rigid_body_projection_rejects_nearly_degenerate_geometry() -> None:
    nodes = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 1.0e-14, 0.0], [3.0, 0.0, 1.0e-14]],
        dtype=np.float64,
    )
    with pytest.raises(ValueError, match="span six rigid-body coordinates"):
        rbe3_constraints(nodes, Rbe3Definition(reference=0, independents=((1, 1.0), (2, 1.0), (3, 1.0))))


def test_rbe3_projection_is_invariant_to_coordinate_and_common_weight_scales() -> None:
    base = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.2, 1.3, 0.0], [0.4, 0.3, 0.8]],
        dtype=np.float64,
    )
    entries = ((1, 0.5), (2, 2.0), (3, 1.5))
    reference_rows: np.ndarray | None = None
    reference_rotation_rows: np.ndarray | None = None
    for coordinate_scale in (1.0e-8, 1.0, 1.0e8):
        translation = coordinate_scale * np.array([5.0, -4.0, 2.0])
        nodes = translation + coordinate_scale * base
        for weight_scale in (1.0e-200, 1.0, 1.0e200):
            definition = Rbe3Definition(
                reference=0,
                independents=tuple((node, weight_scale * weight) for node, weight in entries),
            )
            constraints = rbe3_constraints(nodes, definition)
            projector = np.zeros((6, 9), dtype=np.float64)
            local_node = {node: index for index, (node, _) in enumerate(entries)}
            for component, row in enumerate(constraints):
                for term in row.terms[1:]:
                    projector[component, 3 * local_node[term.node] + ("UX", "UY", "UZ").index(term.dof)] = (
                        -term.coefficient
                    )
            if reference_rows is None:
                reference_rows = projector.copy()
                reference_rotation_rows = projector[3:] * coordinate_scale
            np.testing.assert_allclose(projector[:3], reference_rows[:3], atol=2.0e-13, rtol=2.0e-13)
            np.testing.assert_allclose(
                projector[3:] * coordinate_scale,
                reference_rotation_rows,
                atol=2.0e-12,
                rtol=2.0e-12,
            )


def test_rbe3_projection_is_invariant_to_coordinate_origin_translation() -> None:
    base = np.array(
        [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.2, 1.3, 0.0], [0.4, 0.3, 0.8]],
        dtype=np.float64,
    )
    entries = ((1, 0.5), (2, 2.0), (3, 1.5))
    reference = rbe3_constraints(base, Rbe3Definition(reference=0, independents=entries))
    translated = rbe3_constraints(
        base + np.array([1.0e6, -2.0e6, 4.0e6]),
        Rbe3Definition(reference=0, independents=entries),
    )

    def projector(rows: list[object]) -> np.ndarray:
        result = np.zeros((6, 9), dtype=np.float64)
        positions = {node: index for index, (node, _) in enumerate(entries)}
        for component, row in enumerate(rows):
            for term in row.terms[1:]:
                result[component, 3 * positions[term.node] + ("UX", "UY", "UZ").index(term.dof)] = -term.coefficient
        return result

    np.testing.assert_allclose(projector(translated), projector(reference), atol=2.0e-9, rtol=2.0e-9)


def test_rbe3_projection_matches_independent_weighted_least_squares_and_wrench() -> None:
    nodes = np.array(
        [
            [1.7, -0.6, 2.1],
            [3.2, 0.1, 1.8],
            [0.4, 1.7, 2.9],
            [2.0, -1.1, 4.4],
            [0.9, 0.3, 0.8],
        ],
        dtype=np.float64,
    )
    independent = ((1, 0.7), (2, 1.9), (3, 2.2), (4, 0.8))
    constraints = rbe3_constraints(
        nodes,
        Rbe3Definition(reference=0, independents=independent),
    )

    # Independent oracle: construct the rigid-motion design from cross products
    # and solve the weighted least-squares map directly with NumPy's LAPACK.
    design = np.zeros((3 * len(independent), 6), dtype=np.float64)
    identity = np.eye(3)
    offsets = []
    for index, (node, _) in enumerate(independent):
        offset = nodes[node] - nodes[0]
        offsets.append(offset)
        skew = np.array(
            [[0.0, -offset[2], offset[1]], [offset[2], 0.0, -offset[0]], [-offset[1], offset[0], 0.0]]
        )
        design[3 * index : 3 * index + 3, :3] = identity
        design[3 * index : 3 * index + 3, 3:] = -skew
    coordinate_weights = np.repeat(np.asarray([weight for _, weight in independent]), 3)
    sqrt_weights = np.sqrt(coordinate_weights)
    expected = np.linalg.lstsq(
        sqrt_weights[:, None] * design,
        np.diag(sqrt_weights),
        rcond=None,
    )[0]
    actual = np.zeros_like(expected)
    node_position = {node: index for index, (node, _) in enumerate(independent)}
    for component, row in enumerate(constraints):
        for term in row.terms[1:]:
            actual[component, 3 * node_position[term.node] + ("UX", "UY", "UZ").index(term.dof)] = -term.coefficient
    np.testing.assert_allclose(actual, expected, atol=2.0e-13, rtol=2.0e-13)
    np.testing.assert_allclose(actual @ design, np.eye(6), atol=3.0e-13, rtol=3.0e-13)

    reference_wrench = np.array([4.0, -2.0, 3.0, 5.0, 7.0, -11.0])
    nodal_forces = (actual.T @ reference_wrench).reshape(len(independent), 3)
    resultant_force = np.sum(nodal_forces, axis=0)
    resultant_moment = sum(np.cross(offset, force) for offset, force in zip(offsets, nodal_forces))
    np.testing.assert_allclose(resultant_force, reference_wrench[:3], atol=3.0e-13, rtol=3.0e-13)
    np.testing.assert_allclose(resultant_moment, reference_wrench[3:], atol=4.0e-13, rtol=4.0e-13)


def test_schema_accepts_scale_invariant_rbe3_weights() -> None:
    model = JsonModelReader().from_dict(
        {
            "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
            "elements": [],
            "materials": {},
            "springs": [{"node_a": 1, "dofs": ["UX"], "stiffness": 1.0}],
            "rbe3": [
                {
                    "reference": 0,
                    "independents": [
                        {"node": 1, "weight": 2.0e-200},
                        {"node": 2, "weight": 1.0e-200},
                    ],
                    "dofs": ["UX"],
                    "mode": "weighted",
                }
            ],
        }
    )
    row = model.linear_constraints()[0]
    assert _coefficients(row) == {(0, "UX"): 1.0, (1, "UX"): -2.0 / 3.0, (2, "UX"): -1.0 / 3.0}


def test_programmatic_weighted_rbe3_validates_node_references_when_coordinates_are_available() -> None:
    nodes = np.zeros((2, 3))
    with pytest.raises(ValueError, match="RBE3 reference"):
        rbe3_constraints(nodes, Rbe3Definition(reference=2, independents=((1, 1.0),), dofs=("UX",), mode="weighted"))
    with pytest.raises(ValueError, match="must differ from the reference"):
        rbe3_constraints(nodes, Rbe3Definition(reference=0, independents=((0, 1.0),), dofs=("UX",), mode="weighted"))


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
