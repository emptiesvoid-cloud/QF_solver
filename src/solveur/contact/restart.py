"""Signed accepted-state persistence for the bounded frictional contact route."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.io.checkpoint_common import checkpoint_signature
from solveur.io.model_writer import model_to_dict


CHECKPOINT_SCHEMA_VERSION = 1
_VOLATILE_PARAMETERS = {
    "contact_checkpoint_path",
    "contact_restart_from",
}


def _json_safe(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _path_payload(load_path: list[np.ndarray]) -> list[list[float]]:
    result = []
    for index, vector in enumerate(load_path, start=1):
        values = np.asarray(vector, dtype=float)
        if values.ndim != 1 or not np.all(np.isfinite(values)):
            raise InputValidationError(f"Contact restart load path step {index} is not finite and one-dimensional.")
        result.append(values.tolist())
    return result


def contact_model_signature(model: FiniteElementModel, dofs: DofManager, load_path: list[np.ndarray]) -> str:
    """Sign physical contact inputs and the complete frozen load path."""

    payload = model_to_dict(model)
    parameters = dict(payload["analysis"]["parameters"])
    payload["analysis"]["parameters"] = {
        key: value for key, value in parameters.items() if key not in _VOLATILE_PARAMETERS
    }
    payload["dof_count"] = int(dofs.ndof)
    payload["contact_load_path"] = _path_payload(load_path)
    return checkpoint_signature(payload, label="Frictional contact")


def _checkpoint_path(value: object, name: str) -> Path | None:
    if value is None:
        return None
    if not isinstance(value, (str, os.PathLike)) or not str(value).strip():
        raise InputValidationError(f"{name} must be a non-empty filesystem path.")
    return Path(value)


def checkpoint_paths(parameters: Mapping[str, object]) -> tuple[Path | None, Path | None]:
    return (
        _checkpoint_path(parameters.get("contact_checkpoint_path"), "contact_checkpoint_path"),
        _checkpoint_path(parameters.get("contact_restart_from"), "contact_restart_from"),
    )


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(_json_safe(payload), sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def save_contact_checkpoint(
    path: Path,
    *,
    model: FiniteElementModel,
    dofs: DofManager,
    load_path: list[np.ndarray],
    completed_step: int,
    state: Any,
    cumulative_dissipation: float,
) -> None:
    """Persist exactly one accepted friction state after a completed step."""

    if completed_step <= 0 or completed_step > len(load_path):
        raise InputValidationError("Contact checkpoint completed_step is outside the accepted load path.")
    slip_references = np.asarray(state.slip_references, dtype=float)
    tangential_forces = np.asarray(state.tangential_forces, dtype=float)
    if slip_references.ndim != 2 or slip_references.shape[1] != 2 or not np.all(np.isfinite(slip_references)):
        raise InputValidationError("Contact checkpoint slip references are invalid.")
    if tangential_forces.shape != slip_references.shape or not np.all(np.isfinite(tangential_forces)):
        raise InputValidationError("Contact checkpoint tangential forces are invalid.")
    payload = {
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
        "kind": "frictional_contact_accepted_state",
        "model_signature": contact_model_signature(model, dofs, load_path),
        "completed_step": completed_step,
        "load_path_length": len(load_path),
        "slip_references": slip_references.tolist(),
        "tangential_states": list(state.states),
        "active_contacts": list(state.active),
        "displacement": np.asarray(state.displacement, dtype=float).tolist(),
        "multipliers": np.asarray(state.multipliers, dtype=float).tolist(),
        "gaps": np.asarray(state.gaps, dtype=float).tolist(),
        "pressures": np.asarray(state.pressures, dtype=float).tolist(),
        "tangential_forces": tangential_forces.tolist(),
        "cumulative_dissipation": float(cumulative_dissipation),
    }
    _write_json_atomic(path, payload)


def load_contact_checkpoint(
    path: Path,
    *,
    model: FiniteElementModel,
    dofs: DofManager,
    load_path: list[np.ndarray],
    contact_count: int,
) -> dict[str, Any]:
    """Load and validate a friction checkpoint before any resumed solve."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise InputValidationError("Friction contact restart checkpoint is unreadable.") from error
    if not isinstance(payload, dict):
        raise InputValidationError("Friction contact restart checkpoint is not an object.")
    if payload.get("schema_version") != CHECKPOINT_SCHEMA_VERSION or payload.get("kind") != "frictional_contact_accepted_state":
        raise InputValidationError("Friction contact restart checkpoint schema is unsupported.")
    if payload.get("model_signature") != contact_model_signature(model, dofs, load_path):
        raise InputValidationError("Friction contact restart checkpoint does not match the physical model or load path.")
    completed_step = payload.get("completed_step")
    if isinstance(completed_step, bool) or not isinstance(completed_step, int) or not 0 < completed_step < len(load_path):
        raise InputValidationError("Friction contact restart checkpoint must identify a non-terminal accepted step.")
    if payload.get("load_path_length") != len(load_path):
        raise InputValidationError("Friction contact restart checkpoint load-path length is inconsistent.")
    references = np.asarray(payload.get("slip_references"), dtype=float)
    forces = np.asarray(payload.get("tangential_forces"), dtype=float)
    displacement = np.asarray(payload.get("displacement"), dtype=float)
    if references.shape != (contact_count, 2) or not np.all(np.isfinite(references)):
        raise InputValidationError("Friction contact restart slip references have the wrong shape or are non-finite.")
    if forces.shape != references.shape or not np.all(np.isfinite(forces)):
        raise InputValidationError("Friction contact restart forces have the wrong shape or are non-finite.")
    if displacement.ndim != 1 or displacement.size != dofs.ndof or not np.all(np.isfinite(displacement)):
        raise InputValidationError("Friction contact restart displacement is invalid.")
    states = payload.get("tangential_states")
    active = payload.get("active_contacts")
    if not isinstance(states, list) or len(states) != contact_count or any(item not in {"open", "stick", "slip", "frictionless"} for item in states):
        raise InputValidationError("Friction contact restart states are invalid.")
    if not isinstance(active, list) or any(isinstance(item, bool) or not isinstance(item, int) or not 0 <= item < contact_count for item in active):
        raise InputValidationError("Friction contact restart active contacts are invalid.")
    if active != sorted(set(active)):
        raise InputValidationError("Friction contact restart active contacts must be sorted and unique.")
    active_set = set(active)
    if any(states[index] == "open" for index in active_set) or any(states[index] != "open" for index in range(contact_count) if index not in active_set):
        raise InputValidationError("Friction contact restart states are inconsistent with the active set.")
    gaps = np.asarray(payload.get("gaps"), dtype=float)
    pressures = np.asarray(payload.get("pressures"), dtype=float)
    multipliers = np.asarray(payload.get("multipliers"), dtype=float)
    if gaps.shape != (contact_count,) or pressures.shape != (contact_count,) or not np.all(np.isfinite(gaps)) or not np.all(np.isfinite(pressures)):
        raise InputValidationError("Friction contact restart normal state is invalid.")
    if multipliers.shape != (len(active),) or not np.all(np.isfinite(multipliers)):
        raise InputValidationError("Friction contact restart multipliers are invalid.")
    dissipation = payload.get("cumulative_dissipation", 0.0)
    if isinstance(dissipation, bool) or not isinstance(dissipation, (int, float)) or not np.isfinite(float(dissipation)) or float(dissipation) < 0.0:
        raise InputValidationError("Friction contact restart cumulative dissipation is invalid.")
    return {
        "completed_step": completed_step,
        "slip_references": references,
        "tangential_forces": forces,
        "displacement": displacement,
        "states": tuple(str(item) for item in states),
        "active": tuple(int(item) for item in active),
        "cumulative_dissipation": float(dissipation),
    }
