"""Deterministic mode-shape comparison helpers for controlled V&V."""

from __future__ import annotations

from itertools import permutations
from typing import Any

import numpy as np


def _mode_array(modes: Any, name: str) -> np.ndarray:
    values = np.asarray(modes, dtype=float)
    if values.ndim != 2:
        raise ValueError(f"{name} must be a two-dimensional mode matrix.")
    if not np.isfinite(values).all():
        raise ValueError(f"{name} must contain only finite values.")
    if values.shape[1] == 0:
        raise ValueError(f"{name} must contain at least one mode.")
    norms = np.linalg.norm(values, axis=0)
    if np.any(norms <= 0.0):
        raise ValueError(f"{name} must not contain zero-norm modes.")
    return values


def normalize_modes(modes: Any) -> np.ndarray:
    """Return unit Euclidean modes with a deterministic sign convention."""

    values = _mode_array(modes, "modes").copy()
    values /= np.linalg.norm(values, axis=0, keepdims=True)
    for index in range(values.shape[1]):
        pivot = int(np.argmax(np.abs(values[:, index])))
        if values[pivot, index] < 0.0:
            values[:, index] *= -1.0
    return values


def mac_matrix(reference_modes: Any, candidate_modes: Any) -> np.ndarray:
    """Return the sign-invariant modal assurance criterion matrix."""

    reference = normalize_modes(reference_modes)
    candidate = normalize_modes(candidate_modes)
    if reference.shape[0] != candidate.shape[0]:
        raise ValueError("Mode matrices must have the same number of DOFs.")
    return np.square(reference.T @ candidate)


def _assignment_cost(
    reference_frequencies: np.ndarray,
    candidate_frequencies: np.ndarray,
    mac: np.ndarray,
) -> np.ndarray:
    scale = np.maximum(np.maximum(np.abs(reference_frequencies[:, None]), np.abs(candidate_frequencies[None, :])), 1.0e-30)
    frequency_error = np.abs(reference_frequencies[:, None] - candidate_frequencies[None, :]) / scale
    return frequency_error + (1.0 - mac)


def _best_assignment(cost: np.ndarray) -> list[tuple[int, int]]:
    rows, columns = cost.shape
    if rows != columns:
        raise ValueError("Mode matching requires equal mode counts.")
    # The V&V contract compares a small declared prefix.  Enumerating its
    # permutations makes tie handling deterministic without another backend.
    if rows > 8:
        raise ValueError("Mode matching is limited to at most eight declared modes.")
    candidates = ((float(sum(cost[row, column] for row, column in enumerate(order))), order) for order in permutations(range(rows)))
    _, order = min(candidates, key=lambda item: (item[0], item[1]))
    return [(row, int(column)) for row, column in enumerate(order)]


def _frequency_clusters(frequencies: np.ndarray, relative_gap: float) -> list[list[int]]:
    clusters: list[list[int]] = []
    for index in range(frequencies.size):
        if not clusters:
            clusters.append([index])
            continue
        previous = clusters[-1][-1]
        scale = max(abs(float(frequencies[previous])), abs(float(frequencies[index])), 1.0e-30)
        if abs(float(frequencies[index] - frequencies[previous])) / scale <= relative_gap:
            clusters[-1].append(index)
        else:
            clusters.append([index])
    return clusters


def match_modes(
    reference_frequencies: Any,
    reference_modes: Any,
    candidate_frequencies: Any,
    candidate_modes: Any,
    *,
    frequency_tolerance: float,
    mac_tolerance: float,
    near_degenerate_tolerance: float = 1.0e-5,
) -> dict[str, Any]:
    """Match modes without accepting an out-of-policy pairing.

    Frequencies and MAC jointly choose a deterministic one-to-one pairing.  A
    near-degenerate group is judged by its subspace MAC because individual
    eigenvectors in that subspace are not unique.
    """

    reference_frequency = np.asarray(reference_frequencies, dtype=float)
    candidate_frequency = np.asarray(candidate_frequencies, dtype=float)
    if reference_frequency.ndim != 1 or candidate_frequency.ndim != 1:
        raise ValueError("Frequencies must be one-dimensional.")
    if reference_frequency.size != candidate_frequency.size:
        raise ValueError("Frequency vectors must have equal lengths.")
    if not np.isfinite(reference_frequency).all() or not np.isfinite(candidate_frequency).all():
        raise ValueError("Frequencies must be finite.")
    if frequency_tolerance < 0.0 or not np.isfinite(frequency_tolerance):
        raise ValueError("frequency_tolerance must be finite and non-negative.")
    if not 0.0 <= mac_tolerance <= 1.0:
        raise ValueError("mac_tolerance must be in [0, 1].")
    mac = mac_matrix(reference_modes, candidate_modes)
    assignment = _best_assignment(_assignment_cost(reference_frequency, candidate_frequency, mac))
    reference_normalized = normalize_modes(reference_modes)
    candidate_normalized = normalize_modes(candidate_modes)
    clusters = _frequency_clusters(reference_frequency, near_degenerate_tolerance)
    cluster_by_mode = {mode: cluster_id for cluster_id, cluster in enumerate(clusters) for mode in cluster}
    pairs: list[dict[str, Any]] = []
    for reference_index, candidate_index in assignment:
        scale = max(abs(float(reference_frequency[reference_index])), abs(float(candidate_frequency[candidate_index])), 1.0e-30)
        frequency_error = abs(float(reference_frequency[reference_index] - candidate_frequency[candidate_index])) / scale
        cluster = clusters[cluster_by_mode[reference_index]]
        candidate_cluster = [column for row, column in assignment if row in cluster]
        if len(cluster) > 1:
            reference_basis = reference_normalized[:, cluster]
            candidate_basis = candidate_normalized[:, candidate_cluster]
            singular_values = np.linalg.svd(reference_basis.T @ candidate_basis, compute_uv=False)
            subspace_mac = float(np.sum(singular_values**2) / len(cluster))
            mac_value = subspace_mac
            quality_rule = "subspace_mac"
        else:
            mac_value = float(mac[reference_index, candidate_index])
            quality_rule = "individual_mac"
        accepted = frequency_error <= frequency_tolerance and mac_value >= mac_tolerance
        pairs.append(
            {
                "reference_mode": reference_index + 1,
                "candidate_mode": candidate_index + 1,
                "frequency_error": frequency_error,
                "mac": mac_value,
                "quality_rule": quality_rule,
                "near_degenerate_group": cluster if len(cluster) > 1 else None,
                "accepted": accepted,
            }
        )
    return {
        "status": "PASS" if all(pair["accepted"] for pair in pairs) else "FAIL",
        "pairs": pairs,
        "mac_matrix": mac.tolist(),
        "frequency_tolerance": float(frequency_tolerance),
        "mac_tolerance": float(mac_tolerance),
        "near_degenerate_tolerance": float(near_degenerate_tolerance),
        "normalization": "unit Euclidean norm; sign pivot is first largest-absolute component",
        "matching": "deterministic minimum frequency-error plus one-minus-MAC assignment; out-of-policy pairs fail",
    }


__all__ = ["mac_matrix", "match_modes", "normalize_modes"]
