"""Passive tooling for the WP06-D pre-merge remediation.

The helpers in this module read accepted-state evidence and perform bounded
diagnostic arithmetic.  They do not execute a solver, mutate a model, or
change the WP06-D qualification contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.state import deterministic_state_digest
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore


CROWN_NODE_SET = (2, 3, 4)
ARCHIVE_SCHEMA_VERSION = 1
ARCHIVED_STATE_FIELDS = (
    "reaction_resultant",
    "reaction_moment",
    "residual_norm",
    "arc_length_constraint_value",
    "newton_iterations",
    "cutbacks_retries",
    "terminal_classification",
)


@dataclass(frozen=True)
class CheckpointSnapshot:
    """Detached, validated view of one accepted checkpoint."""

    schema_version: int
    completed_step: int
    load_factor: float
    displacement: np.ndarray
    material_state: Mapping[str | int, Any]
    contact_state: Mapping[str | int, Any]
    continuation_state: Mapping[str | int, Any]
    accepted_increment_metadata: Mapping[str | int, Any]
    state_digest: str
    model_signature: str


@dataclass(frozen=True)
class BalanceResult:
    """Independent force/moment accounting result for one accepted state."""

    external_resultant: np.ndarray
    external_moment: np.ndarray
    reaction_resultant: np.ndarray
    reaction_moment: np.ndarray
    force_residual: np.ndarray
    moment_residual: np.ndarray
    force_relative_error: float
    moment_relative_error: float
    force_pass: bool
    moment_pass: bool


def mean_crown_uz(
    displacement: np.ndarray,
    model: FiniteElementModel,
    *,
    crown_nodes: tuple[int, ...] = CROWN_NODE_SET,
) -> float:
    """Return the frozen ``-mean(UZ)`` monitor over the declared crown nodes.

    There is deliberately no single-node fallback.  A caller must provide the
    frozen node set explicitly when it differs from the WP06-D R1 contract.
    """

    if tuple(crown_nodes) != CROWN_NODE_SET:
        raise InputValidationError("WP06-D monitor requires the frozen crown node set (2, 3, 4).")
    dofs = model.dof_manager()
    values = []
    vector = np.asarray(displacement)
    if vector.ndim != 1 or vector.dtype.hasobject or not np.issubdtype(vector.dtype, np.number):
        raise InputValidationError("WP06-D displacement must be a numeric one-dimensional vector.")
    for node in crown_nodes:
        try:
            values.append(float(vector[dofs.index(node, "UZ")]))
        except (IndexError, ValueError) as exc:
            raise InputValidationError(f"WP06-D crown node {node} has no usable UZ DOF.") from exc
    result = -float(np.mean(values))
    if not np.isfinite(result):
        raise InputValidationError("WP06-D mean crown UZ is non-finite.")
    return result


def _checkpoint_parts(checkpoint: Any) -> tuple[int, int, float, np.ndarray, Mapping[str | int, Any], Mapping[str | int, Any], Mapping[str | int, Any], Mapping[str | int, Any], str, str]:
    accepted = getattr(checkpoint, "accepted_state", None)
    if accepted is not None:
        schema_version = int(getattr(checkpoint, "schema_version", 0))
        state_schema_version = int(getattr(checkpoint, "state_schema_version", 0))
        if schema_version != 2 or state_schema_version != int(getattr(accepted, "schema_version", 0)):
            raise InputValidationError("Unsupported or incomplete nonlinear checkpoint schema.")
        displacement = np.array(accepted.displacement, copy=True)
        load_factor = float(accepted.load_factor)
        material_state = dict(accepted.material_state)
        contact_state = dict(accepted.contact_state)
        continuation_state = dict(accepted.continuation_state)
        metadata = dict(accepted.accepted_increment_metadata)
        state_digest = str(getattr(checkpoint, "composite_digest", ""))
        if state_digest != accepted.digest:
            raise InputValidationError("Schema-v2 checkpoint composite digest does not match accepted state.")
    else:
        schema_version = int(getattr(checkpoint, "schema_version", 0))
        if schema_version != 1:
            raise InputValidationError("Unsupported or incomplete legacy checkpoint schema.")
        displacement = np.array(getattr(checkpoint, "displacement"), copy=True)
        load_factor = float(getattr(checkpoint, "load_factor"))
        material_state = dict(getattr(checkpoint, "material_states"))
        contact_state = {}
        continuation_state = dict(getattr(checkpoint, "continuation_state"))
        metadata = {}
        state_digest = deterministic_state_digest(
            {
                "schema_version": schema_version,
                "completed_step": int(getattr(checkpoint, "completed_step")),
                "load_factor": load_factor,
                "displacement": displacement,
                "material_state": material_state,
                "continuation_state": continuation_state,
            }
        )
    completed_step = int(getattr(checkpoint, "completed_step"))
    model_signature = str(getattr(checkpoint, "model_signature", ""))
    if completed_step < 0 or not model_signature or not state_digest:
        raise InputValidationError("Nonlinear checkpoint metadata is incomplete.")
    if displacement.ndim != 1 or displacement.dtype.hasobject or not np.issubdtype(displacement.dtype, np.number):
        raise InputValidationError("Checkpoint displacement must be numeric and one-dimensional.")
    if not np.all(np.isfinite(displacement)) or not np.isfinite(load_factor):
        raise InputValidationError("Checkpoint accepted state contains non-finite values.")
    return (
        schema_version,
        completed_step,
        load_factor,
        displacement,
        material_state,
        contact_state,
        continuation_state,
        metadata,
        state_digest,
        model_signature,
    )


def read_checkpoint(
    path: str | Path,
    *,
    model: FiniteElementModel | None = None,
    expected_dofs: int | None = None,
    store: Any | None = None,
) -> CheckpointSnapshot:
    """Read a checkpoint through the storage API without mutating solver state.

    The keyword call is the current V2 API.  The narrow TypeError fallback is
    retained for archived V1-compatible stores and only retries the same read
    with the legacy path; all semantic validation remains local and explicit.
    """

    source = Path(path)
    if not source.is_file():
        raise InputValidationError(f"Checkpoint file does not exist: {source}")
    checkpoint_store = store or NpzNonlinearCheckpointStore()
    kwargs: dict[str, Any] = {}
    if model is not None:
        kwargs["model"] = model
    if expected_dofs is not None:
        kwargs["expected_dofs"] = expected_dofs
    try:
        checkpoint = checkpoint_store.load(source, **kwargs)
    except TypeError as exc:
        if not kwargs or "unexpected keyword" not in str(exc).lower():
            raise
        checkpoint = checkpoint_store.load(source)
    try:
        parts = _checkpoint_parts(checkpoint)
    except InputValidationError:
        raise
    except (AttributeError, TypeError, ValueError, KeyError) as exc:
        raise InputValidationError("Checkpoint data is incomplete or malformed.") from exc
    if expected_dofs is not None and parts[3].size != expected_dofs:
        raise InputValidationError("Checkpoint displacement length does not match expected DOFs.")
    return CheckpointSnapshot(*parts)


def _optional_measurement(metrics: Mapping[str, Any], name: str) -> Any:
    if name not in metrics or metrics[name] is None:
        return {"value": None, "reason": "NOT_AVAILABLE_IN_ACCEPTED_STATE"}
    value = metrics[name]
    _ensure_finite_tree(value, name)
    return _jsonable(value)


def archive_accepted_state(
    snapshot: CheckpointSnapshot,
    model: FiniteElementModel,
    *,
    metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one lossless accepted-state evidence record, without solving."""

    values = dict(metrics or {})
    record: dict[str, Any] = {
        "schema_version": ARCHIVE_SCHEMA_VERSION,
        "step": snapshot.completed_step,
        "lambda": snapshot.load_factor,
        "accepted_displacement": snapshot.displacement.tolist(),
        "mean_crown_uz": mean_crown_uz(snapshot.displacement, model),
        "state_digest": snapshot.state_digest,
        "model_signature": snapshot.model_signature,
        "metrics": {name: _optional_measurement(values, name) for name in ARCHIVED_STATE_FIELDS},
    }
    _ensure_finite_tree(record, "accepted_state_record")
    return record


def archive_checkpoint_series(
    snapshots: Iterable[CheckpointSnapshot],
    model: FiniteElementModel,
    output_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Archive a deterministic series of accepted checkpoints in input order."""

    records = [archive_accepted_state(snapshot, model) for snapshot in snapshots]
    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(records, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return records


def _load_vector(model: FiniteElementModel, load_factor: float) -> np.ndarray:
    dofs = model.dof_manager()
    result = np.zeros(dofs.ndof, dtype=float)
    for load in model.loads:
        result[dofs.index(load.node, load.dof)] += load_factor * float(load.value)
    if not np.all(np.isfinite(result)):
        raise InputValidationError("Reconstructed external load is non-finite.")
    return result


def reconstruct_balance(
    *,
    coordinates: np.ndarray,
    internal_force: np.ndarray,
    external_force: np.ndarray,
    fixed_dof_indices: Iterable[int],
    force_scale: float = 1.0,
    moment_scale: float = 2.0,
    threshold: float = 1.0e-8,
) -> BalanceResult:
    """Independently reconstruct vector force/moment balance.

    This is arithmetic over archived state/model terms only.  It does not use
    the production summary equilibrium fields or any continuation algorithm.
    """

    nodes = np.asarray(coordinates, dtype=float)
    internal = np.asarray(internal_force, dtype=float)
    external = np.asarray(external_force, dtype=float)
    if nodes.ndim != 2 or nodes.shape[1] != 3 or internal.ndim != 1 or external.ndim != 1:
        raise InputValidationError("Equilibrium reconstruction inputs have invalid shapes.")
    if internal.size != external.size or internal.size != 3 * nodes.shape[0]:
        raise InputValidationError("Equilibrium reconstruction requires three DOFs per node.")
    if not np.all(np.isfinite(nodes)) or not np.all(np.isfinite(internal)) or not np.all(np.isfinite(external)):
        raise InputValidationError("Equilibrium reconstruction input is non-finite.")
    fixed = {int(index) for index in fixed_dof_indices}
    residual = internal - external
    reaction = np.zeros_like(residual)
    for index in fixed:
        if index < 0 or index >= reaction.size:
            raise InputValidationError("Equilibrium reconstruction fixed DOF index is out of range.")
        reaction[index] = residual[index]
    external_nodes = external.reshape((-1, 3))
    reaction_nodes = reaction.reshape((-1, 3))
    ext_resultant = external_nodes.sum(axis=0)
    reaction_resultant = reaction_nodes.sum(axis=0)
    ext_moment = np.cross(nodes, external_nodes).sum(axis=0)
    reaction_moment = np.cross(nodes, reaction_nodes).sum(axis=0)
    force_residual = reaction_resultant + ext_resultant
    moment_residual = reaction_moment + ext_moment
    machine_floor = float(np.finfo(float).eps)
    force_floor = _max_float(float(force_scale), machine_floor)
    moment_floor = _max_float(float(moment_scale), machine_floor)
    force_denominator = _max_float(
        float(np.linalg.norm(reaction_resultant)), float(np.linalg.norm(ext_resultant)), force_floor
    )
    moment_denominator = _max_float(
        float(np.linalg.norm(reaction_moment)), float(np.linalg.norm(ext_moment)), moment_floor
    )
    force_error = float(np.linalg.norm(force_residual)) / float(force_denominator)
    moment_error = float(np.linalg.norm(moment_residual)) / float(moment_denominator)
    return BalanceResult(
        external_resultant=ext_resultant,
        external_moment=ext_moment,
        reaction_resultant=reaction_resultant,
        reaction_moment=reaction_moment,
        force_residual=force_residual,
        moment_residual=moment_residual,
        force_relative_error=force_error,
        moment_relative_error=moment_error,
        force_pass=force_error <= threshold,
        moment_pass=moment_error <= threshold,
    )


def reconstruct_checkpoint_balance(
    model: FiniteElementModel,
    snapshot: CheckpointSnapshot,
    internal_force: np.ndarray,
    *,
    fixed_dof_indices: Iterable[int],
) -> BalanceResult:
    """Reconstruct balance for a snapshot after an independent assembly step."""

    return reconstruct_balance(
        coordinates=model.nodes,
        internal_force=internal_force,
        external_force=_load_vector(model, snapshot.load_factor),
        fixed_dof_indices=fixed_dof_indices,
    )


def _ensure_finite_tree(value: Any, path: str) -> None:
    if value is None or isinstance(value, (str, bool, int, np.integer)):
        return
    if isinstance(value, (float, np.floating)):
        if not np.isfinite(value):
            raise InputValidationError(f"{path} contains a non-finite value.")
        return
    if isinstance(value, np.ndarray):
        if value.dtype.hasobject or not np.issubdtype(value.dtype, np.number) or not np.all(np.isfinite(value)):
            raise InputValidationError(f"{path} contains a non-finite or unsupported array.")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _ensure_finite_tree(item, f"{path}[{key!r}]")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _ensure_finite_tree(item, f"{path}[{index}]")
        return
    raise InputValidationError(f"{path} contains unsupported value {type(value).__name__}.")


def _max_float(*values: float) -> float:
    result = float(values[0])
    for value in values[1:]:
        candidate = float(value)
        if candidate > result:
            result = candidate
    return result


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.generic):
        return _jsonable(value.item())
    if isinstance(value, np.ndarray):
        return [_jsonable(item) for item in value.tolist()]
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value
