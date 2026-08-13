"""Aggregated audits for large-scale TET4 models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.sparse import spmatrix

from solveur.large.assembler import fixed_dof_indices
from solveur.large.materials import create_large_material
from solveur.large.model import LargeModel
from solveur.mesh.quality import MeshQualityThresholds


@dataclass(frozen=True)
class LargeAuditReport:
    """Compact, machine-readable large-model audit."""

    status: str
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    details: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "details": self.details,
        }


def inspect_large_model(
    model: LargeModel,
    *,
    stiffness: spmatrix | None = None,
    loads: np.ndarray | None = None,
    displacement: np.ndarray | None = None,
    sample_size: int = 32,
) -> LargeAuditReport:
    """Return an aggregated audit without dense matrix conversion."""
    errors: list[str] = []
    warnings: list[str] = []
    _validate_scope(model, errors)
    quality = _tet4_quality_summary(model)
    thresholds = MeshQualityThresholds()
    if quality["invalid_volume_count"]:
        errors.append(f"{quality['invalid_volume_count']} TET4 elements have invalid signed volume.")
    if quality["low_quality_count"]:
        warnings.append(f"{quality['low_quality_count']} TET4 elements are below quality threshold.")
    fixed = fixed_dof_indices(model)
    if fixed.size == 0:
        warnings.append("No fixed degree of freedom is defined; solve may be singular.")
    details: dict[str, Any] = {
        "node_count": model.node_count,
        "element_count": model.element_count,
        "ndof": model.ndof,
        "analysis": model.analysis.get("type", ""),
        "method": model.analysis.get("method", ""),
        "fixed_dof_count": int(fixed.size),
        "free_dof_count": int(model.ndof - fixed.size),
        "load_count": int(model.load_values.size),
        "quality_thresholds": thresholds.to_dict(),
        "tet4_quality": quality,
        "sampled_elements": _sample_elements(model, sample_size),
    }
    if stiffness is not None:
        details["matrix"] = _matrix_summary(stiffness)
    if loads is not None:
        details["load_norm"] = float(np.linalg.norm(loads))
    if stiffness is not None and loads is not None and displacement is not None:
        details["solution"] = _solution_summary(stiffness, loads, displacement, fixed)
    status = "FAIL" if errors else "WARNING" if warnings else "PASS"
    details["error_count"] = len(errors)
    details["warning_count"] = len(warnings)
    return LargeAuditReport(status=status, errors=tuple(errors), warnings=tuple(warnings), details=details)


def _validate_scope(model: LargeModel, errors: list[str]) -> None:
    if model.analysis.get("type", "") != "linear_static":
        errors.append("Large-scale v1 supports only linear_static analysis.")
    if model.nodes.size == 0:
        errors.append("Large-scale model contains no nodes.")
    if model.tet4.size == 0:
        errors.append("Large-scale model contains no TET4 elements.")
    for name in model.material_names:
        material = model.materials.get(name, {})
        try:
            create_large_material(material)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"Material {name!r} is invalid or unsupported: {exc}")


def _tet4_quality_summary(model: LargeModel, chunk_size: int = 65536) -> dict[str, Any]:
    threshold = MeshQualityThresholds()
    stats = _empty_stats()
    invalid = 0
    low_quality = 0
    for start in range(0, model.element_count, chunk_size):
        stop = min(start + chunk_size, model.element_count)
        coords = model.nodes[model.tet4[start:stop]]
        volumes = _signed_volumes(coords)
        edge_lengths = _edge_lengths(coords)
        edge_min = np.min(edge_lengths, axis=1)
        edge_max = np.max(edge_lengths, axis=1)
        rms = np.sqrt(np.mean(edge_lengths**2, axis=1))
        quality = np.divide(
            6.0 * np.sqrt(2.0) * np.abs(volumes),
            rms**3,
            out=np.zeros_like(volumes),
            where=rms > 0.0,
        )
        aspect = np.divide(edge_max, edge_min, out=np.full_like(edge_max, np.inf), where=edge_min > 0.0)
        relative_volume = np.divide(
            np.abs(volumes),
            edge_max**3,
            out=np.zeros_like(volumes),
            where=edge_max > 0.0,
        )
        _update_stats(stats["signed_volume"], volumes)
        _update_stats(stats["quality"], quality)
        _update_stats(stats["aspect_ratio"], aspect)
        _update_stats(stats["relative_volume"], relative_volume)
        invalid += int(np.count_nonzero(volumes <= threshold.tet_min_signed_volume))
        low_quality += int(np.count_nonzero(quality < threshold.tet_min_quality))
    return {
        **{name: _finalize_stats(value, model.element_count) for name, value in stats.items()},
        "invalid_volume_count": invalid,
        "low_quality_count": low_quality,
    }


def _empty_stats() -> dict[str, dict[str, float]]:
    return {
        name: {"min": float("inf"), "max": float("-inf"), "sum": 0.0}
        for name in ("signed_volume", "quality", "aspect_ratio", "relative_volume")
    }


def _update_stats(stats: dict[str, float], values: np.ndarray) -> None:
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return
    stats["min"] = min(stats["min"], float(np.min(finite)))
    stats["max"] = max(stats["max"], float(np.max(finite)))
    stats["sum"] += float(np.sum(finite))


def _finalize_stats(stats: dict[str, float], count: int) -> dict[str, float]:
    if count == 0 or stats["min"] == float("inf"):
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    return {"min": stats["min"], "max": stats["max"], "mean": stats["sum"] / count}


def _signed_volumes(coords: np.ndarray) -> np.ndarray:
    return np.einsum(
        "ij,ij->i",
        np.cross(coords[:, 1] - coords[:, 0], coords[:, 2] - coords[:, 0]),
        coords[:, 3] - coords[:, 0],
    ) / 6.0


def _edge_lengths(coords: np.ndarray) -> np.ndarray:
    pairs = ((0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3))
    return np.column_stack([np.linalg.norm(coords[:, j] - coords[:, i], axis=1) for i, j in pairs])


def _sample_elements(model: LargeModel, sample_size: int) -> list[dict[str, Any]]:
    if model.element_count == 0 or sample_size <= 0:
        return []
    indices = np.unique(np.linspace(0, model.element_count - 1, min(sample_size, model.element_count), dtype=int))
    volumes = _signed_volumes(model.nodes[model.tet4[indices]])
    return [{"index": int(index), "signed_volume": float(volume)} for index, volume in zip(indices, volumes)]


def _matrix_summary(matrix: spmatrix) -> dict[str, Any]:
    csr = matrix.tocsr()
    symmetry = csr - csr.T
    data_norm = float(np.linalg.norm(csr.data))
    return {
        "shape": [int(csr.shape[0]), int(csr.shape[1])],
        "nnz": int(csr.nnz),
        "data_norm": data_norm,
        "symmetry_relative_error": float(np.linalg.norm(symmetry.data) / max(data_norm, 1.0)),
    }


def _solution_summary(matrix: spmatrix, loads: np.ndarray, displacement: np.ndarray, fixed: np.ndarray) -> dict[str, float]:
    internal = matrix @ displacement
    residual = internal - loads
    free = np.setdiff1d(np.arange(loads.size, dtype=np.int64), fixed)
    free_norm = float(np.linalg.norm(residual[free]))
    load_norm = float(np.linalg.norm(loads[free]))
    return {
        "displacement_norm": float(np.linalg.norm(displacement)),
        "max_displacement": float(np.max(np.abs(displacement))) if displacement.size else 0.0,
        "free_residual_norm": free_norm,
        "free_relative_residual": free_norm / max(load_norm, 1.0),
        "reaction_norm": float(np.linalg.norm(residual[fixed])) if fixed.size else 0.0,
        "strain_energy": float(0.5 * displacement @ internal),
        "external_work": float(displacement @ loads),
    }
