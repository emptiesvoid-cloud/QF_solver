"""Bounded, non-invasive evidence capture for the WP-D01-CG damping investigation.

This module only snapshots values supplied by an already-running experimental
test. It does not construct a model, assemble FEM operators, or solve a system.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
from typing import Any

import numpy as np
from scipy.sparse import issparse


CG_EVIDENCE_SCHEMA = "qf-wp-d01-cg-projected-damping-evidence/v1"
CG_MAX_PROPERTY_BYTES = 1 * 1024 * 1024


def _json_safe(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        if np.iscomplexobj(value):
            return {"real": _json_safe(value.real), "imag": _json_safe(value.imag)}
        return _json_safe(value.tolist())
    if isinstance(value, np.generic):
        return _json_safe(value.item())
    if isinstance(value, complex):
        return {"real": _json_safe(value.real), "imag": _json_safe(value.imag)}
    if isinstance(value, float) and not math.isfinite(value):
        name = "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
        return {"nonfinite_float": name}
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _serialize_bounded(document: dict[str, Any]) -> str:
    encoded = json.dumps(_json_safe(document), sort_keys=True, separators=(",", ":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > CG_MAX_PROPERTY_BYTES:
        raise ValueError(f"CG diagnostic property exceeds its {CG_MAX_PROPERTY_BYTES}-byte bound.")
    return encoded


def _numeric_array_snapshot(value: Any) -> dict[str, Any]:
    """Keep readable values and exact dtype/shape-bound bytes."""
    array = np.ascontiguousarray(np.asarray(value))
    if array.dtype.kind not in "biufc":
        raise TypeError(f"CG evidence does not support non-numeric dtype {array.dtype}.")
    raw = array.tobytes(order="C")
    identity = json.dumps(
        {"dtype": array.dtype.str, "shape": list(array.shape), "order": "C"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    digest = hashlib.sha256(identity + b"\0" + raw).hexdigest()
    return {
        "encoding": "C_ORDER_RAW_BYTES_BASE64_AND_JSON_ROUNDTRIP_VALUES",
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "order": "C",
        "values": _json_safe(array),
        "raw_bytes_base64": base64.b64encode(raw).decode("ascii"),
        "raw_representation_sha256": digest,
    }


def _csr_snapshot(matrix: Any) -> dict[str, Any]:
    if not issparse(matrix):
        raise TypeError("CG operator evidence requires sparse matrices.")
    csr = matrix.tocsr(copy=True)
    if np.iscomplexobj(csr.data):
        raise TypeError("CG Rayleigh operator evidence requires real sparse matrices.")
    digest = hashlib.sha256()
    digest.update(json.dumps({"shape": list(csr.shape)}, sort_keys=True).encode("ascii"))
    arrays: dict[str, Any] = {}
    for name, array in (
        ("data", np.ascontiguousarray(csr.data)),
        ("indices", np.ascontiguousarray(csr.indices)),
        ("indptr", np.ascontiguousarray(csr.indptr)),
    ):
        digest.update(name.encode("ascii"))
        digest.update(array.dtype.str.encode("ascii"))
        digest.update(array.tobytes())
        arrays[name] = {
            "dtype": array.dtype.str,
            "values": array.tolist(),
            "raw_bytes_base64": base64.b64encode(array.tobytes()).decode("ascii"),
        }
    return {
        "format": "CSR_COPY_WITH_STORED_ORDER",
        "shape": list(csr.shape),
        "nnz_stored": int(csr.nnz),
        "arrays": arrays,
        "stored_representation_sha256": digest.hexdigest(),
    }


def _sparse_symmetry_metrics(matrix: Any) -> dict[str, float]:
    csr = matrix.tocsr(copy=True)
    csr.sum_duplicates()
    csr.sort_indices()
    skew = float(np.sqrt(np.sum(np.square((csr - csr.T).tocsr().data, dtype=np.float64))))
    norm = float(np.sqrt(np.sum(np.square(csr.data, dtype=np.float64))))
    return {
        "frobenius_norm": norm,
        "skew_frobenius_norm": skew,
        "relative_skew": skew / max(norm, np.finfo(np.float64).tiny),
    }


def source_operator_evidence(
    *,
    mesh_id: str,
    elements: int,
    free_dofs: int,
    source_sha: str,
    operator_identity: str,
    alpha_per_s: float,
    beta_s: float,
    mass: Any,
    stiffness: Any,
    damping: Any,
    frequencies_hz: list[float],
    reduced_force: np.ndarray,
    direct_responses: list[np.ndarray],
    direct_relative_residuals: list[float],
) -> str:
    """Snapshot sparse operators and completed direct references."""
    return _serialize_bounded(
        {
            "schema": CG_EVIDENCE_SCHEMA,
            "evidence_kind": "SOURCE_OPERATORS_AND_COMPLETED_DIRECT_REFERENCES",
            "mesh": {"id": mesh_id, "elements": elements, "free_dofs": free_dofs},
            "source_sha": source_sha,
            "operator_identity": operator_identity,
            "rayleigh_definition": {
                "formula": "C = alpha * M + beta * K",
                "alpha_per_s": alpha_per_s,
                "beta_s": beta_s,
                "units": "projected mass-normalized damping entries have units s^-1",
            },
            "operators": {
                "M": _csr_snapshot(mass),
                "K": _csr_snapshot(stiffness),
                "C_used_by_experiment": _csr_snapshot(damping),
                "symmetry_metrics": {
                    "M": _sparse_symmetry_metrics(mass),
                    "K": _sparse_symmetry_metrics(stiffness),
                    "C": _sparse_symmetry_metrics(damping),
                },
            },
            "direct_reference": {
                "scope": "same assembled constrained FEM operators; internal control only",
                "frequencies_hz": frequencies_hz,
                "reduced_force": reduced_force,
                "responses_full_free_complex": direct_responses,
                "normalized_equilibrium_residuals": direct_relative_residuals,
            },
            "exact_numeric_arrays": {
                "frequencies_hz": _numeric_array_snapshot(np.asarray(frequencies_hz, dtype=np.float64)),
                "normalized_equilibrium_residuals": _numeric_array_snapshot(
                    np.asarray(direct_relative_residuals, dtype=np.float64)
                ),
                "reduced_force": _numeric_array_snapshot(reduced_force),
                "responses_full_free_complex": [_numeric_array_snapshot(response) for response in direct_responses],
            },
            "numeric_encoding": "Typed JSON values plus exact C-order dtype-bound bytes in base64 and SHA-256",
        }
    )


def projected_damping_evidence(
    *,
    mesh_id: str,
    mode_count: int,
    source_sha: str,
    basis_identity: str,
    operator_identity: str,
    basis_diagnostics: dict[str, Any],
    modal_clusters_zero_based: tuple[tuple[int, ...], ...],
    modes: np.ndarray,
    eigenvalues_rad2_s2: np.ndarray,
    mass: Any,
    damping: Any,
    projected_mass: np.ndarray,
    projected_stiffness: np.ndarray,
    alpha_per_s: float,
    beta_s: float,
    symmetry_tolerance: float,
) -> str:
    """Capture exact production projection operands without changing its gate."""
    phi = np.asarray(modes)
    if phi.dtype.kind != "f":
        raise TypeError(f"CG modal basis evidence requires real floating-point modes, got {phi.dtype}.")
    c_physical = damping.tocsr(copy=True)
    damping_times_modes = np.asarray(c_physical @ phi)
    projected = np.asarray(phi.T @ damping_times_modes, dtype=np.float64)
    expected = alpha_per_s * np.asarray(projected_mass) + beta_s * np.asarray(projected_stiffness)
    skew_norm = float(np.linalg.norm(projected - projected.T, ord="fro"))
    projected_norm = float(np.linalg.norm(projected, ord="fro"))
    try:
        condition_number: float | None = float(np.linalg.cond(projected))
    except np.linalg.LinAlgError:
        condition_number = None
    input_metrics = _sparse_symmetry_metrics(c_physical)
    mass_gram = np.asarray(phi.T @ (mass @ phi), dtype=np.float64)
    orthogonality = float(np.linalg.norm(mass_gram - np.eye(mode_count), ord="fro"))
    return _serialize_bounded(
        {
            "schema": CG_EVIDENCE_SCHEMA,
            "evidence_kind": "PROJECTED_DAMPING_PRECHECK_OPERANDS",
            "mesh_id": mesh_id,
            "mode_count": mode_count,
            "source_sha": source_sha,
            "basis_identity": basis_identity,
            "operator_identity": operator_identity,
            "basis_diagnostics": basis_diagnostics,
            "modal_clusters_zero_based": modal_clusters_zero_based,
            "projection_expression": "Phi.T @ (C @ Phi), with C=alpha*M+beta*K",
            "projection_association": "C @ Phi is evaluated first; Phi.T multiplies that stored result",
            "projection_dtype": str(projected.dtype),
            "mode_matrix": phi,
            "eigenvalues_rad2_s2": eigenvalues_rad2_s2,
            "projected_mass": projected_mass,
            "projected_stiffness": projected_stiffness,
            "projected_mass_gram_from_saved_modes": mass_gram,
            "mass_orthogonality_frobenius_error": orthogonality,
            "input_damping": _csr_snapshot(c_physical),
            "damping_times_modes": damping_times_modes,
            "input_damping_symmetry": input_metrics,
            "projected_damping": projected,
            "projected_damping_frobenius_norm": projected_norm,
            "projected_damping_condition_number": condition_number,
            "projected_damping_skew_frobenius_norm": skew_norm,
            "projected_damping_relative_skew": skew_norm / max(projected_norm, np.finfo(np.float64).tiny),
            "frozen_symmetry_threshold": symmetry_tolerance,
            "expected_projected_rayleigh_from_cached_operators": expected,
            "projection_vs_cached_rayleigh_relative_difference": float(
                np.linalg.norm(projected - expected, ord="fro") / max(projected_norm, np.finfo(np.float64).tiny)
            ),
            "acceptance_verdict": "DIAGNOSTIC_ONLY_NOT_AN_ACCEPTANCE_OVERRIDE",
            "exact_numeric_arrays": {
                "mode_matrix": _numeric_array_snapshot(phi),
                "eigenvalues_rad2_s2": _numeric_array_snapshot(eigenvalues_rad2_s2),
                "damping_times_modes": _numeric_array_snapshot(damping_times_modes),
                "projected_mass": _numeric_array_snapshot(projected_mass),
                "projected_stiffness": _numeric_array_snapshot(projected_stiffness),
                "projected_mass_gram": _numeric_array_snapshot(mass_gram),
                "projected_damping": _numeric_array_snapshot(projected),
                "expected_projected_rayleigh_from_cached_operators": _numeric_array_snapshot(expected),
            },
        }
    )
