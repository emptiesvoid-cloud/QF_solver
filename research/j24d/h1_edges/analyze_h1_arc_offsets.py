"""Analyze the 20 J24C-identified H1 cylinder edges without running FEM."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from numpy.polynomial import polynomial as poly

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from solveur.mesh.gmsh_importer import GmshModelImporter  # noqa: E402

CONTRACT_PATH = ROOT / "research/j24b/tet10_torsion/contract-002-h1-digest-corrected.json"
EDGE_ROWS_PATH = ROOT / "research/j24c/results/diagnostic-2026-11-18/warning_edges.csv"
ELEMENT_ROWS_PATH = ROOT / "research/j24c/results/diagnostic-2026-11-18/element_error_comparison.csv"
OUTPUT_DIR = ROOT / "research/j24d/results/diagnostic-2026-11-18"
DISTANCE_CUTOFF_M = 0.010
RADIUS_TOLERANCE_M = 1.0e-8


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def wrapped_angle(angle: float) -> float:
    return (angle + math.pi) % (2.0 * math.pi) - math.pi


def _edge_coordinate_polynomials(p0: np.ndarray, pm: np.ndarray, p1: np.ndarray) -> list[np.ndarray]:
    n0 = np.asarray([1.0, -3.0, 2.0])
    nm = np.asarray([0.0, 4.0, -4.0])
    n1 = np.asarray([0.0, -1.0, 2.0])
    return [n0 * p0[i] + nm * pm[i] + n1 * p1[i] for i in range(3)]


def _curve_radius_extrema(p0: np.ndarray, pm: np.ndarray, p1: np.ndarray, radius: float) -> dict[str, float]:
    x_poly, y_poly, z_poly = _edge_coordinate_polynomials(p0, pm, p1)
    del x_poly
    radius_squared = poly.polyadd(poly.polymul(y_poly, y_poly), poly.polymul(z_poly, z_poly))
    candidates = [0.0, 1.0]
    derivative = poly.polyder(radius_squared)
    if np.any(np.abs(derivative) > 0.0):
        for root in poly.polyroots(derivative):
            if abs(float(np.imag(root))) <= 1.0e-9 and 0.0 < float(np.real(root)) < 1.0:
                candidates.append(float(np.real(root)))
    radii = [(math.sqrt(max(float(poly.polyval(t, radius_squared)), 0.0)), t) for t in candidates]
    min_radius, min_t = min(radii)
    max_radius, max_t = max(radii)
    if abs(min_radius - radius) >= abs(max_radius - radius):
        max_abs_error, max_abs_t = abs(min_radius - radius), min_t
    else:
        max_abs_error, max_abs_t = abs(max_radius - radius), max_t
    return {
        "minimum_radius_m": min_radius,
        "minimum_radius_at_t": min_t,
        "maximum_radius_m": max_radius,
        "maximum_radius_at_t": max_t,
        "maximum_absolute_radius_error_m": max_abs_error,
        "maximum_absolute_radius_error_at_t": max_abs_t,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def _analyze_edge(
    row: dict[str, str],
    coordinates: np.ndarray,
    radius: float,
    element_errors: dict[int, dict[str, str]],
) -> dict[str, Any]:
    endpoint_ids = json.loads(row["endpoint_node_indices"])
    middle_id = int(row["midside_node_index"])
    p0, p1, pm = coordinates[[int(endpoint_ids[0]), int(endpoint_ids[1]), middle_id]]
    theta0 = math.atan2(float(p0[2]), float(p0[1]))
    theta1 = math.atan2(float(p1[2]), float(p1[1]))
    delta = wrapped_angle(theta1 - theta0)
    theta_ideal = theta0 + 0.5 * delta
    theta_actual = math.atan2(float(pm[2]), float(pm[1]))
    angular_offset = wrapped_angle(theta_actual - theta_ideal)
    ideal_midpoint = np.asarray(
        [0.5 * (p0[0] + p1[0]), radius * math.cos(theta_ideal), radius * math.sin(theta_ideal)],
        dtype=float,
    )
    radial_errors = np.abs(np.hypot(np.asarray([p0[1], pm[1], p1[1]]), np.asarray([p0[2], pm[2], p1[2]])) - radius)
    actual_curve = _curve_radius_extrema(p0, pm, p1, radius)
    ideal_curve = _curve_radius_extrema(p0, ideal_midpoint, p1, radius)
    owners = json.loads(row["owner_element_indices"])
    owner_data = [element_errors[int(index)] for index in owners]
    max_ideal_error = math.sqrt(
        float((pm[0] - ideal_midpoint[0]) ** 2)
        + float(2.0 * radius**2 * (1.0 - math.cos(angular_offset)))
    )
    computed_distance = float(np.linalg.norm(pm - ideal_midpoint))
    archived_distance = float(row["distance_to_ideal_cylinder_arc_midpoint_m"])
    if not math.isclose(computed_distance, archived_distance, rel_tol=1.0e-8, abs_tol=1.0e-12):
        raise ValueError(f"archived and recomputed arc-midpoint distances differ for edge {endpoint_ids}")
    return {
        "level": "h1",
        "element_index": int(row["element_index"]),
        "local_edge_index": int(row["local_edge_index"]),
        "endpoint_node_indices": endpoint_ids,
        "midside_node_index": middle_id,
        "owner_element_indices": owners,
        "x_mid_m": float(pm[0]),
        "chord_length_m": float(np.linalg.norm(p1 - p0)),
        "warning_relative_deviation": float(row["relative_midpoint_deviation"]),
        "midside_radial_error_to_R_m": float(np.hypot(pm[1], pm[2]) - radius),
        "max_node_radial_error_to_R_m": float(np.max(radial_errors)),
        "midside_axial_offset_from_chord_midpoint_m": float(pm[0] - 0.5 * (p0[0] + p1[0])),
        "midside_angular_offset_from_short_arc_midpoint_deg": math.degrees(angular_offset),
        "midside_distance_to_ideal_arc_midpoint_mm": computed_distance * 1.0e3,
        "actual_quadratic_edge_radius_extrema": actual_curve,
        "ideal_midpoint_quadratic_edge_radius_extrema": ideal_curve,
        "owner_element_errors": [
            {
                "element_index": int(index),
                "displacement_error_relative_l2": float(data["local_displacement_error_vs_saint_venant_relative_l2"]),
                "ip_shear_error_relative_l2": float(data["local_ip_shear_error_vs_saint_venant_relative_l2"]),
                "sampled_jacobian_ratio": float(data["sampled_jacobian_ratio"]),
                "sampled_jacobian_min": float(data["sampled_jacobian_min"]),
                "corner_quality": float(data["corner_quality"]),
                "corner_radius_ratio": float(data["radius_ratio"]),
                "corner_aspect_ratio": float(data["aspect_ratio"]),
            }
            for index, data in zip(owners, owner_data)
        ],
    }


def _plot(rows: list[dict[str, Any]], output_path: Path, radius: float) -> None:
    order = sorted(range(len(rows)), key=lambda index: rows[index]["midside_distance_to_ideal_arc_midpoint_mm"], reverse=True)
    actual = np.asarray([rows[index]["actual_quadratic_edge_radius_extrema"]["maximum_absolute_radius_error_m"] * 1e3 for index in order])
    ideal = np.asarray([rows[index]["ideal_midpoint_quadratic_edge_radius_extrema"]["maximum_absolute_radius_error_m"] * 1e3 for index in order])
    labels = [
        f"e{rows[index]['element_index']}:{rows[index]['local_edge_index']}"
        for index in order
    ]
    offsets = np.asarray([rows[index]["midside_angular_offset_from_short_arc_midpoint_deg"] for index in order])
    figure, axes = plt.subplots(1, 2, figsize=(15, 5.8), constrained_layout=True)
    axes[0].bar(np.arange(len(order)), offsets, color="#a855f7", width=0.8)
    axes[0].axhline(0.0, color="#334155", linewidth=0.8)
    axes[0].set_title("Milieu d’arc : décalage angulaire du nœud TET10")
    axes[0].set_ylabel("Écart signé [°]")
    axes[0].set_xlabel("Arêtes classées par distance au milieu d’arc")
    axes[0].grid(axis="y", alpha=0.25)
    axes[0].set_xticks(np.arange(len(order)), labels, rotation=70, fontsize=7)

    x = np.arange(len(order))
    width = 0.38
    axes[1].bar(x - width / 2.0, actual, width, label="Nœud milieu archivé", color="#dc2626")
    axes[1].bar(x + width / 2.0, ideal, width, label="Milieu angulaire idéal", color="#2563a6")
    axes[1].set_title("Écart radial maximal de la courbe quadratique")
    axes[1].set_ylabel("Max |r(t) − R| sur l’arête [mm]")
    axes[1].set_xlabel("Même ordre d’arêtes ; rayon cible R = {:.3f} m".format(radius))
    axes[1].grid(axis="y", alpha=0.25)
    axes[1].legend()
    figure.suptitle("20 arêtes latérales H1 avec décalage milieu d’arc > 10 mm — post-traitement géométrique")
    figure.savefig(output_path, dpi=180)
    plt.close(figure)


def main() -> None:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    level = contract["inputs"]["levels"]["h1"]
    mesh_path = ROOT / contract["inputs"]["mesh_directory"] / level["mesh"]
    setup_path = ROOT / contract["inputs"]["mesh_directory"] / level["setup"]
    if sha256(mesh_path) != level["mesh_sha256"]:
        raise ValueError("H1 mesh digest does not match frozen contract 002")
    if sha256(setup_path) != contract["inputs"]["setup_sha256"]:
        raise ValueError("H1 setup digest does not match frozen contract 002")
    model = GmshModelImporter().import_model(mesh_path, setup_path).model
    coordinates = np.asarray(model.nodes, dtype=float)
    edge_rows = _read_csv(EDGE_ROWS_PATH)
    element_rows = _read_csv(ELEMENT_ROWS_PATH)
    element_errors = {
        int(row["element_index"]): row
        for row in element_rows
        if row["level"] == "h1"
    }
    radius = float(contract["model"]["geometry"]["radius_m"])
    candidates = [
        row for row in edge_rows
        if row["level"] == "h1"
        and row["location"] == "lateral_cylinder"
        and float(row["distance_to_ideal_cylinder_arc_midpoint_m"]) > DISTANCE_CUTOFF_M
    ]
    if len(candidates) != 20:
        raise ValueError(f"expected 20 H1 lateral edges above 10 mm, found {len(candidates)}")
    results = [_analyze_edge(row, coordinates, radius, element_errors) for row in candidates]
    radial_node_errors = [row["max_node_radial_error_to_R_m"] for row in results]
    actual_curve_errors = [row["actual_quadratic_edge_radius_extrema"]["maximum_absolute_radius_error_m"] for row in results]
    ideal_curve_errors = [row["ideal_midpoint_quadratic_edge_radius_extrema"]["maximum_absolute_radius_error_m"] for row in results]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    summary = {
        "analysis_id": "J24D-H1-QUADRATIC-EDGE-GEOMETRY-001",
        "analysis_type": "archived mesh geometry post-processing; no FEM solve",
        "j24c_commit": "c8a90f6e52bdb6f42444b9ab2e5efe88f478f488",
        "j24b_run_source_sha": "275c5788e4eaded1ea4305630ea1b0eb0b88158c",
        "j24b_contract_sha256": sha256(CONTRACT_PATH),
        "h1_mesh_sha256": sha256(mesh_path),
        "h1_setup_sha256": sha256(setup_path),
        "j24c_warning_edges_csv_sha256": sha256(EDGE_ROWS_PATH),
        "radius_m": radius,
        "selected_edges": len(results),
        "selection": "H1 unique physical lateral-cylinder warning edges with distance from the midside node to the short-arc midpoint greater than 0.010 m",
        "radius_checks": {
            "node_tolerance_m": RADIUS_TOLERANCE_M,
            "all_selected_edge_nodes_within_tolerance": max(radial_node_errors) <= RADIUS_TOLERANCE_M,
            "maximum_node_radial_error_m": max(radial_node_errors),
            "actual_quadratic_mapping_maximum_radial_error_m": max(actual_curve_errors),
            "actual_quadratic_mapping_p95_radial_error_m": float(np.percentile(actual_curve_errors, 95.0)),
            "ideal_midpoint_quadratic_mapping_maximum_radial_error_m": max(ideal_curve_errors),
            "ideal_midpoint_quadratic_mapping_p95_radial_error_m": float(np.percentile(ideal_curve_errors, 95.0)),
            "method": "For each quadratic edge, form the degree-4 polynomial y(t)^2+z(t)^2; solve its degree-3 derivative for all real roots in (0,1), then evaluate endpoints and all stationary points. This computes radial extrema of the represented edge polynomial up to floating-point root-solving error; it does not bound the interior of the 3D tetrahedron.",
        },
        "interpretation_limit": "Midside nodes lie on the analytical radius, but off-half-angle positions alter the quadratic edge mapping. The continuous edge radial error is quantified here; no acceptance tolerance is established and no causality to the archived mechanical errors is inferred.",
        "edges": results,
        "environment": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "matplotlib": matplotlib.__version__,
        },
    }
    with (OUTPUT_DIR / "h1_edge_geometry.json").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    with (OUTPUT_DIR / "h1_edge_geometry.csv").open("w", newline="", encoding="utf-8") as stream:
        fields = [
            "element_index", "local_edge_index", "endpoint_node_indices", "midside_node_index",
            "owner_element_indices", "x_mid_m", "chord_length_m", "warning_relative_deviation",
            "midside_radial_error_to_R_m", "midside_angular_offset_from_short_arc_midpoint_deg",
            "midside_distance_to_ideal_arc_midpoint_mm", "actual_curve_max_radius_error_mm",
            "actual_curve_max_radius_error_at_t", "ideal_midpoint_curve_max_radius_error_mm",
            "ideal_midpoint_curve_max_radius_error_at_t",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in results:
            writer.writerow({
                "element_index": row["element_index"],
                "local_edge_index": row["local_edge_index"],
                "endpoint_node_indices": json.dumps(row["endpoint_node_indices"]),
                "midside_node_index": row["midside_node_index"],
                "owner_element_indices": json.dumps(row["owner_element_indices"]),
                "x_mid_m": row["x_mid_m"],
                "chord_length_m": row["chord_length_m"],
                "warning_relative_deviation": row["warning_relative_deviation"],
                "midside_radial_error_to_R_m": row["midside_radial_error_to_R_m"],
                "midside_angular_offset_from_short_arc_midpoint_deg": row["midside_angular_offset_from_short_arc_midpoint_deg"],
                "midside_distance_to_ideal_arc_midpoint_mm": row["midside_distance_to_ideal_arc_midpoint_mm"],
                "actual_curve_max_radius_error_mm": row["actual_quadratic_edge_radius_extrema"]["maximum_absolute_radius_error_m"] * 1.0e3,
                "actual_curve_max_radius_error_at_t": row["actual_quadratic_edge_radius_extrema"]["maximum_absolute_radius_error_at_t"],
                "ideal_midpoint_curve_max_radius_error_mm": row["ideal_midpoint_quadratic_edge_radius_extrema"]["maximum_absolute_radius_error_m"] * 1.0e3,
                "ideal_midpoint_curve_max_radius_error_at_t": row["ideal_midpoint_quadratic_edge_radius_extrema"]["maximum_absolute_radius_error_at_t"],
            })
    _plot(results, OUTPUT_DIR / "h1_edge_radial_deviation.png", radius)
    print(f"Analyzed {len(results)} archived H1 edges; max node radial error={max(radial_node_errors):.6e} m")
    print(f"Max represented-edge radial deviation={max(actual_curve_errors)*1e3:.6f} mm; ideal-midpoint={max(ideal_curve_errors)*1e3:.6f} mm")


if __name__ == "__main__":
    main()
