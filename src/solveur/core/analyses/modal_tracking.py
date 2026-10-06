"""Deterministic complex-mode association for experimental Campbell sweeps."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
from scipy.optimize import linear_sum_assignment

from solveur.core.errors import InputValidationError


POLICY_ID = "QF0211-COMPLEX-MAC-GLOBAL-v1"
MAC_MINIMUM = 0.8
FREQUENCY_DISTANCE_MAXIMUM = 0.25
AMBIGUITY_MARGIN_MINIMUM = 0.05
CLUSTER_RELATIVE_GAP = 1.0e-8
SUBSPACE_MINIMUM_SINGULAR_VALUE = 0.99999999
POLARIZATION_WEAK_CHI = 0.1
_UNMATCHED_COST = 0.4
_INVALID_COST = 1.0e6


@dataclass(frozen=True)
class PolarizationEstimate:
    """Transverse complex polarization at one spin speed."""

    chi: float | None
    classification: str
    relative_whirl: str
    defined: bool
    station_chi: tuple[float, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chi": self.chi,
            "classification": self.classification,
            "relative_whirl": self.relative_whirl,
            "defined": self.defined,
            "station_chi": list(self.station_chi),
        }


def complex_mac(left: np.ndarray, right: np.ndarray, mass: np.ndarray) -> float:
    """Return the phase- and scale-invariant Hermitian mass-weighted MAC."""

    phi_left = np.asarray(left, dtype=np.complex128)
    phi_right = np.asarray(right, dtype=np.complex128)
    matrix = np.asarray(mass, dtype=np.complex128)
    if phi_left.ndim != 1 or phi_right.shape != phi_left.shape or matrix.shape != (phi_left.size, phi_left.size):
        raise InputValidationError("Complex MAC mode vectors and mass matrix have incompatible dimensions.")
    if not np.all(np.isfinite(phi_left)) or not np.all(np.isfinite(phi_right)) or not np.all(np.isfinite(matrix)):
        raise InputValidationError("Complex MAC inputs must be finite.")
    left_norm = np.vdot(phi_left, matrix @ phi_left)
    right_norm = np.vdot(phi_right, matrix @ phi_right)
    denominator = float(left_norm.real * right_norm.real)
    if (
        abs(left_norm.imag) > 1.0e-10 * max(abs(left_norm.real), 1.0)
        or abs(right_norm.imag) > 1.0e-10 * max(abs(right_norm.real), 1.0)
        or not np.isfinite(denominator)
        or denominator <= np.finfo(float).tiny
    ):
        raise InputValidationError("Complex MAC requires positive real mass norms for both modes.")
    value = float(abs(np.vdot(phi_left, matrix @ phi_right)) ** 2 / denominator)
    if not np.isfinite(value):
        raise InputValidationError("Complex MAC produced a non-finite score.")
    return min(1.0, max(0.0, value))


def complex_mac_matrix(previous_modes: np.ndarray, current_modes: np.ndarray, mass: np.ndarray) -> np.ndarray:
    """Compute all pairwise complex MAC scores without real projection."""

    previous = np.asarray(previous_modes, dtype=np.complex128)
    current = np.asarray(current_modes, dtype=np.complex128)
    if previous.ndim != 2 or current.ndim != 2 or previous.shape[0] != current.shape[0]:
        raise InputValidationError("Mode matrices for complex MAC must have the same physical row count.")
    return np.asarray(
        [[complex_mac(previous[:, i], current[:, j], mass) for j in range(current.shape[1])] for i in range(previous.shape[1])],
        dtype=float,
    )


def normalized_frequency_distance(left_hz: float, right_hz: float) -> float:
    """Return a bounded, deterministic relative frequency distance."""

    left = float(left_hz)
    right = float(right_hz)
    denominator = max(abs(left), abs(right), 1.0)
    return abs(left - right) / denominator


def estimate_polarization(result: Any, mode_index: int) -> PolarizationEstimate:
    """Estimate the signed transverse polarization using the WP05 axis convention."""

    omega = float(result.spin_speed_rad_s)
    if omega == 0.0:
        return PolarizationEstimate(None, "UNDEFINED", "UNDEFINED", False, ())
    axis = np.asarray(result.axis_global, dtype=float)
    reference = np.eye(3)[int(np.argmin(np.abs(axis)))]
    first = reference - axis * float(np.dot(axis, reference))
    first_norm = float(np.linalg.norm(first))
    if not np.isfinite(first_norm) or first_norm <= np.finfo(float).tiny:
        return PolarizationEstimate(None, "UNDEFINED", "UNDEFINED", False, ())
    first /= first_norm
    second = np.cross(axis, first)
    second /= np.linalg.norm(second)

    mode = np.asarray(result.modes[:, mode_index], dtype=np.complex128)
    station_components: list[tuple[float, float]] = []
    for node in sorted(result.dofs.node_dofs):
        names = result.dofs.node_dofs[node]
        translation = np.zeros(3, dtype=np.complex128)
        for position, name in enumerate(("UX", "UY", "UZ")):
            if name in names:
                translation[position] = mode[result.dofs.index(node, name)]
        station_components.append((complex(np.dot(first, translation)), complex(np.dot(second, translation))))
    max_amplitude = max((float(np.hypot(abs(u1), abs(u2))) for u1, u2 in station_components), default=0.0)
    if not np.isfinite(max_amplitude) or max_amplitude <= np.finfo(float).tiny:
        return PolarizationEstimate(None, "UNDEFINED", "UNDEFINED", False, ())
    station_chi = []
    for u1, u2 in station_components:
        amplitude = float(np.hypot(abs(u1), abs(u2)))
        if amplitude < 1.0e-8 * max_amplitude:
            continue
        denominator = abs(u1) ** 2 + abs(u2) ** 2
        station_chi.append(float(-2.0 * np.imag(np.conj(u1) * u2) / denominator))
    if not station_chi:
        return PolarizationEstimate(None, "UNDEFINED", "UNDEFINED", False, ())
    strong = [value for value in station_chi if abs(value) > POLARIZATION_WEAK_CHI]
    if not strong:
        return PolarizationEstimate(float(np.median(station_chi)), "WEAKLY_POLARIZED", "UNDEFINED", False, tuple(station_chi))
    signs = {1 if value > 0.0 else -1 for value in strong}
    if len(signs) > 1:
        return PolarizationEstimate(None, "INCONSISTENT", "INCONSISTENT", False, tuple(station_chi))
    chi = float(np.clip(np.median(strong), -1.0, 1.0))
    if abs(chi) <= POLARIZATION_WEAK_CHI:
        return PolarizationEstimate(chi, "WEAKLY_POLARIZED", "UNDEFINED", False, tuple(station_chi))
    relative = "FORWARD" if np.sign(omega) * chi > 0.0 else "BACKWARD"
    return PolarizationEstimate(chi, "POLARIZED", relative, True, tuple(station_chi))


def track_modal_sweep(results: Sequence[Any], mass: np.ndarray) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Build branch lineage and diagnostics from an ordered set of rotating results."""

    if len(results) < 2:
        raise InputValidationError("Campbell tracking requires at least two rotating_modal results.")
    speeds = [float(item.spin_speed_rad_s) for item in results]
    if any(not np.isfinite(speed) for speed in speeds) or any(b <= a for a, b in zip(speeds, speeds[1:])):
        raise InputValidationError("Campbell tracking speeds must be finite and strictly increasing.")
    mass_matrix = np.asarray(mass, dtype=np.complex128)
    if mass_matrix.ndim != 2 or mass_matrix.shape[0] != mass_matrix.shape[1]:
        raise InputValidationError("Campbell tracking requires a square physical mass matrix.")
    if any(item.modes.shape[0] != mass_matrix.shape[0] for item in results):
        raise InputValidationError("Campbell result mode dimensions do not match the tracking mass matrix.")

    branch_records: dict[str, dict[str, Any]] = {}
    diagnostics: list[dict[str, Any]] = []
    sample_groups = [_groups_for_result(result) for result in results]
    next_branch_number = 0
    next_cluster_number = 0

    def new_branch(prefix: str = "branch") -> str:
        nonlocal next_branch_number, next_cluster_number
        if prefix == "cluster":
            identifier = f"cluster-{next_cluster_number:03d}"
            next_cluster_number += 1
        else:
            identifier = f"branch-{next_branch_number:03d}"
            next_branch_number += 1
        branch_records[identifier] = {
            "branch_id": identifier,
            "parent_branch_ids": [],
            "child_branch_ids": [],
            "samples": [None] * len(results),
        }
        return identifier

    def append(group: dict[str, Any], speed_index: int, branch_id: str, status: str, **extra: Any) -> None:
        group["branch_id"] = branch_id
        point = _group_sample(group, speed_index, speeds[speed_index], status, extra)
        branch_records[branch_id]["samples"][speed_index] = point

    previous = sample_groups[0]
    for group in previous:
        identifier = new_branch("cluster" if len(group["modes"]) > 1 else "branch")
        append(group, 0, identifier, "DEGENERATE_CLUSTER" if len(group["modes"]) > 1 else "UNTRACKED")

    for speed_index in range(1, len(results)):
        current = sample_groups[speed_index]
        used_previous: set[int] = set()
        used_current: set[int] = set()

        # A cluster becoming a set of separated modes is a lineage event, not a
        # collection of independently identifiable eigenvectors at the parent.
        for i, old in enumerate(previous):
            if len(old["modes"]) < 2:
                continue
            candidate_indices = [j for j, new in enumerate(current) if len(new["modes"]) == 1]
            projections = [(j, _group_projection(old, current[j], mass_matrix)) for j in candidate_indices]
            accepted = [(j, value) for j, value in projections if value >= SUBSPACE_MINIMUM_SINGULAR_VALUE**2]
            if len(accepted) != len(old["modes"]):
                continue
            split_group = _combined_group([current[j] for j, _ in accepted])
            split_similarity = _subspace_similarity(old, split_group, mass_matrix)
            if split_similarity < SUBSPACE_MINIMUM_SINGULAR_VALUE:
                continue
            used_previous.add(i)
            child_labels = _split_child_labels([current[j] for j, _ in accepted])
            children: list[str] = []
            for (j, projection), label in zip(accepted, child_labels):
                child_id = f"{old['branch_id']}.{label}"
                if child_id in branch_records:
                    child_id = f"{old['branch_id']}.child-{len(children) + 1:03d}-at-{speed_index:03d}"
                branch_records[child_id] = {
                    "branch_id": child_id,
                    "parent_branch_ids": [old["branch_id"]],
                    "child_branch_ids": [],
                    "samples": [None] * len(results),
                }
                children.append(child_id)
                used_current.add(j)
                append(current[j], speed_index, child_id, "DEGENERATE_CLUSTER", parent_subspace_projection=projection)
                diagnostics.append({
                    "from_speed_index": speed_index - 1,
                    "to_speed_index": speed_index,
                    "status": "DEGENERATE_CLUSTER",
                    "event": "CLUSTER_SPLIT",
                    "parent_branch_id": old["branch_id"],
                    "child_branch_id": child_id,
                    "subspace_projection": projection,
                    "combined_subspace_minimum_singular_value": split_similarity,
                })
            branch_records[old["branch_id"]]["child_branch_ids"].extend(children)

        # Conversely, multiple individual branches may meet in a degenerate
        # subspace. Preserve the merger rather than pairing arbitrary vectors.
        for j, new in enumerate(current):
            if j in used_current or len(new["modes"]) < 2:
                continue
            candidate_indices = [i for i, old in enumerate(previous) if i not in used_previous and len(old["modes"]) == 1]
            projections = [(i, _group_projection(new, previous[i], mass_matrix)) for i in candidate_indices]
            accepted = [(i, value) for i, value in projections if value >= SUBSPACE_MINIMUM_SINGULAR_VALUE**2]
            if len(accepted) != len(new["modes"]):
                continue
            merged_group = _combined_group([previous[i] for i, _ in accepted])
            merge_similarity = _subspace_similarity(new, merged_group, mass_matrix)
            if merge_similarity < SUBSPACE_MINIMUM_SINGULAR_VALUE:
                continue
            parents = sorted(previous[i]["branch_id"] for i, _ in accepted)
            cluster_id = f"cluster-{speed_index:03d}-{j:03d}"
            branch_records[cluster_id] = {
                "branch_id": cluster_id,
                "parent_branch_ids": parents,
                "child_branch_ids": [],
                "samples": [None] * len(results),
            }
            for i, _ in accepted:
                used_previous.add(i)
                branch_records[previous[i]["branch_id"]]["child_branch_ids"].append(cluster_id)
            used_current.add(j)
            append(new, speed_index, cluster_id, "DEGENERATE_CLUSTER", parent_branch_ids=parents)
            diagnostics.append({
                "from_speed_index": speed_index - 1,
                "to_speed_index": speed_index,
                "status": "DEGENERATE_CLUSTER",
                "event": "CLUSTER_MERGE",
                "parent_branch_ids": parents,
                "cluster_branch_id": cluster_id,
                "combined_subspace_minimum_singular_value": merge_similarity,
            })

        old_indices = [i for i in range(len(previous)) if i not in used_previous]
        new_indices = [j for j in range(len(current)) if j not in used_current]
        ambiguous_targets: dict[int, list[str]] = {}
        candidate_edges_by_target: dict[int, list[dict[str, Any]]] = {}
        if old_indices and new_indices:
            costs, admissible, metrics = _group_costs(
                [previous[i] for i in old_indices], [current[j] for j in new_indices], mass_matrix
            )
            for local_j, new_index in enumerate(new_indices):
                candidate_edges_by_target[new_index] = [
                    {
                        "source_branch_id": previous[old_indices[local_i]]["branch_id"],
                        "source_mode_indices": [
                            mode["source_mode_index"] for mode in previous[old_indices[local_i]]["modes"]
                        ],
                        "target_mode_indices": [mode["source_mode_index"] for mode in current[new_index]["modes"]],
                        "assignment_cost": float(costs[local_i, local_j]),
                        **metrics[local_i][local_j],
                    }
                    for local_i in np.flatnonzero(admissible[:, local_j])
                ]
            assignments = _global_assignment(costs, admissible)
            assigned_old: set[int] = set()
            assigned_new: set[int] = set()
            for local_i, local_j in assignments:
                if not admissible[local_i, local_j]:
                    continue
                margin = _ambiguity_margin(costs, admissible, local_i, local_j)
                old_index = old_indices[local_i]
                new_index = new_indices[local_j]
                metric = metrics[local_i][local_j]
                is_cluster = len(previous[old_index]["modes"]) > 1
                status = (
                    "DEGENERATE_CLUSTER"
                    if is_cluster
                    else ("CLEAR_MATCH" if margin >= AMBIGUITY_MARGIN_MINIMUM else "MULTIPLE_CANDIDATES")
                )
                if status in {"CLEAR_MATCH", "DEGENERATE_CLUSTER"}:
                    branch_id = previous[old_index]["branch_id"]
                    append(current[new_index], speed_index, branch_id, status, **metric, ambiguity_margin=margin)
                    assigned_old.add(old_index)
                    assigned_new.add(new_index)
                else:
                    ambiguous_targets[new_index] = sorted(
                        edge["source_branch_id"] for edge in candidate_edges_by_target[new_index]
                    )
                source_candidate_edges = [
                    {
                        "target_mode_indices": [mode["source_mode_index"] for mode in current[new_indices[candidate_j]]["modes"]],
                        "assignment_cost": float(costs[local_i, candidate_j]),
                        **metrics[local_i][candidate_j],
                    }
                    for candidate_j in np.flatnonzero(admissible[local_i, :])
                ]
                diagnostics.append({
                    "from_speed_index": speed_index - 1,
                    "to_speed_index": speed_index,
                    "source_branch_id": previous[old_index]["branch_id"],
                    "target_group_index": new_index,
                    "status": status,
                    "ambiguity_margin": margin,
                    "individual_association_status": "MULTIPLE_CANDIDATES" if is_cluster else status,
                    "individual_edges_committed": False if is_cluster or status != "CLEAR_MATCH" else True,
                    "source_mode_indices": [mode["source_mode_index"] for mode in previous[old_index]["modes"]],
                    "candidate_mode_indices": [mode["source_mode_index"] for mode in current[new_index]["modes"]],
                    "admissible_edges_for_target": candidate_edges_by_target[new_index],
                    "admissible_edges_for_source": source_candidate_edges,
                    **metric,
                })
            used_previous.update(assigned_old)
            used_current.update(assigned_new)

        for j, group in enumerate(current):
            if j in used_current:
                continue
            candidate_edges = candidate_edges_by_target.get(j, [])
            reason = (
                "MULTIPLE_CANDIDATES"
                if j in ambiguous_targets or candidate_edges
                else _unmatched_reason(group, previous, mass_matrix)
            )
            identifier = new_branch("cluster" if len(group["modes"]) > 1 else "branch")
            append(
                group,
                speed_index,
                identifier,
                reason,
                candidate_branch_ids=ambiguous_targets.get(
                    j, sorted(edge["source_branch_id"] for edge in candidate_edges)
                ),
            )
            diagnostics.append({
                "from_speed_index": speed_index - 1,
                "to_speed_index": speed_index,
                "target_branch_id": identifier,
                "status": reason,
                "event": "UNMATCHED_TARGET",
                "admissible_candidate_edges": candidate_edges,
            })
        previous = current

    branches = list(branch_records.values())
    branches.sort(key=lambda item: item["branch_id"])
    return branches, diagnostics


def _groups_for_result(result: Any) -> list[dict[str, Any]]:
    selected = list(result.selected_mode_indices)
    modes = []
    for index in selected:
        polarization = estimate_polarization(result, int(index))
        modes.append({
            "source_mode_index": int(index),
            "frequency_hz": float(result.frequencies_hz[index]),
            "eigenvalue": complex(result.eigenvalues[index]),
            "mode": np.asarray(result.modes[:, index], dtype=np.complex128),
            "qep_residual": float(result.qep_residuals[index]),
            "polarization": polarization,
        })
    modes.sort(key=_mode_sort_key)
    for canonical_index, mode in enumerate(modes):
        mode["canonical_mode_id"] = f"mode-{canonical_index:03d}"
    groups: list[list[dict[str, Any]]] = []
    for mode in modes:
        if not groups:
            groups.append([mode])
            continue
        previous_frequency = groups[-1][-1]["frequency_hz"]
        scale = max(abs(previous_frequency), abs(mode["frequency_hz"]), np.finfo(float).tiny)
        if abs(mode["frequency_hz"] - previous_frequency) <= CLUSTER_RELATIVE_GAP * scale:
            groups[-1].append(mode)
        else:
            groups.append([mode])
    return [
        {
            "modes": group,
            "branch_id": None,
            "group_mode_id": f"cluster-{index:03d}" if len(group) > 1 else group[0]["canonical_mode_id"],
        }
        for index, group in enumerate(groups)
    ]


def _mode_sort_key(mode: dict[str, Any]) -> tuple[Any, ...]:
    whirl_order = {"FORWARD": 0, "BACKWARD": 1, "UNDEFINED": 2, "INCONSISTENT": 3}
    polarization = mode["polarization"]
    return (
        mode["frequency_hz"],
        float(mode["eigenvalue"].real),
        whirl_order.get(polarization.relative_whirl, 4),
        0.0 if polarization.chi is None else polarization.chi,
    )


def _group_sample(group: dict[str, Any], speed_index: int, speed: float, status: str, extra: dict[str, Any]) -> dict[str, Any]:
    modes = group["modes"]
    return {
        "speed_index": speed_index,
        "spin_speed_rad_s": speed,
        "branch_id": group["branch_id"],
        "ambiguity_status": status,
        "mode_ids": [group["group_mode_id"]] if len(modes) > 1 else [modes[0]["canonical_mode_id"]],
        "source_mode_indices": [item["source_mode_index"] for item in modes],
        "frequencies_hz": [item["frequency_hz"] for item in modes],
        "eigenvalues": [
            {"real": float(item["eigenvalue"].real), "imag": float(item["eigenvalue"].imag)} for item in modes
        ],
        "qep_residuals": [item["qep_residual"] for item in modes],
        "polarization": [item["polarization"].to_dict() for item in modes],
        **extra,
    }


def _group_projection(cluster: dict[str, Any], singleton_group: dict[str, Any], mass: np.ndarray) -> float:
    if len(singleton_group["modes"]) != 1:
        return 0.0
    basis = _mass_orthonormal_basis(cluster["modes"], mass)
    vector = singleton_group["modes"][0]["mode"]
    norm = float(np.vdot(vector, mass @ vector).real)
    if not np.isfinite(norm) or norm <= np.finfo(float).tiny:
        return 0.0
    projection = basis.conj().T @ mass @ vector
    return min(1.0, max(0.0, float(np.vdot(projection, projection).real / norm)))


def _mass_orthonormal_basis(modes: list[dict[str, Any]], mass: np.ndarray) -> np.ndarray:
    vectors = np.column_stack([item["mode"] for item in modes])
    gram = vectors.conj().T @ mass @ vectors
    gram = 0.5 * (gram + gram.conj().T)
    values, vectors_eig = np.linalg.eigh(gram)
    if not np.all(np.isfinite(values)) or np.min(values) <= np.finfo(float).eps * max(float(np.max(values)), 1.0):
        raise InputValidationError("Degenerate mode cluster has a rank-deficient or non-positive mass Gram matrix.")
    return vectors @ vectors_eig @ np.diag(1.0 / np.sqrt(values)) @ vectors_eig.conj().T


def _subspace_similarity(left: dict[str, Any], right: dict[str, Any], mass: np.ndarray) -> float:
    if len(left["modes"]) != len(right["modes"]):
        return 0.0
    q_left = _mass_orthonormal_basis(left["modes"], mass)
    q_right = _mass_orthonormal_basis(right["modes"], mass)
    singular = np.linalg.svd(q_left.conj().T @ mass @ q_right, compute_uv=False)
    if singular.size == 0 or not np.all(np.isfinite(singular)):
        return 0.0
    return float(np.min(singular))


def _combined_group(groups: list[dict[str, Any]]) -> dict[str, Any]:
    """Represent individually returned modes as one candidate subspace."""

    return {"modes": [mode for group in groups for mode in group["modes"]]}


def _group_costs(
    previous: list[dict[str, Any]], current: list[dict[str, Any]], mass: np.ndarray
) -> tuple[np.ndarray, np.ndarray, list[list[dict[str, float]]]]:
    costs = np.full((len(previous), len(current)), _INVALID_COST, dtype=float)
    admissible = np.zeros_like(costs, dtype=bool)
    metrics: list[list[dict[str, float]]] = [[{} for _ in current] for _ in previous]
    for i, left in enumerate(previous):
        for j, right in enumerate(current):
            if len(left["modes"]) != len(right["modes"]):
                continue
            frequency_left = float(np.mean([mode["frequency_hz"] for mode in left["modes"]]))
            frequency_right = float(np.mean([mode["frequency_hz"] for mode in right["modes"]]))
            distance = normalized_frequency_distance(frequency_left, frequency_right)
            if len(left["modes"]) == 1:
                left_mode, right_mode = left["modes"][0], right["modes"][0]
                if (
                    left_mode["polarization"].classification == "INCONSISTENT"
                    or right_mode["polarization"].classification == "INCONSISTENT"
                ):
                    continue
                mac = complex_mac(left_mode["mode"], right_mode["mode"], mass)
                left_pol = left_mode["polarization"]
                right_pol = right_mode["polarization"]
                pol_distance = None
                if left_pol.defined and right_pol.defined and left_pol.chi is not None and right_pol.chi is not None:
                    pol_distance = abs(left_pol.chi - right_pol.chi) / 2.0
                if mac < MAC_MINIMUM or distance > FREQUENCY_DISTANCE_MAXIMUM:
                    continue
                weights = [(0.65, 1.0 - mac), (0.25, min(distance, 1.0))]
                if pol_distance is not None:
                    weights.append((0.10, pol_distance))
                weight_sum = sum(weight for weight, _ in weights)
                costs[i, j] = sum(weight * value for weight, value in weights) / weight_sum
                admissible[i, j] = True
                metrics[i][j] = {"complex_mac": mac, "normalized_frequency_distance": distance}
                if pol_distance is not None:
                    metrics[i][j]["polarization_distance"] = pol_distance
            else:
                similarity = _subspace_similarity(left, right, mass)
                if similarity < SUBSPACE_MINIMUM_SINGULAR_VALUE or distance > FREQUENCY_DISTANCE_MAXIMUM:
                    continue
                costs[i, j] = 0.75 * (1.0 - similarity) + 0.25 * min(distance, 1.0)
                admissible[i, j] = True
                metrics[i][j] = {
                    "subspace_minimum_singular_value": similarity,
                    "normalized_frequency_distance": distance,
                }
    return costs, admissible, metrics


def _global_assignment(costs: np.ndarray, admissible: np.ndarray) -> list[tuple[int, int]]:
    rows, columns = costs.shape
    if rows == 0 or columns == 0:
        return []
    size = rows + columns
    augmented = np.full((size, size), _INVALID_COST, dtype=float)
    augmented[:rows, :columns] = np.where(admissible, costs, _INVALID_COST)
    for i in range(rows):
        augmented[i, columns + i] = _UNMATCHED_COST
    for j in range(columns):
        augmented[rows + j, j] = _UNMATCHED_COST
    augmented[rows:, columns:] = 0.0
    assigned_rows, assigned_columns = linear_sum_assignment(augmented)
    return [
        (int(i), int(j))
        for i, j in zip(assigned_rows, assigned_columns)
        if i < rows and j < columns and augmented[i, j] < _INVALID_COST
    ]


def _ambiguity_margin(costs: np.ndarray, valid: np.ndarray, assigned_i: int, assigned_j: int) -> float:
    assigned_cost = float(costs[assigned_i, assigned_j])
    margins = []
    row_alternatives = [
        float(costs[assigned_i, j]) for j in range(costs.shape[1]) if j != assigned_j and valid[assigned_i, j]
    ]
    column_alternatives = [
        float(costs[i, assigned_j]) for i in range(costs.shape[0]) if i != assigned_i and valid[i, assigned_j]
    ]
    for alternatives in (row_alternatives, column_alternatives):
        if alternatives:
            margins.append(min(alternatives) - assigned_cost)
    return float(min(margins)) if margins else 1.0


def _split_child_labels(groups: list[dict[str, Any]]) -> list[str]:
    ordered = sorted(groups, key=lambda group: _mode_sort_key(group["modes"][0]))
    whirl = [group["modes"][0]["polarization"].relative_whirl for group in ordered]
    if len(ordered) == 2 and set(whirl) == {"FORWARD", "BACKWARD"}:
        by_whirl = {group["modes"][0]["polarization"].relative_whirl: group for group in ordered}
        return ["F", "B"] if by_whirl["FORWARD"] is ordered[0] else ["B", "F"]
    return [f"child-{index + 1:03d}" for index in range(len(ordered))]


def _unmatched_reason(
    group: dict[str, Any], previous: list[dict[str, Any]], mass: np.ndarray
) -> str:
    if len(group["modes"]) > 1:
        return "DEGENERATE_CLUSTER"
    mode = group["modes"][0]
    saw_low_mac = False
    saw_frequency_jump = False
    saw_polarization_conflict = False
    for old in previous:
        if len(old["modes"]) != 1:
            continue
        old_mode = old["modes"][0]
        saw_polarization_conflict |= (
            old_mode["polarization"].classification == "INCONSISTENT"
            or mode["polarization"].classification == "INCONSISTENT"
        )
        mac = complex_mac(old_mode["mode"], mode["mode"], mass)
        distance = normalized_frequency_distance(old_mode["frequency_hz"], mode["frequency_hz"])
        saw_low_mac |= distance <= FREQUENCY_DISTANCE_MAXIMUM and mac < MAC_MINIMUM
        saw_frequency_jump |= mac >= MAC_MINIMUM and distance > FREQUENCY_DISTANCE_MAXIMUM
    if saw_low_mac:
        return "LOW_MAC"
    if saw_frequency_jump:
        return "FREQUENCY_JUMP"
    if saw_polarization_conflict:
        return "POLARIZATION_CONFLICT"
    return "UNTRACKED"
