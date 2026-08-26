"""Adversarial checks for nonlinear checkpoint rejection contracts."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.core.nonlinear_checkpoint import (
    NonlinearCheckpoint,
    NonlinearCheckpointSession,
    NonlinearCheckpointSettings,
)
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore


def _checkpoint_failure_record(name: str, error: InputValidationError) -> dict[str, object]:
    """Represent a rejected checkpoint as a structured, non-converged failure."""

    return {
        "name": name,
        "passed": True,
        "converged": False,
        "failure_reason": NonlinearFailureReason.CHECKPOINT_FAILURE.value,
        "diagnostics": {
            "solver": "nonlinear_checkpoint",
            "error_type": type(error).__name__,
            "message": str(error),
        },
    }


def _failed_checkpoint_record(name: str) -> dict[str, object]:
    """Return the defensive result used if a rejection unexpectedly succeeds."""

    return {
        "name": name,
        "passed": False,
        "converged": True,
        "failure_reason": None,
        "diagnostics": {"solver": "nonlinear_checkpoint"},
    }


def run_checkpoint_failure_cases() -> list[dict[str, object]]:
    """Exercise corruption and model-mismatch rejection without changing the loader API."""

    store = NpzNonlinearCheckpointStore()
    with TemporaryDirectory(prefix="qf_solver_failure_checkpoint_") as directory:
        root = Path(directory)
        corrupted = root / "corrupted.npz"
        corrupted.write_bytes(b"not an npz")
        try:
            store.load(corrupted)
        except InputValidationError as error:
            corruption = _checkpoint_failure_record("checkpoint_corruption", error)
        else:  # pragma: no cover - defensive contract failure
            corruption = _failed_checkpoint_record("checkpoint_corruption")

        valid_path = root / "valid.npz"
        store.save(
            valid_path,
            NonlinearCheckpoint(
                model_signature="actual-model-signature",
                completed_step=1,
                load_factor=1.0,
                displacement=np.zeros(1),
                material_states={0: []},
            ),
        )
        session = NonlinearCheckpointSession(
            settings=NonlinearCheckpointSettings(None, 1, False, str(valid_path)),
            store=store,
            signature="different-model-signature",
            total_steps=1,
        )
        try:
            session.restore(np.zeros(1), {0: []}, [1.0])
        except InputValidationError as error:
            mismatch = _checkpoint_failure_record("checkpoint_model_mismatch", error)
        else:  # pragma: no cover - defensive contract failure
            mismatch = _failed_checkpoint_record("checkpoint_model_mismatch")
    return [corruption, mismatch]
