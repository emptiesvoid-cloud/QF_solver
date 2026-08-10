"""Mechanical checks for the bounded frictionless node-to-triangle contact."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.core.errors import MeshValidationError
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader
from solveur.mesh.validation import MeshValidator


def _model(load: float) -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]],
        "elements": [],
        "materials": {},
        "fixed_dofs": [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY"]},
        ],
        "springs": [{"node_a": 3, "dofs": ["UZ"], "stiffness": 1000.0}],
        "loads": [{"node": 3, "dof": "UZ", "value": load}],
        "contacts": [{"name": "plane", "slave_node": 3, "master_nodes": [0, 1, 2]}],
    }


def test_separated_contact_is_inactive_and_matches_the_unilateral_solution() -> None:
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(_model(20.0)))
    contact = result.solver["contact"]

    assert contact["active_contact_count"] == 0
    assert contact["contacts"][0]["gap"] == pytest.approx(0.12)
    assert contact["contacts"][0]["pressure"] == pytest.approx(0.0)
    assert result.displacements[result.dofs.index(3, "UZ")] == pytest.approx(0.02)


def test_compression_contact_satisfies_kkt_conditions_and_global_equilibrium() -> None:
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(_model(-200.0)))
    contact = result.solver["contact"]
    row = contact["contacts"][0]

    assert contact["active_contact_count"] == 1
    assert row["gap"] == pytest.approx(0.0, abs=1.0e-12)
    assert row["pressure"] == pytest.approx(100.0, abs=1.0e-10)
    assert row["complementarity"] < 1.0e-10
    assert result.displacements[result.dofs.index(3, "UZ")] == pytest.approx(-0.1)
    assert result.run_verdict.value == "WARNING"
    assert result.audit is not None
    assert all(check.status != "FAIL" for check in result.audit.checks)
    assert result.audit is not None
    equilibrium = result.audit.equilibrium
    assert equilibrium["free_relative_residual"] < 1.0e-12
    assert equilibrium["force_balance_relative_error"] < 1.0e-12
    assert equilibrium["moment_balance_relative_error"] < 1.0e-12


def test_contact_rejects_slave_projection_outside_master_triangle() -> None:
    data = _model(-1.0)
    data["nodes"][3] = [2.0, 2.0, 0.1]
    model = JsonModelReader().from_dict(data)
    report = MeshValidator().validate(model)

    assert report.status == "FAIL"
    assert "projection lies outside" in " ".join(report.errors)


def test_contact_rejects_non_direct_method_and_mpc_combination() -> None:
    data = _model(-1.0)
    data["analysis"]["method"] = "cg"
    data["multipoint_constraints"] = [
        {
            "terms": [
                {"node": 3, "dof": "UZ", "coefficient": 1.0},
                {"node": 0, "dof": "UZ", "coefficient": -1.0},
            ]
        }
    ]
    report = MeshValidator().validate(JsonModelReader().from_dict(data))

    assert report.status == "FAIL"
    message = " ".join(report.errors)
    assert "direct sparse method" in message
    assert "MPC or RBE" in message


@pytest.mark.parametrize(
    "rotation",
    [
        np.eye(3),
        np.array([[1.0, 0.0, 0.0], [0.0, 0.0, -1.0], [0.0, 1.0, 0.0]]),
        np.array([[0.0, 0.0, 1.0], [0.0, 1.0, 0.0], [-1.0, 0.0, 0.0]]),
    ],
)
def test_contact_is_invariant_for_rotated_master_triangle_orientations(rotation: np.ndarray) -> None:
    """The frozen normal and exact gap constraint must be frame independent."""
    model, normal = _rotated_compression_model(rotation)
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(model))
    contact = result.solver["contact"]["contacts"][0]
    displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)[3]

    assert contact["active"] is True
    assert contact["gap"] == pytest.approx(0.0, abs=1.0e-12)
    assert contact["pressure"] == pytest.approx(100.0, abs=1.0e-10)
    assert normal @ displacement == pytest.approx(-0.1, abs=1.0e-12)
    assert np.linalg.norm(displacement + 0.1 * normal) < 1.0e-12


def test_orthogonal_contact_corner_activates_both_independent_constraints() -> None:
    """A slave entering an orthogonal corner must recover both normal reactions."""
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(_contact_corner_model()))
    contact = result.solver["contact"]
    rows = contact["contacts"]
    displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)[4]

    assert contact["active_contact_count"] == 2
    assert [row["active"] for row in rows] == [True, True]
    assert [row["gap"] for row in rows] == pytest.approx([0.0, 0.0], abs=1.0e-12)
    assert [row["pressure"] for row in rows] == pytest.approx([100.0, 200.0], abs=1.0e-10)
    assert displacement == pytest.approx([-0.1, -0.1, 0.0], abs=1.0e-12)
    assert result.audit is not None
    assert result.audit.equilibrium["free_relative_residual"] < 1.0e-12
    assert result.audit.equilibrium["force_balance_relative_error"] < 1.0e-12


def test_contact_transfers_load_to_a_deformable_master_triangle() -> None:
    """The exact gap must include the barycentric displacement of master nodes."""
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(_deformable_master_model()))
    row = result.solver["contact"]["contacts"][0]
    displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)
    pressure = 0.1 / (1.0 / 1000.0 + 0.375 / 600.0)
    weights = np.array([0.5, 0.25, 0.25])
    master_z = -pressure * weights / 600.0

    assert row["active"] is True
    assert row["gap"] == pytest.approx(0.0, abs=1.0e-12)
    assert row["pressure"] == pytest.approx(pressure, abs=1.0e-10)
    assert displacement[3, 2] == pytest.approx((-200.0 + pressure) / 1000.0, abs=1.0e-12)
    assert displacement[:3, 2] == pytest.approx(master_z, abs=1.0e-12)
    assert result.audit is not None
    assert result.audit.equilibrium["force_balance_relative_error"] < 1.0e-12


def test_contact_transfers_load_to_a_deformable_tet4_master_face() -> None:
    """Master-face displacement from a TET4 must participate in the closed gap."""
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(_deformable_tet4_master_model()))
    row = result.solver["contact"]["contacts"][0]
    displacement = np.asarray(result.displacements, dtype=float).reshape(-1, 3)

    assert row["active"] is True
    assert row["gap"] == pytest.approx(0.0, abs=1.0e-12)
    assert row["pressure"] > 0.0
    assert displacement[4, 2] < -0.1
    assert np.max(np.abs(displacement[:3, 2])) > 0.0
    assert result.audit is not None
    assert result.audit.equilibrium["free_relative_residual"] < 1.0e-12


def test_contact_selects_the_compatible_triangle_on_a_bounded_master_surface() -> None:
    """Only the initially compatible facet must constrain a shared slave node."""
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(_master_surface_model()))
    row = result.solver["contact"]["contacts"][0]

    assert row["active"] is True
    assert row["master_face_count"] == 2
    assert row["master_face_index"] == 1
    assert row["master_nodes"] == [1, 3, 2]
    assert row["gap"] == pytest.approx(0.0, abs=1.0e-12)
    assert row["pressure"] == pytest.approx(100.0, abs=1.0e-10)
    assert result.displacements[result.dofs.index(4, "UZ")] == pytest.approx(-0.1)


def test_contact_rejects_ambiguous_or_invalid_master_surface_json() -> None:
    data = _master_surface_model()
    contact = data["contacts"][0]
    contact["master_nodes"] = [0, 1, 2]
    contact["master_faces"] = [[0, 1, 2], [1, 3, 2]]
    with pytest.raises(ValueError, match="exactly one of master_nodes or master_faces"):
        JsonModelReader().from_dict(data)

    data = _master_surface_model()
    data["contacts"][0]["master_faces"] = [[0, 1, 2], [0, 1, 2]]
    with pytest.raises(ValueError, match="duplicates an earlier master face"):
        JsonModelReader().from_dict(data)


def test_updated_contact_search_switches_to_the_face_under_the_deformed_slave() -> None:
    """The bounded geometric iteration must update an initially different facet."""
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(_updated_master_surface_model()))
    details = result.solver["contact"]
    row = details["contacts"][0]

    assert details["search_mode"] == "updated_initial_geometry_iteration"
    assert details["search_iteration_count"] >= 2
    assert row["master_face_index"] == 1
    assert row["gap"] == pytest.approx(0.0, abs=1.0e-12)
    assert result.displacements[result.dofs.index(4, "UX")] == pytest.approx(0.6, abs=1.0e-12)


def test_updated_contact_search_rejects_frictional_pairs() -> None:
    data = _updated_master_surface_model()
    data["contacts"][0]["friction_coefficient"] = 0.2
    data["contacts"][0]["tangential_stiffness"] = 1000.0
    with pytest.raises(MeshValidationError, match="not yet available with frictional contact"):
        LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    report = MeshValidator().validate(JsonModelReader().from_dict(data))
    assert report.status == "FAIL"
    assert "not yet available with frictional contact" in " ".join(report.errors)


@pytest.mark.parametrize(
    ("parameter", "value", "message"),
    [
        ("contact_max_iterations", 5.5, "positive integer"),
        ("contact_search_max_iterations", 0, "positive integer"),
        ("contact_search_tolerance", float("nan"), "positive finite number"),
    ],
)
def test_updated_contact_search_rejects_invalid_numerical_parameters(
    parameter: str, value: object, message: str
) -> None:
    data = _updated_master_surface_model()
    data["analysis"][parameter] = value
    model = JsonModelReader().from_dict(data)

    report = MeshValidator().validate(model)
    assert report.status == "FAIL"
    assert message in " ".join(report.errors)
    with pytest.raises(MeshValidationError, match=message):
        LinearStaticSolver().solve(model)


def test_updated_contact_search_recomputes_the_normal_on_a_folded_surface() -> None:
    """A facet switch must also use the normal of the newly selected facet."""
    from solveur.verification.contact_master_surface import _folded_updated_model_data

    result = LinearStaticSolver().solve(JsonModelReader().from_dict(_folded_updated_model_data()))
    row = result.solver["contact"]["contacts"][0]

    assert row["master_face_index"] == 1
    assert row["gap"] == pytest.approx(0.0, abs=1.0e-12)
    assert row["normal"] == pytest.approx([-0.4082482904638631, -0.4082482904638631, 0.8164965809277261])
    assert result.solver["contact"]["search_history"][0]["master_face_indices"] == [0]
    assert result.solver["contact"]["search_history"][1]["master_face_indices"] == [1]


def _rotated_compression_model(rotation: np.ndarray) -> tuple[dict[str, object], np.ndarray]:
    local_nodes = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]])
    nodes = local_nodes @ rotation.T
    normal = rotation @ np.array([0.0, 0.0, 1.0])
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": nodes.tolist(),
        "elements": [],
        "materials": {},
        "fixed_dofs": [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(3)],
        "springs": [{"node_a": 3, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0, 1000.0, 1000.0]}],
        "loads": [{"node": 3, "dof": dof, "value": float(-200.0 * normal[index])} for index, dof in enumerate(("UX", "UY", "UZ"))],
        "contacts": [{"name": "rotated_plane", "slave_node": 3, "master_nodes": [0, 1, 2]}],
    }, normal


def _contact_corner_model() -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": [
            [0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.1, 0.1, 0.1],
        ],
        "elements": [],
        "materials": {},
        "fixed_dofs": [{"node": index, "dofs": ["UX", "UY", "UZ"]} for index in range(4)],
        "springs": [{"node_a": 4, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0, 1000.0, 1000.0]}],
        "loads": [{"node": 4, "dof": "UX", "value": -200.0}, {"node": 4, "dof": "UY", "value": -300.0}],
        "contacts": [
            {"name": "x_plane", "slave_node": 4, "master_nodes": [0, 1, 2]},
            {"name": "y_plane", "slave_node": 4, "master_nodes": [0, 2, 3]},
        ],
    }


def _deformable_master_model() -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]],
        "elements": [],
        "materials": {},
        "springs": [
            {"node_a": node, "dofs": ["UX", "UY", "UZ"], "stiffness": [600.0, 600.0, 600.0]}
            for node in range(3)
        ] + [{"node_a": 3, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0, 1000.0, 1000.0]}],
        "loads": [{"node": 3, "dof": "UZ", "value": -200.0}],
        "contacts": [{"name": "elastic_master", "slave_node": 3, "master_nodes": [0, 1, 2]}],
    }


def _deformable_tet4_master_model() -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": [[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.25, 0.25, -1.0], [0.25, 0.25, 0.1]],
        "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "elastic"}],
        "materials": {"elastic": {"type": "isotropic_3d", "E": 100000.0, "nu": 0.3}},
        "fixed_dofs": [
            *[{"node": node, "dofs": ["UX", "UY"]} for node in range(3)],
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
            {"node": 4, "dofs": ["UX", "UY"]},
        ],
        "springs": [{"node_a": 4, "dofs": ["UZ"], "stiffness": 1000.0}],
        "loads": [{"node": 4, "dof": "UZ", "value": -200.0}],
        "contacts": [{"name": "tet4_master", "slave_node": 4, "master_nodes": [0, 2, 1]}],
    }


def _master_surface_model() -> dict[str, object]:
    return {
        "analysis": {"type": "linear_static", "method": "direct", "contact_max_iterations": 12},
        "nodes": [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.75, 0.5, 0.1],
        ],
        "elements": [],
        "materials": {},
        "fixed_dofs": [
            *[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)],
            {"node": 4, "dofs": ["UX", "UY"]},
        ],
        "springs": [{"node_a": 4, "dofs": ["UZ"], "stiffness": 1000.0}],
        "loads": [{"node": 4, "dof": "UZ", "value": -200.0}],
        "contacts": [{"name": "surface", "slave_node": 4, "master_faces": [[0, 1, 2], [1, 3, 2]]}],
    }


def _updated_master_surface_model() -> dict[str, object]:
    return {
        "analysis": {
            "type": "linear_static",
            "method": "direct",
            "contact_max_iterations": 12,
            "contact_search_mode": "updated",
            "contact_search_max_iterations": 8,
        },
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [1.0, 1.0, 0.0], [0.25, 0.5, 0.1]],
        "elements": [],
        "materials": {},
        "fixed_dofs": [
            *[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in range(4)],
            {"node": 4, "dofs": ["UY"]},
        ],
        "springs": [{"node_a": 4, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0, 1000.0, 1000.0]}],
        "loads": [{"node": 4, "dof": "UX", "value": 600.0}, {"node": 4, "dof": "UZ", "value": -200.0}],
        "contacts": [{"name": "updated_surface", "slave_node": 4, "master_faces": [[0, 1, 2], [1, 3, 2]]}],
    }
