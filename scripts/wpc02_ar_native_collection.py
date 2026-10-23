"""Strict decoding helpers for the production SolverAudit sparse vectors."""
from __future__ import annotations

import math
from typing import Any

import numpy as np


_VECTOR_FIELDS = {"name", "size", "norm", "max_abs", "nonzero_count", "nonzero_entries"}


def production_free_stationarity_inf(
    total_internal_force_n: np.ndarray,
    external_force_n: np.ndarray,
    free_dofs: np.ndarray,
) -> float:
    """Return the free-DOF residual for the production total internal force.

    The frictionless contact solver exports ``K @ u + C.T @ mu`` as
    ``internal_force``. Its physical compression is ``p = -mu``, therefore
    this exported total is ``K @ u - P``. Contact is already included: the
    production equilibrium residual is ``internal_force - external_force``
    on free DOFs. The independent KKT oracle has a different decomposition
    and must be evaluated separately.
    """
    internal = _finite_vector(total_internal_force_n, "total internal force")
    external = _finite_vector(external_force_n, "external force")
    free = _validated_mask(free_dofs, internal.size)
    if external.shape != internal.shape:
        raise ValueError("internal and external force vectors must have the same shape")
    return float(np.linalg.norm((internal - external)[free], ord=np.inf))


def recover_elastic_internal_force(
    total_internal_force_n: np.ndarray,
    physical_contact_force_n: np.ndarray,
) -> np.ndarray:
    """Recover ``K @ u`` from production ``K @ u - P`` and physical ``P``."""
    total = _finite_vector(total_internal_force_n, "total internal force")
    contact = _finite_vector(physical_contact_force_n, "physical contact force")
    if contact.shape != total.shape:
        raise ValueError("total internal and contact force vectors must have the same shape")
    return total + contact


def elastic_strain_energy_from_total_internal(
    displacement_m: np.ndarray,
    total_internal_force_n: np.ndarray,
    physical_contact_force_n: np.ndarray,
) -> float:
    """Compute elastic energy ``1/2 u.T K u`` from contact-inclusive output."""
    displacement = _finite_vector(displacement_m, "displacement")
    elastic_internal = recover_elastic_internal_force(total_internal_force_n, physical_contact_force_n)
    if displacement.shape != elastic_internal.shape:
        raise ValueError("displacement and internal force vectors must have the same shape")
    energy = 0.5 * float(displacement @ elastic_internal)
    if not math.isfinite(energy):
        raise ValueError("elastic strain energy is non-finite")
    return energy


def _finite_vector(values: np.ndarray, name: str) -> np.ndarray:
    vector = np.asarray(values, dtype=float)
    if vector.ndim != 1 or vector.size == 0 or not np.all(np.isfinite(vector)):
        raise ValueError(f"{name} must be a non-empty finite vector")
    return vector


def _validated_mask(indices: np.ndarray, size: int) -> np.ndarray:
    raw = np.asarray(indices)
    if raw.ndim != 1 or raw.dtype.kind not in "iu" or raw.size == 0:
        raise ValueError("free DOFs must be a non-empty one-dimensional integer array")
    if np.any(raw < 0) or np.any(raw >= size) or len(set(int(i) for i in raw)) != len(raw):
        raise ValueError("free DOFs must be unique valid vector indices")
    mask = np.zeros(size, dtype=bool)
    mask[raw] = True
    return mask


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


def decode_contact_rows(
    rows: Any,
    *,
    contact_nodes: np.ndarray,
    area_weights_m2: np.ndarray,
    expected_normals: np.ndarray | None = None,
    active_force_tolerance_n: float = 1.0e-7,
) -> dict[str, np.ndarray]:
    """Decode contact output using SolverAudit's positive-compression pressure.

    ``support._pressures`` stores ``-raw_lagrange_multiplier`` because the
    saddle-system multiplier has the opposite sign to the physical force on
    the slave.  The row's ``pressure`` is therefore already the nonnegative
    physical contact force (N); it must not be negated a second time.
    ``pressure_pa`` is that force divided by its nodal tributary area.
    """
    nodes = np.asarray(contact_nodes)
    areas = np.asarray(area_weights_m2, dtype=float)
    if nodes.ndim != 1 or nodes.size == 0 or nodes.dtype.kind not in "iu":
        raise ValueError("contact node IDs must be a non-empty one-dimensional integer array")
    if len(set(int(node) for node in nodes)) != len(nodes) or np.any(nodes < 0):
        raise ValueError("contact node IDs must be unique non-negative integers")
    if areas.shape != nodes.shape or not np.all(np.isfinite(areas)) or np.any(areas <= 0.0):
        raise ValueError("contact tributary areas must be finite, positive, and match contact node IDs")
    if (not math.isfinite(active_force_tolerance_n) or active_force_tolerance_n < 0.0):
        raise ValueError("active force tolerance must be finite and non-negative")
    if not isinstance(rows, list) or len(rows) != len(nodes):
        raise ValueError("contact rows must be a list with exactly one row per frozen contact node")

    gaps = np.empty(len(rows), dtype=float)
    forces = np.empty(len(rows), dtype=float)
    active_flags = np.empty(len(rows), dtype=bool)
    normals = np.empty((len(rows), 3), dtype=float)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"contact row {index} must be an object")
        try:
            gap = float(row["gap"])
            force = float(row["pressure"])
            normal = np.asarray(row["normal"], dtype=float)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"contact row {index} is missing a valid gap, pressure, or normal") from exc
        active = row.get("active")
        if not isinstance(active, bool):
            raise ValueError(f"contact row {index} active flag must be boolean")
        if not math.isfinite(gap) or not math.isfinite(force):
            raise ValueError(f"contact row {index} gap and pressure must be finite")
        if force < -active_force_tolerance_n:
            raise ValueError(f"contact row {index} has tensile contact force beyond the frozen tolerance")
        if active and force < -active_force_tolerance_n:
            raise ValueError(f"contact row {index} active flag conflicts with tensile contact force")
        if not active and force > active_force_tolerance_n:
            raise ValueError(f"contact row {index} inactive flag conflicts with compressive contact force")
        if normal.shape != (3,) or not np.all(np.isfinite(normal)):
            raise ValueError(f"contact row {index} normal must be a finite global XYZ vector")
        if not math.isclose(float(np.linalg.norm(normal)), 1.0, rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError(f"contact row {index} normal must be unit length")
        gaps[index] = gap
        forces[index] = force
        active_flags[index] = active
        normals[index] = normal

    if expected_normals is not None:
        expected = np.asarray(expected_normals, dtype=float)
        if expected.shape == (3,):
            expected = np.broadcast_to(expected, normals.shape)
        if expected.shape != normals.shape or not np.all(np.isfinite(expected)):
            raise ValueError("expected contact normals must be finite XYZ vectors matching the rows")
        if not np.allclose(normals, expected, rtol=0.0, atol=1.0e-12):
            raise ValueError("production contact normals differ from the frozen qualification convention")

    return {
        "gaps_m": gaps,
        "multipliers_n": forces,
        "active_flags": active_flags,
        "pressure_pa": forces / areas,
        "normals": normals,
    }


def contact_force_vectors(
    *,
    node_ids: np.ndarray,
    normals: np.ndarray,
    force_magnitudes_n: np.ndarray,
    node_count: int,
) -> np.ndarray:
    """Assemble physical forces on slave nodes: compression magnitude × normal."""
    nodes = np.asarray(node_ids)
    directions = np.asarray(normals, dtype=float)
    magnitudes = np.asarray(force_magnitudes_n, dtype=float)
    if isinstance(node_count, bool) or not isinstance(node_count, int) or node_count <= 0:
        raise ValueError("node_count must be a positive integer")
    if nodes.ndim != 1 or nodes.dtype.kind not in "iu" or magnitudes.shape != nodes.shape:
        raise ValueError("contact node IDs and force magnitudes must be matching one-dimensional arrays")
    if directions.shape != (len(nodes), 3):
        raise ValueError("contact normals must be an N-by-3 array")
    if len(set(int(node) for node in nodes)) != len(nodes) or np.any(nodes < 0) or np.any(nodes >= node_count):
        raise ValueError("contact node IDs must be unique and within the nodal force array")
    if not np.all(np.isfinite(directions)) or not np.all(np.isfinite(magnitudes)):
        raise ValueError("contact directions and force magnitudes must be finite")
    if np.any(np.abs(np.linalg.norm(directions, axis=1) - 1.0) > 1.0e-12):
        raise ValueError("contact normals must be unit length")
    forces = np.zeros((node_count, 3), dtype=float)
    forces[nodes] = magnitudes[:, None] * directions
    return forces


def resultant_and_moment(coordinates_m: np.ndarray, forces_n: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Sum global force and moment about the global origin using SI inputs."""
    coordinates = np.asarray(coordinates_m, dtype=float)
    forces = np.asarray(forces_n, dtype=float)
    if coordinates.ndim != 2 or forces.shape != coordinates.shape or coordinates.shape[1] != 3:
        raise ValueError("coordinates and forces must be matching N-by-3 global XYZ arrays")
    if not np.all(np.isfinite(coordinates)) or not np.all(np.isfinite(forces)):
        raise ValueError("coordinates and forces must be finite")
    return np.sum(forces, axis=0), np.sum(np.cross(coordinates, forces), axis=0)
