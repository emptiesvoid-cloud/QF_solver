"""Focused WP03-D tests for the common arc-length radius policy."""

from __future__ import annotations

from copy import deepcopy
import inspect
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.controls import ArcLengthControls
from solveur.core.nonlinear.driver import RetryClassification, UnifiedContinuationController
from solveur.core.nonlinear.robustness import (
    UnifiedAdaptiveStepPolicy,
    UnifiedArcLengthRadiusPolicy,
    UnifiedNonlinearRobustnessController,
)
from solveur.core.nonlinear.solver import NonlinearStaticSolver
from solveur.core.nonlinear.state import NonlinearState, deterministic_state_digest
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from tests.unit.test_analysis_features import nonlinear_tet4_model


BASELINE = Path("qualification/0_2_9/wp03_d_baseline.json")


def _controls(**overrides: object) -> ArcLengthControls:
    parameters: dict[str, object] = {
        "adaptive_arc_length": True,
        "min_arc_length_radius": 0.1,
        "arc_length_growth_factor": 2.0,
        "arc_length_shrink_factor": 0.5,
        "arc_length_grow_below_iterations": 3,
        "arc_length_shrink_above_iterations": 8,
    }
    parameters.update(overrides)
    return ArcLengthControls.from_parameters(parameters, max_iterations=20)


def _policy_failure(
    policy: UnifiedArcLengthRadiusPolicy,
    *,
    reason: NonlinearFailureReason = NonlinearFailureReason.MAX_ITERATIONS,
    classification: RetryClassification = RetryClassification.RETRYABLE,
    rejected_count: int = 1,
    policy_radius: float = 0.4,
    effective_radius: float | None = None,
    diagnostics: dict[str, Any] | None = None,
    rollback_verified: bool = True,
):
    return policy.on_failure(
        accepted_step=2,
        base_load_factor=0.4,
        policy_radius=policy_radius,
        effective_attempt_radius=policy_radius if effective_radius is None else effective_radius,
        maximum_radius=1.0,
        failure_reason=reason,
        retry_classification=classification,
        rejected_count=rejected_count,
        failure_diagnostics=diagnostics,
        rollback_verified=rollback_verified,
        accepted_state_digest="a" * 64,
    )


def _arc_model(**parameters: object) -> Any:
    model = nonlinear_tet4_model(method="arc_length")
    model.analysis.parameters.update(
        {
            "max_arc_steps": 6,
            "arc_length_stop_mode": "max_steps",
            "arc_length_allow_load_factor_turning": True,
            "arc_length_load_factor_limit": 5.0,
            "arc_length_radius": 0.05,
            "max_arc_length_radius": 0.2,
            "min_arc_length_radius": 1.0e-6,
            "arc_length_shrink_factor": 0.5,
            **parameters,
        }
    )
    return model


def _checkpointed_arc(root: Path, stem: str, **parameters: object) -> tuple[Any, Any]:
    model = _arc_model(**parameters)
    model.analysis.parameters.update(
        {
            "checkpoint_path": str(root / f"{stem}.npz"),
            "checkpoint_interval": 1,
            "checkpoint_keep_steps": True,
        }
    )
    return model, solve_model(model, enforce_policy=False)


def _step_file(result: Any, step: int) -> Path:
    suffix = f".step{step:08d}.npz"
    for raw_path in result.solver["checkpoint_files"]:
        path = Path(str(raw_path))
        if path.name.endswith(suffix):
            return path
    raise AssertionError(f"No retained accepted checkpoint for step {step}.")


def _restart_from(reference: tuple[Any, Any], output: Path, step: int, **parameters: object) -> Any:
    model, result = reference
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(output),
            "restart_from": str(_step_file(result, step)),
            "checkpoint_interval": 1,
            "checkpoint_keep_steps": True,
            **parameters,
        }
    )
    return solve_model(restarted, enforce_policy=False)


def _rejection_run(monkeypatch: pytest.MonkeyPatch, *, failure_attempt: int = 1, **parameters: object) -> Any:
    original = NonlinearStaticSolver._solve_arc_length_step
    calls = {"count": 0}

    def reject_at(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls["count"] += 1
        if calls["count"] == failure_attempt:
            raise NumericalConvergenceError(
                "controlled WP03-D arc rejection",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
                diagnostics={"controlled": True},
            )
        return original(self, *args, **kwargs)

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_arc_length_step", reject_at)
    model = _arc_model(**parameters)
    return solve_model(model, enforce_policy=False).to_dict()


def test_t03d_01_arc_policy_validates_controls() -> None:
    policy = UnifiedArcLengthRadiusPolicy(_controls())
    diagnostics = policy.configuration_diagnostics()
    assert diagnostics["policy_id"] == "qf-solver-unified-arc-length-radius"
    assert diagnostics["minimum_radius_equality"] == "PERMITTED"
    assert diagnostics["radius_roles"]["policy_radius"]


def test_t03d_02_fixed_radius_accepted_keep() -> None:
    decision = UnifiedArcLengthRadiusPolicy(_controls(adaptive_arc_length=False)).on_accept(
        accepted_step=1,
        base_load_factor=0.0,
        policy_radius=0.4,
        effective_attempt_radius=0.4,
        maximum_radius=1.0,
        iterations=1,
    )
    assert decision.decision == "ACCEPT_KEEP"
    assert decision.accepted_next_radius == pytest.approx(0.4)


def test_t03d_03_adaptive_accepted_growth() -> None:
    decision = UnifiedArcLengthRadiusPolicy(_controls()).on_accept(
        accepted_step=1,
        base_load_factor=0.0,
        policy_radius=0.4,
        effective_attempt_radius=0.4,
        maximum_radius=1.0,
        iterations=3,
    )
    assert decision.decision == "ACCEPT_GROW"
    assert decision.accepted_next_radius == pytest.approx(0.8)


def test_t03d_04_adaptive_accepted_shrink() -> None:
    decision = UnifiedArcLengthRadiusPolicy(_controls()).on_accept(
        accepted_step=1,
        base_load_factor=0.0,
        policy_radius=0.4,
        effective_attempt_radius=0.4,
        maximum_radius=1.0,
        iterations=8,
    )
    assert decision.decision == "ACCEPT_SHRINK"
    assert decision.accepted_next_radius == pytest.approx(0.2)


def test_t03d_05_growth_is_capped_at_maximum() -> None:
    decision = UnifiedArcLengthRadiusPolicy(_controls()).on_accept(
        accepted_step=1,
        base_load_factor=0.0,
        policy_radius=0.4,
        effective_attempt_radius=0.4,
        maximum_radius=0.5,
        iterations=1,
    )
    assert decision.accepted_next_radius == pytest.approx(0.5)


def test_t03d_06_shrink_is_floored_at_minimum() -> None:
    decision = UnifiedArcLengthRadiusPolicy(_controls(min_arc_length_radius=0.2)).on_accept(
        accepted_step=1,
        base_load_factor=0.0,
        policy_radius=0.4,
        effective_attempt_radius=0.4,
        maximum_radius=1.0,
        iterations=20,
    )
    assert decision.accepted_next_radius == pytest.approx(0.2)


def test_t03d_07_retryable_failure_shrinks_radius() -> None:
    decision = _policy_failure(UnifiedArcLengthRadiusPolicy(_controls()))
    assert decision.decision == "RETRY_SHRINK"
    assert decision.retry_radius == pytest.approx(0.2)


def test_t03d_08_non_retryable_failure_is_terminal() -> None:
    decision = _policy_failure(
        UnifiedArcLengthRadiusPolicy(_controls()),
        reason=NonlinearFailureReason.MATERIAL_UPDATE_FAILURE,
        classification=RetryClassification.NON_RETRYABLE,
    )
    assert decision.decision == "TERMINAL_NON_RETRYABLE"


def test_t03d_09_owner_policy_failure_behavior_is_preserved() -> None:
    error = dict(
        reason=NonlinearFailureReason.SINGULAR_TANGENT,
        classification=RetryClassification.OWNER_POLICY_DEPENDENT,
    )
    assert _policy_failure(UnifiedArcLengthRadiusPolicy(_controls()), **error).decision == "RETRY_SHRINK"
    assert _policy_failure(
        UnifiedArcLengthRadiusPolicy(_controls()), **error, rollback_verified=True
    ).retry_classification == "OWNER_POLICY_DEPENDENT"
    assert _policy_failure(
        UnifiedArcLengthRadiusPolicy(_controls(), allow_owner_policy=False), **error
    ).decision == "TERMINAL_NON_RETRYABLE"


def test_t03d_10_rollback_precedes_radius_decision_in_route() -> None:
    source = inspect.getsource(NonlinearStaticSolver._solve_arc_length)
    assert source.index("controller.rollback(") < source.index("radius_policy.on_failure(")


def test_t03d_11_rollback_digest_is_exact() -> None:
    state = NonlinearState(
        np.zeros(2),
        load_factor=0.2,
        material_state={"ip": {"plastic": 0.0}},
        contact_state={"pair": {"active": False}},
        continuation_state={"radius": 0.1, "previous_du": [0.0, 0.0]},
    )
    controller = UnifiedContinuationController(state)
    before = controller.accepted_digest
    trial = controller.begin_trial()
    trial.displacement[:] = 4.0
    trial.material_state["ip"]["plastic"] = 2.0
    trial.contact_state["pair"]["active"] = True
    trial.continuation_state["radius"] = 0.01
    controller.rollback(NumericalConvergenceError("retry", reason=NonlinearFailureReason.MAX_ITERATIONS), path="arc")
    assert controller.accepted_digest == before
    assert controller.rejection_log[-1]["accepted_digest_before"] == before
    assert controller.rejection_log[-1]["accepted_digest_after"] == before


def test_t03d_12_rejected_radius_is_not_persisted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model = _arc_model(
        max_arc_steps=1,
        checkpoint_path=str(tmp_path / "arc.npz"),
        checkpoint_interval=1,
        checkpoint_keep_steps=True,
    )
    original = NonlinearStaticSolver._solve_arc_length_step
    calls = {"count": 0}

    def reject_once(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls["count"] += 1
        if calls["count"] == 1:
            raise NumericalConvergenceError("retry", reason=NonlinearFailureReason.MAX_ITERATIONS)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_arc_length_step", reject_once)
    result = solve_model(model, enforce_policy=False)
    data = result.to_dict()
    rejection = data["solver"]["rejection_log"][0]
    checkpoint = NpzNonlinearCheckpointStore().load(Path(str(data["solver"]["checkpoint_path"])))
    accepted_decisions = [
        item
        for item in data["solver"]["arc_radius_policy"]["decisions"]
        if item["accepted_next_radius"] is not None
    ]
    assert checkpoint.completed_step == 1
    assert rejection["retry_radius"] < rejection["rejected_radius"]
    assert accepted_decisions
    assert accepted_decisions[-1]["accepted_state_digest"] == checkpoint.composite_digest
    assert checkpoint.accepted_state.continuation_state["radius"] == pytest.approx(
        accepted_decisions[-1]["accepted_next_radius"]
    )
    assert checkpoint.accepted_state.continuation_state["radius"] != pytest.approx(
        rejection["rejected_radius"]
    )


def test_t03d_13_accepted_next_radius_is_persisted_after_commit(tmp_path: Path) -> None:
    _model, result = _checkpointed_arc(
        tmp_path,
        "accepted",
        adaptive_arc_length=True,
        arc_length_growth_factor=2.0,
        arc_length_grow_below_iterations=10,
        arc_length_shrink_above_iterations=50,
    )
    data = result.to_dict()
    policy = data["solver"]["arc_radius_policy"]
    accepted_decisions = [item for item in policy["decisions"] if item["decision"].startswith("ACCEPT_")]
    checkpoint = NpzNonlinearCheckpointStore().load(Path(str(data["solver"]["checkpoint_path"])))
    assert accepted_decisions
    assert checkpoint.accepted_state.continuation_state["radius"] == pytest.approx(
        accepted_decisions[-1]["accepted_next_radius"]
    )


def test_t03d_14_minimum_radius_above_boundary_is_retryable() -> None:
    decision = _policy_failure(
        UnifiedArcLengthRadiusPolicy(_controls(min_arc_length_radius=0.1)),
        policy_radius=0.25,
    )
    assert decision.decision == "RETRY_SHRINK"
    assert decision.retry_radius == pytest.approx(0.125)


def test_t03d_15_minimum_radius_equality_is_permitted() -> None:
    decision = _policy_failure(
        UnifiedArcLengthRadiusPolicy(_controls(min_arc_length_radius=0.1)),
        policy_radius=0.2,
    )
    assert decision.decision == "RETRY_SHRINK"
    assert decision.retry_radius == pytest.approx(0.1)


def test_t03d_16_minimum_radius_below_boundary_is_terminal() -> None:
    decision = _policy_failure(
        UnifiedArcLengthRadiusPolicy(_controls(min_arc_length_radius=0.1)),
        policy_radius=0.19,
    )
    assert decision.decision == "TERMINAL_MIN_RADIUS"


def test_t03d_17_target_clipped_radius_is_detected() -> None:
    decision = _policy_failure(
        UnifiedArcLengthRadiusPolicy(_controls()),
        policy_radius=0.1,
        effective_radius=0.01,
    )
    assert decision.target_clipped is True
    assert decision.effective_attempt_radius == pytest.approx(0.01)


def test_t03d_18_target_clipped_retry_decreases_effective_attempt_radius(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = NonlinearStaticSolver._solve_arc_length_step
    attempted: list[float] = []
    calls = {"count": 0}

    def reject_once(self: Any, *args: Any, **kwargs: Any) -> Any:
        attempted.append(float(args[9]))
        calls["count"] += 1
        if calls["count"] == 1:
            raise NumericalConvergenceError("target-clipped retry", reason=NonlinearFailureReason.MAX_ITERATIONS)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_arc_length_step", reject_once)
    model = _arc_model(
        max_arc_steps=10,
        arc_length_stop_mode="target_load",
        target_load_factor=0.05,
        arc_length_radius=0.1,
        max_arc_length_radius=0.2,
        min_arc_length_radius=1.0e-8,
    )
    solve_model(model, enforce_policy=False)
    assert len(attempted) >= 2
    assert attempted[1] < attempted[0]


def _baseline_case(name: str) -> dict[str, Any]:
    document = json.loads(BASELINE.read_text(encoding="utf-8"))
    return document["cases"][name]


def test_t03d_19_monotonic_preservation() -> None:
    result = solve_model(_arc_model(max_arc_steps=6), enforce_policy=False).to_dict()
    expected = _baseline_case("D-B01_monotonic_fixed_radius")
    actual_factors = [step["load_factor"] for step in result["solver"]["steps"]]
    actual_radii = [step["arc_length_radius"] for step in result["solver"]["steps"]]
    assert actual_factors == pytest.approx(expected["accepted_load_factors"], rel=1.0e-9, abs=1.0e-12)
    assert actual_radii == pytest.approx(expected["effective_attempt_radii"], rel=1.0e-9, abs=1.0e-12)


def test_t03d_20_adaptive_radius_preservation() -> None:
    result = solve_model(
        _arc_model(
            adaptive_arc_length=True,
            arc_length_growth_factor=2.0,
            arc_length_grow_below_iterations=10,
            arc_length_shrink_above_iterations=50,
        ),
        enforce_policy=False,
    ).to_dict()
    expected = _baseline_case("D-B02_monotonic_adaptive_radius")
    decisions = [item for item in result["solver"]["arc_radius_policy"]["decisions"] if item["accepted_next_radius"]]
    assert [item["accepted_next_radius"] for item in decisions] == pytest.approx(
        expected["policy_radii_after_acceptance"], rel=1.0e-9, abs=1.0e-12
    )


def test_t03d_21_turning_branch_preservation() -> None:
    result = solve_model(_arc_model(max_arc_steps=6), enforce_policy=False).to_dict()
    expected = _baseline_case("D-B03_turning_branch")
    actual = [step["arc_length_branch_direction"] for step in result["solver"]["steps"]]
    assert actual == expected["branch_direction"]


def test_t03d_22_rejection_before_turning_preserves_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _rejection_run(monkeypatch, failure_attempt=1, max_arc_steps=4)
    assert all(step["arc_length_branch_direction"] == 1 for step in data["solver"]["steps"])
    assert data["solver"]["rejection_log"][0]["radius_policy"]["rollback_verified"] is True


def test_t03d_23_rejection_near_turning_preserves_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _rejection_run(monkeypatch, failure_attempt=2, max_arc_steps=4)
    assert all(step["arc_length_branch_direction"] == 1 for step in data["solver"]["steps"])
    assert data["solver"]["rejected_increments"] == 1


def test_t03d_24_rejection_after_turning_preserves_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    data = _rejection_run(monkeypatch, failure_attempt=3, max_arc_steps=4)
    assert all(step["arc_length_branch_direction"] == 1 for step in data["solver"]["steps"])
    assert data["solver"]["continuation_rejection_log"][0]["accepted_continuation_before"] == data["solver"]["continuation_rejection_log"][0]["accepted_continuation_after"]


@pytest.fixture(scope="module")
def standard_reference(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Any]:
    return _checkpointed_arc(tmp_path_factory.mktemp("wp03d-standard"), "arc")


@pytest.fixture(scope="module")
def adaptive_reference(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Any]:
    return _checkpointed_arc(
        tmp_path_factory.mktemp("wp03d-adaptive"),
        "arc",
        adaptive_arc_length=True,
        arc_length_growth_factor=2.0,
        arc_length_grow_below_iterations=10,
        arc_length_shrink_above_iterations=50,
    )


def test_t03d_25_restart_monotonic(standard_reference: tuple[Any, Any], tmp_path: Path) -> None:
    _model, reference = standard_reference
    resumed = _restart_from(standard_reference, tmp_path / "restart.npz", 2)
    np.testing.assert_allclose(resumed.displacements, reference.displacements, rtol=1.0e-9, atol=1.0e-12)
    expected = [step["load_factor"] for step in reference.solver["steps"][2:]]
    actual = [step["load_factor"] for step in resumed.solver["steps"]]
    assert actual == pytest.approx(expected, rel=1.0e-9, abs=1.0e-12)


def test_t03d_26_restart_turning_branch(standard_reference: tuple[Any, Any], tmp_path: Path) -> None:
    _model, reference = standard_reference
    resumed = _restart_from(standard_reference, tmp_path / "restart-turn.npz", 2)
    expected = [step["arc_length_branch_direction"] for step in reference.solver["steps"][2:]]
    assert [step["arc_length_branch_direction"] for step in resumed.solver["steps"]] == expected


def test_t03d_27_restart_adaptive_radius(adaptive_reference: tuple[Any, Any], tmp_path: Path) -> None:
    _model, reference = adaptive_reference
    resumed = _restart_from(adaptive_reference, tmp_path / "restart-adaptive.npz", 2)
    expected = [step["arc_length_radius"] for step in reference.solver["steps"][2:]]
    actual = [step["arc_length_radius"] for step in resumed.solver["steps"]]
    assert actual == pytest.approx(expected, rel=1.0e-9, abs=1.0e-12)
    np.testing.assert_allclose(resumed.displacements, reference.displacements, rtol=1.0e-9, atol=1.0e-12)


def test_t03d_28_restart_rejection_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "rejection"
    model, _reference = _checkpointed_arc(root, "arc", max_arc_steps=4)
    original = NonlinearStaticSolver._solve_arc_length_step
    calls = {"count": 0}

    def reject_once(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls["count"] += 1
        if calls["count"] == 1:
            raise NumericalConvergenceError("retry", reason=NonlinearFailureReason.MAX_ITERATIONS)
        return original(self, *args, **kwargs)

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_arc_length_step", reject_once)
    rejected = solve_model(model, enforce_policy=False)
    resumed = _restart_from((model, rejected), tmp_path / "restarted.npz", 2)
    assert rejected.solver["rejected_increments"] == 1
    expected = [step["load_factor"] for step in rejected.solver["steps"][2:]]
    assert [step["load_factor"] for step in resumed.solver["steps"]] == pytest.approx(
        expected, rel=1.0e-9, abs=1.0e-12
    )


def test_t03d_29_path_dependent_material_restart_retry(tmp_path: Path) -> None:
    from dataclasses import replace

    from solveur.verification.robustness_nonlinear_solids import _refinement_model

    model = _refinement_model("TET4", 1)
    parameters = {**model.analysis.parameters}
    parameters.pop("load_path", None)
    parameters.update(
        {
            "load_steps": 3,
            "max_arc_steps": 4,
            "max_iterations": 40,
            "tolerance": 1.0e-7,
            "kinematics": "total_lagrangian_j2",
            "arc_length_stop_mode": "max_steps",
            "arc_length_allow_load_factor_turning": True,
            "arc_length_load_factor_limit": 5.0,
            "arc_length_radius": 0.02,
            "max_arc_length_radius": 0.05,
            "min_arc_length_radius": 1.0e-8,
            "checkpoint_path": str(tmp_path / "material.npz"),
            "checkpoint_interval": 1,
            "checkpoint_keep_steps": True,
        }
    )
    model.analysis = replace(model.analysis, method="arc_length", parameters=parameters)
    reference = solve_model(model, enforce_policy=False)
    resumed = _restart_from((model, reference), tmp_path / "material-restart.npz", 2)
    assert deterministic_state_digest(resumed.material_states) == deterministic_state_digest(reference.material_states)
    np.testing.assert_allclose(resumed.displacements, reference.displacements, rtol=1.0e-9, atol=1.0e-12)


def test_t03d_30_checkpoint_failure_does_not_cutback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from solveur.core.nonlinear.checkpoint import NonlinearCheckpointSession

    commits: list[str] = []
    original_commit = UnifiedContinuationController.commit

    def commit_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        accepted = original_commit(self, *args, **kwargs)
        commits.append(accepted.digest)
        return accepted

    def save_failure(self: Any, *args: Any, **kwargs: Any) -> None:
        raise NumericalConvergenceError("checkpoint failure", reason=NonlinearFailureReason.CHECKPOINT_FAILURE)

    monkeypatch.setattr(UnifiedContinuationController, "commit", commit_spy)
    monkeypatch.setattr(NonlinearCheckpointSession, "save_state", save_failure)
    model = _arc_model(
        max_arc_steps=1,
        checkpoint_path=str(tmp_path / "failure.npz"),
        checkpoint_interval=1,
    )
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_model(model, enforce_policy=False)
    assert raised.value.reason is NonlinearFailureReason.CHECKPOINT_FAILURE
    assert len(commits) == 1
    assert "radius_policy" not in raised.value.diagnostics


def test_t03d_31_checkpoint_failure_does_not_rollback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from solveur.core.nonlinear.checkpoint import NonlinearCheckpointSession

    rollbacks: list[str] = []
    original_rollback = UnifiedContinuationController.rollback

    def rollback_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        rollbacks.append("rollback")
        return original_rollback(self, *args, **kwargs)

    def save_failure(self: Any, *args: Any, **kwargs: Any) -> None:
        raise NumericalConvergenceError("checkpoint failure", reason=NonlinearFailureReason.CHECKPOINT_FAILURE)

    monkeypatch.setattr(UnifiedContinuationController, "rollback", rollback_spy)
    monkeypatch.setattr(NonlinearCheckpointSession, "save_state", save_failure)
    model = _arc_model(
        max_arc_steps=1,
        checkpoint_path=str(tmp_path / "failure.npz"),
        checkpoint_interval=1,
    )
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_model(model, enforce_policy=False)
    assert raised.value.reason is NonlinearFailureReason.CHECKPOINT_FAILURE
    assert rollbacks == []


def test_t03d_32_max_steps_failure_is_preserved() -> None:
    model = _arc_model(
        max_arc_steps=1,
        arc_length_stop_mode="target_load",
        target_load_factor=10.0,
        arc_length_load_factor_limit=20.0,
    )
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_model(model, enforce_policy=False)
    assert raised.value.reason is NonlinearFailureReason.ARC_LENGTH_FAILURE
    assert raised.value.diagnostics["max_arc_steps"] == 1


def test_t03d_33_load_factor_limit_failure_is_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    original = NonlinearStaticSolver._solve_arc_length_step
    calls = {"count": 0}

    def count_calls(self: Any, *args: Any, **kwargs: Any) -> Any:
        calls["count"] += 1
        return original(self, *args, **kwargs)

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_arc_length_step", count_calls)
    model = _arc_model(
        max_arc_steps=2,
        arc_length_load_factor_limit=1.0e-3,
        arc_length_radius=0.1,
        max_arc_length_radius=0.1,
        min_arc_length_radius=0.09,
    )
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_model(model, enforce_policy=False)
    assert raised.value.reason is NonlinearFailureReason.ARC_LENGTH_FAILURE
    assert calls["count"] == 1


def test_t03d_34_unknown_runtime_error_policy_is_explicitly_preserved() -> None:
    decision = _policy_failure(
        UnifiedArcLengthRadiusPolicy(_controls()),
        reason=RuntimeError,
        classification=RetryClassification.OWNER_POLICY_DEPENDENT,
    )
    assert decision.decision == "RETRY_SHRINK"
    assert decision.retry_classification == "OWNER_POLICY_DEPENDENT"


def test_t03d_35_one_radius_policy_authority_source_audit() -> None:
    from solveur.core.nonlinear import arc_length, robustness

    assert inspect.getsource(robustness).count("class UnifiedArcLengthRadiusPolicy") == 1
    assert inspect.getsource(arc_length).count("radius_policy = UnifiedArcLengthRadiusPolicy(") == 1
    assert inspect.getsource(arc_length).count("radius_policy.on_failure(") == 1


def test_t03d_36_no_duplicate_radius_shrink_implementation() -> None:
    from solveur.core.nonlinear.arc_length import NonlinearArcLengthMixin

    source = inspect.getsource(NonlinearArcLengthMixin._solve_arc_length)
    assert "radius *= controls.shrink_factor" not in source
    assert source.count("radius_policy.on_accept(") == 1
    assert source.count("radius_policy.on_failure(") == 1


def test_t03d_37_wp03b_line_search_and_stagnation_are_unaffected() -> None:
    controller = UnifiedNonlinearRobustnessController(
        stagnation_window=3,
        plateau_threshold=1.0e-3,
        line_search_enabled=True,
        min_alpha=0.1,
        max_reductions=3,
    )
    assert controller.stagnation_decision([1.0, 0.9999, 0.9998]).reason is NonlinearFailureReason.CONVERGENCE_STAGNATION
    result = controller.line_search(1.0, lambda alpha: 2.0 if alpha == 1.0 else 0.5, raise_on_failure=False)
    assert result.accepted is True


def test_t03d_38_wp03c_adaptive_policy_is_unaffected() -> None:
    from tests.unit.test_wp03_c_adaptive_policy import _controls as adaptive_controls

    policy = UnifiedAdaptiveStepPolicy(adaptive_controls())
    assert policy.on_accept(
        base_load_factor=0.0,
        policy_increment=0.4,
        proposed_increment=0.4,
        iterations=3,
        cutback_count=0,
    ).next_increment == pytest.approx(0.6)


def test_t03d_39_radius_diagnostics_are_deterministic() -> None:
    def run() -> str:
        policy = UnifiedArcLengthRadiusPolicy(_controls())
        policy.on_accept(
            accepted_step=1,
            base_load_factor=0.0,
            policy_radius=0.4,
            effective_attempt_radius=0.2,
            maximum_radius=1.0,
            iterations=2,
        )
        _policy_failure(policy, policy_radius=0.4, effective_radius=0.2)
        return deterministic_state_digest(policy.configuration_diagnostics())

    assert run() == run()


def test_t03d_40_mapping_order_independent_diagnostics() -> None:
    first = {"policy": {"b": [1, 2], "a": (3, 4)}, "failure": "MAX_ITERATIONS"}
    second = {"failure": "MAX_ITERATIONS", "policy": {"a": (3, 4), "b": [1, 2]}}
    assert deterministic_state_digest(first) == deterministic_state_digest(second)
    assert deterministic_state_digest({1: "value"}) != deterministic_state_digest({"1": "value"})
