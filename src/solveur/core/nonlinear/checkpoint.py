"""Storage-neutral checkpoint contracts for nonlinear statics."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

import numpy as np

from solveur.core.errors import InfrastructureError, InputValidationError
from solveur.core.nonlinear.material_state import MaterialStateTable, copy_material_states
from solveur.core.model import FiniteElementModel


@dataclass(frozen=True)
class NonlinearCheckpoint:
    """Committed nonlinear state after one converged load increment."""

    model_signature: str
    completed_step: int
    load_factor: float
    displacement: np.ndarray
    material_states: MaterialStateTable
    continuation_state: dict[str, object] = field(default_factory=dict)
    schema_version: int = 1

    def validate(self, expected_dofs: int | None = None) -> None:
        if self.schema_version != 1 or not self.model_signature:
            raise InputValidationError("Unsupported or incomplete nonlinear checkpoint metadata.")
        if self.completed_step < 0 or not np.isfinite(self.load_factor):
            raise InputValidationError("Nonlinear checkpoint step or load factor is invalid.")
        if self.displacement.ndim != 1 or not np.all(np.isfinite(self.displacement)):
            raise InputValidationError("Nonlinear checkpoint displacement must be a finite vector.")
        if expected_dofs is not None and self.displacement.size != expected_dofs:
            raise InputValidationError(
                f"Nonlinear checkpoint has {self.displacement.size} dofs; the model requires {expected_dofs}."
            )
        _validate_material_states(self.material_states)
        if not isinstance(self.continuation_state, dict) or not _finite_tree(self.continuation_state):
            raise InputValidationError("Nonlinear checkpoint continuation state is invalid.")


class NonlinearCheckpointStore(Protocol):
    """Persistence boundary injected into the nonlinear solver."""

    def signature(self, payload: dict[str, object]) -> str: ...

    def load(self, path: str | Path) -> NonlinearCheckpoint: ...

    def save(
        self, path: str | Path, checkpoint: NonlinearCheckpoint, *, keep_step: bool = False
    ) -> tuple[Path, ...]: ...


@dataclass(frozen=True)
class NonlinearCheckpointSettings:
    """Validated checkpoint controls for fixed nonlinear load paths."""

    path: str | None
    interval: int
    keep_steps: bool
    restart_from: str | None

    @classmethod
    def from_parameters(cls, parameters: dict[str, object], total_steps: int) -> NonlinearCheckpointSettings:
        path = _optional_npz_path(parameters.get("checkpoint_path"), "checkpoint_path")
        restart = _optional_npz_path(parameters.get("restart_from"), "restart_from")
        keep = parameters.get("checkpoint_keep_steps", False)
        if not isinstance(keep, bool):
            raise InputValidationError("checkpoint_keep_steps must be a boolean.")
        raw_interval = parameters.get("checkpoint_interval", total_steps)
        if isinstance(raw_interval, bool) or not isinstance(raw_interval, int) or raw_interval <= 0:
            raise InputValidationError("checkpoint_interval must be a positive integer.")
        if "checkpoint_interval" in parameters and path is None:
            raise InputValidationError("checkpoint_interval requires checkpoint_path.")
        if keep and path is None:
            raise InputValidationError("checkpoint_keep_steps requires checkpoint_path.")
        return cls(path, raw_interval, keep, restart)

    @property
    def enabled(self) -> bool:
        return self.path is not None or self.restart_from is not None

    def should_save(self, step: int, total_steps: int) -> bool:
        return self.path is not None and (step % self.interval == 0 or step == total_steps)


@dataclass
class NonlinearCheckpointSession:
    """Coordinate signature validation, restart and atomic saves."""

    settings: NonlinearCheckpointSettings
    store: NonlinearCheckpointStore | None
    signature: str
    total_steps: int
    restart_step: int = 0
    files: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        model: FiniteElementModel,
        total_steps: int,
        store: NonlinearCheckpointStore | None,
    ) -> NonlinearCheckpointSession:
        settings = NonlinearCheckpointSettings.from_parameters(model.analysis.parameters, total_steps)
        if settings.enabled and store is None:
            raise InfrastructureError("Nonlinear checkpoint persistence is not configured.")
        signature = store.signature(_signature_payload(model)) if settings.enabled and store else ""
        return cls(settings, store, signature, total_steps)

    def restore(
        self,
        displacement: np.ndarray,
        material_states: MaterialStateTable,
        load_factors: list[float],
    ) -> tuple[np.ndarray, MaterialStateTable]:
        if self.settings.restart_from is None:
            return displacement, material_states
        checkpoint = self.store.load(self.settings.restart_from)  # type: ignore[union-attr]
        checkpoint.validate(displacement.size)
        if checkpoint.model_signature != self.signature:
            raise InputValidationError("Nonlinear checkpoint does not match the physical model or load path.")
        if checkpoint.completed_step > self.total_steps:
            raise InputValidationError("Nonlinear checkpoint is beyond the requested load path.")
        expected_factor = 0.0 if checkpoint.completed_step == 0 else load_factors[checkpoint.completed_step - 1]
        if not np.isclose(checkpoint.load_factor, expected_factor, rtol=0.0, atol=1.0e-14):
            raise InputValidationError("Nonlinear checkpoint load-factor metadata is inconsistent.")
        _validate_state_topology(material_states, checkpoint.material_states)
        self.restart_step = checkpoint.completed_step
        return checkpoint.displacement.copy(), copy_material_states(checkpoint.material_states)

    def restore_continuation(
        self,
        displacement: np.ndarray,
        material_states: MaterialStateTable,
        target_load_factor: float,
        load_factor_limit: float | None = None,
    ) -> tuple[np.ndarray, MaterialStateTable, dict[str, object] | None]:
        """Restore an arc-length checkpoint without assuming a fixed load path."""

        if self.settings.restart_from is None:
            return displacement, material_states, None
        checkpoint = self.store.load(self.settings.restart_from)  # type: ignore[union-attr]
        checkpoint.validate(displacement.size)
        if checkpoint.model_signature != self.signature:
            raise InputValidationError("Nonlinear checkpoint does not match the physical model or continuation path.")
        limit = abs(float(load_factor_limit)) if load_factor_limit is not None else max(abs(target_load_factor), 1.0)
        if not np.isfinite(limit) or limit <= 0.0:
            raise InputValidationError("Arc-length checkpoint load-factor limit must be finite and positive.")
        if abs(checkpoint.load_factor) > limit + 1.0e-12:
            raise InputValidationError("Arc-length checkpoint load factor is outside the requested continuation envelope.")
        _validate_state_topology(material_states, checkpoint.material_states)
        if not checkpoint.continuation_state:
            raise InputValidationError("Arc-length checkpoint does not contain continuation state.")
        self.restart_step = checkpoint.completed_step
        return (
            checkpoint.displacement.copy(),
            copy_material_states(checkpoint.material_states),
            dict(checkpoint.continuation_state),
        )

    def save(
        self,
        step: int,
        load_factor: float,
        displacement: np.ndarray,
        material_states: MaterialStateTable,
        continuation_state: dict[str, object] | None = None,
    ) -> None:
        if not self.settings.should_save(step, self.total_steps):
            return
        checkpoint = NonlinearCheckpoint(
            model_signature=self.signature,
            completed_step=step,
            load_factor=load_factor,
            displacement=displacement.copy(),
            material_states=copy_material_states(material_states),
            continuation_state=dict(continuation_state or {}),
        )
        written = self.store.save(  # type: ignore[union-attr]
            self.settings.path, checkpoint, keep_step=self.settings.keep_steps
        )
        self.files.extend(str(path) for path in written if str(path) not in self.files)


def _signature_payload(model: FiniteElementModel) -> dict[str, object]:
    excluded = {"checkpoint_path", "checkpoint_interval", "checkpoint_keep_steps", "restart_from"}
    parameters = {key: value for key, value in model.analysis.parameters.items() if key not in excluded}
    return {
        "schema_version": model.schema_version,
        "units": model.units,
        "nodes": model.nodes.tolist(),
        "elements": [asdict(element) for element in model.elements],
        "materials": model.materials,
        "fixed_dofs": [asdict(condition) for condition in model.fixed_dofs],
        "loads": [asdict(load) for load in model.loads],
        "distributed_loads": [asdict(load) for load in model.distributed_loads],
        "analysis": {"type": model.analysis.type, "method": model.analysis.method, "parameters": parameters},
    }


def _validate_state_topology(expected: MaterialStateTable, restored: MaterialStateTable) -> None:
    expected_shape = {element: len(points) for element, points in expected.items()}
    restored_shape = {element: len(points) for element, points in restored.items()}
    if restored_shape != expected_shape:
        raise InputValidationError("Nonlinear checkpoint material-state topology does not match the model.")


def _optional_npz_path(value: object, name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise InputValidationError(f"{name} must be a non-empty path string.")
    if Path(value).suffix.lower() != ".npz":
        raise InputValidationError(f"{name} must use the .npz format.")
    return value


def _validate_material_states(states: MaterialStateTable) -> None:
    if not isinstance(states, dict):
        raise InputValidationError("Nonlinear checkpoint material states must be a mapping.")
    for element, points in states.items():
        if not isinstance(element, int) or element < 0 or not isinstance(points, list):
            raise InputValidationError("Nonlinear checkpoint material-state topology is invalid.")
        for state in points:
            if not isinstance(state, dict) or not _finite_tree(state):
                raise InputValidationError("Nonlinear checkpoint contains invalid material-state values.")


def _finite_tree(value: object) -> bool:
    if isinstance(value, bool) or isinstance(value, str):
        return True
    if isinstance(value, (int, float)):
        return bool(np.isfinite(float(value)))
    if isinstance(value, list):
        return all(_finite_tree(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _finite_tree(item) for key, item in value.items())
    return False
