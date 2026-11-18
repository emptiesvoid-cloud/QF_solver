"""Post-process J24B TET10 curvature warnings without running FEM.

The script binds its input meshes and archived observables to the frozen
J24B contract, checks the raw archive manifest, and rebuilds warning
locations and local error summaries from the archived H1-H4 campaign.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from solveur.elements.solid.tet10 import Tet10Element  # noqa: E402
from solveur.mesh.gmsh_importer import GmshModelImporter  # noqa: E402
from solveur.mesh.quality import MeshQuality, MeshQualityThresholds  # noqa: E402

CONTRACT_PATH = ROOT / "research/j24b/tet10_torsion/contract-002-h1-digest-corrected.json"
PROVENANCE_PATH = ROOT / "research/j24b/results/diagnostic-2026-11-17/provenance.json"
ARCHIVE_PATH = ROOT / "research/j24b/results/diagnostic-2026-11-17/raw_results.zip"
OUTPUT_DIR = ROOT / "research/j24c/results/diagnostic-2026-11-18"
LEVELS = ("h1", "h2", "h3", "h4")
TET10_FACES = ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3))
WARNING_RE = re.compile(
    r"Element (\d+): curved or misplaced TET10 midside node; maximum relative edge deviation "
    r"([0-9]+(?:\.[0-9]*)?(?:[eE][+-]?\d+)?)\."
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify_archive(archive: zipfile.ZipFile, expected_sha: str) -> dict[str, Any]:
    archive_bytes = ARCHIVE_PATH.read_bytes()
    actual_archive_sha = _sha256(archive_bytes)
    if actual_archive_sha != expected_sha:
        raise ValueError(f"raw archive SHA mismatch: expected {expected_sha}, got {actual_archive_sha}")
    manifest = json.loads(archive.read("archive_manifest.json").decode("utf-8"))
    expected_members = manifest["files_sha256"]
    actual_members = {name for name in archive.namelist() if name != "archive_manifest.json"}
    if actual_members != set(expected_members):
        raise ValueError("raw archive member set differs from archive_manifest.json")
    mismatches = [name for name, digest in expected_members.items() if _sha256(archive.read(name)) != digest]
    if mismatches:
        raise ValueError(f"raw archive member SHA mismatch: {mismatches[:5]}")
    return {"sha256": actual_archive_sha, "bytes": len(archive_bytes), "verified_member_count": len(actual_members)}


def _boundary_edge_keys(elements: list[Any]) -> set[tuple[int, int]]:
    face_counts: Counter[tuple[int, int, int]] = Counter()
    faces_by_key: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    for element in elements:
        corners = element.nodes[:4]
        for face in TET10_FACES:
            oriented = tuple(int(corners[i]) for i in face)
            key = tuple(sorted(oriented))
            face_counts[key] += 1
            faces_by_key[key] = oriented
    boundary_edges: set[tuple[int, int]] = set()
    for key, count in face_counts.items():
        if count != 1:
            continue
        face = faces_by_key[key]
        boundary_edges.update(tuple(sorted(edge)) for edge in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])))
    return boundary_edges


def _edge_geometry(
    level: str,
    element_index: int,
    element: Any,
    local_edge_index: int,
    edge_nodes: tuple[int, int, int],
    coordinates: np.ndarray,
    boundary_edges: set[tuple[int, int]],
    radius: float,
    length: float,
) -> dict[str, Any]:
    first, second, middle = edge_nodes
    node_ids = element.nodes
    points = coordinates[[node_ids[first], node_ids[second], node_ids[middle]]]
    p0, p1, pm = points
    chord_length = float(np.linalg.norm(p1 - p0))
    deviation = float(np.linalg.norm(pm - 0.5 * (p0 + p1)))
    ratio = deviation / chord_length if chord_length > 0.0 else math.inf
    radial = np.hypot(points[:, 1], points[:, 2])
    tolerance = 1.0e-8 * max(radius, 1.0)
    on_cylinder = bool(np.max(np.abs(radial - radius)) <= tolerance)
    x_values = points[:, 0]
    root_end = bool(np.max(np.abs(x_values)) <= 1.0e-8 * max(length, 1.0))
    tip_end = bool(np.max(np.abs(x_values - length)) <= 1.0e-8 * max(length, 1.0))
    edge_key = tuple(sorted((int(node_ids[first]), int(node_ids[second]))))
    is_boundary = edge_key in boundary_edges
    if is_boundary and on_cylinder and root_end:
        location = "cylindrical_rim_x0"
    elif is_boundary and on_cylinder and tip_end:
        location = "cylindrical_rim_xL"
    elif is_boundary and on_cylinder:
        location = "lateral_cylinder"
    elif is_boundary and root_end:
        location = "planar_end_face_x0"
    elif is_boundary and tip_end:
        location = "planar_end_face_xL"
    elif is_boundary:
        location = "other_boundary"
    else:
        location = "interior"

    ideal_curve_error = None
    radial_mid_error = None
    if on_cylinder:
        theta0 = math.atan2(float(p0[2]), float(p0[1]))
        theta1 = math.atan2(float(p1[2]), float(p1[1]))
        delta = (theta1 - theta0 + math.pi) % (2.0 * math.pi) - math.pi
        theta_half = theta0 + 0.5 * delta
        ideal_mid = np.asarray([0.5 * (p0[0] + p1[0]), radius * math.cos(theta_half), radius * math.sin(theta_half)])
        ideal_curve_error = float(np.linalg.norm(pm - ideal_mid))
        radial_mid_error = abs(float(radial[2]) - radius)

    return {
        "level": level,
        "element_index": element_index,
        "local_edge_index": local_edge_index,
        "endpoint_node_indices": list(edge_key),
        "midside_node_index": int(node_ids[middle]),
        "location": location,
        "is_boundary_edge": is_boundary,
        "on_analytical_cylinder": on_cylinder,
        "x_mid_m": float(pm[0]),
        "theta_mid_deg": float(math.degrees(math.atan2(float(pm[2]), float(pm[1]))) % 360.0),
        "radial_mid_m": float(math.hypot(float(pm[1]), float(pm[2]))),
        "radial_mid_error_to_R_m": radial_mid_error,
        "chord_length_m": chord_length,
        "midpoint_deviation_m": deviation,
        "midpoint_deviation_mm": deviation * 1.0e3,
        "relative_midpoint_deviation": ratio,
        "distance_to_ideal_cylinder_arc_midpoint_m": ideal_curve_error,
    }


def _finite_stats(values: list[float]) -> dict[str, float | int | None]:
    finite = np.asarray([value for value in values if math.isfinite(value)], dtype=float)
    if finite.size == 0:
        return {"count": 0, "median": None, "p95": None, "max": None, "mean": None}
    return {
        "count": int(finite.size),
        "median": float(np.median(finite)),
        "p95": float(np.percentile(finite, 95.0)),
        "max": float(np.max(finite)),
        "mean": float(np.mean(finite)),
    }


def _element_error_metrics(
    archive: zipfile.ZipFile,
    level: str,
    elements: list[Any],
    coordinates: np.ndarray,
    young_modulus: float,
    poisson_ratio: float,
    radius: float,
    length: float,
    torque: float,
) -> tuple[dict[int, float], dict[int, float]]:
    with np.load(io.BytesIO(archive.read(f"output/{level}/displacements_xyz.npz"))) as arrays:
        stored_coordinates = arrays["node_coordinates"]
        displacement = arrays["displacements_xyz"]
    if not np.array_equal(stored_coordinates, coordinates):
        raise ValueError(f"{level}: archived displacement coordinates differ from the input mesh")
    shear_modulus = young_modulus / (2.0 * (1.0 + poisson_ratio))
    polar_moment = math.pi * radius**4 / 2.0
    twist_rate = torque / (shear_modulus * polar_moment)
    exact = np.zeros_like(displacement)
    exact[:, 1] = -twist_rate * coordinates[:, 0] * coordinates[:, 2]
    exact[:, 2] = twist_rate * coordinates[:, 0] * coordinates[:, 1]
    displacement_errors: dict[int, float] = {}
    for index, element in enumerate(elements):
        node_ids = np.asarray(element.nodes, dtype=int)
        reference = exact[node_ids]
        denominator = float(np.linalg.norm(reference))
        displacement_errors[index] = (
            float(np.linalg.norm(displacement[node_ids] - reference) / denominator)
            if denominator > 0.0
            else math.nan
        )

    stress_sums: dict[int, list[float]] = defaultdict(lambda: [0.0, 0.0])
    reader = csv.DictReader(io.StringIO(archive.read(f"output/{level}/integration_point_stresses.csv").decode("utf-8")))
    for row in reader:
        element_index = int(row["element"])
        weight = float(row["physical_volume_weight_m3"])
        dx = float(row["qf_Sxy_Pa"]) - float(row["sv_Sxy_Pa"])
        dz = float(row["qf_Sxz_Pa"]) - float(row["sv_Sxz_Pa"])
        rx = float(row["sv_Sxy_Pa"])
        rz = float(row["sv_Sxz_Pa"])
        stress_sums[element_index][0] += weight * (dx * dx + dz * dz)
        stress_sums[element_index][1] += weight * (rx * rx + rz * rz)
    stress_errors = {
        index: math.sqrt(numerator / denominator) if denominator > 0.0 else math.nan
        for index, (numerator, denominator) in stress_sums.items()
    }
    if set(stress_errors) != set(range(len(elements))):
        raise ValueError(f"{level}: archived integration-point stress rows do not cover each element")
    return displacement_errors, stress_errors


def _analyze_level(
    archive: zipfile.ZipFile,
    contract: dict[str, Any],
    level: str,
    threshold: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    input_data = contract["inputs"]["levels"][level]
    mesh_path = ROOT / contract["inputs"]["mesh_directory"] / input_data["mesh"]
    setup_path = ROOT / contract["inputs"]["mesh_directory"] / input_data["setup"]
    if _sha256(mesh_path.read_bytes()) != input_data["mesh_sha256"]:
        raise ValueError(f"{level}: mesh does not match frozen contract SHA")
    if _sha256(setup_path.read_bytes()) != contract["inputs"]["setup_sha256"]:
        raise ValueError(f"{level}: setup does not match frozen contract SHA")
    model = GmshModelImporter().import_model(mesh_path, setup_path).model
    coordinates = np.asarray(model.nodes, dtype=float)
    elements = list(model.elements)
    geometry = contract["model"]["geometry"]
    radius = float(geometry["radius_m"])
    length = float(geometry["length_m"])
    boundary_edges = _boundary_edge_keys(elements)
    checkpoint = json.loads(archive.read(f"output/{level}/result_checkpoint.json").decode("utf-8"))
    audit = checkpoint["solver"]["audit_diagnostic"]
    warning_texts = audit["mesh_warnings"]
    parsed_warnings: dict[int, float] = {}
    other_warning_texts: list[str] = []
    for warning in warning_texts:
        match = WARNING_RE.fullmatch(warning)
        if match:
            parsed_warnings[int(match.group(1))] = float(match.group(2))
        else:
            other_warning_texts.append(warning)

    edge_rows: list[dict[str, Any]] = []
    element_rows: list[dict[str, Any]] = []
    physical_edges: dict[tuple[int, int], dict[str, Any]] = {}
    physical_edge_owners: dict[tuple[int, int], set[int]] = defaultdict(set)
    all_jacobians: list[float] = []
    local_jacobian_ratios: list[float] = []
    local_metrics: list[dict[str, float]] = []
    for element_index, element in enumerate(elements):
        local_coordinates = coordinates[list(element.nodes)]
        metrics = {key: float(value) for key, value in MeshQuality.tet10_metrics(local_coordinates).items()}
        local_metrics.append(metrics)
        local_edges = []
        for local_edge_index, edge_nodes in enumerate(Tet10Element.edge_nodes):
            row = _edge_geometry(
                level,
                element_index,
                element,
                local_edge_index,
                edge_nodes,
                coordinates,
                boundary_edges,
                radius,
                length,
            )
            local_edges.append(row)
            physical_key = tuple(row["endpoint_node_indices"])
            physical_edge_owners[physical_key].add(element_index)
            if row["relative_midpoint_deviation"] > threshold:
                edge_rows.append(row)
                existing = physical_edges.get(physical_key)
                if existing is None or row["relative_midpoint_deviation"] > existing["relative_midpoint_deviation"]:
                    physical_edges[physical_key] = row
        determinants = Tet10Element.jacobian_determinants(local_coordinates)
        all_jacobians.extend(float(value) for value in determinants)
        local_jacobian_ratios.append(float(np.min(determinants) / np.max(determinants)) if np.max(determinants) > 0.0 else -math.inf)
        element_rows.append(
            {
                "element_index": element_index,
                "centroid_x_m": float(np.mean(local_coordinates[:, 0])),
                "max_relative_mid_edge_deviation": max(row["relative_midpoint_deviation"] for row in local_edges),
                "max_absolute_mid_edge_deviation_m": max(row["midpoint_deviation_m"] for row in local_edges),
                "warned_by_threshold": max(row["relative_midpoint_deviation"] for row in local_edges) > threshold,
                "sampled_jacobian_min": metrics["sampled_jacobian_min"],
                "sampled_jacobian_max": metrics["sampled_jacobian_max"],
                "sampled_jacobian_ratio": metrics["sampled_jacobian_ratio"],
                "corner_quality": metrics["quality"],
                "radius_ratio": metrics["radius_ratio"],
                "aspect_ratio": metrics["aspect_ratio"],
                "relative_corner_volume": metrics["relative_volume"],
            }
        )

    computed_warning_indices = {row["element_index"] for row in element_rows if row["warned_by_threshold"]}
    archived_warning_indices = set(parsed_warnings)
    if computed_warning_indices != archived_warning_indices:
        raise ValueError(
            f"{level}: recomputed warning elements differ from archive: "
            f"missing={sorted(computed_warning_indices - archived_warning_indices)[:8]}, "
            f"extra={sorted(archived_warning_indices - computed_warning_indices)[:8]}"
        )

    displacement_errors, stress_errors = _element_error_metrics(
        archive,
        level,
        elements,
        coordinates,
        float(contract["model"]["material"]["young_modulus_Pa"]),
        float(contract["model"]["material"]["poisson_ratio"]),
        radius,
        length,
        float(contract["model"]["load"]["torque_Nm"]),
    )
    warned_group = [row["element_index"] for row in element_rows if row["warned_by_threshold"]]
    unwarned_group = [row["element_index"] for row in element_rows if not row["warned_by_threshold"]]
    for element_index, row in enumerate(element_rows):
        row["local_displacement_error_vs_saint_venant_relative_l2"] = displacement_errors[element_index]
        row["local_ip_shear_error_vs_saint_venant_relative_l2"] = stress_errors[element_index]

    def zone(x: float) -> str:
        if x < length / 4.0:
            return "root_quarter"
        if x > 3.0 * length / 4.0:
            return "tip_quarter"
        return "middle_half"

    category_incidence = Counter(row["location"] for row in edge_rows)
    category_physical = Counter(row["location"] for row in physical_edges.values())
    warned_zones = Counter(zone(row["centroid_x_m"]) for row in element_rows if row["warned_by_threshold"])
    lateral_physical_edges = [
        row for row in physical_edges.values() if row["location"] == "lateral_cylinder"
    ]
    lateral_arc_midpoint_distances_mm = [
        float(row["distance_to_ideal_cylinder_arc_midpoint_m"]) * 1.0e3
        for row in lateral_physical_edges
        if row["distance_to_ideal_cylinder_arc_midpoint_m"] is not None
    ]
    jac_min = min(all_jacobians)
    jac_max = max(all_jacobians)
    quality_thresholds = MeshQualityThresholds()
    jacobian_bad = sum(value <= quality_thresholds.tet10_min_sampled_jacobian for value in all_jacobians)
    low_jacobian_ratio_count = sum(value < quality_thresholds.tet10_min_jacobian_ratio for value in local_jacobian_ratios)
    quality_summary = {
        "jacobian_sample_count_per_element": int(len(all_jacobians) / len(elements)),
        "jacobian_sample_count_total": len(all_jacobians),
        "jacobian_sampled_minimum_m3": jac_min,
        "jacobian_sampled_maximum_m3": jac_max,
        "jacobian_sampled_nonpositive_count": sum(value <= 0.0 for value in all_jacobians),
        "jacobian_sampled_below_failure_threshold_count": jacobian_bad,
        "minimum_per_element_sampled_jacobian_ratio": min(local_jacobian_ratios),
        "elements_below_sampled_jacobian_ratio_warning_threshold": low_jacobian_ratio_count,
        "minimum_corner_quality": min(row["quality"] for row in local_metrics),
        "minimum_corner_radius_ratio": min(row["radius_ratio"] for row in local_metrics),
        "maximum_corner_aspect_ratio": max(row["aspect_ratio"] for row in local_metrics),
        "minimum_relative_corner_volume": min(row["relative_volume"] for row in local_metrics),
        "mesh_errors_archived": len(audit["mesh_errors"]),
        "other_mesh_warning_count": len(other_warning_texts),
        "other_mesh_warning_examples": other_warning_texts[:5],
        "sampling_limit": "Tet10Element.jacobian_determinants default closed lattice; 35 samples per element. Finite sampling does not certify positivity everywhere inside each curved element.",
    }
    summary = {
        "level": level,
        "node_count": int(model.node_count),
        "element_count": len(elements),
        "archived_warning_element_count": len(archived_warning_indices),
        "recomputed_warning_element_count": len(computed_warning_indices),
        "warning_threshold_relative_deviation": threshold,
        "warning_element_indices_match_archive": True,
        "warning_edge_element_incidences_above_threshold": len(edge_rows),
        "unique_physical_warning_edges_above_threshold": len(physical_edges),
        "warning_edge_incidences_by_location": dict(category_incidence),
        "unique_warning_edges_by_location": dict(category_physical),
        "warning_elements_by_axial_zone": dict(warned_zones),
        "maximum_relative_mid_edge_deviation": max(row["relative_midpoint_deviation"] for row in edge_rows),
        "maximum_relative_deviation_edge": max(edge_rows, key=lambda row: row["relative_midpoint_deviation"]),
        "maximum_absolute_mid_edge_deviation_mm": max(row["midpoint_deviation_mm"] for row in edge_rows),
        "maximum_absolute_deviation_edge": max(edge_rows, key=lambda row: row["midpoint_deviation_m"]),
        "cylindrical_warning_edge_radial_midpoint_error_mm_max": max(
            (abs(float(row["radial_mid_error_to_R_m"])) * 1.0e3 for row in physical_edges.values() if row["radial_mid_error_to_R_m"] is not None),
            default=None,
        ),
        "cylindrical_warning_edge_distance_to_ideal_arc_midpoint_mm_max": max(
            (float(row["distance_to_ideal_cylinder_arc_midpoint_m"]) * 1.0e3 for row in physical_edges.values() if row["distance_to_ideal_cylinder_arc_midpoint_m"] is not None),
            default=None,
        ),
        "lateral_warning_edge_ideal_arc_midpoint_distance_mm": {
            **_finite_stats(lateral_arc_midpoint_distances_mm),
            "count_over_1mm": sum(value > 1.0 for value in lateral_arc_midpoint_distances_mm),
            "count_over_10mm": sum(value > 10.0 for value in lateral_arc_midpoint_distances_mm),
        },
        "quality_indicators": quality_summary,
        "warning_vs_unwarning_element_errors": {
            "warned_displacement_relative_l2": _finite_stats([displacement_errors[index] for index in warned_group]),
            "unwarned_displacement_relative_l2": _finite_stats([displacement_errors[index] for index in unwarned_group]),
            "warned_ip_shear_relative_l2": _finite_stats([stress_errors[index] for index in warned_group]),
            "unwarned_ip_shear_relative_l2": _finite_stats([stress_errors[index] for index in unwarned_group]),
        },
        "interpretation": (
            "Warning-edge categories are reconstructed by topological boundary faces and node positions. "
            "Element-local error grouping is descriptive, unweighted for nodal displacement, and cannot establish causality."
        ),
    }
    for row in physical_edges.values():
        row["owner_element_indices"] = sorted(physical_edge_owners[tuple(row["endpoint_node_indices"])])
    return summary, list(physical_edges.values()), element_rows


def _plot_localization(summaries: list[dict[str, Any]], edges_by_level: dict[str, list[dict[str, Any]]], path: Path) -> None:
    category_style = {
        "lateral_cylinder": ("#2563a6", "o"),
        "cylindrical_rim_x0": ("#059669", "^"),
        "cylindrical_rim_xL": ("#d97706", "s"),
        "planar_end_face_x0": ("#7c3aed", "D"),
        "planar_end_face_xL": ("#9333ea", "D"),
        "other_boundary": ("#c2410c", "P"),
        "interior": ("#dc2626", "x"),
    }
    figure, axes = plt.subplots(2, 2, figsize=(12.5, 8.3), sharex=True, sharey=True, constrained_layout=True)
    for axis, summary in zip(axes.flat, summaries):
        level = summary["level"]
        edges = edges_by_level[level]
        for category, (color, marker) in category_style.items():
            group = [row for row in edges if row["location"] == category]
            if not group:
                continue
            axis.scatter(
                [row["x_mid_m"] for row in group],
                [row["theta_mid_deg"] for row in group],
                color=color,
                marker=marker,
                s=26,
                alpha=0.8,
                linewidths=0.8,
                label=category.replace("_", " "),
            )
        axis.axvline(0.0, color="#64748b", linestyle="--", linewidth=0.8)
        axis.axvline(3.0, color="#64748b", linestyle="--", linewidth=0.8)
        axis.set_xlim(-0.08, 3.08)
        axis.set_ylim(0.0, 360.0)
        axis.set_yticks([0, 90, 180, 270, 360])
        axis.grid(True, alpha=0.22)
        axis.set_title(
            f"{level.upper()}: {summary['archived_warning_element_count']}/{summary['element_count']} éléments; "
            f"{summary['unique_physical_warning_edges_above_threshold']} arêtes uniques\n"
            f"max ratio={summary['maximum_relative_mid_edge_deviation']:.4f}; "
            f"max déviation={summary['maximum_absolute_mid_edge_deviation_mm']:.2f} mm"
        )
        if axis is axes[1, 0] or axis is axes[1, 1]:
            axis.set_xlabel("Position axiale x [m]")
        if axis is axes[0, 0] or axis is axes[1, 0]:
            axis.set_ylabel("θ du nœud milieu [°], atan2(z,y)")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    if handles:
        figure.legend(handles, labels, loc="outside lower center", ncol=3, fontsize=8)
    figure.suptitle(
        "Arêtes TET10 au-dessus du contrôle de déviation (5 %) — maillages J24B\n"
        "Position déroulée du cylindre ; symboles selon la localisation topologique"
    )
    figure.savefig(path, dpi=190)
    plt.close(figure)


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty diagnostic table: {path.name}")
    fields = list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: json.dumps(row[key]) if isinstance(row[key], list) else row.get(key) for key in fields})


def main() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    provenance = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))
    if contract["contract_id"] != "J24B-TET10-CIRCULAR-TORSION-STATIC-002":
        raise ValueError("unexpected J24B contract identity")
    if contract["status"] != "FROZEN_BEFORE_SOLVE":
        raise ValueError("J24B contract is not frozen")
    if tuple(contract["inputs"]["levels"]) != LEVELS:
        raise ValueError("unexpected J24B mesh-level set")
    threshold = float(MeshQualityThresholds().tet10_max_mid_edge_deviation_ratio)
    with zipfile.ZipFile(ARCHIVE_PATH) as archive:
        archive_status = _verify_archive(archive, provenance["archive"]["sha256"])
        summaries: list[dict[str, Any]] = []
        all_edges: list[dict[str, Any]] = []
        edges_by_level: dict[str, list[dict[str, Any]]] = {}
        element_rows: list[dict[str, Any]] = []
        for level in LEVELS:
            summary, edges, per_element = _analyze_level(archive, contract, level, threshold)
            summaries.append(summary)
            edges_by_level[level] = edges
            all_edges.extend(edges)
            element_rows.extend({"level": level, **row} for row in per_element)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = {
        "schema": "qf-j24c-tet10-curvature-warning-postprocess-v1",
        "analysis_id": "J24C-TET10-MIDEDGE-ARCHIVE-001",
        "analysis_type": "archival post-processing only; no FEM solve",
        "baseline_main_sha": provenance["baseline"]["main"],
        "j24b_run_source_sha": provenance["baseline"]["r1_source"],
        "j24b_run_source_tree": provenance["baseline"]["r1_tree"],
        "pr150_head_sha_at_analysis": "de3f39c536da73cf43cd19bae58b27a78bb528b2",
        "j24b_contract_id": contract["contract_id"],
        "j24b_contract_sha256": _sha256(CONTRACT_PATH.read_bytes()),
        "archive": archive_status,
        "postprocess_environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
        },
        "quality_control": {
            "source": "src/solveur/mesh/quality.py: MeshQualityThresholds.tet10_max_mid_edge_deviation_ratio",
            "warning_threshold_relative_deviation": threshold,
            "definition": "For each of the six TET10 edges: Euclidean distance from the midside node to the straight chord midpoint divided by corner-to-corner chord length; the element warning uses the maximum over six edges.",
            "jacobian_sampling": "Tet10Element.jacobian_determinants default closed lattice; 35 points per element; not a continuum certificate.",
        },
        "levels": summaries,
        "historical_status": {
            "contract_001": provenance["historical_attempt_001"]["status"],
            "contract_001_campaign": "INCONCLUSIVE",
            "contract_002_campaign": "PASS (bounded to frozen J24B configuration)",
            "audit_run_verdicts": "WARNING preserved at all four levels",
        },
    }
    (OUTPUT_DIR / "warning_diagnostics.json").write_text(json.dumps(output, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    _write_csv(OUTPUT_DIR / "warning_edges.csv", all_edges)
    _write_csv(OUTPUT_DIR / "element_error_comparison.csv", element_rows)
    _plot_localization(summaries, edges_by_level, OUTPUT_DIR / "warning_edge_localization.png")
    print(f"Wrote archived warning diagnostics for {len(summaries)} mesh levels to {OUTPUT_DIR}")
    for summary in summaries:
        print(
            f"{summary['level']}: {summary['archived_warning_element_count']} warning elements; "
            f"{summary['warning_edge_element_incidences_above_threshold']} local edge incidences; "
            f"{summary['unique_physical_warning_edges_above_threshold']} unique edges; "
            f"max ratio {summary['maximum_relative_mid_edge_deviation']:.6g}"
        )


if __name__ == "__main__":
    main()
