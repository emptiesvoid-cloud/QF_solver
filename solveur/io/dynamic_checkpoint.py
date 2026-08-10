"""Atomic NPZ persistence for Newmark checkpoints."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np

from solveur.core.dynamic_checkpoint import DynamicCheckpoint
from solveur.core.errors import InputValidationError
from solveur.io.checkpoint_common import checkpoint_signature


class NpzDynamicCheckpointStore:
    """Read and write compact, versioned transient states."""

    def signature(self, payload: dict[str, object]) -> str:
        return checkpoint_signature(payload, label="Dynamic")

    def save(
        self, path: str | Path, checkpoint: DynamicCheckpoint, *, keep_step: bool = False
    ) -> tuple[Path, ...]:
        checkpoint.validate()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.tmp.npz")
        metadata = {
            "schema_version": checkpoint.schema_version,
            "model_signature": checkpoint.model_signature,
            "completed_step": checkpoint.completed_step,
            "time": checkpoint.time,
            "time_step": checkpoint.time_step,
            "beta": checkpoint.beta,
            "gamma": checkpoint.gamma,
            "initial_energy": checkpoint.initial_energy,
        }
        np.savez_compressed(
            temporary,
            metadata_json=json.dumps(metadata, sort_keys=True),
            displacement=checkpoint.displacement,
            velocity=checkpoint.velocity,
            acceleration=checkpoint.acceleration,
        )
        temporary.replace(target)
        written = [target]
        if keep_step:
            step_path = target.with_name(f"{target.stem}.step{checkpoint.completed_step:08d}{target.suffix}")
            shutil.copy2(target, step_path)
            written.append(step_path)
        return tuple(written)

    def load(self, path: str | Path) -> DynamicCheckpoint:
        source = Path(path)
        try:
            with np.load(source, allow_pickle=False) as data:
                metadata = json.loads(str(data["metadata_json"].item()))
                checkpoint = DynamicCheckpoint(
                    schema_version=int(metadata["schema_version"]),
                    model_signature=str(metadata["model_signature"]),
                    completed_step=int(metadata["completed_step"]),
                    time=float(metadata["time"]),
                    time_step=float(metadata["time_step"]),
                    beta=float(metadata["beta"]),
                    gamma=float(metadata["gamma"]),
                    initial_energy=float(metadata["initial_energy"]),
                    displacement=np.asarray(data["displacement"], dtype=float),
                    velocity=np.asarray(data["velocity"], dtype=float),
                    acceleration=np.asarray(data["acceleration"], dtype=float),
                )
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"Cannot read dynamic checkpoint {source}: invalid or corrupted NPZ.") from exc
        checkpoint.validate()
        return checkpoint
