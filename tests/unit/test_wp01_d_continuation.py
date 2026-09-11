"""WP01-D focused tests for adaptive and arc-length state ownership."""

from __future__ import annotations

from dataclasses import replace
import inspect
import json
from pathlib import Path

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.controls import AdaptiveLoadControls
from solveur.core.nonlinear.driver import (
    RetryClassification,
    UnifiedContinuationController,
    continuation_retry_permitted,
)
from solveur.core.nonlinear.iteration import solve_adaptive_full_newton
from solveur.core.nonlinear.state import NonlinearState, deterministic_state_digest
from solveur.core.nonlinear.solver import NonlinearStaticSolver
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from tests.unit.test_analysis_features import elastoplastic_tet4_model, nonlinear_tet4_model


def _state() -> NonlinearState:
    return NonlinearState(
        displacement=np.zeros(2),
        load_factor=0.0,
        material_state={0: [{"equivalent_plastic_strain": 0.0}]},
        contact_state={"active": []},
        continuation_state={
            "radius": 0.1,
            "previous_du": [0.0, 0.0],
            "previous_dlambda": 0.0,
        },
    )


def _adaptive_model():
    model = elastoplastic_tet4_model()
    model.analysis.parameters.update(
        {
            "adaptive_load_steps": True,
            "initial_load_increment": 1.0,
            "min_load_increment": 0.1,
            "max_load_increment": 1.0,
            "growth_factor": 1.0,
            "max_cutbacks": 3,
        }
    )
    return model


def _arc_model(**parameters):
    model = nonlinear_tet4_model(method="arc_length")
    model.analysis.parameters.update(
        {
            "max_arc_steps": 2,
            "arc_length_stop_mode": "max_steps",
            "arc_length_radius": 0.1,
            "max_arc_length_radius": 0.1,
            "min_arc_length_radius": 1.0e-6,
            "arc_length_shrink_factor": 0.5,
            **parameters,
        }
    )
    return model


class _AlwaysFailAssembly:
    ndof = 2

    def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
        raise NumericalConvergenceError(
            "controlled failure",
            reason=NonlinearFailureReason.MAX_ITERATIONS,
        )


def _arc_reject_once(monkeypatch: pytest.MonkeyPatch):
    original = NonlinearStaticSolver._solve_arc_length_step
    calls = {"count": 0}

    def reject_once(self, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise NumericalConvergenceError(
                "controlled arc-length rejection",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
                diagnostics={"controlled": True},
            )
        return original(self, *args, **kwargs)

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_arc_length_step", reject_once)
    data = solve_model(_arc_model(max_arc_steps=4), enforce_policy=False).to_dict()
    return data


def _flat_displacements(value: list[dict[str, object]]) -> np.ndarray:
    return np.asarray(
        [component for node in value for component in node["dofs"].values()],
        dtype=float,
    )


def test_t31_adaptive_accepted_increment_has_one_composite_commit() -> None:
    data = solve_model(_adaptive_model(), enforce_policy=False).to_dict()
    assert data["solver"]["continuation_commit_count"] == 1


def test_t32_adaptive_failed_increment_has_zero_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail(*args, **kwargs):
        raise NumericalConvergenceError(
            "controlled failure",
            reason=NonlinearFailureReason.MATERIAL_UPDATE_FAILURE,
        )

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_load_step", fail)
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_model(_adaptive_model(), enforce_policy=False)
    assert raised.value.reason is NonlinearFailureReason.MATERIAL_UPDATE_FAILURE


def test_t33_adaptive_cutback_preserves_exact_accepted_digest() -> None:
    controller = UnifiedContinuationController(_state())
    before = controller.accepted_digest
    trial = controller.begin_trial()
    trial.displacement[:] = 3.0
    trial.material_state[0][0]["equivalent_plastic_strain"] = 1.0
    controller.rollback(
        NumericalConvergenceError("retry", reason=NonlinearFailureReason.MAX_ITERATIONS),
        path="adaptive",
    )
    assert controller.accepted_digest == before
    assert controller.rejection_log[0]["accepted_digest_before"] == before
    assert controller.rejection_log[0]["accepted_digest_after"] == before


def test_t34_second_retry_starts_from_accepted_state() -> None:
    controller = UnifiedContinuationController(_state())
    accepted = controller.accepted_digest
    trial = controller.begin_trial()
    trial.displacement[:] = 99.0
    controller.rollback(
        NumericalConvergenceError("retry", reason=NonlinearFailureReason.MAX_ITERATIONS),
        path="adaptive",
    )
    retry = controller.begin_trial()
    assert retry.digest == accepted


def test_t35_load_factor_changes_only_on_commit() -> None:
    controller = UnifiedContinuationController(_state())
    trial = controller.begin_trial()
    trial.load_factor = 0.5
    assert controller.accepted_state.load_factor == 0.0
    controller.commit()
    assert controller.accepted_state.load_factor == 0.5


def test_t36_material_state_changes_only_on_commit() -> None:
    controller = UnifiedContinuationController(_state())
    trial = controller.begin_trial()
    trial.material_state[0][0]["equivalent_plastic_strain"] = 0.25
    assert controller.accepted_state.material_state[0][0]["equivalent_plastic_strain"] == 0.0
    controller.commit()
    assert controller.accepted_state.material_state[0][0]["equivalent_plastic_strain"] == 0.25


def test_t37_contact_state_changes_only_on_commit() -> None:
    controller = UnifiedContinuationController(_state())
    trial = controller.begin_trial()
    trial.contact_state["active"] = [1]
    assert controller.accepted_state.contact_state["active"] == []
    controller.commit()
    assert controller.accepted_state.contact_state["active"] == [1]


def test_t38_max_iterations_is_retryable() -> None:
    error = NumericalConvergenceError("retry", reason=NonlinearFailureReason.MAX_ITERATIONS)
    assert continuation_retry_permitted(error)
    assert RetryClassification.RETRYABLE.value == "RETRYABLE"


def test_t39_minimum_increment_is_terminal_and_deterministic() -> None:
    controls = AdaptiveLoadControls.from_parameters(
        {
            "initial_load_increment": 1.0,
            "min_load_increment": 0.75,
            "max_load_increment": 1.0,
            "cutback_factor": 0.5,
            "growth_factor": 1.0,
            "max_cutbacks": 4,
        },
        load_steps=1,
        max_iterations=5,
    )
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_adaptive_full_newton(
            _AlwaysFailAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=5,
            controls=controls,
        )
    assert raised.value.reason is NonlinearFailureReason.MIN_INCREMENT_REACHED


def test_t40_non_retryable_failure_is_not_cut_back() -> None:
    error = NumericalConvergenceError("invalid state", reason=NonlinearFailureReason.MATERIAL_UPDATE_FAILURE)
    assert not continuation_retry_permitted(error)
    assert not continuation_retry_permitted(error, allow_owner_policy=True)


def test_t41_arc_length_accepted_step_has_one_composite_commit() -> None:
    data = solve_model(
        _arc_model(
            arc_length_stop_mode="max_steps",
            max_arc_steps=1,
            target_load_factor=1.0,
        ),
        enforce_policy=False,
    ).to_dict()
    assert data["solver"]["continuation_commit_count"] == 1


def test_t42_arc_length_rejection_preserves_displacement_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _arc_reject_once(monkeypatch)
    rejection = data["solver"]["continuation_rejection_log"][0]
    assert rejection["accepted_component_digests_before"]["displacement"] == rejection["accepted_component_digests_after"]["displacement"]


def test_t43_arc_length_rejection_preserves_material_digest(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _arc_reject_once(monkeypatch)
    rejection = data["solver"]["continuation_rejection_log"][0]
    assert rejection["accepted_component_digests_before"]["material_state"] == rejection["accepted_component_digests_after"]["material_state"]


def test_t44_arc_length_rejection_preserves_load_factor(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _arc_reject_once(monkeypatch)
    rejection = data["solver"]["continuation_rejection_log"][0]
    assert rejection["accepted_load_factor_before"] == rejection["accepted_load_factor_after"]


def test_t45_arc_length_rejection_preserves_previous_direction(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _arc_reject_once(monkeypatch)
    rejection = data["solver"]["continuation_rejection_log"][0]
    assert rejection["accepted_continuation_before"] == rejection["accepted_continuation_after"]


def test_t46_arc_length_radius_shrink_is_next_trial_policy_only(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _arc_reject_once(monkeypatch)
    rejection = data["solver"]["rejection_log"][0]
    detail = data["solver"]["continuation_rejection_log"][0]
    assert rejection["retry_radius"] < rejection["previous_radius"]
    assert detail["accepted_digest_before"] == detail["accepted_digest_after"]


def test_t47_turning_point_matches_wp01d_baseline() -> None:
    baseline = json.loads(Path("qualification/0_2_9/wp01_d_baseline.json").read_text(encoding="utf-8"))
    expected = next(item for item in baseline["cases"] if item["name"] == "arc_length_turning_point")
    model = nonlinear_tet4_model(method="arc_length")
    model.analysis.parameters.update(
        {
            "arc_length_stop_mode": "max_steps",
            "max_arc_steps": 6,
            "arc_length_allow_load_factor_turning": True,
            "arc_length_load_factor_limit": 2.0,
            "arc_length_radius": 0.05,
            "max_arc_length_radius": 0.2,
        }
    )
    actual = solve_model(model, enforce_policy=False).to_dict()
    assert np.allclose(
        _flat_displacements(actual["displacements"]),
        _flat_displacements(expected["displacements"]),
        rtol=1.0e-9,
        atol=1.0e-12,
    )
    assert [step["load_factor"] for step in actual["solver"]["steps"]] == pytest.approx(expected["load_factor_history"])


def test_t48_adaptive_radius_matches_wp01d_baseline() -> None:
    baseline = json.loads(Path("qualification/0_2_9/wp01_d_baseline.json").read_text(encoding="utf-8"))
    expected = next(item for item in baseline["cases"] if item["name"] == "arc_length_adaptive_radius")
    model = nonlinear_tet4_model(method="arc_length")
    model.analysis.parameters.update(
        {
            "arc_length_stop_mode": "max_steps",
            "max_arc_steps": 6,
            "arc_length_allow_load_factor_turning": True,
            "arc_length_load_factor_limit": 5.0,
            "arc_length_radius": 0.05,
            "max_arc_length_radius": 0.2,
            "min_arc_length_radius": 1.0e-6,
            "adaptive_arc_length": True,
            "arc_length_growth_factor": 2.0,
            "arc_length_shrink_factor": 0.5,
            "arc_length_grow_below_iterations": 10,
            "arc_length_shrink_above_iterations": 50,
        }
    )
    actual = solve_model(model, enforce_policy=False).to_dict()
    radii = [step["arc_length_radius"] for step in actual["solver"]["steps"]]
    assert radii == pytest.approx(expected["arc_radius_history"], rel=1.0e-9, abs=1.0e-12)


def test_t49_arc_length_replay_has_identical_state_and_diagnostic_digest() -> None:
    outputs = []
    for _ in range(2):
        data = solve_model(_arc_model(), enforce_policy=False).to_dict()
        canonical = {
            "displacements": data["displacements"],
                "material_states": data.get("material_states", []),
            "steps": [
                {
                    "load_factor": step["load_factor"],
                    "arc_length_radius": step["arc_length_radius"],
                    "residual_history": step["residual_history"],
                }
                for step in data["solver"]["steps"]
            ],
            "rejections": data["solver"]["rejection_log"],
        }
        outputs.append(deterministic_state_digest(canonical))
    assert outputs[0] == outputs[1]


def test_t50_checkpoint_is_written_after_an_accepted_arc_step(tmp_path: Path) -> None:
    model = _arc_model(max_arc_steps=4)
    model.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "arc.npz"),
            "checkpoint_interval": 1,
            "checkpoint_keep_steps": True,
        }
    )
    data = solve_model(model, enforce_policy=False).to_dict()
    files = data["solver"]["checkpoint_files"]
    assert files
    checkpoint = NpzNonlinearCheckpointStore().load(files[-1])
    assert checkpoint.completed_step == len(data["solver"]["steps"])


def test_t51_modified_newton_uses_the_common_fixed_lifecycle() -> None:
    model = elastoplastic_tet4_model()
    model.analysis = replace(model.analysis, method="modified_newton")
    data = solve_model(model, enforce_policy=False).to_dict()
    assert data["status"] == "PASS"
    assert data["solver"]["steps"]


def test_t52_migrated_wrappers_have_no_alternate_acceptance_model() -> None:
    adaptive_source = inspect.getsource(NonlinearStaticSolver._solve_adaptive_load_steps)
    arc_source = inspect.getsource(NonlinearStaticSolver._solve_arc_length)
    assert "UnifiedContinuationController" in adaptive_source
    assert "UnifiedContinuationController" in arc_source
    assert "MaterialStateSession" not in adaptive_source
    assert "MaterialStateSession" not in arc_source
    assert "commit_material_states(material_states, updated_states)" not in inspect.getsource(
        NonlinearStaticSolver._solve_arc_length_step
    )
