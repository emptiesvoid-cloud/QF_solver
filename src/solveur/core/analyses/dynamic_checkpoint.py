"""Storage-neutral checkpoint contracts for transient dynamics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from solveur.core.errors import InputValidationError


@dataclass(frozen=True)
class DynamicCheckpoint:
    """Restartable Newmark state at one completed time step."""

    model_signature: str
    completed_step: int
    time: float
    time_step: float
    beta: float
    gamma: float
    initial_energy: float
    displacement: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray
    schema_version: int = 1

    def validate(self, expected_dofs: int | None = None) -> None:
        if self.schema_version != 1 or not self.model_signature:
            raise InputValidationError("Unsupported or incomplete dynamic checkpoint metadata.")
        if self.completed_step < 0 or self.time < 0.0 or self.time_step <= 0.0:
            raise InputValidationError("Dynamic checkpoint step and time metadata are invalid.")
        vectors = (self.displacement, self.velocity, self.acceleration)
        if any(vector.ndim != 1 or not np.all(np.isfinite(vector)) for vector in vectors):
            raise InputValidationError("Dynamic checkpoint state vectors must be finite one-dimensional arrays.")
        if len({vector.size for vector in vectors}) != 1:
            raise InputValidationError("Dynamic checkpoint state vectors have inconsistent sizes.")
        if expected_dofs is not None and vectors[0].size != expected_dofs:
            raise InputValidationError(
                f"Dynamic checkpoint has {vectors[0].size} dofs; the model requires {expected_dofs}."
            )


class DynamicCheckpointStore(Protocol):
    """Persistence boundary injected into the numerical solver."""

    def signature(self, payload: dict[str, object]) -> str: ...

    def load(self, path: str | Path) -> DynamicCheckpoint: ...

    def save(
        self, path: str | Path, checkpoint: DynamicCheckpoint, *, keep_step: bool = False
    ) -> tuple[Path, ...]: ...


@dataclass(frozen=True)
class DynamicCheckpointSettings:
    """Validated checkpoint controls extracted from analysis parameters."""

    path: str | None
    interval: int
    keep_steps: bool
    restart_from: str | None

    @classmethod
    def from_parameters(cls, parameters: dict[str, object], total_steps: int) -> "DynamicCheckpointSettings":
        path = _optional_path(parameters.get("checkpoint_path"), "checkpoint_path")
        restart = _optional_path(parameters.get("restart_from"), "restart_from")
        keep = parameters.get("checkpoint_keep_steps", False)
        if not isinstance(keep, bool):
            raise InputValidationError("checkpoint_keep_steps must be a boolean.")
        if "checkpoint_interval" in parameters and path is None:
            raise InputValidationError("checkpoint_interval requires checkpoint_path.")
        interval = total_steps
        if path is not None and "checkpoint_interval" in parameters:
            value = parameters["checkpoint_interval"]
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise InputValidationError("checkpoint_interval must be a positive integer.")
            interval = value
        if keep and path is None:
            raise InputValidationError("checkpoint_keep_steps requires checkpoint_path.")
        return cls(path=path, interval=interval, keep_steps=keep, restart_from=restart)

    @property
    def requires_store(self) -> bool:
        return self.path is not None or self.restart_from is not None

    def should_save(self, step: int, total_steps: int) -> bool:
        return self.path is not None and (step % self.interval == 0 or step == total_steps)


def _optional_path(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{name} must be a non-empty path string.")
    if Path(value).suffix.lower() != ".npz":
        raise InputValidationError(f"{name} must use the .npz format.")
    return value
