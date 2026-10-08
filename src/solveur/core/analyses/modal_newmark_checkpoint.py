"""Versioned, fail-closed checkpoint contract for modal Newmark states."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import shutil
from typing import Protocol

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.io.checkpoint_common import checkpoint_signature


MODAL_NEWMARK_CHECKPOINT_SCHEMA = "qf-modal-newmark-checkpoint/v1"


@dataclass(frozen=True)
class ModalNewmarkCheckpoint:
    """Accepted reduced state bound to exact physical and modal identities."""

    run_signature: str
    source_sha: str
    physical_identity: str
    operator_identity: str
    excitation_identity: str
    damping_identity: str
    basis_identity: str
    completed_step: int
    total_steps: int
    time: float
    time_step: float
    beta: float
    gamma: float
    initial_energy: float
    coordinates: np.ndarray
    velocity: np.ndarray
    acceleration: np.ndarray
    schema: str = MODAL_NEWMARK_CHECKPOINT_SCHEMA
    state_sha256: str = ""

    def validate(self, expected_modes: int | None = None) -> None:
        if self.schema != MODAL_NEWMARK_CHECKPOINT_SCHEMA:
            raise InputValidationError("Unsupported modal Newmark checkpoint schema.")
        required_identities = (
            self.run_signature,
            self.source_sha,
            self.physical_identity,
            self.operator_identity,
            self.excitation_identity,
            self.damping_identity,
            self.basis_identity,
        )
        if any(not isinstance(value, str) or not value for value in required_identities):
            raise InputValidationError("Modal Newmark checkpoint is missing a required execution identity.")
        if (
            isinstance(self.completed_step, bool)
            or isinstance(self.total_steps, bool)
            or self.completed_step < 0
            or self.total_steps <= 0
            or self.completed_step > self.total_steps
        ):
            raise InputValidationError("Modal Newmark checkpoint step metadata is invalid.")
        scalar_values = (self.time, self.time_step, self.beta, self.gamma, self.initial_energy)
        if not all(np.isfinite(value) for value in scalar_values) or self.time < 0.0 or self.time_step <= 0.0:
            raise InputValidationError("Modal Newmark checkpoint integration metadata is invalid.")
        arrays = (self.coordinates, self.velocity, self.acceleration)
        if any(value.ndim != 1 or value.size == 0 or not np.all(np.isfinite(value)) for value in arrays):
            raise InputValidationError("Modal Newmark checkpoint states must be non-empty finite vectors.")
        if len({value.size for value in arrays}) != 1:
            raise InputValidationError("Modal Newmark checkpoint state vectors have inconsistent dimensions.")
        if expected_modes is not None and arrays[0].size != expected_modes:
            raise InputValidationError("Modal Newmark checkpoint mode count does not match the retained basis.")
        digest = _state_digest(*arrays)
        if self.state_sha256 and self.state_sha256 != digest:
            raise InputValidationError("Modal Newmark checkpoint state content hash does not match its arrays.")


class ModalNewmarkCheckpointStore(Protocol):
    """Persistence interface for modal checkpoints, separate from direct states."""

    def signature(self, payload: dict[str, object]) -> str: ...

    def load(self, path: str | Path) -> ModalNewmarkCheckpoint: ...

    def save(
        self, path: str | Path, checkpoint: ModalNewmarkCheckpoint, *, keep_step: bool = False
    ) -> tuple[Path, ...]: ...


class NpzModalNewmarkCheckpointStore:
    """Atomic NPZ persistence; direct Newmark checkpoints are not accepted."""

    def signature(self, payload: dict[str, object]) -> str:
        return checkpoint_signature(payload, label="Modal Newmark")

    def save(
        self, path: str | Path, checkpoint: ModalNewmarkCheckpoint, *, keep_step: bool = False
    ) -> tuple[Path, ...]:
        checkpoint.validate()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.tmp.npz")
        metadata = {
            "schema": checkpoint.schema,
            "run_signature": checkpoint.run_signature,
            "source_sha": checkpoint.source_sha,
            "physical_identity": checkpoint.physical_identity,
            "operator_identity": checkpoint.operator_identity,
            "excitation_identity": checkpoint.excitation_identity,
            "damping_identity": checkpoint.damping_identity,
            "basis_identity": checkpoint.basis_identity,
            "completed_step": checkpoint.completed_step,
            "total_steps": checkpoint.total_steps,
            "time": checkpoint.time,
            "time_step": checkpoint.time_step,
            "beta": checkpoint.beta,
            "gamma": checkpoint.gamma,
            "initial_energy": checkpoint.initial_energy,
            "state_sha256": _state_digest(checkpoint.coordinates, checkpoint.velocity, checkpoint.acceleration),
        }
        np.savez_compressed(
            temporary,
            metadata_json=json.dumps(metadata, sort_keys=True, separators=(",", ":"), allow_nan=False),
            coordinates=np.asarray(checkpoint.coordinates, dtype=np.float64),
            velocity=np.asarray(checkpoint.velocity, dtype=np.float64),
            acceleration=np.asarray(checkpoint.acceleration, dtype=np.float64),
        )
        temporary.replace(target)
        written = [target]
        if keep_step:
            step_path = target.with_name(f"{target.stem}.step{checkpoint.completed_step:08d}{target.suffix}")
            shutil.copy2(target, step_path)
            written.append(step_path)
        return tuple(written)

    def load(self, path: str | Path) -> ModalNewmarkCheckpoint:
        source = Path(path)
        try:
            with np.load(source, allow_pickle=False) as data:
                metadata = json.loads(str(data["metadata_json"].item()))
                checkpoint = ModalNewmarkCheckpoint(
                    schema=str(metadata["schema"]),
                    run_signature=str(metadata["run_signature"]),
                    source_sha=str(metadata["source_sha"]),
                    physical_identity=str(metadata["physical_identity"]),
                    operator_identity=str(metadata["operator_identity"]),
                    excitation_identity=str(metadata["excitation_identity"]),
                    damping_identity=str(metadata["damping_identity"]),
                    basis_identity=str(metadata["basis_identity"]),
                    completed_step=int(metadata["completed_step"]),
                    total_steps=int(metadata["total_steps"]),
                    time=float(metadata["time"]),
                    time_step=float(metadata["time_step"]),
                    beta=float(metadata["beta"]),
                    gamma=float(metadata["gamma"]),
                    initial_energy=float(metadata["initial_energy"]),
                    coordinates=np.asarray(data["coordinates"], dtype=np.float64),
                    velocity=np.asarray(data["velocity"], dtype=np.float64),
                    acceleration=np.asarray(data["acceleration"], dtype=np.float64),
                    state_sha256=str(metadata["state_sha256"]),
                )
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise InputValidationError(
                f"Cannot read modal Newmark checkpoint {source}: unsupported, incompatible or corrupted NPZ."
            ) from exc
        if not checkpoint.state_sha256:
            raise InputValidationError("Modal Newmark checkpoint is missing its required state content hash.")
        checkpoint.validate()
        expected_time = checkpoint.completed_step * checkpoint.time_step
        if not np.isclose(checkpoint.time, expected_time, rtol=0.0, atol=1.0e-12 * max(1.0, expected_time)):
            raise InputValidationError("Modal Newmark checkpoint time does not match its completed step.")
        return checkpoint


def _state_digest(*arrays: np.ndarray) -> str:
    digest = hashlib.sha256()
    for label, raw in zip(("coordinates", "velocity", "acceleration"), arrays, strict=True):
        values = np.asarray(raw, dtype="<f8")
        digest.update(label.encode("ascii"))
        digest.update(np.asarray(values.shape, dtype="<i8").tobytes())
        digest.update(values.tobytes(order="C"))
    return digest.hexdigest()
