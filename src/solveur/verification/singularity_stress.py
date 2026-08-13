"""Assess stress convergence near finite concentrations and true singularities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np


ReferenceKind = Literal["analytic", "code_aster", "calculix", "test"]


@dataclass(frozen=True)
class StressPathSample:
    """Stress values sampled at fixed physical distances for one mesh level."""

    mesh_size: float
    distances: tuple[float, ...]
    values: tuple[float, ...]
    band_average: float

    def __post_init__(self) -> None:
        mesh_size = float(self.mesh_size)
        distances = np.asarray(self.distances, dtype=float)
        values = np.asarray(self.values, dtype=float)
        if not np.isfinite(mesh_size) or mesh_size <= 0.0:
            raise ValueError("mesh_size must be finite and positive.")
        if distances.ndim != 1 or values.ndim != 1 or distances.size < 2 or distances.size != values.size:
            raise ValueError("distances and values must be one-dimensional vectors of the same size >= 2.")
        if not np.all(np.isfinite(distances)) or not np.all(np.isfinite(values)):
            raise ValueError("stress path distances and values must be finite.")
        if np.any(distances <= 0.0) or np.any(np.diff(distances) <= 0.0):
            raise ValueError("stress path distances must be strictly increasing and positive.")
        if not np.isfinite(float(self.band_average)):
            raise ValueError("band_average must be finite.")


class SingularityStressAssessor:
    """Apply the controlled acceptance protocol to path and band stress data."""

    min_distance_over_h = 2.0
    final_increment_limit = 0.05
    reference_error_limit = 0.05

    def assess(
        self,
        samples: Sequence[StressPathSample],
        *,
        true_singularity: bool,
        reference_values: Sequence[float],
        reference_band_average: float,
        reference_kind: ReferenceKind,
    ) -> dict[str, object]:
        """Return a machine-readable verdict without using a nodal peak as evidence."""
        ordered = tuple(samples)
        self._validate_sequence(ordered, reference_values, reference_band_average)
        coarse_to_fine = all(left.mesh_size > right.mesh_size for left, right in zip(ordered, ordered[1:]))
        distances = np.asarray(ordered[-1].distances, dtype=float)
        values = np.asarray([sample.values for sample in ordered], dtype=float)
        bands = np.asarray([sample.band_average for sample in ordered], dtype=float)
        reference = np.asarray(reference_values, dtype=float)
        clearance = min(float(np.min(distances / sample.mesh_size)) for sample in ordered)
        path_increment = _relative_vector(values[-1], values[-2])
        band_increment = _relative_scalar(bands[-1], bands[-2])
        path_reference_error = _relative_vector(values[-1], reference)
        band_reference_error = _relative_scalar(bands[-1], float(reference_band_average))
        checks = [
            _check("mesh_order", float(coarse_to_fine), 1.0, "lower"),
            _check("minimum_distance_over_h", clearance, self.min_distance_over_h, "lower"),
            _check("final_path_increment", float(np.max(path_increment)), self.final_increment_limit, "upper"),
            _check("final_band_increment", band_increment, self.final_increment_limit, "upper"),
            _check("reference_path_error", float(np.max(path_reference_error)), self.reference_error_limit, "upper"),
            _check("reference_band_error", band_reference_error, self.reference_error_limit, "upper"),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        peak_rule = (
            "informative_only_true_singularity"
            if true_singularity
            else "eligible_only_after_finite_radius_convergence"
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "reference_kind": reference_kind,
            "true_singularity": bool(true_singularity),
            "point_peak_rule": peak_rule,
            "acceptance_observables": ["fixed_distance_path", "band_average"],
            "mesh_sizes": [float(sample.mesh_size) for sample in ordered],
            "distances": distances.tolist(),
            "fine_path_values": values[-1].tolist(),
            "fine_band_average": float(bands[-1]),
            "checks": checks,
        }

    @staticmethod
    def _validate_sequence(
        samples: tuple[StressPathSample, ...],
        reference_values: Sequence[float],
        reference_band_average: float,
    ) -> None:
        if len(samples) < 3:
            raise ValueError("singularity stress acceptance requires at least three mesh levels.")
        reference = np.asarray(reference_values, dtype=float)
        if reference.ndim != 1 or not np.all(np.isfinite(reference)):
            raise ValueError("reference_values must be a finite one-dimensional vector.")
        if not np.isfinite(float(reference_band_average)):
            raise ValueError("reference_band_average must be finite.")
        first_distances = samples[0].distances
        if reference.size != len(first_distances):
            raise ValueError("reference_values must match the number of sampling distances.")
        if any(sample.distances != first_distances for sample in samples[1:]):
            raise ValueError("all mesh levels must use identical physical sampling distances.")


def _relative_vector(values: np.ndarray, reference: np.ndarray) -> np.ndarray:
    denominator = np.maximum(np.maximum(np.abs(values), np.abs(reference)), np.finfo(float).tiny)
    return np.abs(values - reference) / denominator


def _relative_scalar(value: float, reference: float) -> float:
    denominator = max(abs(value), abs(reference), np.finfo(float).tiny)
    return abs(value - reference) / denominator


def _check(identifier: str, value: float, limit: float, direction: Literal["lower", "upper"]) -> dict[str, object]:
    passed = value >= limit if direction == "lower" else value <= limit
    return {
        "id": identifier,
        "value": value,
        "limit": limit,
        "direction": direction,
        "status": "PASS" if passed else "FAIL",
    }
