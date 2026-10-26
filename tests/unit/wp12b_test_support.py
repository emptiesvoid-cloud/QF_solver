"""Shared, pre-assertion evidence helpers for the WP12-B cases."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import uuid
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np


WP12B_WORKTREE_ID = "wp12_elements_loads"


def require_controller_scope(expected_dofs: int, expected_worktree_id: str) -> Path:
    """Refuse a scientific solve outside its exact registered controller scope."""
    if os.environ.get("QF_DEVELOPMENT_AUTONOMOUS") != "1":
        raise RuntimeError("WP12-B FEM cases require the autonomous development controller.")
    if expected_worktree_id != WP12B_WORKTREE_ID:
        raise RuntimeError("WP12-B test declares the wrong controller worktree ID.")
    if os.environ.get("QF_DEV_WORKTREE_ID") != expected_worktree_id:
        raise RuntimeError("WP12-B FEM case received the wrong controller worktree ID.")
    selected = os.environ.get("QF_DEV_SELECTED_DOFS")
    if selected != str(expected_dofs):
        raise RuntimeError(f"Selected DDL {selected!r} does not match expected {expected_dofs}.")
    root_value = os.environ.get("QF_DEV_EVIDENCE_ROOT")
    if not root_value:
        raise RuntimeError("Controller did not assign an evidence root.")
    root = Path(root_value).expanduser().resolve()
    if not root.is_dir():
        raise RuntimeError(f"Controller evidence root does not exist: {root}")
    return root


def json_safe(value: Any) -> Any:
    """Convert numerical/container values to strict JSON, marking non-finite floats."""
    if isinstance(value, np.ndarray):
        return json_safe(value.tolist())
    if isinstance(value, np.generic):
        return json_safe(value.item())
    if isinstance(value, float):
        if np.isfinite(value):
            return value
        return {"non_finite": str(value)}
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    return repr(value)


def new_attempt_id() -> str:
    """Allocate a unique identity before a single-case solver invocation."""
    return str(uuid.uuid4())


def atomic_write_json_no_overwrite(path: Path, payload: dict[str, Any]) -> None:
    """Publish strict JSON atomically and fail if the target already exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(json_safe(payload), sort_keys=True, indent=2, allow_nan=False).encode("utf-8")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        # A hard link is an atomic no-clobber publication on the same volume.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def source_identity(paths: list[Path], repo_root: Path) -> dict[str, Any]:
    hashes = {}
    for path in paths:
        absolute = path.resolve()
        hashes[str(absolute.relative_to(repo_root.resolve()))] = hashlib.sha256(absolute.read_bytes()).hexdigest()
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unavailable"
    return {"git_head": commit, "sha256": hashes}


def model_identity(model: Any, case_parameters: dict[str, Any]) -> dict[str, Any]:
    def entity_data(entity: Any) -> Any:
        if is_dataclass(entity):
            return {field.name: getattr(entity, field.name) for field in fields(entity)}
        if isinstance(entity, (list, tuple)):
            return [entity_data(item) for item in entity]
        if isinstance(entity, dict):
            return {key: entity_data(value) for key, value in entity.items()}
        return entity

    model_data = {
        "nodes": np.asarray(model.nodes, dtype=float).tolist(),
        "elements": [
            {"type": item.type, "nodes": list(item.nodes), "material": item.material} for item in model.elements
        ],
        "materials": entity_data(model.materials),
        "fixed_dofs": entity_data(model.fixed_dofs),
        "nodal_loads": entity_data(model.loads),
        "distributed_loads": entity_data(model.distributed_loads),
        "case_parameters": case_parameters,
    }
    canonical = json.dumps(json_safe(model_data), sort_keys=True, separators=(",", ":"), allow_nan=False)
    return {"sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(), **model_data}


def write_result_before_assertions(
    *,
    evidence_root: Path,
    nodeid: str,
    model: Any,
    result: Any,
    case_parameters: dict[str, Any],
    source_paths: list[Path],
    repo_root: Path,
    solve_seconds: float,
    attempt_id: str,
) -> Path:
    displacement = np.asarray(result.displacements, dtype=float)
    audit = result.audit
    equilibrium = audit.equilibrium
    solver = dict(result.solver)
    record = {
        "schema": "wp12-b-observables-v1",
        "stage": "PRE_ASSERTION_METRICS",
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "attempt_id": attempt_id,
        "controller": {
            "worktree_id": os.environ.get("QF_DEV_WORKTREE_ID"),
            "selected_dofs": os.environ.get("QF_DEV_SELECTED_DOFS"),
            "controller_attempt_id": os.environ.get("QF_DEV_ATTEMPT_ID"),
            "evidence_root": str(evidence_root),
        },
        "identity": {
            "nodeid": nodeid,
            "sources": source_identity(source_paths, repo_root),
            "model": model_identity(model, case_parameters),
        },
        "units": case_parameters.get("units", {}),
        "mesh": {
            "nodes": model.node_count,
            "elements": len(model.elements),
            "dofs": int(displacement.size),
            "status": audit.mesh_status,
            "quality": audit.mesh_details,
            "element_quality": audit.diagnostic.get("element_quality", {}),
            "boundary": audit.boundary,
        },
        "result_status": result.status,
        "displacements": displacement.tolist(),
        "element_results": result.element_results,
        "maximum_absolute_displacement": float(np.max(np.abs(displacement))) if displacement.size else 0.0,
        "maximum_absolute_displacement_dof_index": int(np.argmax(np.abs(displacement))) if displacement.size else None,
        "reactions": equilibrium.get("reactions"),
        "equilibrium": equilibrium,
        "load_assembly": solver.get("load_assembly", {}),
        "residual": {
            "free_norm": equilibrium.get("free_residual_norm"),
            "free_relative": equilibrium.get("free_relative_residual"),
            "definition": "r_free = (K u - f)_free in the reduced unconstrained equilibrium equations",
        },
        "energy": {
            "strain_energy": equilibrium.get("secant_internal_energy"),
            "external_work": equilibrium.get("external_work_at_final_load"),
            "linear_energy_identity_relative_error": equilibrium.get("linear_energy_identity_relative_error"),
        },
        "solver": solver,
        "timing": {"solve_wall_seconds": solve_seconds, "reported": solver.get("execution", {})},
        "fem_solve_invocations": 1,
    }
    safe_node = nodeid.replace("::", "__").replace("/", "_").replace("\\", "_")
    destination = evidence_root / "wp12b" / safe_node / f"{attempt_id}.json"
    atomic_write_json_no_overwrite(destination, record)
    return destination
