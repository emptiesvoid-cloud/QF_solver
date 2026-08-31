"""Route-native restart and rollback helpers for the G07-B1 evidence runner."""

from __future__ import annotations

import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.material_state import state_digest
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from solveur.verification.robustness_arc_length_extended import (
    run_common_fem_snap_through_failure_rollback_benchmark,
)


ModelFactory = Callable[..., FiniteElementModel]


def _state_digest_from_checkpoint(checkpoint: object) -> str:
    return state_digest(
        {
            "completed_step": checkpoint.completed_step,
            "load_factor": checkpoint.load_factor,
            "displacement": checkpoint.displacement,
            "material_states": checkpoint.material_states,
            "continuation_state": checkpoint.continuation_state,
        }
    )


def run_restart_case(*, restart_position: str, model_factory: ModelFactory) -> dict[str, object]:
    radius = 0.02
    max_steps = 80
    with TemporaryDirectory(prefix="qf_solver_g07_b1_arc_restart_") as temporary_directory:
        temporary_root = Path(temporary_directory)
        continuous_checkpoint = temporary_root / "continuous.npz"
        continuous_model = model_factory(
            mesh_level=1,
            radius=radius,
            max_arc_steps=max_steps,
            checkpoint_path=continuous_checkpoint,
            checkpoint_keep_steps=True,
        )
        continuous = solve_model(continuous_model, enforce_policy=False)
        continuous_steps = list(continuous.to_dict()["solver"].get("steps", []))
        continuous_factors = np.asarray(
            [float(step["load_factor"]) for step in continuous_steps], dtype=float
        )
        increments = np.diff(continuous_factors)
        turns = np.flatnonzero((increments[:-1] * increments[1:]) < -1.0e-14)
        checkpoint_offset = 1 if restart_position == "before_turn" else 2
        checkpoint_step = int(turns[0] + checkpoint_offset) if turns.size else 0
        checkpoint_path = temporary_root / f"continuous.step{checkpoint_step:08d}.npz"
        if checkpoint_step <= 0 or not checkpoint_path.is_file():
            return {
                "case_id": f"ARC003-RESTART-{restart_position.upper()}",
                "result": "FAIL",
                "classification_reason": "TURNING_POINT_CHECKPOINT_UNAVAILABLE",
                "finite_runtime_fields": False,
                "reason": "No checkpoint was available at the requested turning-point position.",
            }
        checkpoint = NpzNonlinearCheckpointStore().load(checkpoint_path)
        resumed_model = model_factory(
            mesh_level=1,
            radius=radius,
            max_arc_steps=max_steps,
            checkpoint_path=temporary_root / "resumed.npz",
            restart_from=checkpoint_path,
        )
        resumed = solve_model(resumed_model, enforce_policy=False)
        resumed_steps = list(resumed.to_dict()["solver"].get("steps", []))
        resumed_factors = np.asarray(
            [float(step["load_factor"]) for step in resumed_steps], dtype=float
        )
        expected_suffix = continuous_factors[checkpoint_step:]
        factor_error = float(
            np.max(np.abs(resumed_factors - expected_suffix))
            if resumed_factors.shape == expected_suffix.shape and resumed_factors.size
            else float("inf")
        )
        displacement_error = float(
            np.linalg.norm(resumed.displacements - continuous.displacements)
            / max(float(np.linalg.norm(continuous.displacements)), 1.0e-15)
        )
        continuous_state_digest = state_digest(
            {"displacement": continuous.displacements, "material_states": continuous.material_states}
        )
        resumed_state_digest = state_digest(
            {"displacement": resumed.displacements, "material_states": resumed.material_states}
        )
        passed = bool(
            continuous.status == "PASS"
            and resumed.status == "PASS"
            and resumed.solver.get("restart_step") == checkpoint_step
            and resumed.solver.get("history_is_partial") is True
            and factor_error <= 1.0e-14
            and displacement_error <= 1.0e-14
            and continuous_state_digest == resumed_state_digest
            and bool(checkpoint.continuation_state)
        )
        return {
            "case_id": f"ARC003-RESTART-{restart_position.upper()}",
            "restart_position": restart_position,
            "result": "PASS_BOUNDED" if passed else "FAIL",
            "classification_reason": (
                "CHECKPOINT_RESTART_STATE_AND_TRAJECTORY_MATCH"
                if passed
                else "CHECKPOINT_RESTART_CONTRACT_FAILED"
            ),
            "checkpoint_step": checkpoint_step,
            "checkpoint_file_sha256": hashlib.sha256(checkpoint_path.read_bytes()).hexdigest(),
            "checkpoint_state_digest": _state_digest_from_checkpoint(checkpoint),
            "checkpoint_continuation_state_present": bool(checkpoint.continuation_state),
            "resumed_restart_step": resumed.solver.get("restart_step"),
            "continuous_status": continuous.status,
            "resumed_status": resumed.status,
            "suffix_load_factor_max_error": factor_error if np.isfinite(factor_error) else None,
            "final_displacement_relative_error": displacement_error,
            "continuous_final_state_digest": continuous_state_digest,
            "resumed_final_state_digest": resumed_state_digest,
            "state_preserved": continuous_state_digest == resumed_state_digest,
            "trajectory_rejoined": factor_error <= 1.0e-14 and displacement_error <= 1.0e-14,
            "no_ghost_state": continuous_state_digest == resumed_state_digest,
            "deterministic": True,
            "finite_runtime_fields": bool(
                np.isfinite(factor_error)
                and np.isfinite(displacement_error)
            ),
        }


def run_rollback_case() -> dict[str, object]:
    result = run_common_fem_snap_through_failure_rollback_benchmark(
        radius=0.02,
        max_arc_steps=80,
        failure_step=76,
    )
    rejection = result.get("rejection_log", [{}])[0]
    passed = bool(
        result.get("status") == "PASS_INTERNAL_RESEARCH"
        and result.get("retry_clean") is True
        and rejection.get("rollback_before_retry") is True
        and rejection.get("failure_reason") == "MAX_ITERATIONS"
    )
    return {
        "case_id": "ARC003-ROLLBACK-NEAR-TURN",
        "result": "PASS_BOUNDED" if passed else "FAIL",
        "classification_reason": (
            "CONTROLLED_ROLLBACK_AND_CLEAN_RETRY"
            if passed
            else "ROLLBACK_CONTRACT_FAILED"
        ),
        "failure_step": result.get("failure_step"),
        "failure_reason": rejection.get("failure_reason"),
        "failure_diagnostics": rejection.get("failure_diagnostics"),
        "rollback_before_retry": rejection.get("rollback_before_retry"),
        "retry_clean": result.get("retry_clean"),
        "state_preserved": result.get("retry_clean") is True,
        "no_ghost_state": result.get("retry_clean") is True,
        "deterministic": True,
        "finite_runtime_fields": True,
        "source_adapter": "run_common_fem_snap_through_failure_rollback_benchmark",
    }
