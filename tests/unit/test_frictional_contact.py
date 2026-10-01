"""Mechanical checks for the regularized Coulomb contact extension."""

from __future__ import annotations

import pytest

from solveur.core.errors import InputValidationError, MeshValidationError
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


def test_frictional_contact_accepted_state_restart_matches_uninterrupted_path(tmp_path, monkeypatch) -> None:
    data = _model(horizontal_load=200.0, vertical_load=-200.0)
    data["analysis"]["contact_load_history"] = [
        [0.0, 1.0], [0.2, 1.0], [1.0, 1.0], [0.2, 1.0],
        [-0.2, 1.0], [-1.0, 1.0], [0.0, 1.0],
    ]
    uninterrupted = LinearStaticSolver().solve(JsonModelReader().from_dict(data))

    checkpoint = tmp_path / "friction_step4.json"
    interrupted_data = {**data, "analysis": {**data["analysis"], "contact_checkpoint_path": str(checkpoint)}}
    from solveur.contact.solver import FrictionlessActiveSetSolver

    original = FrictionlessActiveSetSolver._solve_friction_increment

    def stop_before_step_five(*args, **kwargs):
        if kwargs.get("step") == 5:
            raise RuntimeError("test interruption after accepted step four")
        return original(*args, **kwargs)

    monkeypatch.setattr(FrictionlessActiveSetSolver, "_solve_friction_increment", staticmethod(stop_before_step_five))
    with pytest.raises(RuntimeError, match="accepted step four"):
        LinearStaticSolver().solve(JsonModelReader().from_dict(interrupted_data))
    assert checkpoint.is_file()
    monkeypatch.undo()

    resumed_data = {
        **data,
        "analysis": {
            **data["analysis"],
            "contact_checkpoint_path": str(checkpoint),
            "contact_restart_from": str(checkpoint),
        },
    }
    resumed = LinearStaticSolver().solve(JsonModelReader().from_dict(resumed_data))
    assert resumed.displacements == pytest.approx(uninterrupted.displacements, abs=1.0e-12)
    assert resumed.solver["contact"]["restart"]["restarted_from_step"] == 4
    assert resumed.solver["contact"]["restart"]["accepted_steps_written"] == 3
    assert resumed.solver["contact"]["cumulative_local_dissipation"] == pytest.approx(
        uninterrupted.solver["contact"]["cumulative_local_dissipation"], abs=1.0e-12
    )


def test_frictional_contact_restart_rejects_tampered_checkpoint(tmp_path, monkeypatch) -> None:
    data = _model(horizontal_load=200.0, vertical_load=-200.0)
    data["analysis"]["contact_load_history"] = [
        [0.0, 1.0], [0.2, 1.0], [1.0, 1.0], [0.2, 1.0],
        [-0.2, 1.0], [-1.0, 1.0], [0.0, 1.0],
    ]
    checkpoint = tmp_path / "friction_step4.json"
    from solveur.contact.solver import FrictionlessActiveSetSolver

    original = FrictionlessActiveSetSolver._solve_friction_increment

    def stop_before_step_five(*args, **kwargs):
        if kwargs.get("step") == 5:
            raise RuntimeError("test interruption")
        return original(*args, **kwargs)

    monkeypatch.setattr(FrictionlessActiveSetSolver, "_solve_friction_increment", staticmethod(stop_before_step_five))
    with pytest.raises(RuntimeError):
        LinearStaticSolver().solve(
            JsonModelReader().from_dict(
                {**data, "analysis": {**data["analysis"], "contact_checkpoint_path": str(checkpoint)}}
            )
        )
    monkeypatch.undo()
    payload = checkpoint.read_text(encoding="utf-8").replace("\"model_signature\": \"", "\"model_signature\": \"tampered-")
    checkpoint.write_text(payload, encoding="utf-8")
    resumed = {
        **data,
        "analysis": {
            **data["analysis"],
            "contact_restart_from": str(checkpoint),
        },
    }
    with pytest.raises(InputValidationError, match="does not match"):
        LinearStaticSolver().solve(JsonModelReader().from_dict(resumed))


def test_frictional_contact_restart_missing_checkpoint_fails_closed() -> None:
    data = _model(horizontal_load=2.0, vertical_load=-200.0)
    data["analysis"]["contact_restart_from"] = "missing-friction-checkpoint.json"
    with pytest.raises(InputValidationError, match="checkpoint is unreadable"):
        LinearStaticSolver().solve(JsonModelReader().from_dict(data))


def test_frictional_contact_negative_and_nonfinite_coefficients_fail_closed() -> None:
    for value in (-0.1, float("nan"), float("inf")):
        data = _model(horizontal_load=2.0, vertical_load=-200.0)
        data["contacts"][0]["friction_coefficient"] = value
        with pytest.raises(InputValidationError, match="non-negative finite"):
            JsonModelReader().from_dict(data)


def test_updated_search_with_friction_is_explicitly_unsupported() -> None:
    data = _model(horizontal_load=2.0, vertical_load=-200.0)
    data["analysis"]["contact_search_mode"] = "updated"
    model = JsonModelReader().from_dict(data)
    with pytest.raises(MeshValidationError, match="Updated contact search is not yet available with frictional contact"):
        LinearStaticSolver().solve(model)
