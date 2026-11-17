"""Rebuild J24B torsion figures and compact data from the frozen run archive.

Requires NumPy, Matplotlib and the optional Gmsh reader dependency used by
QF Solver. This script only reads evidence; it does not run the solver.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from solveur.mesh.gmsh_reader import GmshNativeReader  # noqa: E402

ARTIFACT_DIR = ROOT / "research/j24b/results/diagnostic-2026-11-17"
DEFAULT_ARCHIVE = ARTIFACT_DIR / "raw_results.zip"
DEFAULT_CONTRACT = ROOT / "research/j24b/tet10_torsion/contract-002-h1-digest-corrected.json"
TIP_TWIST_AMPLIFICATION = 200_000.0
TORSION_NM = 1000.0
RADIUS_M = 0.5
LENGTH_M = 3.0
POLAR_MOMENT_M4 = math.pi * RADIUS_M**4 / 2.0
G_PA = 80.0e9 / (2.0 * (1.0 + 0.30))
REFERENCE_TWIST_RAD = TORSION_NM * LENGTH_M / (G_PA * POLAR_MOMENT_M4)


def _read_json(archive: zipfile.ZipFile, name: str) -> dict[str, Any]:
    return json.loads(archive.read(name).decode("utf-8"))


def _read_csv(archive: zipfile.ZipFile, name: str) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(archive.read(name).decode("utf-8"))))


def _boundary_triangles(mesh: Any) -> np.ndarray:
    faces: dict[tuple[int, int, int], tuple[int, int, int]] = {}
    counts: Counter[tuple[int, int, int]] = Counter()
    local_faces = ((0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3))
    for cell in mesh.cells.values():
        if cell.dimension != 3 or cell.gmsh_type != 11:
            continue
        corners = cell.nodes[:4]
        for local in local_faces:
            oriented = tuple(int(corners[i]) for i in local)
            key = tuple(sorted(oriented))
            counts[key] += 1
            faces[key] = oriented
    boundary = [faces[key] for key, count in counts.items() if count == 1]
    if not boundary:
        raise ValueError("No external TET10 corner faces were found in the H4 mesh")
    return np.asarray(boundary, dtype=np.int64)


def _surface_edges(faces: np.ndarray, tag_index: dict[int, int]) -> np.ndarray:
    edges: set[tuple[int, int]] = set()
    for face in faces:
        for a, b in ((face[0], face[1]), (face[1], face[2]), (face[2], face[0])):
            edges.add(tuple(sorted((tag_index[int(a)], tag_index[int(b)]))))
    return np.asarray(sorted(edges), dtype=np.int64)


def _style_3d(ax: Any, *, deformed: bool) -> None:
    ax.set_xlabel("x [m]")
    ax.set_ylabel("y [m]")
    ax.set_zlabel("z [m]")
    ax.set_xlim(0.0, LENGTH_M + 0.08)
    ax.set_ylim(-0.72, 0.72)
    ax.set_zlim(-0.72, 0.72)
    ax.set_box_aspect((3.0, 1.44, 1.44))
    ax.view_init(elev=22, azim=-55)
    if deformed:
        ax.set_title(f"Déformée H4, amplification ×{TIP_TWIST_AMPLIFICATION:,.0f}")
    else:
        ax.set_title("Géométrie H4 : appui et couple terminal")


def _draw_surface(ax: Any, coordinates: np.ndarray, faces: np.ndarray, edges: np.ndarray, *, color: str) -> None:
    polygons = coordinates[faces]
    collection = Poly3DCollection(polygons, facecolor=color, edgecolor="none", alpha=0.16)
    ax.add_collection3d(collection)
    lines = coordinates[edges]
    ax.add_collection3d(Line3DCollection(lines, colors=color, linewidths=0.28, alpha=0.65))


def _plot_mesh_and_deformation(
    output: Path,
    mesh_path: Path,
    coordinates_from_archive: np.ndarray,
    displacement: np.ndarray,
) -> None:
    mesh = GmshNativeReader().read(mesh_path)
    tags = sorted(mesh.nodes)
    coordinates = np.asarray([mesh.nodes[tag] for tag in tags], dtype=float)
    if coordinates.shape != coordinates_from_archive.shape or not np.array_equal(coordinates, coordinates_from_archive):
        raise ValueError("Archived H4 coordinates do not match the frozen Gmsh input node ordering")
    tag_index = {tag: index for index, tag in enumerate(tags)}
    faces_by_tag = _boundary_triangles(mesh)
    faces = np.asarray([[tag_index[int(tag)] for tag in face] for face in faces_by_tag], dtype=np.int64)
    edges = _surface_edges(faces_by_tag, tag_index)
    deformed = coordinates + TIP_TWIST_AMPLIFICATION * displacement
    root_mask = np.abs(coordinates[:, 0]) <= 1.0e-10 * max(LENGTH_M, 1.0)
    root_nodes = coordinates[root_mask]

    figure = plt.figure(figsize=(12, 5.5), constrained_layout=True)
    ax0 = figure.add_subplot(1, 2, 1, projection="3d")
    _draw_surface(ax0, coordinates, faces, edges, color="#65758b")
    ax0.scatter(root_nodes[:, 0], root_nodes[:, 1], root_nodes[:, 2], s=6, color="#b83240", label="UX=UY=UZ=0")
    ax0.quiver(LENGTH_M, RADIUS_M, 0, 0, 0, 0.18, color="#d97706", arrow_length_ratio=0.22, linewidth=2)
    ax0.quiver(LENGTH_M, 0, RADIUS_M, 0, -0.18, 0, color="#d97706", arrow_length_ratio=0.22, linewidth=2)
    ax0.legend(loc="upper left", fontsize=8)
    ax0.text2D(
        0.58,
        0.94,
        "Tₓ=+1000 N·m ; traction tangente sur x=L",
        transform=ax0.transAxes,
        color="#a34f00",
        fontsize=8,
    )
    _style_3d(ax0, deformed=False)

    ax1 = figure.add_subplot(1, 2, 2, projection="3d")
    _draw_surface(ax1, deformed, faces, edges, color="#2563a6")
    ax1.scatter(deformed[root_mask, 0], deformed[root_mask, 1], deformed[root_mask, 2], s=6, color="#b83240")
    _style_3d(ax1, deformed=True)
    ax1.text2D(
        0.03,
        0.02,
        "Le déplacement affiché est multiplié ; les valeurs quantitatives restent celles du calcul.",
        transform=ax1.transAxes,
        fontsize=8,
    )
    figure.suptitle("Arbre circulaire TET10 sous torsion statique — H4")
    figure.savefig(output, dpi=190)
    plt.close(figure)


def _plot_tip_cross_section(output: Path, coordinates: np.ndarray, displacement: np.ndarray, faces: np.ndarray, tip_twist: float) -> None:
    tolerance = 1.0e-10 * max(LENGTH_M, 1.0)
    tip_faces = faces[np.all(np.abs(coordinates[faces, 0] - LENGTH_M) <= tolerance, axis=1)]
    if len(tip_faces) == 0:
        raise ValueError("H4 boundary triangulation contains no terminal cross-section faces")
    deformed = coordinates + TIP_TWIST_AMPLIFICATION * displacement
    tip_xyz = coordinates[tip_faces][:, :, 1:3]
    tip_deformed_yz = deformed[tip_faces][:, :, 1:3]
    figure, ax = plt.subplots(figsize=(6.2, 5.2), constrained_layout=True)
    ax.add_collection(PolyCollection(tip_xyz, facecolors="none", edgecolors="#64748b", linewidths=0.45, linestyles="--"))
    ax.add_collection(PolyCollection(tip_deformed_yz, facecolors="none", edgecolors="#d97706", linewidths=0.65))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-0.62, 0.62)
    ax.set_ylim(-0.62, 0.62)
    ax.set_xlabel("y [m]")
    ax.set_ylabel("z [m]")
    ax.set_title("Section x=L : maillage initial et déformé")
    ax.grid(True, alpha=0.2)
    ax.legend(
        handles=[
            Line2D([0], [0], color="#64748b", linestyle="--", label="Maillage initial"),
            Line2D([0], [0], color="#d97706", label=f"Déformée ×{TIP_TWIST_AMPLIFICATION:,.0f}"),
        ],
        loc="upper right",
        fontsize=8,
    )
    amplified = tip_twist * TIP_TWIST_AMPLIFICATION
    ax.text(
        0.03,
        0.03,
        f"Angle calculé : {tip_twist:.6e} rad\nangle affiché : {amplified:.3f} rad ({math.degrees(amplified):.1f}°)",
        transform=ax.transAxes,
        fontsize=8,
        bbox={"boxstyle": "round", "facecolor": "white", "alpha": 0.88},
    )
    figure.savefig(output, dpi=190)
    plt.close(figure)


def _plot_convergence(output: Path, rows: list[dict[str, Any]]) -> None:
    labels = [row["level"] for row in rows]
    twist_um = np.asarray([row["response"]["tip_twist_rad"] * 1e6 for row in rows])
    twist_error_pct = np.asarray([row["response"]["tip_twist_relative_error"] * 100 for row in rows])
    stress_error_pct = np.asarray(
        [row["response"]["integration_point_volume_weighted_stress_l2_relative_error"] * 100 for row in rows]
    )
    x = np.arange(len(rows))
    figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.4), constrained_layout=True)
    axes[0].plot(x, twist_um, marker="o", linewidth=2, color="#2563a6", label="QF Solver TET10")
    axes[0].axhline(REFERENCE_TWIST_RAD * 1e6, color="#c2410c", linestyle="--", label="Saint-Venant")
    axes[0].set_xticks(x, labels)
    axes[0].set_ylabel("Angle de torsion à x=L [µrad]")
    axes[0].set_title("Angle à la section terminale")
    axes[0].grid(True, alpha=0.25)
    axes[0].legend()

    axes[1].semilogy(x, twist_error_pct, marker="o", linewidth=2, color="#2563a6", label="Erreur relative de l’angle")
    axes[1].semilogy(x, stress_error_pct, marker="s", linewidth=2, color="#7c3aed", label="Écart L2 des cisaillements aux IP")
    axes[1].axhline(
        1.0,
        color="#c2410c",
        linestyle="--",
        linewidth=1,
        label="Critère angle H4 : 1 % (angle seul)",
    )
    axes[1].set_xticks(x, labels)
    axes[1].set_ylabel("Écart relatif [%], échelle logarithmique")
    axes[1].set_title("Évolution avec les maillages gelés")
    axes[1].grid(True, which="both", alpha=0.25)
    axes[1].legend(fontsize=8)
    figure.suptitle("Torsion statique TET10 — comparaison à Saint-Venant")
    figure.savefig(output, dpi=190)
    plt.close(figure)


def _plot_ip_stress(output: Path, stress_rows: list[dict[str, str]]) -> None:
    x_values = np.asarray([float(row["x_m"]) for row in stress_rows])
    y = np.asarray([float(row["y_m"]) for row in stress_rows])
    z = np.asarray([float(row["z_m"]) for row in stress_rows])
    qf_xy = np.asarray([float(row["qf_Sxy_Pa"]) for row in stress_rows])
    qf_xz = np.asarray([float(row["qf_Sxz_Pa"]) for row in stress_rows])
    r = np.hypot(y, z)
    tau_qf = np.hypot(qf_xy, qf_xz)
    tau_sv = TORSION_NM * r / POLAR_MOMENT_M4
    mask = np.abs(x_values - LENGTH_M / 2.0) <= 0.05
    if not np.any(mask):
        raise ValueError("No H4 integration points fall in the frozen central sampling slice")

    figure, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    scatter = axes[0].scatter(y[mask], z[mask], c=tau_qf[mask], s=9, cmap="viridis", rasterized=True)
    circle = plt.Circle((0.0, 0.0), RADIUS_M, fill=False, color="#333333", linewidth=1.1)
    axes[0].add_patch(circle)
    axes[0].set_aspect("equal", adjustable="box")
    axes[0].set_xlim(-0.55, 0.55)
    axes[0].set_ylim(-0.55, 0.55)
    axes[0].set_xlabel("y [m]")
    axes[0].set_ylabel("z [m]")
    axes[0].set_title(f"\u03c4 résultante aux IP, |x−1,5| ≤ 0,05 m\n{int(mask.sum())} points")
    colorbar = figure.colorbar(scatter, ax=axes[0], shrink=0.82)
    colorbar.set_label("√(Sxy²+Sxz²) [Pa]")

    axes[1].scatter(r[::12] / RADIUS_M, tau_qf[::12], s=5, alpha=0.25, color="#2563a6", label="QF, points d’intégration H4")
    radial = np.linspace(0.0, RADIUS_M, 200)
    axes[1].plot(radial / RADIUS_M, TORSION_NM * radial / POLAR_MOMENT_M4, color="#c2410c", linewidth=2, label="Saint-Venant : T r/J")
    axes[1].set_xlabel("r/R [-]")
    axes[1].set_ylabel("√(Sxy²+Sxz²) [Pa]")
    axes[1].set_title("Cisaillement aux points d’intégration\n(un point sur 12 affiché)")
    axes[1].grid(True, alpha=0.25)
    axes[1].legend(fontsize=8)
    figure.suptitle("Contraintes de cisaillement H4 — mesure directe aux points d’intégration")
    figure.savefig(output, dpi=190)
    plt.close(figure)


def build(archive_path: Path, contract_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    with zipfile.ZipFile(archive_path, "r") as archive:
        archive_manifest = _read_json(archive, "archive_manifest.json")
        expected_files = archive_manifest.get("files_sha256", {})
        archive_members = set(archive.namelist()) - {"archive_manifest.json"}
        if archive_members != set(expected_files):
            raise ValueError("Raw archive member list differs from its frozen integrity manifest")
        for name, expected_sha in expected_files.items():
            actual_sha = hashlib.sha256(archive.read(name)).hexdigest()
            if actual_sha != expected_sha:
                raise ValueError(f"Raw archive member checksum mismatch: {name}")
        if archive.read("contract/contract-002.json") != contract_path.read_bytes():
            raise ValueError("Archived contract 002 differs from the local frozen contract")
        summary = _read_json(archive, "output/campaign_summary.json")
        levels = summary["mesh_levels"]
        if [row["level"] for row in levels] != ["h1", "h2", "h3", "h4"]:
            raise ValueError("The frozen campaign must contain h1 through h4 in order")
        site_rows: list[dict[str, Any]] = []
        csv_rows: list[dict[str, Any]] = []
        for row in levels:
            response = row["response"]
            resource = row["resource_observations"]
            mesh = row["mesh"]
            site_row = {
                "level": row["level"],
                "point_status": row["point_status"],
                "mesh_sha256": row["mesh_sha256"],
                "setup_sha256": row["setup_sha256"],
                **mesh,
                "load_resultant_N": row["load"]["reintegrated_force_N"],
                "load_moment_about_origin_Nm": row["load"]["reintegrated_moment_about_origin_Nm"],
                "torque_relative_error": row["load"]["torque_relative_error"],
                "tip_twist_rad": response["tip_twist_rad"],
                "saint_venant_tip_twist_rad": response["saint_venant_tip_twist_rad"],
                "tip_twist_relative_error": response["tip_twist_relative_error"],
                "ip_shear_volume_weighted_l2_relative_error": response[
                    "integration_point_volume_weighted_stress_l2_relative_error"
                ],
                "free_relative_residual": response["free_relative_residual"],
                "force_closure_over_T_over_R": response["reaction_force_closure_over_T_over_R"],
                "moment_x_closure_over_T": response["reaction_moment_x_closure_over_T"],
                "linear_energy_identity_relative_error": response["linear_energy_identity_relative_error"],
                "external_work_J": response["external_work_J"],
                "secant_internal_energy_J": response["secant_internal_energy_J"],
                "level_elapsed_seconds": resource["level_elapsed_seconds"],
                "assembly_solve_audit_seconds": resource["phase_times_seconds"][
                    "assembly_solve_and_solver_audit_seconds"
                ],
                "integration_point_count": row["integration_point_count"],
                "solver_status": row["solver"]["status"],
                "solver_run_verdict": row["solver"]["run_verdict"],
                "all_contract_checks_pass": all(row["checks"].values()),
            }
            site_rows.append(site_row)
            csv_rows.append({key: value for key, value in site_row.items() if not isinstance(value, (list, dict))})

        provenance_path = output_dir / "provenance.json"
        provenance = json.loads(provenance_path.read_text(encoding="utf-8")) if provenance_path.is_file() else None
        site_data = {
            "schema": "qf-j24b-tet10-torsion-site-data-v1",
            "status": summary["status"],
            "scope_limit": summary["scope_limit"],
            "contract_id": contract["contract_id"],
            "model": contract["model"],
            "reference": contract["reference"],
            "criteria": contract["criteria_fixed_before_solve"],
            "provenance": provenance,
            "campaign_indicators": levels[0].get("campaign_indicators", {}),
            "mesh_levels": site_rows,
            "notes": [
                "The solver run verdict contains audit WARNINGs; the prospective J24B point criteria and campaign indicator are reported separately.",
                "Integration-point shear is compared at the actual TET10 stiffness integration coordinates; no nodal extrapolation is used.",
                "The stress comparison uses a volume-weighted L2 norm over all integration points of each mesh.",
                "The figures are prepared assets only and have not been published.",
            ],
        }
        (output_dir / "site_data.json").write_text(
            json.dumps(site_data, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        with (output_dir / "mesh_results.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(csv_rows[0]))
            writer.writeheader()
            writer.writerows(csv_rows)

        with tempfile.TemporaryDirectory(prefix="qf-j24b-plot-") as temporary:
            temporary_path = Path(temporary)
            h4_mesh = temporary_path / "torsion_tet10_h4.msh"
            h4_mesh.write_bytes(archive.read("inputs/torsion_tet10_h4.msh"))
            npz_bytes = io.BytesIO(archive.read("output/h4/displacements_xyz.npz"))
            displacement_data = np.load(npz_bytes)
            _plot_mesh_and_deformation(
                output_dir / "torsion_deformed_mesh_h4.png",
                h4_mesh,
                displacement_data["node_coordinates"],
                displacement_data["displacements_xyz"],
            )
            tip_twist = next(row["response"]["tip_twist_rad"] for row in levels if row["level"] == "h4")
            mesh = GmshNativeReader().read(h4_mesh)
            tags = sorted(mesh.nodes)
            coordinates = np.asarray([mesh.nodes[tag] for tag in tags], dtype=float)
            tag_index = {tag: index for index, tag in enumerate(tags)}
            tag_faces = _boundary_triangles(mesh)
            indexed_faces = np.asarray([[tag_index[int(tag)] for tag in face] for face in tag_faces], dtype=np.int64)
            _plot_tip_cross_section(
                output_dir / "torsion_tip_section_twist_h4.png",
                coordinates,
                displacement_data["displacements_xyz"],
                indexed_faces,
                tip_twist,
            )
        h4_stress_rows = _read_csv(archive, "output/h4/integration_point_stresses.csv")
        _plot_convergence(output_dir / "torsion_mesh_convergence.png", levels)
        _plot_ip_stress(output_dir / "torsion_integration_point_stress_h4.png", h4_stress_rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output-dir", type=Path, default=ARTIFACT_DIR)
    args = parser.parse_args()
    build(args.archive, args.contract, args.output_dir)
    print(f"Prepared site assets in {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
