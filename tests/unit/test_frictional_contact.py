"""Mechanical checks for the regularized Coulomb contact extension."""

from __future__ import annotations

import pytest

from solveur.core.errors import InputValidationError
from solveur.core.solver import LinearStaticSolver
from solveur.io.json_reader import JsonModelReader


def _model(*, horizontal_load: float, vertical_load: float, friction: float = 0.5) -> dict[str, object]:
    return {
        "analysis": {
            "type": "linear_static",
            "method": "direct",
            "contact_max_iterations": 16,
            "contact_friction_tolerance": 1.0e-11,
        },
        "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.25, 0.25, 0.1]],
        "elements": [],
        "materials": {},
        "fixed_dofs": [
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UY"]},
        ],
        "springs": [{"node_a": 3, "dofs": ["UX", "UZ"], "stiffness": [1000.0, 1000.0]}],
        "loads": [
            {"node": 3, "dof": "UX", "value": horizontal_load},
            {"node": 3, "dof": "UZ", "value": vertical_load},
        ],
        "contacts": [
            {
                "name": "rough_plane",
                "slave_node": 3,
                "master_nodes": [0, 1, 2],
                "friction_coefficient": friction,
                "tangential_stiffness": 10000.0,
            }
        ],
    }


def test_frictional_contact_stays_open_under_separation() -> None:
    result = LinearStaticSolver().solve(
        JsonModelReader().from_dict(_model(horizontal_load=100.0, vertical_load=20.0))
    )
    row = result.solver["contact"]["contacts"][0]

    assert row["tangential_state"] == "open"
    assert row["pressure"] == pytest.approx(0.0)
    assert row["tangential_force_norm"] == pytest.approx(0.0)
    assert row["gap"] == pytest.approx(0.12)


def test_frictional_contact_sticks_below_the_coulomb_limit() -> None:
    result = LinearStaticSolver().solve(
        JsonModelReader().from_dict(_model(horizontal_load=2.0, vertical_load=-200.0))
    )
    row = result.solver["contact"]["contacts"][0]

    assert row["tangential_state"] == "stick"
    assert row["gap"] == pytest.approx(0.0, abs=1.0e-12)
    assert row["pressure"] == pytest.approx(100.0)
    assert row["tangential_force_norm"] < row["friction_limit"]
    assert row["tangential_force_norm"] == pytest.approx(20.0 / 11.0)


def test_frictional_contact_slides_at_the_coulomb_bound_and_dissipates() -> None:
    result = LinearStaticSolver().solve(
        JsonModelReader().from_dict(_model(horizontal_load=200.0, vertical_load=-200.0))
    )
    row = result.solver["contact"]["contacts"][0]

    assert row["tangential_state"] == "slip"
    assert row["friction_limit"] == pytest.approx(50.0)
    assert row["tangential_force_norm"] == pytest.approx(50.0)
    assert row["tangential_force"][0] * row["tangential_displacement"][0] > 0.0
    assert result.displacements[result.dofs.index(3, "UX")] == pytest.approx(0.15)
    assert result.audit is not None
    assert all(check.status != "FAIL" for check in result.audit.checks)


def test_positive_friction_requires_a_tangential_regularization_stiffness() -> None:
    data = _model(horizontal_load=0.0, vertical_load=-1.0)
    del data["contacts"][0]["tangential_stiffness"]

    with pytest.raises(InputValidationError, match="tangential_stiffness"):
        JsonModelReader().from_dict(data)


def test_contact_load_history_preserves_slip_memory_and_positive_dissipation() -> None:
    data = _model(horizontal_load=200.0, vertical_load=-200.0)
    data["analysis"]["contact_load_history"] = [
        [0.0, 1.0], [0.2, 1.0], [1.0, 1.0], [0.2, 1.0],
        [-0.2, 1.0], [-1.0, 1.0], [0.0, 1.0],
    ]
    result = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    contact = result.solver["contact"]
    steps = contact["load_steps"]
    forces = [step["tangential_forces"][0][0] for step in steps]

    assert contact["cumulative_local_dissipation"] > 0.0
    assert any(value > 0.0 for value in forces)
    assert any(value < 0.0 for value in forces)
    assert any(abs(step["slip_references"][0][0]) > 0.0 for step in steps)
    assert all(step["iteration_count"] <= 20 for step in steps)


def test_constant_normal_pressure_ramp_is_independent_of_the_contact_step_count() -> None:
    responses = []
    for count in (1, 2, 4, 8, 16):
        data = _model(horizontal_load=200.0, vertical_load=-200.0)
        data["analysis"]["contact_load_history"] = [[index / count, 1.0] for index in range(1, count + 1)]
        result = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
        row = result.solver["contact"]["contacts"][0]
        responses.append(
            (
                result.displacements[result.dofs.index(3, "UX")],
                row["tangential_force"][0],
                result.solver["contact"]["cumulative_local_dissipation"],
            )
        )

    for response in responses[1:]:
        assert response == pytest.approx(responses[0], abs=1.0e-12)
