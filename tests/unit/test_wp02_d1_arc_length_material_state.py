"""WP02-D1 checks for arc-length restart material-state ownership."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.driver import UnifiedContinuationController
from solveur.core.nonlinear.solver import NonlinearStaticSolver
from solveur.core.nonlinear.state import deterministic_state_digest
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from solveur.post.stress import StressPostProcessor
from solveur.verification.robustness_nonlinear_solids import _refinement_model
from tests.unit.test_analysis_features import nonlinear_tet4_model


def _path_dependent_arc_model(checkpoint_path: Path, *, max_arc_steps: int = 6) -> Any:
    model = _refinement_model("TET4", 1)
    parameters = {**model.analysis.parameters}
    parameters.pop("load_path", None)
    parameters.update(
        {
            "load_steps": 3,
            "max_arc_steps": max_arc_steps,
            "max_iterations": 40,
            "tolerance": 1.0e-7,
            "kinematics": "total_lagrangian_j2",
            "arc_length_stop_mode": "max_steps",
            "arc_length_allow_load_factor_turning": True,
            "arc_length_load_factor_limit": 5.0,
            "arc_length_radius": 0.02,
            "max_arc_length_radius": 0.05,
            "min_arc_length_radius": 1.0e-8,
            "checkpoint_path": str(checkpoint_path),
            "checkpoint_interval": 1,
            "checkpoint_keep_steps": True,
        }
    )
    model.analysis = replace(model.analysis, method="arc_length", parameters=parameters)
    return model


@pytest.fixture(scope="module")
def path_dependent_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Any]:
    root = tmp_path_factory.mktemp("wp02d1-path-dependent")
    model = _path_dependent_arc_model(root / "continuous.npz")
    return model, solve_model(model, enforce_policy=False)


@pytest.fixture(scope="module")
def path_dependent_short_run(tmp_path_factory: pytest.TempPathFactory) -> tuple[Any, Any]:
    root = tmp_path_factory.mktemp("wp02d1-path-dependent-short")
    model = _path_dependent_arc_model(root / "continuous.npz", max_arc_steps=3)
    return model, solve_model(model, enforce_policy=False)


def _step_file(result: Any, step: int) -> Path:
    suffix = f".step{step:08d}.npz"
    for raw_path in result.solver["checkpoint_files"]:
        path = Path(str(raw_path))
        if path.name.endswith(suffix):
            return path
    raise AssertionError(f"No retained checkpoint for accepted step {step}.")


def _restart_model(
    model: Any,
    result: Any,
    output_path: Path,
    step: int,
    *,
    max_arc_steps: int | None = None,
) -> Any:
    restarted = deepcopy(model)
    parameters = {
        **restarted.analysis.parameters,
        "checkpoint_path": str(output_path),
        "restart_from": str(_step_file(result, step)),
        "checkpoint_interval": 1,
        "checkpoint_keep_steps": True,
    }
    if max_arc_steps is not None:
        parameters["max_arc_steps"] = max_arc_steps
    restarted.analysis = replace(restarted.analysis, parameters=parameters)
    return restarted


def _digest(states: Any) -> str:
    return deterministic_state_digest(states)


def _final_checkpoint(result: Any) -> Any:
    return NpzNonlinearCheckpointStore().load(Path(str(result.solver["checkpoint_path"])))


def _run_rejected_restart(
    model: Any,
    result: Any,
    output_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    max_arc_steps: int | None = None,
) -> tuple[Any, list[tuple[str, str]]]:
    outer: dict[str, Any] = {}
    rollback_digests: list[tuple[str, str]] = []
    original_solve = NonlinearStaticSolver._solve_arc_length
    original_step = NonlinearStaticSolver._solve_arc_length_step
    original_rollback = UnifiedContinuationController.rollback
    calls = {"step": 0}

    def solve_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        outer["material_states"] = args[5]
        return original_solve(self, *args, **kwargs)

    def reject_once(self: Any, *args: Any, **kwargs: Any) -> Any:
        if calls["step"] == 0:
            calls["step"] += 1
            raise NumericalConvergenceError(
                "controlled WP02-D1 arc-length rejection",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
            )
        return original_step(self, *args, **kwargs)

    def rollback_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        before = _digest(outer["material_states"])
        returned = original_rollback(self, *args, **kwargs)
        after = _digest(outer["material_states"])
        rollback_digests.append((before, after))
        return returned

    monkeypatch.setattr(NonlinearStaticSolver, "_solve_arc_length", solve_spy)
    monkeypatch.setattr(NonlinearStaticSolver, "_solve_arc_length_step", reject_once)
    monkeypatch.setattr(UnifiedContinuationController, "rollback", rollback_spy)
    restarted = _restart_model(model, result, output_path, 2, max_arc_steps=max_arc_steps)
    return solve_model(restarted, enforce_policy=False), rollback_digests


def test_d1_01_restart_material_state_is_caller_visible(
    path_dependent_short_run: tuple[Any, Any], tmp_path: Path
) -> None:
    model, reference = path_dependent_short_run
    resumed = solve_model(_restart_model(model, reference, tmp_path / "initial.npz", 2), enforce_policy=False)
    checkpoint = NpzNonlinearCheckpointStore().load(_step_file(reference, 3))
    assert _digest(resumed.material_states) == checkpoint.component_digests["material_state"]


def test_d1_02_one_post_restart_increment_matches_controller_accepted_material(
    path_dependent_short_run: tuple[Any, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, reference = path_dependent_short_run
    accepted: list[Any] = []
    original_commit = UnifiedContinuationController.commit

    def commit_spy(self: Any) -> Any:
        state = original_commit(self)
        accepted.append(state.detached_copy())
        return state

    monkeypatch.setattr(UnifiedContinuationController, "commit", commit_spy)
    resumed = solve_model(_restart_model(model, reference, tmp_path / "one.npz", 2), enforce_policy=False)
    assert len(accepted) == 1
    assert _digest(resumed.material_states) == _digest(accepted[-1].material_state)


def test_d1_03_multiple_post_restart_increments_match_controller_accepted_material(
    path_dependent_run: tuple[Any, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, reference = path_dependent_run
    accepted: list[Any] = []
    original_commit = UnifiedContinuationController.commit

    def commit_spy(self: Any) -> Any:
        state = original_commit(self)
        accepted.append(state.detached_copy())
        return state

    monkeypatch.setattr(UnifiedContinuationController, "commit", commit_spy)
    resumed = solve_model(_restart_model(model, reference, tmp_path / "multiple.npz", 2), enforce_policy=False)
    assert len(accepted) == len(resumed.solver["steps"]) == 4
    assert _digest(resumed.material_states) == _digest(accepted[-1].material_state)


def test_d1_04_rejected_increment_does_not_change_caller_material_state(
    path_dependent_run: tuple[Any, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, reference = path_dependent_run
    resumed, rollback_digests = _run_rejected_restart(model, reference, tmp_path / "rejected.npz", monkeypatch)
    assert rollback_digests
    assert all(before == after for before, after in rollback_digests)
    assert resumed.solver["rejected_increments"] == 1


def test_d1_05_rollback_retry_publishes_only_final_accepted_material(
    path_dependent_run: tuple[Any, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, reference = path_dependent_run
    resumed, _rollback_digests = _run_rejected_restart(model, reference, tmp_path / "retry.npz", monkeypatch)
    checkpoint = _final_checkpoint(resumed)
    assert _digest(resumed.material_states) == checkpoint.component_digests["material_state"]
    assert checkpoint.completed_step == 6


def test_d1_06_path_dependent_arc_restart_matches_continuous_material_digest(
    path_dependent_run: tuple[Any, Any], tmp_path: Path
) -> None:
    model, reference = path_dependent_run
    resumed = solve_model(_restart_model(model, reference, tmp_path / "equivalence.npz", 2), enforce_policy=False)
    assert _digest(resumed.material_states) == _digest(reference.material_states)
    np.testing.assert_allclose(resumed.displacements, reference.displacements, rtol=1.0e-9, atol=1.0e-12)


def test_d1_07_postprocess_receives_final_accepted_material(
    path_dependent_run: tuple[Any, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, reference = path_dependent_run
    observed: list[str] = []
    original = StressPostProcessor.element_results

    def element_results_spy(self: Any, model: Any, dofs: Any, displacement: Any, material_states: Any = None) -> Any:
        observed.append(_digest(material_states))
        return original(self, model, dofs, displacement, material_states)

    monkeypatch.setattr(StressPostProcessor, "element_results", element_results_spy)
    resumed = solve_model(_restart_model(model, reference, tmp_path / "post.npz", 2), enforce_policy=False)
    assert observed
    assert observed[-1] == _digest(resumed.material_states) == _final_checkpoint(resumed).component_digests["material_state"]


def test_d1_08_final_internal_tangent_receives_final_accepted_material(
    path_dependent_run: tuple[Any, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model, reference = path_dependent_run
    observed: list[str] = []
    original = NonlinearStaticSolver._assemble_internal_tangent

    def assembly_spy(self: Any, *args: Any, **kwargs: Any) -> Any:
        if len(args) >= 4:
            observed.append(_digest(args[3]))
        return original(self, *args, **kwargs)

    monkeypatch.setattr(NonlinearStaticSolver, "_assemble_internal_tangent", assembly_spy)
    resumed = solve_model(_restart_model(model, reference, tmp_path / "assembly.npz", 2), enforce_policy=False)
    assert observed
    assert observed[-1] == _digest(resumed.material_states) == _final_checkpoint(resumed).component_digests["material_state"]


def test_d1_09_final_checkpoint_matches_final_accepted_material(
    path_dependent_run: tuple[Any, Any], tmp_path: Path
) -> None:
    model, reference = path_dependent_run
    resumed = solve_model(_restart_model(model, reference, tmp_path / "checkpoint.npz", 2), enforce_policy=False)
    checkpoint = _final_checkpoint(resumed)
    assert checkpoint.component_digests["material_state"] == _digest(resumed.material_states)
    assert checkpoint.accepted_state.component_digests["material_state"] == _digest(resumed.material_states)


def test_d1_10_elastic_arc_results_are_unchanged(
    tmp_path: Path,
) -> None:
    base = nonlinear_tet4_model(method="arc_length")
    parameters = {
        **base.analysis.parameters,
        "max_arc_steps": 4,
        "arc_length_stop_mode": "max_steps",
        "arc_length_allow_load_factor_turning": True,
        "checkpoint_path": str(tmp_path / "elastic.npz"),
        "checkpoint_interval": 1,
        "checkpoint_keep_steps": True,
    }
    first = deepcopy(base)
    first.analysis = replace(first.analysis, parameters=parameters)
    second = deepcopy(first)
    second.analysis = replace(
        second.analysis,
        parameters={**parameters, "checkpoint_path": str(tmp_path / "elastic-second.npz")},
    )
    first_result = solve_model(first, enforce_policy=False)
    second_result = solve_model(second, enforce_policy=False)
    np.testing.assert_array_equal(first_result.displacements, second_result.displacements)
    assert [step["load_factor"] for step in first_result.solver["steps"]] == [
        step["load_factor"] for step in second_result.solver["steps"]
    ]
    assert first_result.element_results == second_result.element_results
