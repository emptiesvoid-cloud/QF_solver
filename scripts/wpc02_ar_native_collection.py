"""Strict decoding helpers for the production SolverAudit sparse vectors."""
from __future__ import annotations

import math
from typing import Any

import numpy as np


_VECTOR_FIELDS = {"name", "size", "norm", "max_abs", "nonzero_count", "nonzero_entries"}


def decode_audit_vectors(vectors: Any, *, expected_size: int) -> dict[str, np.ndarray]:
    """Decode full-detail SolverAudit vector summaries without guessing schema.

    SolverAudit stores a list of named summaries. Full detail encodes each
    vector sparsely as ``nonzero_entries: [{index, value}, ...]``; omitted
    values are explicitly zero under the producer's 1e-30 sparsity rule.
    """
    if not isinstance(vectors, list):
        raise ValueError("audit.vectors must be the SolverAudit list of named vector summaries")
    if expected_size <= 0:
        raise ValueError("expected vector size must be positive")
    decoded: dict[str, np.ndarray] = {}
    for position, item in enumerate(vectors):
        if not isinstance(item, dict) or set(item) != _VECTOR_FIELDS:
            raise ValueError(f"audit.vectors[{position}] is missing required summary fields")
        name = item["name"]
        if not isinstance(name, str) or not name or name in decoded:
            raise ValueError(f"audit.vectors[{position}] has an invalid or duplicate name")
        if isinstance(item["size"], bool) or not isinstance(item["size"], int) or item["size"] != expected_size:
            raise ValueError(f"audit vector {name!r} has unexpected size {item['size']!r}")
        for field in ("norm", "max_abs"):
            value = item[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"audit vector {name!r} has non-finite or invalid {field}")
        entries = item["nonzero_entries"]
        if not isinstance(entries, list):
            raise ValueError(f"audit vector {name!r} has no full-detail nonzero_entries list")
        if (isinstance(item["nonzero_count"], bool) or not isinstance(item["nonzero_count"], int)
                or item["nonzero_count"] != len(entries)):
            raise ValueError(f"audit vector {name!r} nonzero_count does not match its entries")
        values = np.zeros(expected_size, dtype=float)
        seen: set[int] = set()
        previous_index = -1
        for entry in entries:
            if not isinstance(entry, dict) or set(entry) != {"index", "value"}:
                raise ValueError(f"audit vector {name!r} contains a malformed nonzero entry")
            index, value = entry["index"], entry["value"]
            if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < expected_size:
                raise ValueError(f"audit vector {name!r} contains an out-of-range index")
            if index in seen:
                raise ValueError(f"audit vector {name!r} contains a duplicate index")
            if index <= previous_index:
                raise ValueError(f"audit vector {name!r} entries are not in producer index order")
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                raise ValueError(f"audit vector {name!r} contains a non-finite value")
            if abs(float(value)) <= 1.0e-30:
                raise ValueError(f"audit vector {name!r} encodes a value omitted by its sparse rule")
            values[index] = float(value)
            seen.add(index)
            previous_index = index
        actual_norm = float(np.linalg.norm(values))
        actual_max = float(np.max(np.abs(values), initial=0.0))
        omission_bound = math.sqrt(expected_size) * 1.0e-30
        if not math.isclose(actual_norm, float(item["norm"]), rel_tol=1e-12, abs_tol=omission_bound):
            raise ValueError(f"audit vector {name!r} norm disagrees with its sparse entries")
        if not math.isclose(actual_max, float(item["max_abs"]), rel_tol=1e-12, abs_tol=1e-30):
            raise ValueError(f"audit vector {name!r} max_abs disagrees with its sparse entries")
        decoded[name] = values
    required = {"loads", "displacements", "internal_force", "residual", "reactions"}
    if set(decoded) != required:
        raise ValueError(f"audit vector names must be exactly {sorted(required)}; got {sorted(decoded)}")
    return decoded


def production_support_reactions(vectors: dict[str, np.ndarray], *, top_nodes: np.ndarray) -> np.ndarray:
    """Return global XYZ reactions on the body's prescribed top nodes (N)."""
    reactions = vectors["reactions"]
    if reactions.size % 3:
        raise ValueError("reaction vector size is not divisible into global XYZ nodal triples")
    nodal = reactions.reshape((-1, 3))
    if np.any(top_nodes < 0) or np.any(top_nodes >= len(nodal)):
        raise ValueError("support node index is outside the global reaction vector")
    support = np.zeros_like(nodal)
    support[top_nodes] = nodal[top_nodes]
    return support


def resultant_and_moment(coordinates_m: np.ndarray, forces_n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sum global force and moment about the global origin using SI inputs."""
    coordinates = np.asarray(coordinates_m, dtype=float)
    forces = np.asarray(forces_n, dtype=float)
    if coordinates.ndim != 2 or forces.shape != coordinates.shape or coordinates.shape[1] != 3:
        raise ValueError("coordinates and forces must be matching N-by-3 global XYZ arrays")
    if not np.all(np.isfinite(coordinates)) or not np.all(np.isfinite(forces)):
        raise ValueError("coordinates and forces must be finite")
    return np.sum(forces, axis=0), np.sum(np.cross(coordinates, forces), axis=0)
