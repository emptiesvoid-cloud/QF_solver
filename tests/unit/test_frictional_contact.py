"""Mechanical checks for the regularized Coulomb contact extension."""

from __future__ import annotations

import json

import numpy as np
import pytest

from solveur.core.errors import InputValidationError, MeshValidationError
from solveur.core.solver import LinearStaticSolver
from solveur.contact.solver import FrictionlessActiveSetSolver
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


@pytest.mark.parametrize(
    "normal_increment,tangential_load,expected",
    [(-5e-8, 1e-6, "open"), (5e-8, 1e-8, "stick"), (5e-8, 1e-6, "slip")],
)
def test_spring_contact_switches_near_analytical_closure(
    normal_increment: float, tangential_load: float, expected: str
) -> None:
    # Free axial closure occurs at 100 N for a 0.1 m gap and a 1000 N/m spring.
    normal_load = -(100.0 + normal_increment)
    data = _model(horizontal_load=tangential_load, vertical_load=normal_load)
    data["contacts"][0]["gap_tolerance"] = 1e-12
    model = JsonModelReader().from_dict(data)
    result = LinearStaticSolver().solve(model)
    row = result.solver["contact"]["contacts"][0]
    pressure = max(normal_increment, 0.0)
    gap = max(-normal_increment / 1000.0, 0.0)
    force = {
        "open": 0.0, "stick": tangential_load * (10.0 / 11.0), "slip": 0.5 * pressure
    }[expected]

    assert row["tangential_state"] == expected
    assert row["pressure"] == pytest.approx(pressure, abs=3e-14)
    assert row["gap"] == pytest.approx(gap, abs=3e-17)
    assert row["tangential_force_norm"] == pytest.approx(force, abs=3e-14)
    assert row["pressure"] * row["gap"] == pytest.approx(0.0, abs=1e-20)
    assert result.displacements[result.dofs.index(3, "UX")] * 1000.0 + force == pytest.approx(
        tangential_load, abs=3e-14
    )
    assert result.displacements[result.dofs.index(3, "UZ")] * 1000.0 - pressure == pytest.approx(
        normal_load, rel=0.0, abs=3e-14
    )


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


@pytest.mark.parametrize("scale", [1.0e-3, 1.0, 1.0e3])
@pytest.mark.parametrize(
    "open_history",
    [
        [[1.0, -1.0], [0.0, -1.0]],
        [[1.0, -1.0], [0.5, -1.0], [0.0, -1.0]],
    ],
    ids=["single-open-displacement", "intermediate-open-motion"],
)
def test_open_slip_pair_recloses_without_replaying_open_motion(
    monkeypatch, scale: float, open_history: list[list[float]]
) -> None:
    """Only post-reclosure tangential loading can restore friction force."""
    data = _model(horizontal_load=200.0 * scale, vertical_load=-200.0 * scale)
    data["springs"] = [{"node_a": 3, "dofs": ["UX", "UZ"], "stiffness": [1000.0 * scale, 1000.0 * scale]}]
    data["contacts"][0]["tangential_stiffness"] = 10000.0 * scale
    history = [
        [0.0, 1.0],  # Close in compression without tangential loading.
        [1.0, 1.0],  # Slide at the Coulomb cap.
        *open_history,
        [0.0, 1.0],  # Reclose with no tangential load.
        [0.025, 1.0],  # Apply new tangential loading after closure.
    ]
    data["analysis"]["contact_load_history"] = history
    accepted_states = []
    original_solve_increment = FrictionlessActiveSetSolver._solve_friction_increment

    def observe_increment(*args, **kwargs):
        state = original_solve_increment(*args, **kwargs)
        accepted_states.append(state)
        return state

    monkeypatch.setattr(
        FrictionlessActiveSetSolver,
        "_solve_friction_increment",
        staticmethod(observe_increment),
    )

    result = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    steps = result.solver["contact"]["load_steps"]
    close_index = 2 + len(open_history)
    close = steps[close_index]
    reload = steps[close_index + 1]
    force_tolerance = max(scale, 1.0) * 2.0e-12

    assert len(accepted_states) == len(history)
    assert steps[0]["states"] == ["stick"]
    assert steps[1]["states"] == ["slip"]
    assert all(step["states"] == ["open"] for step in steps[2:close_index])
    assert all(step["tangential_forces"] == [[0.0, 0.0]] for step in steps[2:close_index])
    assert close["states"] == ["stick"]
    assert close["tangential_forces"] == [[0.0, 0.0]]
    assert close["slip_references"][0] == pytest.approx([0.0, 0.0], abs=1.0e-14)
    assert reload["states"] == ["stick"]
    assert reload["tangential_forces"][0][0] == pytest.approx((50.0 / 11.0) * scale, abs=force_tolerance)
    assert reload["tangential_forces"][0][1] == pytest.approx(0.0, abs=force_tolerance)
    assert result.displacements[result.dofs.index(3, "UX")] == pytest.approx(
        5.0 / 11000.0, rel=1.0e-11, abs=1.0e-14
    )

    for state, (tangential_factor, normal_factor) in zip(accepted_states, history, strict=True):
        tangential_displacement = state.displacement[result.dofs.index(3, "UX")]
        normal_displacement = state.displacement[result.dofs.index(3, "UZ")]
        tangential_force = state.tangential_forces[0, 0]
        pressure = state.pressures[0]
        gap = state.gaps[0]
        assert 1000.0 * scale * tangential_displacement + tangential_force == pytest.approx(
            200.0 * scale * tangential_factor, rel=2.0e-11, abs=1.0e-13
        )
        assert 1000.0 * scale * normal_displacement - pressure == pytest.approx(
            -200.0 * scale * normal_factor, rel=2.0e-11, abs=1.0e-13
        )
        if state.states == ("open",):
            assert gap > 0.0
            assert pressure == 0.0
            assert tangential_force == 0.0
            np.testing.assert_array_equal(state.slip_references[0], state.tangential_displacements[0])
        else:
            assert gap == pytest.approx(0.0, abs=1.0e-12)
            assert pressure >= 0.0
            assert abs(gap * pressure) / max(abs(pressure), 1.0) <= 1.0e-10


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


@pytest.mark.parametrize("open_tangent", [0.0, 1.0])
def test_open_contact_checkpoint_restart_and_failed_increment_are_transactional(tmp_path, monkeypatch, open_tangent):
    from solveur.core.errors import NumericalConvergenceError, NonlinearFailureReason

    data = _model(horizontal_load=200.0, vertical_load=-200.0)
    data["analysis"]["contact_load_history"] = [
        [0.0, 1.0], [1.0, 1.0], [open_tangent, -1.0], [0.0, 1.0], [0.025, 1.0],
    ]
    uninterrupted = LinearStaticSolver().solve(JsonModelReader().from_dict(data))
    checkpoint = tmp_path / "open.json"
    interrupted = {**data, "analysis": {**data["analysis"], "contact_checkpoint_path": str(checkpoint)}}
    original = FrictionlessActiveSetSolver._solve_friction_increment

    def fail_after_mutating_trial(*args, **kwargs):
        if kwargs.get("step") == 4:
            args[5][:] = 12345.0
            raise NumericalConvergenceError("injected rejected increment", reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE)
        return original(*args, **kwargs)

    monkeypatch.setattr(FrictionlessActiveSetSolver, "_solve_friction_increment", staticmethod(fail_after_mutating_trial))
    with pytest.raises(NumericalConvergenceError, match="injected rejected increment"):
        LinearStaticSolver().solve(JsonModelReader().from_dict(interrupted))
    saved = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert saved["completed_step"] == 3
    assert saved["tangential_states"] == ["open"]
    assert 12345.0 not in saved["slip_references"][0]
    monkeypatch.undo()

    resumed_data = {**data, "analysis": {**data["analysis"], "contact_restart_from": str(checkpoint)}}
    resumed = LinearStaticSolver().solve(JsonModelReader().from_dict(resumed_data))
    assert resumed.displacements == pytest.approx(uninterrupted.displacements, abs=1.0e-12)
    np.testing.assert_allclose(resumed.solver["contact"]["slip_references"], uninterrupted.solver["contact"]["slip_references"], atol=1.0e-12)
    assert resumed.solver["contact"]["cumulative_local_dissipation"] == pytest.approx(uninterrupted.solver["contact"]["cumulative_local_dissipation"])

    zero_capacity = {**saved, "active_contacts": [0], "pressures": [0.0], "gaps": [0.0], "multipliers": [0.0]}
    checkpoint.write_text(json.dumps(zero_capacity), encoding="utf-8")
    at_zero = LinearStaticSolver().solve(JsonModelReader().from_dict(resumed_data))
    np.testing.assert_allclose(at_zero.displacements, resumed.displacements, atol=1.0e-12)

    saved["schema_version"] = 1
    checkpoint.write_text(json.dumps(saved), encoding="utf-8")
    with pytest.raises(InputValidationError, match="previous open-contact memory"):
        LinearStaticSolver().solve(JsonModelReader().from_dict(resumed_data))


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
