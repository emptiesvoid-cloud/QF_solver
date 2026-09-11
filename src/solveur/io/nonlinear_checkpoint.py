"""Atomic NPZ persistence for nonlinear checkpoint schema v2."""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.checkpoint import (
    NonlinearCheckpoint,
    NonlinearCheckpointV2,
    build_state_topology,
    migrate_v1_checkpoint,
    model_signature_v2,
)
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.state import (
    NonlinearState,
    canonical_state_payload,
    decode_canonical_state_payload,
)
from solveur.io.checkpoint_common import checkpoint_signature


class NpzNonlinearCheckpointStore:
    """Persist one validated accepted nonlinear state atomically.

    ``allow_pickle=False`` is retained as a hard boundary.  Schema-v1 input
    is read and promoted in memory; every write emitted by this store is
    schema v2.
    """

    def signature(self, payload: dict[str, object]) -> str:
        return checkpoint_signature(payload, label="Nonlinear")

    def save(
        self,
        path: str | Path,
        checkpoint: NonlinearCheckpoint | NonlinearCheckpointV2,
        *,
        keep_step: bool = False,
    ) -> tuple[Path, ...]:
        if isinstance(checkpoint, NonlinearCheckpoint):
            checkpoint = migrate_v1_checkpoint(checkpoint)
        if not isinstance(checkpoint, NonlinearCheckpointV2):
            raise InputValidationError("Unsupported nonlinear checkpoint object.")
        checkpoint.validate()
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        metadata = _v2_metadata(checkpoint)
        temporary = target.with_name(f".{target.name}.tmp.npz")
        try:
            with temporary.open("wb") as stream:
                np.savez_compressed(
                    stream,
                    metadata_json=json.dumps(metadata, sort_keys=True, allow_nan=False),
                )
                stream.flush()
                _fsync_file(stream)
            temporary.replace(target)
            _sync_directory(target.parent)
        except (OSError, TypeError, ValueError) as exc:
            _remove_if_present(temporary)
            raise NumericalConvergenceError(
                "Nonlinear checkpoint save failed; the previous canonical file was preserved.",
                reason=NonlinearFailureReason.CHECKPOINT_FAILURE,
                diagnostics={"canonical_path": str(target), "temporary_path": str(temporary)},
            ) from exc
        finally:
            _remove_if_present(temporary)

        written = [target]
        if keep_step:
            step_path = target.with_name(f"{target.stem}.step{checkpoint.completed_step:08d}{target.suffix}")
            try:
                shutil.copy2(target, step_path)
            except OSError as exc:
                raise NumericalConvergenceError(
                    "Canonical checkpoint saved, but retained-step copy failed.",
                    reason=NonlinearFailureReason.CHECKPOINT_FAILURE,
                    diagnostics={
                        "canonical_saved": True,
                        "retained_step_saved": False,
                        "canonical_path": str(target),
                        "retained_path": str(step_path),
                    },
                ) from exc
            written.append(step_path)
        return tuple(written)

    def load(
        self,
        path: str | Path,
        *,
        model: FiniteElementModel | None = None,
        expected_model_signature: str | None = None,
        expected_dofs: int | None = None,
        expected_topology: dict[str, Any] | None = None,
    ) -> NonlinearCheckpointV2:
        source = Path(path)
        try:
            with np.load(source, allow_pickle=False) as data:
                metadata = json.loads(str(data["metadata_json"].item()))
                schema_version = int(metadata["schema_version"])
                if schema_version == 1:
                    legacy = _decode_v1(data, metadata)
                    checkpoint = migrate_v1_checkpoint(
                        legacy,
                        model=model,
                        expected_dofs=expected_dofs,
                        expected_model_signature=expected_model_signature,
                    )
                elif schema_version == 2:
                    checkpoint = _decode_v2(metadata)
                    model_signature = expected_model_signature
                    topology = expected_topology
                    if model is not None:
                        model_signature = model_signature_v2(model, checkpoint.state_topology)
                        topology = build_state_topology(model, checkpoint.accepted_state)
                    checkpoint.validate(
                        expected_dofs,
                        expected_model_signature=model_signature,
                        expected_topology=topology,
                    )
                else:
                    raise InputValidationError(f"Unsupported nonlinear checkpoint schema version {schema_version}.")
        except NumericalConvergenceError:
            raise
        except InputValidationError:
            raise
        except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
            raise InputValidationError(f"Cannot read nonlinear checkpoint {source}: invalid or corrupted NPZ.") from exc
        return checkpoint


def _v2_metadata(checkpoint: NonlinearCheckpointV2) -> dict[str, Any]:
    state = checkpoint.accepted_state
    accepted_payload = {
        "schema_version": state.schema_version,
        "displacement": state.displacement,
        "load_factor": state.load_factor,
        "material_state": state.material_state,
        "contact_state": state.contact_state,
        "continuation_state": state.continuation_state,
        "accepted_increment_metadata": state.accepted_increment_metadata,
    }
    return {
        "schema_version": checkpoint.schema_version,
        "state_schema_version": checkpoint.state_schema_version,
        "model_signature": checkpoint.model_signature,
        "completed_step": checkpoint.completed_step,
        "state_topology": checkpoint.state_topology,
        "component_digests": checkpoint.component_digests,
        "composite_digest": checkpoint.composite_digest,
        "migration_metadata": checkpoint.migration_metadata,
        "accepted_state": canonical_state_payload(accepted_payload),
    }


def _decode_v2(metadata: dict[str, Any]) -> NonlinearCheckpointV2:
    try:
        raw_state = decode_canonical_state_payload(metadata["accepted_state"])
        if not isinstance(raw_state, dict):
            raise ValueError("accepted_state is not a mapping")
        state = NonlinearState(
            displacement=raw_state["displacement"],
            load_factor=raw_state["load_factor"],
            material_state=raw_state["material_state"],
            contact_state=raw_state["contact_state"],
            continuation_state=raw_state["continuation_state"],
            accepted_increment_metadata=raw_state["accepted_increment_metadata"],
            schema_version=int(raw_state["schema_version"]),
        )
        return NonlinearCheckpointV2(
            schema_version=int(metadata["schema_version"]),
            state_schema_version=int(metadata["state_schema_version"]),
            model_signature=str(metadata["model_signature"]),
            completed_step=int(metadata["completed_step"]),
            accepted_state=state,
            state_topology=dict(metadata["state_topology"]),
            component_digests={str(key): str(value) for key, value in metadata["component_digests"].items()},
            composite_digest=str(metadata["composite_digest"]),
            migration_metadata=dict(metadata.get("migration_metadata", {})),
        )
    except NumericalConvergenceError:
        raise
    except (KeyError, TypeError, ValueError) as exc:
        if "finite" in str(exc).lower():
            raise NumericalConvergenceError(
                "Schema-v2 checkpoint contains a non-finite accepted state.",
                reason=NonlinearFailureReason.STATE_CORRUPTION,
            ) from exc
        raise InputValidationError("Schema-v2 checkpoint metadata or typed state is invalid.") from exc


def _decode_v1(data: Any, metadata: dict[str, Any]) -> NonlinearCheckpoint:
    try:
        return NonlinearCheckpoint(
            schema_version=int(metadata["schema_version"]),
            model_signature=str(metadata["model_signature"]),
            completed_step=int(metadata["completed_step"]),
            load_factor=float(metadata["load_factor"]),
            displacement=np.asarray(data["displacement"], dtype=float),
            material_states=_restore_material_states(metadata["material_states"]),
            continuation_state=dict(metadata.get("continuation_state", {})),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise InputValidationError("Legacy schema-v1 nonlinear checkpoint is invalid.") from exc


def _restore_material_states(raw: object) -> dict[int, list[dict[str, Any]]]:
    if not isinstance(raw, dict):
        raise InputValidationError("Nonlinear checkpoint material states are invalid.")
    try:
        restored = {int(element): points for element, points in raw.items()}
    except (TypeError, ValueError) as exc:
        raise InputValidationError("Nonlinear checkpoint element identifiers are invalid.") from exc
    return {key: list(points) for key, points in restored.items()}


def _fsync_file(stream: Any) -> None:
    try:
        os.fsync(stream.fileno())
    except (OSError, AttributeError):
        # Some supported filesystems/platforms do not expose a usable fsync.
        # The atomic replace contract still holds; durability is bounded.
        return


def _sync_directory(directory: Path) -> None:
    if os.name == "nt":
        return
    descriptor: int | None = None
    try:
        descriptor = os.open(directory, os.O_RDONLY)
        os.fsync(descriptor)
    except OSError:
        return
    finally:
        if descriptor is not None:
            os.close(descriptor)


def _remove_if_present(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass
    except OSError:
        pass
