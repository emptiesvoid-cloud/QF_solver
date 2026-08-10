"""MPI and PETSc diagnostics for large-scale runs."""

from __future__ import annotations

from typing import Any

import numpy as np


def communication_diagnostics(
    *,
    node_counts: list[int],
    owned_node_counts: list[int],
    halo_node_counts: list[int],
    fixed_counts: list[int],
    load_counts: list[int],
    partition_details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return deterministic communication-size estimates for audit reports."""
    halo_bytes = [int(count) * 3 * np.dtype(np.float64).itemsize for count in halo_node_counts]
    fixed_bytes = [
        int(count) * (np.dtype(np.int64).itemsize + np.dtype(np.int8).itemsize)
        for count in fixed_counts
    ]
    load_bytes = [
        int(count)
        * (np.dtype(np.int64).itemsize + np.dtype(np.int8).itemsize + np.dtype(np.float64).itemsize)
        for count in load_counts
    ]
    details = dict(partition_details or {})
    return {
        "local_compact_node_counts": [int(value) for value in node_counts],
        "local_owned_node_counts": [int(value) for value in owned_node_counts],
        "local_halo_node_counts": [int(value) for value in halo_node_counts],
        "max_halo_node_count": int(max(halo_node_counts)) if halo_node_counts else 0,
        "halo_node_ratio_max": float(max(halo_node_counts) / max(node_counts)) if node_counts and max(node_counts) else 0.0,
        "estimated_halo_coordinate_bytes_by_rank": halo_bytes,
        "estimated_halo_coordinate_bytes_total": int(sum(halo_bytes)),
        "local_fixed_dof_counts": [int(value) for value in fixed_counts],
        "local_load_counts": [int(value) for value in load_counts],
        "estimated_fixed_payload_bytes_by_rank": fixed_bytes,
        "estimated_load_payload_bytes_by_rank": load_bytes,
        "estimated_boundary_payload_bytes_total": int(sum(fixed_bytes) + sum(load_bytes)),
        "graph_cut_face_count": int(details.get("cut_face_count", 0) or 0),
        "graph_cut_face_ratio": float(details.get("cut_face_ratio", 0.0) or 0.0),
    }


def petsc_ksp_diagnostics(ksp: Any, matrix: Any) -> dict[str, Any]:
    """Collect PETSc diagnostics without depending on version-specific APIs."""
    pc = ksp.getPC()
    diagnostics: dict[str, Any] = {
        "ksp_type": _safe_call(ksp, "getType"),
        "pc_type": _safe_call(pc, "getType"),
        "pc_mg_levels": _safe_call(pc, "getMGLevels"),
        "matrix_global_size": _safe_list(_safe_call(matrix, "getSize")),
        "matrix_local_size": _safe_list(_safe_call(matrix, "getLocalSize")),
        "matrix_ownership_range": _safe_list(_safe_call(matrix, "getOwnershipRange")),
        "matrix_info": _safe_matrix_info(matrix),
    }
    hypre_type = _safe_call(pc, "getHYPREType")
    if hypre_type is not None:
        diagnostics["hypre_type"] = hypre_type
    return diagnostics


def _safe_call(obj: Any, method_name: str) -> Any:
    method = getattr(obj, method_name, None)
    if method is None:
        return None
    try:
        return method()
    except Exception:
        return None


def _safe_list(value: Any) -> list[int] | None:
    if value is None:
        return None
    try:
        return [int(item) for item in value]
    except TypeError:
        return None


def _safe_matrix_info(matrix: Any) -> dict[str, float] | None:
    info = _safe_call(matrix, "getInfo")
    if info is None:
        return None
    try:
        return {str(key): float(value) for key, value in dict(info).items()}
    except (TypeError, ValueError):
        return None
