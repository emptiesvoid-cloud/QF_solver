"""WP02-D focused tests for the schema-v2 arc-length restart boundary."""

from __future__ import annotations

from copy import deepcopy
import inspect
import json
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.nonlinear.checkpoint import NonlinearCheckpointSession
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.driver import UnifiedContinuationController
from solveur.core.nonlinear.material_state import initial_material_states
from solveur.core.nonlinear.solver import NonlinearStaticSolver
from solveur.core.nonlinear.state import NonlinearState
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from tests.unit.test_analysis_features import nonlinear_tet4_model


def _arc_model(**parameters: object):
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


def _checkpointed_run(root: Path, stem: str, **parameters: object) -> tuple[Any, Any]:
    model = _arc_model(**parameters)
    model.analysis.parameters.update(
        {
            "checkpoint_path": str(root / f"{stem}.npz"),
            "checkpoint_interval": 1,
            "checkpoint_keep_steps": True,
        }
    )
    return model, solve_model(model, enforce_policy=False)


@pytest.fixture(scope="module")
def standard_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Any]:
    return _checkpointed_run(tmp_path_factory.mktemp("wp02d-standard"), "arc")


@pytest.fixture(scope="module")
def adaptive_radius_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Any]:
    return _checkpointed_run(
        tmp_path_factory.mktemp("wp02d-adaptive-radius"),
        "arc",
        adaptive_arc_length=True,
        arc_length_growth_factor=2.0,
        arc_length_shrink_factor=0.5,
        arc_length_grow_below_iterations=10,
        arc_length_shrink_above_iterations=50,
    )


def _step_file(run: tuple[Any, Any], step: int) -> Path:
    _model, result = run
    suffix = f".step{step:08d}.npz"
    for raw_path in result.solver["checkpoint_files"]:
        path = Path(str(raw_path))
        if path.name.endswith(suffix):
            return path
    raise AssertionError(f"No retained checkpoint for accepted step {step}.")


def _restart_from(
    run: tuple[Any, Any],
    output_dir: Path,
    step: int,
    *,
    name: str = "restart",
    **parameters: object,
) -> tuple[Any, Any]:
    model, _reference = run
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(output_dir / f"{name}.npz"),
            "restart_from": str(_step_file(run, step)),
            "checkpoint_interval": 1,
            "checkpoint_keep_steps": True,
            **parameters,
        }
    )
    return restarted, solve_model(restarted, enforce_policy=False)


def _assert_final_equivalence(reference: Any, resumed: Any) -> None:
    np.testing.assert_allclose(resumed.displacements, reference.displacements, rtol=1.0e-9, atol=1.0e-12)
    assert resumed.material_states == reference.material_states


def _assert_path_equivalence(reference: Any, resumed: Any, restart_step: int) -> None:
    expected = reference.solver["steps"][restart_step:]
    actual = resumed.solver["steps"]
    assert len(actual) == len(expected)
    for expected_step, actual_step in zip(expected, actual, strict=True):
        assert actual_step["load_factor"] == pytest.approx(expected_step["load_factor"], rel=1.0e-9, abs=1.0e-12)
        assert actual_step["arc_length_radius"] == pytest.approx(
            expected_step["arc_length_radius"], rel=1.0e-9, abs=1.0e-12
        )


def _json_normalize(value: Any) -> Any:
    if isinstance(value, np.generic):
        return _json_normalize(value.item())
    if isinstance(value, np.ndarray):
        return [_json_normalize(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): _json_normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_normalize(item) for item in value]
    if isinstance(value, tuple):
        return [_json_normalize(item) for item in value]
    return value


def _write_v1_checkpoint(model: Any, source: Path, destination: Path, *, incomplete: bool = False) -> None:
    store = NpzNonlinearCheckpointStore()
    checkpoint = store.load(source)
    session = NonlinearCheckpointSession.create(model, 6, store)
    required = {
        "accepted_step",
        "load_factor",
        "radius",
        "maximum_radius",
        "load_scale",
        "previous_du",
        "previous_dlambda",
    }
    continuation = {
        key: checkpoint.continuation_state[key]
        for key in required
        if key in checkpoint.continuation_state
    }
    if incomplete:
        continuation.pop("previous_du", None)
    metadata = {
        "schema_version": 1,
        "model_signature": session.signature,
        "completed_step": checkpoint.completed_step,
        "load_factor": float(checkpoint.load_factor),
        "material_states": _json_normalize(checkpoint.material_states),
        "continuation_state": _json_normalize(continuation),
    }
    destination.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        destination,
        metadata_json=json.dumps(metadata, sort_keys=True, allow_nan=False),
        displacement=checkpoint.displacement,
    )


def _tamper_composite_digest(source: Path, destination: Path) -> None:
    with np.load(source, allow_pickle=False) as data:
        metadata = json.loads(str(data["metadata_json"].item()))
    metadata["composite_digest"] = "0" * 64
    np.savez_compressed(
        destination,
        metadata_json=json.dumps(metadata, sort_keys=True, allow_nan=False),
    )


def _run_rejection_case(root: Path) -> tuple[Any, Any]:
    model = _arc_model()
    model.analysis.parameters.update(
        {
            "checkpoint_path": str(root / "rejected.npz"),
            "checkpoint_interval": 1,
            "checkpoint_keep_steps": True,
        }
    )
    original = NonlinearStaticSolver._solve_arc_length_step
    calls = {"count": 0}

    def reject_once(self: Any, *args: Any, **kwargs: Any):
        calls["count"] += 1
        if calls["count"] == 1:
            raise NumericalConvergenceError(
                "controlled arc-length rejection",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
            )
        return original(self, *args, **kwargs)

    NonlinearStaticSolver._solve_arc_length_step = reject_once
    try:
        result = solve_model(model, enforce_policy=False)
    finally:
        NonlinearStaticSolver._solve_arc_length_step = original
    return model, result


@pytest.fixture(scope="module")
def rejection_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Any]:
    return _run_rejection_case(tmp_path_factory.mktemp("wp02d-rejection"))


def test_t02d_01_arc_restore_uses_composite_restore_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[NonlinearState] = []
    original = NonlinearCheckpointSession.restore_state

    def spy(self: Any, initial_state: NonlinearState, *args: Any, **kwargs: Any) -> NonlinearState:
        restored = original(self, initial_state, *args, **kwargs)
        calls.append(restored)
        return restored

    monkeypatch.setattr(NonlinearCheckpointSession, "restore_state", spy)
    model, _result = _checkpointed_run(tmp_path, "restore")
    assert calls and all(isinstance(state, NonlinearState) for state in calls)
    assert "restore_continuation" not in inspect.getsource(NonlinearStaticSolver.solve)
    assert model.analysis.method == "arc_length"


def test_t02d_02_arc_save_uses_accepted_composite_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[int, NonlinearState]] = []
    original = NonlinearCheckpointSession.save_state

    def spy(self: Any, step: int, accepted_state: NonlinearState, *args: Any, **kwargs: Any) -> None:
        calls.append((step, accepted_state.detached_copy()))
        original(self, step, accepted_state, *args, **kwargs)

    monkeypatch.setattr(NonlinearCheckpointSession, "save_state", spy)
    _model, result = _checkpointed_run(tmp_path, "save")
    assert len(calls) == len(result.solver["steps"]) == 6
    for step, state in calls:
        assert state.continuation_state["accepted_step"] == step
        assert state.accepted_increment_metadata["step"] == step
        assert state.digest == state.detached_copy().digest


def test_t02d_03_checkpoint_is_saved_only_after_controller_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[tuple[str, int]] = []
    original_commit = UnifiedContinuationController.commit
    original_save = NonlinearCheckpointSession.save_state

    def commit_spy(self: Any) -> NonlinearState:
        accepted = original_commit(self)
        events.append(("commit", int(accepted.continuation_state["accepted_step"])))
        return accepted

    def save_spy(self: Any, step: int, accepted_state: NonlinearState, *args: Any, **kwargs: Any) -> None:
        events.append(("save", step))
        original_save(self, step, accepted_state, *args, **kwargs)

    monkeypatch.setattr(UnifiedContinuationController, "commit", commit_spy)
    monkeypatch.setattr(NonlinearCheckpointSession, "save_state", save_spy)
    _checkpointed_run(tmp_path, "order")
    assert len([event for event in events if event[0] == "commit"]) == 6
    assert len([event for event in events if event[0] == "save"]) == 6
    for index, event in enumerate(events):
        if event[0] == "save":
            assert any(previous == ("commit", event[1]) for previous in events[:index])


def test_t02d_04_continuous_vs_restarted_monotonic_path(
    standard_run: tuple[Any, Any], tmp_path: Path
) -> None:
    model, reference = standard_run
    restarted, resumed = _restart_from(standard_run, tmp_path, 2)
    _assert_final_equivalence(reference, resumed)
    _assert_path_equivalence(reference, resumed, 2)
    assert restarted.analysis.parameters["restart_from"]
    assert resumed.solver["restart_step"] == 2
    assert model.analysis.parameters["arc_length_stop_mode"] == "max_steps"


def test_t02d_05_continuous_vs_restarted_turning_point_path(
    standard_run: tuple[Any, Any], tmp_path: Path
) -> None:
    _model, reference = standard_run
    _restarted, resumed = _restart_from(standard_run, tmp_path, 2)
    _assert_path_equivalence(reference, resumed, 2)
    expected_loads = [step["load_factor"] for step in reference.solver["steps"][2:]]
    actual_loads = [step["load_factor"] for step in resumed.solver["steps"]]
    assert actual_loads == pytest.approx(expected_loads, rel=1.0e-9, abs=1.0e-12)


def test_t02d_06_continuous_vs_restarted_adaptive_radius_path(
    adaptive_radius_run: tuple[Any, Any], tmp_path: Path
) -> None:
    _model, reference = adaptive_radius_run
    _restarted, resumed = _restart_from(adaptive_radius_run, tmp_path, 2)
    _assert_final_equivalence(reference, resumed)
    _assert_path_equivalence(reference, resumed, 2)


def test_t02d_07_continuous_vs_restarted_rejection_radius_shrink(
    rejection_run: tuple[Any, Any], tmp_path: Path
) -> None:
    _model, reference = rejection_run
    assert reference.solver["rejected_increments"] == 1
    _restarted, resumed = _restart_from(rejection_run, tmp_path, 2)
    _assert_final_equivalence(reference, resumed)
    _assert_path_equivalence(reference, resumed, 2)


def test_t02d_08_checkpoint_boundary_composite_digest_is_exact(standard_run: tuple[Any, Any]) -> None:
    checkpoint = NpzNonlinearCheckpointStore().load(_step_file(standard_run, 3))
    assert checkpoint.composite_digest == checkpoint.accepted_state.digest


def test_t02d_09_material_digest_is_exact_after_restore(standard_run: tuple[Any, Any]) -> None:
    checkpoint = NpzNonlinearCheckpointStore().load(_step_file(standard_run, 3))
    assert checkpoint.component_digests["material_state"] == checkpoint.accepted_state.component_digests[
        "material_state"
    ]


def test_t02d_10_continuation_digest_is_exact_after_restore(standard_run: tuple[Any, Any]) -> None:
    checkpoint = NpzNonlinearCheckpointStore().load(_step_file(standard_run, 3))
    assert checkpoint.component_digests["continuation_state"] == checkpoint.accepted_state.component_digests[
        "continuation_state"
    ]


def test_t02d_11_previous_du_is_exact_after_restore(standard_run: tuple[Any, Any]) -> None:
    checkpoint = NpzNonlinearCheckpointStore().load(_step_file(standard_run, 3))
    previous_du = np.asarray(checkpoint.continuation_state["previous_du"], dtype=float)
    assert previous_du.shape == (3,)
    assert np.array_equal(previous_du, np.asarray(checkpoint.accepted_state.continuation_state["previous_du"]))


def test_t02d_12_previous_dlambda_is_exact_after_restore(standard_run: tuple[Any, Any]) -> None:
    checkpoint = NpzNonlinearCheckpointStore().load(_step_file(standard_run, 3))
    assert checkpoint.continuation_state["previous_dlambda"] == checkpoint.accepted_state.continuation_state[
        "previous_dlambda"
    ]


def test_t02d_13_radius_is_exact_after_restore(standard_run: tuple[Any, Any]) -> None:
    checkpoint = NpzNonlinearCheckpointStore().load(_step_file(standard_run, 3))
    assert checkpoint.continuation_state["radius"] == checkpoint.accepted_state.continuation_state["radius"]


def test_t02d_14_load_scale_is_exact_after_restore(standard_run: tuple[Any, Any]) -> None:
    checkpoint = NpzNonlinearCheckpointStore().load(_step_file(standard_run, 3))
    assert checkpoint.continuation_state["load_scale"] == checkpoint.accepted_state.continuation_state["load_scale"]


def test_t02d_15_accepted_load_factor_is_exact_after_restore(standard_run: tuple[Any, Any]) -> None:
    checkpoint = NpzNonlinearCheckpointStore().load(_step_file(standard_run, 3))
    assert checkpoint.load_factor == checkpoint.accepted_state.load_factor
    assert checkpoint.continuation_state["load_factor"] == checkpoint.load_factor


def test_t02d_16_failed_restore_does_not_mutate_runtime_state(
    standard_run: tuple[Any, Any], tmp_path: Path
) -> None:
    model, _reference = standard_run
    bad = tmp_path / "tampered.npz"
    _tamper_composite_digest(_step_file(standard_run, 2), bad)
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "output.npz"),
            "restart_from": str(bad),
            "checkpoint_keep_steps": False,
        }
    )
    session = NonlinearCheckpointSession.create(restarted, 6, NpzNonlinearCheckpointStore())
    initial = NonlinearState(
        displacement=np.zeros(restarted.dof_manager().ndof),
        material_state=initial_material_states(restarted),
    )
    before = initial.digest
    with pytest.raises(NumericalConvergenceError) as raised:
        session.restore_state(initial, require_continuation=True)
    assert raised.value.reason is NonlinearFailureReason.STATE_CORRUPTION
    assert initial.digest == before
    assert session.restart_step == 0


def test_t02d_17_rejected_arc_trial_is_never_persisted(rejection_run: tuple[Any, Any]) -> None:
    _model, result = rejection_run
    files = [Path(str(raw)) for raw in result.solver["checkpoint_files"]]
    accepted_steps = sorted(
        int(path.name.split(".step", 1)[1].split(".npz", 1)[0])
        for path in files
        if ".step" in path.name
    )
    assert accepted_steps == list(range(1, 7))
    assert all(NpzNonlinearCheckpointStore().load(path).completed_step in accepted_steps for path in files)


def test_t02d_18_minimum_radius_failure_preserves_last_accepted_checkpoint(
    standard_run: tuple[Any, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, _reference = standard_run
    source = _step_file(standard_run, 1)
    before = NpzNonlinearCheckpointStore().load(source).composite_digest
    failing = deepcopy(model)
    failing.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "terminal.npz"),
            "restart_from": str(source),
            "checkpoint_keep_steps": True,
        }
    )

    def always_fail(*args: Any, **kwargs: Any) -> Any:
        raise NumericalConvergenceError("controlled minimum-radius failure", reason=NonlinearFailureReason.MAX_ITERATIONS)

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_arc_length_step", always_fail)
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_model(failing, enforce_policy=False)
    assert raised.value.reason is NonlinearFailureReason.ARC_LENGTH_FAILURE
    assert NpzNonlinearCheckpointStore().load(source).composite_digest == before


def test_t02d_19_checkpoint_write_failure_does_not_trigger_radius_cutback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[tuple[int, NonlinearState]] = []

    def fail_save(self: Any, step: int, accepted_state: NonlinearState, *args: Any, **kwargs: Any) -> None:
        calls.append((step, accepted_state.detached_copy()))
        raise NumericalConvergenceError("checkpoint infrastructure failure", reason=NonlinearFailureReason.CHECKPOINT_FAILURE)

    monkeypatch.setattr(NonlinearCheckpointSession, "save_state", fail_save)
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_model(
            _arc_model(
                checkpoint_path=str(tmp_path / "failure.npz"),
                checkpoint_interval=1,
            ),
            enforce_policy=False,
        )
    assert raised.value.reason is NonlinearFailureReason.CHECKPOINT_FAILURE
    assert len(calls) == 1
    assert calls[0][0] == 1
    assert calls[0][1].continuation_state["accepted_step"] == 1


def test_t02d_20_checkpoint_write_failure_preserves_accepted_runtime_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commits: list[NonlinearState] = []
    original_commit = UnifiedContinuationController.commit

    def commit_spy(self: Any) -> NonlinearState:
        accepted = original_commit(self)
        commits.append(accepted.detached_copy())
        return accepted

    def fail_save(self: Any, step: int, accepted_state: NonlinearState, *args: Any, **kwargs: Any) -> None:
        raise NumericalConvergenceError("checkpoint infrastructure failure", reason=NonlinearFailureReason.CHECKPOINT_FAILURE)

    monkeypatch.setattr(UnifiedContinuationController, "commit", commit_spy)
    monkeypatch.setattr(NonlinearCheckpointSession, "save_state", fail_save)
    with pytest.raises(NumericalConvergenceError) as raised:
        solve_model(
            _arc_model(
                checkpoint_path=str(tmp_path / "failure-runtime.npz"),
                checkpoint_interval=1,
            ),
            enforce_policy=False,
        )
    assert raised.value.reason is NonlinearFailureReason.CHECKPOINT_FAILURE
    assert len(commits) == 1
    assert commits[0].continuation_state["accepted_step"] == 1


def test_t02d_21_supported_v1_arc_checkpoint_migrates(
    standard_run: tuple[Any, Any], tmp_path: Path
) -> None:
    model, _reference = standard_run
    v1 = tmp_path / "legacy.npz"
    _write_v1_checkpoint(model, _step_file(standard_run, 2), v1)
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "v2-output.npz"),
            "restart_from": str(v1),
            "checkpoint_keep_steps": True,
        }
    )
    resumed = solve_model(restarted, enforce_policy=False)
    assert resumed.solver["restart_step"] == 2
    assert resumed.solver["checkpoint_files"]


def test_t02d_22_incomplete_v1_arc_checkpoint_is_rejected(
    standard_run: tuple[Any, Any], tmp_path: Path
) -> None:
    model, _reference = standard_run
    v1 = tmp_path / "incomplete.npz"
    _write_v1_checkpoint(model, _step_file(standard_run, 2), v1, incomplete=True)
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "rejected.npz"),
            "restart_from": str(v1),
            "checkpoint_keep_steps": False,
        }
    )
    with pytest.raises(InputValidationError, match="incomplete"):
        solve_model(restarted, enforce_policy=False)


def test_t02d_23_v1_resumed_arc_run_writes_v2(
    standard_run: tuple[Any, Any], tmp_path: Path
) -> None:
    model, _reference = standard_run
    v1 = tmp_path / "legacy.npz"
    output = tmp_path / "resumed-v2.npz"
    _write_v1_checkpoint(model, _step_file(standard_run, 2), v1)
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(output),
            "restart_from": str(v1),
            "checkpoint_keep_steps": False,
        }
    )
    solve_model(restarted, enforce_policy=False)
    with np.load(output, allow_pickle=False) as data:
        metadata = json.loads(str(data["metadata_json"].item()))
    assert metadata["schema_version"] == 2


def test_t02d_24_turning_branch_direction_is_preserved_after_restart(
    standard_run: tuple[Any, Any], tmp_path: Path
) -> None:
    _model, reference = standard_run
    checkpoint = NpzNonlinearCheckpointStore().load(_step_file(standard_run, 2))
    _restarted, resumed = _restart_from(standard_run, tmp_path, 2)
    reference_direction = np.sign(float(checkpoint.continuation_state["previous_dlambda"]))
    resumed_first = np.sign(float(resumed.solver["steps"][0]["load_increment"]))
    assert resumed_first == reference_direction
    _assert_path_equivalence(reference, resumed, 2)


def test_t02d_25_two_identical_restart_runs_have_same_terminal_digest(
    standard_run: tuple[Any, Any], tmp_path: Path
) -> None:
    _first_model, first = _restart_from(standard_run, tmp_path / "one", 2, name="one")
    _second_model, second = _restart_from(standard_run, tmp_path / "two", 2, name="two")
    first_file = Path(str(first.solver["checkpoint_path"]))
    second_file = Path(str(second.solver["checkpoint_path"]))
    first_checkpoint = NpzNonlinearCheckpointStore().load(first_file)
    second_checkpoint = NpzNonlinearCheckpointStore().load(second_file)
    assert first_checkpoint.composite_digest == second_checkpoint.composite_digest


def test_t02d_26_retained_files_are_accepted_steps_only(rejection_run: tuple[Any, Any]) -> None:
    _model, result = rejection_run
    paths = [Path(str(raw)) for raw in result.solver["checkpoint_files"]]
    retained = [path for path in paths if ".step" in path.name]
    assert retained
    completed_steps = [NpzNonlinearCheckpointStore().load(path).completed_step for path in retained]
    assert completed_steps == list(range(1, 7))


def test_t02d_27_legacy_restore_continuation_delegates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _arc_model()
    session = NonlinearCheckpointSession.create(model, 6, NpzNonlinearCheckpointStore())
    calls: list[NonlinearState] = []
    original = NonlinearCheckpointSession.restore_state

    def spy(self: Any, initial_state: NonlinearState, *args: Any, **kwargs: Any) -> NonlinearState:
        calls.append(initial_state.detached_copy())
        return original(self, initial_state, *args, **kwargs)

    monkeypatch.setattr(NonlinearCheckpointSession, "restore_state", spy)
    displacement = np.zeros(model.dof_manager().ndof)
    session.restore_continuation(displacement, initial_material_states(model), 1.0)
    assert len(calls) == 1
    assert "restore_continuation" not in inspect.getsource(NonlinearStaticSolver.solve)


def test_t02d_28_legacy_save_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _arc_model()
    session = NonlinearCheckpointSession.create(model, 6, NpzNonlinearCheckpointStore())
    calls: list[NonlinearState] = []
    original = NonlinearCheckpointSession.save_state

    def spy(self: Any, step: int, accepted_state: NonlinearState, *args: Any, **kwargs: Any) -> None:
        calls.append(accepted_state.detached_copy())
        original(self, step, accepted_state, *args, **kwargs)

    monkeypatch.setattr(NonlinearCheckpointSession, "save_state", spy)
    session.save(
        1,
        0.25,
        np.zeros(model.dof_manager().ndof),
        initial_material_states(model),
        continuation_state={"accepted_step": 1},
    )
    assert len(calls) == 1
    assert calls[0].load_factor == 0.25
