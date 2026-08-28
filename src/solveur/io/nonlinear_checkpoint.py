"""Atomic NPZ persistence for nonlinear static checkpoints."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.core.material_state import MaterialStateTable, copy_material_states
from solveur.core.nonlinear_checkpoint import NonlinearCheckpoint
from solveur.io.checkpoint_common import checkpoint_signature


class NpzNonlinearCheckpointStore:
    """Persist committed displacements and integration-point states."""

    def signature(self, payload: dict[str, object]) -> str:
        return checkpoint_signature(payload, label="Nonlinear")

    def save(
        self, path: str | Path, checkpoint: NonlinearCheckpoint, *, keep_step: bool = False
    ) -> tuple[Path, ...]:
        checkpoint.validate()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.tmp.npz")
        metadata = {
            "schema_version": checkpoint.schema_version,
            "model_signature": checkpoint.model_signature,
            "completed_step": checkpoint.completed_step,
            "load_factor": checkpoint.load_factor,
            "material_states": checkpoint.material_states,
            "continuation_state": checkpoint.continuation_state,
        }
        np.savez_compressed(
            temporary,
            metadata_json=json.dumps(metadata, sort_keys=True, allow_nan=False),
            displacement=checkpoint.displacement,
        )
        temporary.replace(target)
        written = [target]
        if keep_step:
            step_path = target.with_name(f"{target.stem}.step{checkpoint.completed_step:08d}{target.suffix}")
            shutil.copy2(target, step_path)
            written.append(step_path)
        return tuple(written)

    def load(self, path: str | Path) -> NonlinearCheckpoint:
        source = Path(path)
        try:
            with np.load(source, allow_pickle=False) as data:
                metadata = json.loads(str(data["metadata_json"].item()))
                checkpoint = NonlinearCheckpoint(
                    schema_version=int(metadata["schema_version"]),
                    model_signature=str(metadata["model_signature"]),
                    completed_step=int(metadata["completed_step"]),
                    load_factor=float(metadata["load_factor"]),
                    displacement=np.asarray(data["displacement"], dtype=float),
                    material_states=_restore_material_states(metadata["material_states"]),
                    continuation_state=dict(metadata.get("continuation_state", {})),
                )
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"Cannot read nonlinear checkpoint {source}: invalid or corrupted NPZ.") from exc
        checkpoint.validate()
        return checkpoint


def _restore_material_states(raw: object) -> MaterialStateTable:
    if not isinstance(raw, dict):
        raise InputValidationError("Nonlinear checkpoint material states are invalid.")
    try:
        restored = {int(element): points for element, points in raw.items()}
    except (TypeError, ValueError) as exc:
        raise InputValidationError("Nonlinear checkpoint element identifiers are invalid.") from exc
    return copy_material_states(restored)
