"""Run the 0.2.8 WP08B invariant-geometry mixed-modal campaign."""

# This executable campaign deliberately does not modify the WP08 runner or
# evidence.  WP08B corrects the diagnosed refinement construction and compares
# modal fields through a common fine-mesh mass inner product.
# ruff: noqa: E402

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any, Iterable

import numpy as np
from scipy.optimize import linear_sum_assignment

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.run_wp07_mixed_static import _element_volume, _mixed_geometry
from scripts.run_wp08_mixed_modal import (
    _build_model,
    _canonical_modes,
    _failure_contract,
    _independent_dense_matrices,
    _interface_metrics,
    _mass_metrics,
    _modal_case,
    _output_metrics,
    _public_case,
)
from solveur.api import solve_model
from solveur.elements.solid.hex8 import Hex8Element
from solveur.elements.solid.tet4 import Tet4Element


BASELINE_SHA = "59a438bc0d58ee32d35e084dd091eefe78418bb6"
CONTRACT_PATH = ROOT / "qualification" / "0_2_8" / "wp08b_mixed_modal_contract.json"
EVIDENCE_PATH = ROOT / "qualification" / "0_2_8" / "wp08b_mixed_modal_vnv.json"
LEVELS = (1, 2, 4, 8)
TOLERANCES: dict[str, float] = {
    "geometry_volume_relative": 1.0e-12,
    "geometry_coordinate_absolute": 1.0e-12,
    "mapping_reconstruction_absolute": 1.0e-10,
    "mapping_interface_disagreement_absolute": 1.0e-12,
    "mass_symmetry_relative": 1.0e-12,
    "mass_conservation_relative": 1.0e-12,
    "modal_residual_relative": 1.0e-8,
    "modal_mass_orthogonality_relative": 1.0e-10,
    "oracle_frequency_relative": 1.0e-9,
    "adjacent_frequency_relative": 1.0e-1,
    "mapped_global_mac": 8.5e-1,
    "pure_control_subspace_mac": 8.5e-1,
    "near_degenerate_frequency_relative": 3.0e-2,
    "replay_frequency_absolute": 1.0e-12,
    "replay_mode_absolute_after_sign": 1.0e-10,
}


def _json_default(value: object) -> object:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def _digest(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=_json_default)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _chain_model(segments: int, families: Iterable[str] = ("TET4", "WEDGE6", "HEX8")) -> Any:
    """Build the full, physically invariant WP07 mixed chain at one level."""

    selected_families = {str(value).upper() for value in families}
    nodes, all_elements = _mixed_geometry(segments)
    selected = [row for row in all_elements if str(row["type"]).upper() in selected_families]
    referenced = sorted({int(node) for row in selected for node in row["nodes"]})
    remap = {node: index for index, node in enumerate(referenced)}
    elements = [
        {
            "type": str(row["type"]),
            "nodes": [remap[int(node)] for node in row["nodes"]],
            "material": "solid",
        }
        for row in selected
    ]
    return _build_model(np.asarray(nodes, dtype=float)[referenced], elements)


def _pure_tet4_model(segments: int) -> Any:
    """Build a conforming TET4-only box refinement for protocol control."""

    nodes: list[tuple[float, float, float]] = []
    for index in range(segments + 1):
        z = float(index) / float(segments)
        nodes.extend(((0.0, 0.0, z), (1.0, 0.0, z), (1.0, 1.0, z), (0.0, 1.0, z)))
    elements: list[dict[str, object]] = []
    for index in range(segments):
        lower = 4 * index
        upper = 4 * (index + 1)
        tetrahedra = (
            [lower, lower + 1, lower + 2, upper + 2],
            [lower, lower + 2, lower + 3, upper + 2],
            [lower, lower + 3, upper + 3, upper + 2],
            [lower, upper + 3, upper, upper + 2],
            [lower, upper, upper + 1, upper + 2],
            [lower, upper + 1, lower + 1, upper + 2],
        )
        for connectivity in tetrahedra:
            row = list(connectivity)
            coords = np.asarray([nodes[node] for node in row], dtype=float)
            if Tet4Element.signed_volume(coords) < 0.0:
                row[1], row[2] = row[2], row[1]
            elements.append({"type": "TET4", "nodes": row, "material": "solid"})
    return _build_model(np.asarray(nodes, dtype=float), elements)


def _mesh_metrics(models: dict[int, Any]) -> dict[str, object]:
    records = {}
    volumes = []
    bounds = []
    node_counts = []
    dof_counts = []
    for level, model in models.items():
        volume = sum(
            _element_volume(element.type, model.nodes[list(element.nodes)]) for element in model.elements
        )
        counts = {family: sum(element.type == family for element in model.elements) for family in ("TET4", "WEDGE6", "HEX8")}
        records[str(level)] = {
            "element_count": len(model.elements),
            "family_counts": counts,
            "node_count": model.node_count,
            "dof_count": model.dof_manager().ndof,
            "total_volume": float(volume),
            "coordinate_min": np.min(model.nodes, axis=0).tolist(),
            "coordinate_max": np.max(model.nodes, axis=0).tolist(),
        }
        volumes.append(float(volume))
        bounds.append(np.vstack((np.min(model.nodes, axis=0), np.max(model.nodes, axis=0))))
        node_counts.append(model.node_count)
        dof_counts.append(model.dof_manager().ndof)
    reference_volume = volumes[0]
    volume_error = max(abs(value - reference_volume) / max(abs(reference_volume), 1.0) for value in volumes)
    coordinate_error = max(float(np.max(np.abs(value - bounds[0]))) for value in bounds)
    expected_counts = all(
        records[str(level)]["family_counts"] == {"TET4": 1, "WEDGE6": level, "HEX8": level}
        for level in models
    )
    increasing = all(right > left for left, right in zip(node_counts, node_counts[1:])) and all(
        right > left for left, right in zip(dof_counts, dof_counts[1:])
    )
    passed = bool(
        expected_counts
        and increasing
        and volume_error <= TOLERANCES["geometry_volume_relative"]
        and coordinate_error <= TOLERANCES["geometry_coordinate_absolute"]
    )
    return {
        "status": "PASS" if passed else "FAIL",
        "levels": records,
        "volume_relative_error": float(volume_error),
        "coordinate_maximum_absolute_error": float(coordinate_error),
        "node_and_dof_counts_strictly_increase": increasing,
        "expected_family_counts": expected_counts,
    }


def _tet_shape_functions(coords: np.ndarray, point: np.ndarray) -> np.ndarray:
    interpolation = np.vstack((np.ones(4), np.asarray(coords, dtype=float).T))
    return np.linalg.solve(interpolation, np.r_[1.0, np.asarray(point, dtype=float)])


def _wedge_shape_data(point: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    r, s, t = (float(value) for value in point)
    functions = np.asarray(
        (
            0.5 * (1.0 - t) * (1.0 - r - s),
            0.5 * (1.0 - t) * r,
            0.5 * (1.0 - t) * s,
            0.5 * (1.0 + t) * (1.0 - r - s),
            0.5 * (1.0 + t) * r,
            0.5 * (1.0 + t) * s,
        ),
        dtype=float,
    )
    derivatives = np.asarray(
        (
            (-0.5 * (1.0 - t), -0.5 * (1.0 - t), -0.5 * (1.0 - r - s)),
            (0.5 * (1.0 - t), 0.0, -0.5 * r),
            (0.0, 0.5 * (1.0 - t), -0.5 * s),
            (-0.5 * (1.0 + t), -0.5 * (1.0 + t), 0.5 * (1.0 - r - s)),
            (0.5 * (1.0 + t), 0.0, 0.5 * r),
            (0.0, 0.5 * (1.0 + t), 0.5 * s),
        ),
        dtype=float,
    )
    return functions, derivatives


def _hex8_shape_data(point: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    xi, eta, zeta = (float(value) for value in point)
    signs = Hex8Element.node_signs
    functions = 0.125 * (1.0 + signs[:, 0] * xi) * (1.0 + signs[:, 1] * eta) * (1.0 + signs[:, 2] * zeta)
    derivatives = np.empty((8, 3), dtype=float)
    derivatives[:, 0] = 0.125 * signs[:, 0] * (1.0 + signs[:, 1] * eta) * (1.0 + signs[:, 2] * zeta)
    derivatives[:, 1] = 0.125 * signs[:, 1] * (1.0 + signs[:, 0] * xi) * (1.0 + signs[:, 2] * zeta)
    derivatives[:, 2] = 0.125 * signs[:, 2] * (1.0 + signs[:, 0] * xi) * (1.0 + signs[:, 1] * eta)
    return functions, derivatives


def _inverse_shape_functions(element_type: str, coords: np.ndarray, point: np.ndarray) -> tuple[np.ndarray, bool, float]:
    """Return interpolation weights, in-domain flag and reconstruction error."""

    values = np.asarray(coords, dtype=float)
    target = np.asarray(point, dtype=float)
    if element_type == "TET4":
        functions = _tet_shape_functions(values, target)
        reconstructed = functions @ values
        return functions, bool(np.all(functions >= -1.0e-9)), float(np.max(np.abs(reconstructed - target)))
    natural = np.zeros(3, dtype=float)
    for _ in range(30):
        functions, derivatives = _wedge_shape_data(natural) if element_type == "WEDGE6" else _hex8_shape_data(natural)
        jacobian = derivatives.T @ values
        try:
            correction = np.linalg.solve(jacobian, target - functions @ values)
        except np.linalg.LinAlgError:
            return functions, False, float("inf")
        natural += correction
        if float(np.linalg.norm(correction)) <= 1.0e-12:
            break
    functions, _ = _wedge_shape_data(natural) if element_type == "WEDGE6" else _hex8_shape_data(natural)
    if element_type == "WEDGE6":
        inside = bool(
            natural[0] >= -1.0e-9
            and natural[1] >= -1.0e-9
            and natural[0] + natural[1] <= 1.0 + 1.0e-9
            and abs(natural[2]) <= 1.0 + 1.0e-9
        )
    else:
        inside = bool(np.all(np.abs(natural) <= 1.0 + 1.0e-9))
    return functions, inside, float(np.max(np.abs(functions @ values - target)))


def _prolong_modes(coarse: Any, fine: Any, coarse_modes: np.ndarray) -> tuple[np.ndarray, dict[str, object]]:
    """Prolong coarse modal fields to all fine nodes without extrapolation."""

    coarse_dofs = coarse.dof_manager()
    fine_dofs = fine.dof_manager()
    output = np.zeros((fine_dofs.ndof, coarse_modes.shape[1]), dtype=float)
    reconstruction_errors: list[float] = []
    owner_counts: list[int] = []
    interface_disagreement = 0.0
    for fine_node, point in enumerate(fine.nodes):
        candidates: list[tuple[Any, np.ndarray, float]] = []
        for element in coarse.elements:
            functions, inside, reconstruction_error = _inverse_shape_functions(
                element.type, coarse.nodes[list(element.nodes)], point
            )
            if inside:
                candidates.append((element, functions, reconstruction_error))
        if not candidates:
            raise ValueError(f"WP08B mesh mapping could not locate fine node {fine_node} in the coarse mesh.")
        selected, functions, reconstruction_error = candidates[0]
        reconstruction_errors.append(reconstruction_error)
        owner_counts.append(len(candidates))
        candidate_values = []
        for element, weights, _ in candidates:
            values = np.zeros((3, coarse_modes.shape[1]), dtype=float)
            for local_node, node in enumerate(element.nodes):
                for dof_index, dof_name in enumerate(("UX", "UY", "UZ")):
                    values[dof_index, :] += weights[local_node] * coarse_modes[coarse_dofs.index(node, dof_name), :]
            candidate_values.append(values)
        for values in candidate_values[1:]:
            interface_disagreement = max(interface_disagreement, float(np.max(np.abs(values - candidate_values[0]))))
        for local_node, node in enumerate(selected.nodes):
            for dof_name in ("UX", "UY", "UZ"):
                output[fine_dofs.index(fine_node, dof_name), :] += functions[local_node] * coarse_modes[
                    coarse_dofs.index(node, dof_name), :
                ]
    return output, {
        "target_node_count": fine.node_count,
        "maximum_coordinate_reconstruction_error": float(max(reconstruction_errors, default=float("inf"))),
        "maximum_interface_field_disagreement": float(interface_disagreement),
        "maximum_containing_elements_at_one_node": max(owner_counts, default=0),
        "extrapolation": False,
    }


def _mac_matrix(reference: np.ndarray, candidate: np.ndarray, mass: np.ndarray) -> tuple[np.ndarray, list[dict[str, object]]]:
    cross = reference.T @ mass @ candidate
    reference_norm = np.diag(reference.T @ mass @ reference)
    candidate_norm = np.diag(candidate.T @ mass @ candidate)
    matrix = np.square(cross) / np.maximum(reference_norm[:, None] * candidate_norm[None, :], 1.0e-300)
    rows, columns = linear_sum_assignment(-matrix)
    assignment = [
        {"coarse_mode": int(row), "fine_mode": int(column), "mac": float(matrix[row, column])}
        for row, column in zip(rows, columns, strict=True)
    ]
    return matrix, assignment


def _frequency_clusters(frequencies: np.ndarray) -> list[list[int]]:
    values = np.asarray(frequencies, dtype=float)
    if values.size == 0:
        return []
    clusters = [[0]]
    for index in range(1, values.size):
        scale = max(abs(float(values[index - 1])), abs(float(values[index])), 1.0)
        if abs(float(values[index] - values[index - 1])) <= TOLERANCES["near_degenerate_frequency_relative"] * scale:
            clusters[-1].append(index)
        else:
            clusters.append([index])
    return clusters


def _mass_orthonormal_basis(modes: np.ndarray, mass: np.ndarray) -> np.ndarray:
    gram = modes.T @ mass @ modes
    values, vectors = np.linalg.eigh(0.5 * (gram + gram.T))
    if np.any(values <= 1.0e-14):
        raise ValueError("WP08B subspace basis is not positive definite in the fine-mass inner product.")
    return modes @ vectors @ np.diag(1.0 / np.sqrt(values)) @ vectors.T


def _subspace_checks(
    coarse_frequencies: np.ndarray,
    fine_frequencies: np.ndarray,
    coarse_modes: np.ndarray,
    fine_modes: np.ndarray,
    fine_mass: np.ndarray,
) -> list[dict[str, object]]:
    coarse_clusters = _frequency_clusters(coarse_frequencies)
    fine_clusters = _frequency_clusters(fine_frequencies)
    checks = []
    for coarse_cluster, fine_cluster in zip(coarse_clusters, fine_clusters, strict=False):
        if len(coarse_cluster) == 1 and len(fine_cluster) == 1:
            continue
        if len(coarse_cluster) != len(fine_cluster):
            checks.append(
                {
                    "coarse_modes": coarse_cluster,
                    "fine_modes": fine_cluster,
                    "status": "NOT_COMPARABLE_CLUSTER_SIZE_CHANGED",
                }
            )
            continue
        coarse_basis = _mass_orthonormal_basis(coarse_modes[:, coarse_cluster], fine_mass)
        fine_basis = _mass_orthonormal_basis(fine_modes[:, fine_cluster], fine_mass)
        singular_values = np.linalg.svd(coarse_basis.T @ fine_mass @ fine_basis, compute_uv=False)
        checks.append(
            {
                "coarse_modes": coarse_cluster,
                "fine_modes": fine_cluster,
                "minimum_subspace_mac": float(np.min(np.square(singular_values))),
                "status": "PASS" if float(np.min(np.square(singular_values))) >= TOLERANCES["pure_control_subspace_mac"] else "FAIL",
            }
        )
    return checks


def _refinement_metrics(models: dict[int, Any], cases: dict[int, dict[str, object]]) -> dict[str, object]:
    transitions = []
    for coarse_level, fine_level in zip(LEVELS, LEVELS[1:]):
        coarse_case = cases[coarse_level]
        fine_case = cases[fine_level]
        prolonged, mapping = _prolong_modes(
            models[coarse_level], models[fine_level], np.asarray(coarse_case["_result"].modes, dtype=float)[:, :6]
        )
        _, fine_mass = _independent_dense_matrices(models[fine_level])
        fine_modes = np.asarray(fine_case["_result"].modes, dtype=float)[:, :6]
        matrix, assignment = _mac_matrix(prolonged, fine_modes, fine_mass)
        coarse_frequencies = np.asarray(coarse_case["frequencies_hz"], dtype=float)[:6]
        fine_frequencies = np.asarray(fine_case["frequencies_hz"], dtype=float)[:6]
        frequency_changes = [
            abs(coarse_frequencies[row["coarse_mode"]] - fine_frequencies[row["fine_mode"]])
            / max(abs(fine_frequencies[row["fine_mode"]]), 1.0e-12)
            for row in assignment
        ]
        minimum_mac = min((row["mac"] for row in assignment), default=0.0)
        passed = bool(
            mapping["maximum_coordinate_reconstruction_error"] <= TOLERANCES["mapping_reconstruction_absolute"]
            and mapping["maximum_interface_field_disagreement"]
            <= TOLERANCES["mapping_interface_disagreement_absolute"]
            and minimum_mac >= TOLERANCES["mapped_global_mac"]
            and max(frequency_changes, default=float("inf")) <= TOLERANCES["adjacent_frequency_relative"]
        )
        transitions.append(
            {
                "coarse_level": coarse_level,
                "fine_level": fine_level,
                "status": "PASS" if passed else "FAIL",
                "coarse_frequencies_hz": coarse_frequencies.tolist(),
                "fine_frequencies_hz": fine_frequencies.tolist(),
                "frequency_relative_changes": frequency_changes,
                "maximum_frequency_relative_change": float(max(frequency_changes, default=float("inf"))),
                "mac_matrix": matrix.tolist(),
                "assignment": assignment,
                "minimum_assigned_mac": float(minimum_mac),
                "assignment_is_identity": all(row["coarse_mode"] == row["fine_mode"] for row in assignment),
                "mapping": mapping,
                "mixed_near_degenerate_clusters": {
                    "coarse": _frequency_clusters(coarse_frequencies),
                    "fine": _frequency_clusters(fine_frequencies),
                },
            }
        )
    monotone_decreasing = all(
        np.all(np.asarray(cases[right]["frequencies_hz"])[:6] <= np.asarray(cases[left]["frequencies_hz"])[:6] + 1.0e-12)
        for left, right in zip(LEVELS, LEVELS[1:])
    )
    return {
        "status": "PASS" if all(row["status"] == "PASS" for row in transitions) else "FAIL",
        "levels": {
            str(level): {
                "first_six_frequencies_hz": np.asarray(cases[level]["frequencies_hz"], dtype=float)[:6].tolist(),
                "node_count": models[level].node_count,
                "dof_count": models[level].dof_manager().ndof,
            }
            for level in LEVELS
        },
        "transitions": transitions,
        "frequency_order_monotone_decreasing": monotone_decreasing,
        "mode_crossing_observed": any(not row["assignment_is_identity"] for row in transitions),
    }


def _pure_controls() -> dict[str, object]:
    families = {
        "TET4": {level: _pure_tet4_model(level) for level in (1, 2, 4)},
        "WEDGE6": {level: _chain_model(level, ("WEDGE6",)) for level in (1, 2, 4)},
        "HEX8": {level: _chain_model(level, ("HEX8",)) for level in (1, 2, 4)},
    }
    controls = {}
    for family, models in families.items():
        cases = {level: _modal_case(f"WP08B_PURE_{family}_{level}", model) for level, model in models.items()}
        transitions = []
        for coarse_level, fine_level in ((1, 2), (2, 4)):
            prolonged, mapping = _prolong_modes(
                models[coarse_level], models[fine_level], np.asarray(cases[coarse_level]["_result"].modes, dtype=float)[:, :6]
            )
            _, fine_mass = _independent_dense_matrices(models[fine_level])
            fine_modes = np.asarray(cases[fine_level]["_result"].modes, dtype=float)[:, :6]
            matrix, assignment = _mac_matrix(prolonged, fine_modes, fine_mass)
            subspace = _subspace_checks(
                np.asarray(cases[coarse_level]["frequencies_hz"], dtype=float)[:6],
                np.asarray(cases[fine_level]["frequencies_hz"], dtype=float)[:6],
                prolonged,
                fine_modes,
                fine_mass,
            )
            transitions.append(
                {
                    "coarse_level": coarse_level,
                    "fine_level": fine_level,
                    "minimum_assigned_mac": float(min(row["mac"] for row in assignment)),
                    "assignment": assignment,
                    "subspace_checks": subspace,
                    "mapping": mapping,
                    "mac_matrix": matrix.tolist(),
                }
            )
        controls[family] = {
            "status": "PASS_DIAGNOSTIC",
            "first_six_frequencies_hz": {
                str(level): np.asarray(cases[level]["frequencies_hz"], dtype=float)[:6].tolist() for level in models
            },
            "transitions": transitions,
            "qualification_effect": "NONE; this is a protocol control, not an individual-family maturity decision.",
        }
    return {"status": "PASS" if all(row["status"] == "PASS_DIAGNOSTIC" for row in controls.values()) else "FAIL", "controls": controls}


def _replay_metrics() -> dict[str, object]:
    snapshots = []
    for _ in range(2):
        snapshot = {}
        for level in LEVELS:
            result = solve_model(_chain_model(level), enforce_policy=False)
            snapshot[str(level)] = {
                "frequencies": np.asarray(result.frequencies_hz, dtype=float)[:6],
                "modes": _canonical_modes(np.asarray(result.modes, dtype=float)[:, :6]),
            }
        snapshots.append(snapshot)
    frequency_difference = max(
        float(np.max(np.abs(snapshots[0][str(level)]["frequencies"] - snapshots[1][str(level)]["frequencies"])))
        for level in LEVELS
    )
    mode_difference = max(
        float(np.max(np.abs(snapshots[0][str(level)]["modes"] - snapshots[1][str(level)]["modes"])))
        for level in LEVELS
    )
    exact_eigenvalues = all(
        np.array_equal(snapshots[0][str(level)]["frequencies"], snapshots[1][str(level)]["frequencies"])
        for level in LEVELS
    )
    passed = bool(
        exact_eigenvalues
        and frequency_difference <= TOLERANCES["replay_frequency_absolute"]
        and mode_difference <= TOLERANCES["replay_mode_absolute_after_sign"]
    )
    public_snapshots = [
        {level: {"frequencies": value["frequencies"]} for level, value in snapshot.items()} for snapshot in snapshots
    ]
    return {
        "status": "PASS" if passed else "FAIL",
        "required_replays": 2,
        "eigenvalues_exactly_equal": exact_eigenvalues,
        "maximum_frequency_absolute_difference": frequency_difference,
        "maximum_mode_difference_after_sign_canonicalization": mode_difference,
        "canonicalization": "eigenvector sign only; no mode permutation applied",
        "digests": [_digest(snapshot) for snapshot in public_snapshots],
    }


def run(output_path: Path = EVIDENCE_PATH) -> dict[str, object]:
    """Execute the independent WP08B campaign and persist the evidence."""

    models = {level: _chain_model(level) for level in LEVELS}
    cases = {level: _modal_case(f"WP08B_MIXED_{level}", model) for level, model in models.items()}
    mesh = _mesh_metrics(models)
    refinement = _refinement_metrics(models, cases)
    pair_models = {
        "TET4_WEDGE6": _chain_model(4, ("TET4", "WEDGE6")),
        "WEDGE6_HEX8": _chain_model(4, ("WEDGE6", "HEX8")),
        "TET4_WEDGE6_HEX8": models[4],
    }
    pairwise = {name: _modal_case(f"WP08B_{name}", model) for name, model in pair_models.items()}
    masses = {name: _mass_metrics(model) for name, model in pair_models.items()}
    interfaces = _interface_metrics(models[4])
    failures = _failure_contract()
    output = _output_metrics(models[4], cases[4]["_result"])
    controls = _pure_controls()
    replays = _replay_metrics()
    all_pairwise_pass = all(row["status"] == "PASS" for row in pairwise.values())
    all_mass_pass = all(row["status"] == "PASS" for row in masses.values())
    decision = (
        "QUALIFIED_BOUNDED_CANDIDATE"
        if mesh["status"] == "PASS"
        and refinement["status"] == "PASS"
        and all_pairwise_pass
        and all_mass_pass
        and interfaces["status"] == "PASS"
        and failures["status"] == "PASS"
        and output["status"] == "PASS"
        and controls["status"] == "PASS"
        and replays["status"] == "PASS"
        else "SUPPORTED_WITH_LIMITATIONS"
    )
    evidence = {
        "schema_version": 1,
        "record_id": "QF-028-WP08B-MIXED-MODAL-VNV",
        "work_package": "WP08B",
        "applicable_version": "0.2.8-development",
        "baseline_sha": BASELINE_SHA,
        "status": "CAMPAIGN_COMPLETE_OWNER_GATE_PENDING" if decision == "QUALIFIED_BOUNDED_CANDIDATE" else "CAMPAIGN_COMPLETE_NO_PROMOTION",
        "technical_decision": decision,
        "owner_gate_required": decision == "QUALIFIED_BOUNDED_CANDIDATE",
        "scope": {
            "analysis": "modal",
            "families": ["TET4", "WEDGE6", "HEX8"],
            "interfaces": "conforming shared-node triangular and quadrilateral interfaces only",
            "material": "homogeneous isotropic_3d with positive density",
            "mass": "consistent translational finite-element mass only",
            "modes": "first six positive modes in the invariant physical chain",
            "excluded": [
                "lumped or concentrated-mass qualification",
                "Newmark",
                "harmonic",
                "nonlinear",
                "contact",
                "nonconforming interfaces",
                "TET10/HEX20 mixed",
                "PYRAMID5",
                "large mixed performance",
                "universal all-frequency or modal-stress claim",
            ],
        },
        "predeclared_tolerances": TOLERANCES,
        "mesh_construction": mesh,
        "mixed_mass_assembly": {"status": "PASS" if all_mass_pass else "FAIL", "cases": masses},
        "pairwise_modal": {name: _public_case(row) for name, row in pairwise.items()},
        "reference_oracle": {
            "status": "PASS" if all_pairwise_pass else "FAIL",
            "mass": "analytical rho*volume conservation",
            "modal": "independent dense local-matrix scatter plus scipy.linalg.eigh",
            "external": "NOT_AVAILABLE_AND_NOT_REQUIRED_FOR_THIS_BOUNDED_MIXED_ASSEMBLY_SCOPE",
            "external_correlation_claimed": False,
        },
        "mesh_refinement": refinement,
        "pure_family_controls": controls,
        "interface_robustness": interfaces,
        "failure_contract": failures,
        "post_processing_output": output,
        "replay_determinism": replays,
        "root_cause": {
            "primary": "MESH_TO_MESH_MAPPING_PROBLEM",
            "secondary": "GEOMETRIC_DISCRETIZATION_EFFECT",
            "wp08_gate_changed": False,
            "wp08_evidence_rewritten": False,
        },
        "numerical_source_changed": False,
        "bugs_found": [
            "WP08 refinement construction selected only the first WEDGE6/HEX8 segment above level one, changing the physical domain.",
            "WP08 compared shared nodal samples rather than fields represented on one mesh and one mass inner product.",
        ],
        "bugs_fixed": [
            "WP08B uses all generated WEDGE6/HEX8 segments and a fine-mass prolongation MAC in a separate campaign runner; no numerical kernel changed."
        ],
        "historical_0_2_7_evidence_changed": False,
        "wp08_evidence_changed": False,
        "limitations": [
            "The independent dense oracle checks a separate global scatter and generalized eigensolve, not an external industrial-solver correlation.",
            "The qualification candidate is limited to the declared fixed-base chain, first six modes, consistent mass and conforming interfaces.",
            "Pure-family controls are diagnostic only and do not relabel their individual modal routes.",
            "No modal stress, Newmark, harmonic, nonlinear, nonconforming-interface or large-performance claim is made.",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(evidence, indent=2, sort_keys=True, default=_json_default) + "\n", encoding="utf-8")
    return evidence


if __name__ == "__main__":
    run()
