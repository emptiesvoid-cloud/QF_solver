"""CalculiX S6 correlation for a curved MITC3+ projected-axis laminate."""

from __future__ import annotations

from solveur.paths import project_root

import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import check_mesh, solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_composite import parse_original_frd_displacement
from solveur.verification.mitc3_models import LAMINATE_MATERIAL
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC3-LAMINATE-CURVED-PROJECTED-CALCULIX-S6-024"
CALCULIX_IMAGE = "qf-solver/calculix-nafems13h:2.20"
REFERENCE_DIRECTION = np.asarray([0.7, 1.0, 0.2], dtype=float)
LAYUP = (0.0, 90.0, 90.0, 0.0)


@dataclass(frozen=True)
class CurvedS6Mesh:
    """Quadratic triangle mesh and boundary data for the external solver."""

    nodes: np.ndarray
    elements: tuple[tuple[int, ...], ...]
    triangles: np.ndarray
    fixed_nodes: tuple[int, ...]
    tip_nodes: tuple[int, ...]
    tip_weights: np.ndarray
    orientations: tuple[np.ndarray, ...]


class CalculixMitc3CurvedCompositeCorrelation:
    """Compare MITC3+ faceted triangles with CalculiX S6 on a curved laminate."""

    study_id = STUDY_ID
    meshes = (
        (8, 4),
        (16, 8),
        (24, 12),
        (32, 16),
        (48, 24),
        (64, 32),
        (80, 40),
        (96, 48),
        (128, 64),
    )
    vector_limit = 0.10
    fine_vector_limit = 0.05
    final_increment_limit = 0.03
    # acos converts a near-unit dot product to degrees; this bound covers
    # floating-point round-off without hiding a geometric orientation error.
    orientation_limit_deg = 1.0e-5

    def __init__(
        self,
        output_dir: str | Path,
        *,
        image: str = CALCULIX_IMAGE,
        load_case: str = "mixed",
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.image = image
        self.load_case = str(load_case)
        if self.load_case not in {"mixed", "transverse", "axial"}:
            raise ValueError(f"Unsupported curved MITC3 load case: {self.load_case}")

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_mesh(nx, ny) for nx, ny in self.meshes]
        fine = rows[-1]
        refined_rows = rows[-2:]
        checks = [
            _check("fine_displacement_vector_difference", float(fine["vector_difference"]), self.fine_vector_limit),
            _check(
                "refined_displacement_vector_difference",
                max(float(row["vector_difference"]) for row in refined_rows),
                self.vector_limit,
            ),
            _check("orientation_projection_reproduction_deg", max(float(row["orientation_error_deg"]) for row in rows), self.orientation_limit_deg),
            _check("qf_free_residual", max(float(row["qf_free_residual"]) for row in rows), 1.0e-8),
        ]
        if len(rows) >= 2:
            checks.extend(
                (
                    _check("qf_final_mesh_increment", _last_increment(rows, "qf_uz"), self.final_increment_limit),
                    _check("calculix_final_mesh_increment", _last_increment(rows, "calculix_uz"), self.final_increment_limit),
                )
            )
        else:
            checks.extend(
                (
                    {"id": "qf_final_mesh_increment", "value": None, "limit": self.final_increment_limit, "status": "NOT_ASSESSED"},
                    {"id": "calculix_final_mesh_increment", "value": None, "limit": self.final_increment_limit, "status": "NOT_ASSESSED"},
                )
            )
        passed = all(item["status"] == "PASS" for item in checks)
        summary: dict[str, Any] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if passed else "WARNING",
            "maturity": "verified_development_external_correlation" if passed else "experimental",
            "external_solver": {"name": "CalculiX", "version": "2.20", "image": self.image, "element": "S6 COMPOSITE"},
            "qf_element": "MITC3+ shell_laminate",
            "load_case": self.load_case,
            "geometry": {"kind": "cylindrical_panel", "length_m": 1.0, "radius_m": 0.5, "opening_deg": 60.0},
            "layup_deg": list(LAYUP),
            "reference_direction_global": REFERENCE_DIRECTION.tolist(),
            "orientation_rule": "Project the global reference direction into each triangular facet, normalize it, and add its local angle to each ply angle.",
            "comparison_basis": {
                "same_corner_mesh": True,
                "same_boundary_nodes": True,
                "same_resultants": True,
                "observable": "weighted right-edge UX and UZ, plus mesh and orientation convergence",
                "external_geometry": "quadratic S6 midside nodes are the straight-edge midpoints of the same faceted corner triangles as QF MITC3+",
            },
            "rows": rows,
            "coarse_mesh_vector_difference_max": max(float(row["vector_difference"]) for row in rows[:-2])
            if len(rows) > 2
            else None,
            "checks": checks,
            "limitations": [
                "MITC3+ and CalculiX S6 are different shell formulations and geometrical interpolation orders.",
                "The external comparison covers global displacements, not ply stresses or interlaminar quantities.",
                "Both solvers use the same faceted geometry; the S6 midside nodes are straight-edge midpoints.",
                "Damage, delamination, rupture, nonlinear dynamics and experimental calibration are excluded.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot_convergence(rows)
        self._plot_deformation(rows[-1])
        self._plot_orientation(rows[-1])
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        self._publish_reference()
        return summary

    def _run_mesh(self, nx: int, ny: int) -> dict[str, Any]:
        model, mesh = _qf_model(nx, ny, load_case=self.load_case)
        mesh_report = check_mesh(model)
        qf = solve_model(model, enforce_policy=False)
        right = list(mesh.tip_nodes)
        qf_ux = _weighted_displacement(qf, right, mesh.tip_weights, "UX")
        qf_uz = _weighted_displacement(qf, right, mesh.tip_weights, "UZ")
        stem = f"mitc3_curved_composite_s6_{nx}x{ny}"
        write_s6_input(self.output_dir / f"{stem}.inp", mesh, load_case=self.load_case)
        self._execute(stem)
        displacement = parse_original_frd_displacement(self.output_dir / f"{stem}.frd", len(mesh.nodes))
        tip_indices = np.asarray(mesh.tip_nodes, dtype=int)
        calculix_ux = float(mesh.tip_weights @ displacement[tip_indices, 0])
        calculix_uz = float(mesh.tip_weights @ displacement[tip_indices, 2])
        qf_vector = np.asarray([qf_ux, qf_uz], dtype=float)
        calculix_vector = np.asarray([calculix_ux, calculix_uz], dtype=float)
        return {
            "nx": nx,
            "ny": ny,
            "mitc3_elements": int(len(mesh.triangles)),
            "s6_elements": int(len(mesh.elements)),
            "qf_ux": qf_ux,
            "qf_uz": qf_uz,
            "calculix_ux": calculix_ux,
            "calculix_uz": calculix_uz,
            "ux_difference": _relative(qf_ux, calculix_ux),
            "uz_difference": _relative(qf_uz, calculix_uz),
            "vector_difference": float(np.linalg.norm(qf_vector - calculix_vector) / max(np.linalg.norm(calculix_vector), 1.0e-30)),
            "orientation_offset_min_deg": float(min(_facet_angle(mesh, triangle) for triangle in mesh.triangles)),
            "orientation_offset_max_deg": float(max(_facet_angle(mesh, triangle) for triangle in mesh.triangles)),
            "orientation_error_deg": max(
                _orientation_error_deg(mesh, triangle, mesh.orientations[index])
                for index, triangle in enumerate(mesh.triangles)
            ),
            "qf_mesh_status": mesh_report.status,
            "qf_free_residual": float(qf.audit.equilibrium["free_relative_residual"]),
            "calculix_nodes": mesh.nodes.tolist() if (nx, ny) == self.meshes[-1] else [],
            "calculix_elements": [list(element) for element in mesh.elements] if (nx, ny) == self.meshes[-1] else [],
            "calculix_displacement": displacement.tolist() if (nx, ny) == self.meshes[-1] else [],
        }

    def _execute(self, stem: str) -> None:
        completed = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{self.output_dir}:/work", "-w", "/work", self.image, stem],
            capture_output=True,
            text=True,
            timeout=900,
            check=False,
        )
        (self.output_dir / f"{stem}.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
        if completed.returncode != 0:
            tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-60:])
            raise RuntimeError(f"CalculiX MITC3 curved correlation failed for {stem}:\n{tail}")

    def _plot_convergence(self, rows: list[dict[str, Any]]) -> None:
        elements = [int(row["mitc3_elements"]) for row in rows]
        figure, axes = plt.subplots(1, 2, figsize=(10.6, 4.4))
        axes[0].semilogx(elements, [abs(float(row["qf_uz"])) for row in rows], "o-", label="QF_solver MITC3+")
        axes[0].semilogx(elements, [abs(float(row["calculix_uz"])) for row in rows], "s--", label="CalculiX S6")
        axes[0].set(xlabel="Elements MITC3+", ylabel="|UZ bord droit| [m]", title="Convergence courbe")
        axes[0].grid(True, which="both", alpha=0.25)
        axes[0].legend(fontsize=8)
        axes[1].loglog(elements, [100.0 * float(row["vector_difference"]) for row in rows], "^-", color="#009E73")
        axes[1].axhline(5.0, color="#D55E00", linestyle="--", label="seuil fin 5 %")
        axes[1].set(xlabel="Elements MITC3+", ylabel="Ecart UX/UZ [%]", title="Correlation globale")
        axes[1].grid(True, which="both", alpha=0.25)
        axes[1].legend(fontsize=8)
        figure.tight_layout()
        figure.savefig(self.output_dir / "mitc3_curved_composite_calculix_correlation.png", dpi=180)
        plt.close(figure)

    def _plot_deformation(self, fine: dict[str, Any]) -> None:
        nodes = np.asarray(fine["calculix_nodes"], dtype=float)
        elements = np.asarray(fine["calculix_elements"], dtype=int) - 1
        displacement = np.asarray(fine["calculix_displacement"], dtype=float)
        scale = 0.15 / max(float(np.max(np.linalg.norm(displacement, axis=1))), 1.0e-30)
        deformed = nodes + scale * displacement
        figure = plt.figure(figsize=(9.0, 5.0))
        axis = figure.add_subplot(111, projection="3d")
        for element in elements:
            loop = np.append(element[:3], element[0])
            axis.plot(nodes[loop, 0], nodes[loop, 1], nodes[loop, 2], color="#777777", linewidth=0.3)
            axis.plot(deformed[loop, 0], deformed[loop, 1], deformed[loop, 2], color="#D55E00", linewidth=0.6)
        axis.set_title(f"MITC3+ curved laminate / CalculiX S6, amplification x{scale:.1f}")
        axis.set(xlabel="X", ylabel="Y", zlabel="Z")
        axis.view_init(elev=24.0, azim=-58.0)
        figure.tight_layout()
        figure.savefig(self.output_dir / "mitc3_curved_composite_deformation.png", dpi=180)
        plt.close(figure)

    def _plot_orientation(self, fine: dict[str, Any]) -> None:
        values = [float(row["orientation_offset_min_deg"]) for row in [fine]]
        maximum = [float(row["orientation_offset_max_deg"]) for row in [fine]]
        figure, axis = plt.subplots(figsize=(7.2, 4.0))
        axis.bar(["min", "max"], [values[0], maximum[0]], color=["#0072B2", "#D55E00"])
        axis.set(ylabel="Angle projete [deg]", title="Orientation locale projetee - maillage fin")
        axis.grid(axis="y", alpha=0.25)
        figure.tight_layout()
        figure.savefig(self.output_dir / "mitc3_curved_composite_projected_orientation.png", dpi=180)
        plt.close(figure)

    def _publish_reference(self) -> None:
        root = project_root()
        reference = root / "qualification" / "vnv" / "external" / "calculix_mitc3_curved_composite" / "reference"
        reference.mkdir(parents=True, exist_ok=True)
        for name in (
            "summary.json",
            "report.md",
            "vnv_manifest.json",
            "mitc3_curved_composite_calculix_correlation.png",
            "mitc3_curved_composite_deformation.png",
            "mitc3_curved_composite_projected_orientation.png",
        ):
            shutil.copy2(self.output_dir / name, reference / name)


def _qf_model(nx: int, ny: int, *, load_case: str = "mixed") -> tuple[FiniteElementModel, CurvedS6Mesh]:
    if load_case not in {"mixed", "transverse", "axial"}:
        raise ValueError(f"Unsupported curved MITC3 load case: {load_case}")
    mesh = build_curved_s6_mesh(nx, ny)
    material = {
        "type": "shell_laminate",
        "reference_direction": REFERENCE_DIRECTION.tolist(),
        "drilling_scale": 1.0e-4,
        "shear_factor": 5.0 / 6.0,
        "plies": [
            {
                "name": f"ply-{index + 1}",
                **LAMINATE_MATERIAL,
                "thickness": 2.0e-3,
                "angle_deg": angle,
            }
            for index, angle in enumerate(LAYUP)
        ],
    }
    loads = []
    axial_force = 1000.0 if load_case in {"mixed", "axial"} else 0.0
    transverse_force = -20.0 if load_case == "mixed" else (-1000.0 if load_case == "transverse" else 0.0)
    for index, node in enumerate(mesh.tip_nodes):
        loads.extend(
            (
                {"node": node, "dof": "UX", "value": axial_force * float(mesh.tip_weights[index])},
                {"node": node, "dof": "UZ", "value": transverse_force * float(mesh.tip_weights[index])},
            )
        )
    model = FiniteElementModel.from_raw(
        nodes=mesh.nodes[: len(mesh.triangles) * 0 + _corner_count(nx, ny)].tolist(),
        elements=[{"type": "MITC3", "nodes": triangle.tolist(), "material": "laminate"} for triangle in mesh.triangles],
        materials={"laminate": material},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in mesh.fixed_nodes],
        loads=loads,
        verification_profile="engineering",
    )
    return model, mesh


def build_curved_s6_mesh(nx: int, ny: int) -> CurvedS6Mesh:
    if nx <= 0 or ny <= 0:
        raise ValueError("Curved MITC3 mesh dimensions must be positive.")
    corners = [_cylinder_point(i / nx, -0.5 + j / ny) for i in range(nx + 1) for j in range(ny + 1)]
    corner_array = np.asarray(corners, dtype=float)
    triangles = []
    for i in range(nx):
        for j in range(ny):
            a, b = _corner_id(i, j, ny), _corner_id(i + 1, j, ny)
            c, d = _corner_id(i + 1, j + 1, ny), _corner_id(i, j + 1, ny)
            triangles.extend(((a, b, c), (a, c, d)))
    edge_nodes: dict[tuple[int, int], int] = {}
    coordinates = [tuple(point) for point in corner_array]

    def midpoint(first: int, second: int) -> int:
        key = (min(first, second), max(first, second))
        if key not in edge_nodes:
            edge_nodes[key] = len(coordinates)
            # Keep the S6 geometry on the same straight faceted edges as QF.
            # This isolates the shell formulation from the quadratic-geometry effect.
            coordinates.append(tuple(0.5 * (corner_array[first] + corner_array[second])))
        return edge_nodes[key]

    elements = []
    orientations = []
    for triangle in triangles:
        first, second, third = (int(value) for value in triangle)
        elements.append((first + 1, second + 1, third + 1, midpoint(first, second) + 1, midpoint(second, third) + 1, midpoint(third, first) + 1))
        normal = _facet_normal(corner_array[list(triangle)])
        projected = REFERENCE_DIRECTION - np.dot(REFERENCE_DIRECTION, normal) * normal
        projected /= np.linalg.norm(projected)
        orientations.append(np.column_stack((projected, np.cross(normal, projected), normal)))
    all_nodes = np.asarray(coordinates, dtype=float)
    fixed = tuple(_corner_id(0, j, ny) for j in range(ny + 1))
    tip = tuple(_corner_id(nx, j, ny) for j in range(ny + 1))
    weights = _edge_weights(all_nodes, tip)
    return CurvedS6Mesh(all_nodes, tuple(elements), np.asarray(triangles, dtype=int), fixed, tip, weights, tuple(orientations))


def write_s6_input(path: str | Path, mesh: CurvedS6Mesh, *, load_case: str = "mixed") -> Path:
    if load_case not in {"mixed", "transverse", "axial"}:
        raise ValueError(f"Unsupported curved MITC3 load case: {load_case}")
    target = Path(path)
    lines = ["*HEADING", "QF_solver MITC3 curved projected laminate", "*NODE"]
    lines.extend(f"{index},{point[0]:.14g},{point[1]:.14g},{point[2]:.14g}" for index, point in enumerate(mesh.nodes, start=1))
    lines.append("*ELEMENT,TYPE=S6,ELSET=EALL")
    lines.extend(f"{index}," + ",".join(str(node) for node in element) for index, element in enumerate(mesh.elements, start=1))
    lines.extend(
        [
            "*NSET,NSET=FIXED",
            *_csv(tuple(node + 1 for node in mesh.fixed_nodes)),
            "*NSET,NSET=TIP",
            *_csv(tuple(node + 1 for node in mesh.tip_nodes)),
        ]
    )
    material = LAMINATE_MATERIAL
    lines.extend(
        [
            "*MATERIAL,NAME=LAMINA",
            "*ELASTIC,TYPE=ENGINEERING CONSTANTS",
            f"{material['E1']:.16g},{material['E2']:.16g},{material['E2']:.16g},{material['nu12']:.16g},{material['nu12']:.16g},{material['nu12']:.16g},{material['G12']:.16g},{material['G13']:.16g}",
            f"{material['G23']:.16g}",
            "*DENSITY",
            f"{material['density']:.16g}",
        ]
    )
    for index, orientation in enumerate(mesh.orientations, start=1):
        e1, e2, normal = orientation.T
        base = ",".join(f"{value:.16g}" for value in (*e1, *normal))
        for ply, angle in enumerate(LAYUP, start=1):
            lines.extend([f"*ORIENTATION,NAME=ORI{index}_{ply}", base, f"3,{angle:.16g}"])
    for index in range(1, len(mesh.elements) + 1):
        lines.extend(
            [
                f"*ELSET,ELSET=E{index}",
                str(index),
                f"*SHELL SECTION,ELSET=E{index},COMPOSITE",
                *[f"0.002,,LAMINA,ORI{index}_{ply}" for ply in range(1, len(LAYUP) + 1)],
            ]
        )
    lines.extend(["*BOUNDARY", "FIXED,1,6", "*STEP", "*STATIC", "*CLOAD"])
    axial_force = 1000.0 if load_case in {"mixed", "axial"} else 0.0
    transverse_force = -20.0 if load_case == "mixed" else (-1000.0 if load_case == "transverse" else 0.0)
    lines.extend(
        f"{node + 1},1,{axial_force * float(weight):.16g}\n{node + 1},3,{transverse_force * float(weight):.16g}"
        for node, weight in zip(mesh.tip_nodes, mesh.tip_weights, strict=True)
    )
    lines.extend(["*NODE FILE,OUTPUT=2D", "U", "*END STEP"])
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def _cylinder_point(x_ratio: float, theta_ratio: float) -> tuple[float, float, float]:
    radius = 0.5
    theta = math.radians(60.0) * theta_ratio
    return (float(x_ratio), radius * math.sin(theta), radius * (math.cos(theta) - math.cos(math.radians(30.0))))


def _corner_id(i: int, j: int, ny: int) -> int:
    return i * (ny + 1) + j


def _corner_count(nx: int, ny: int) -> int:
    return (nx + 1) * (ny + 1)


def _facet_normal(points: np.ndarray) -> np.ndarray:
    vector = np.cross(points[1] - points[0], points[2] - points[0])
    return vector / np.linalg.norm(vector)


def _facet_angle(mesh: CurvedS6Mesh, triangle: np.ndarray) -> float:
    normal = _facet_normal(mesh.nodes[triangle])
    projected = REFERENCE_DIRECTION - np.dot(REFERENCE_DIRECTION, normal) * normal
    local_e1 = mesh.nodes[int(triangle[1])] - mesh.nodes[int(triangle[0])]
    local_e1 -= np.dot(local_e1, normal) * normal
    local_e1 /= np.linalg.norm(local_e1)
    local_e2 = np.cross(normal, local_e1)
    projected /= np.linalg.norm(projected)
    return math.degrees(math.atan2(float(np.dot(projected, local_e2)), float(np.dot(projected, local_e1))))


def _orientation_error_deg(mesh: CurvedS6Mesh, triangle: np.ndarray, frame: np.ndarray) -> float:
    """Compare a stored facet axis with an independently recomputed projection."""
    normal = _facet_normal(mesh.nodes[triangle])
    projected = REFERENCE_DIRECTION - np.dot(REFERENCE_DIRECTION, normal) * normal
    projected /= np.linalg.norm(projected)
    cosine = float(np.clip(np.dot(projected, frame[:, 0]), -1.0, 1.0))
    return math.degrees(math.acos(cosine))


def _edge_weights(nodes: np.ndarray, edge: tuple[int, ...]) -> np.ndarray:
    order = np.argsort(nodes[list(edge), 1])
    ordered = np.asarray(edge, dtype=int)[order]
    weights = np.zeros(len(edge), dtype=float)
    segments = np.linalg.norm(np.diff(nodes[ordered], axis=0), axis=1)
    weights[:-1] += 0.5 * segments
    weights[1:] += 0.5 * segments
    return weights / np.sum(weights)


def _weighted_displacement(result: object, nodes: list[int], weights: np.ndarray, dof: str) -> float:
    return float(sum(weights[index] * result.displacements[result.dofs.index(node, dof)] for index, node in enumerate(nodes)))


def _last_increment(rows: list[dict[str, Any]], key: str) -> float:
    return _relative(float(rows[-1][key]), float(rows[-2][key]))


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": float(value), "limit": float(limit), "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _csv(values: tuple[int, ...]) -> list[str]:
    return [",".join(str(value) for value in values[index : index + 16]) for index in range(0, len(values), 16)]


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut automatise : **{summary['status']}**.",
        "",
        "MITC3+ et CalculiX S6 utilisent une plaque cylindrique de 60 degres, un empilement [0/90/90/0] et la direction globale [0.7, 1.0, 0.2]. Cette direction est projetee dans chaque facette QF_solver ; CalculiX recoit l'orientation locale correspondante.",
        "",
        "| Maillage | MITC3+ | S6 | UZ QF [m] | UZ CalculiX [m] | Ecart UX/UZ | Angle projete |", 
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary["rows"]:
        lines.append(f"| {row['nx']}x{row['ny']} | {row['mitc3_elements']} | {row['s6_elements']} | {row['qf_uz']:.6e} | {row['calculix_uz']:.6e} | {100.0 * row['vector_difference']:.4f} % | {row['orientation_offset_min_deg']:.3f} / {row['orientation_offset_max_deg']:.3f} deg |")
    lines.extend(
        [
            "",
            "![Correlation courbe MITC3+ / CalculiX](mitc3_curved_composite_calculix_correlation.png)",
            "",
            "![Deformee](mitc3_curved_composite_deformation.png)",
            "",
            "![Orientation projetee](mitc3_curved_composite_projected_orientation.png)",
            "",
            "## Limites",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["limitations"])
    return "\n".join(lines) + "\n"
