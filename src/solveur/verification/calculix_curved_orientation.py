"""CalculiX correlation for intrinsic ply orientations on a curved shell."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from math import cos, pi, sin
from pathlib import Path

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_composite import parse_original_frd_displacement
from solveur.verification.calculix_curved_composite import (
    CurvedS8RMesh,
    _csv_lines,
    _last_increment,
    _relative,
    _upper,
    _weighted_qf_displacement,
    build_curved_s8r_mesh,
)
from solveur.verification.composite_curved_assembly import (
    _cylindrical_panel,
    _edge_weights_3d,
    _nodes_at_x,
)
from solveur.verification.composite_structural import _laminate_definition
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class OrientationDefinition:
    """One CalculiX rectangular orientation attached to a shell row and ply."""

    name: str
    first_axis: np.ndarray
    second_axis: np.ndarray
    normal: np.ndarray


class CalculixCurvedOrientationCorrelation:
    """Compare QF and CalculiX with identical intrinsic tangent ply axes."""

    study_id = "VNV-COMP-CURVED-ORIENTATION-008"
    meshes = ((8, 4), (16, 8), (24, 12), (48, 24), (96, 48))
    angles = (0.0, 45.0, -45.0, 90.0)
    reference_direction = np.array([1.0, 1.0, 0.0])

    def __init__(
        self,
        output_dir: str | Path,
        *,
        image: str = "qf-solver/calculix-nafems13h:2.20",
        meshes: tuple[tuple[int, int], ...] | None = None,
        faceted_geometry: bool = False,
    ):
        self.output_dir = Path(output_dir).resolve()
        self.image = image
        self.mesh_levels = meshes or self.meshes
        self.faceted_geometry = faceted_geometry

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows: list[dict[str, object]] = []
        fine_payload: tuple[CurvedS8RMesh, np.ndarray] | None = None
        for nx, ny in self.mesh_levels:
            row, payload = self._run_mesh(nx, ny)
            rows.append(row)
            fine_payload = payload
        checks = [
            _upper("fine_displacement_vector_difference", rows[-1]["vector_difference"], 0.03),
            _upper("fine_uz_difference", rows[-1]["uz_difference"], 0.03),
            _upper("maximum_displacement_vector_difference", max(row["vector_difference"] for row in rows), 0.15),
            _upper("qf_final_mesh_increment", _last_increment(rows, "qf_uz"), 0.01),
            _upper("calculix_final_mesh_increment", _last_increment(rows, "calculix_uz"), 0.01),
            _upper(
                "coarse_to_fine_difference_reduction",
                float(rows[-1]["vector_difference"]) / float(rows[0]["vector_difference"]),
                0.35,
            ),
            _upper(
                "orientation_orthonormality",
                max(float(row["orientation_error"]) for row in rows),
                1.0e-10,
            ),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if passed else "WARNING",
            "maturity": "experimental",
            "closed_anomaly": "ANOM-COMP-CURVED-ORIENTATION-001" if passed else None,
            "external_solver": {
                "name": "CalculiX",
                "version": "2.20",
                "image": self.image,
                "element": "S8R COMPOSITE",
            },
            "qf_element": "MITC4 shell_laminate",
            "external_geometry": (
                "faceted bilinear surface"
                if self.faceted_geometry
                else "exact cylindrical quadratic surface"
            ),
            "layup": list(self.angles),
            "reference_direction": self.reference_direction.tolist(),
            "orientation_convention": (
                "The global reference direction is projected into each row-centre "
                "tangent plane. Each ply angle is then applied about the shell "
                "normal. CalculiX receives the resulting physical tangent axes "
                "directly, without a subsequent three-dimensional angle rotation."
            ),
            "rows": rows,
            "checks": checks,
            "limitations": [
                "CalculiX orientations are piecewise constant by circumferential row.",
                "MITC4 is linear and faceted; CalculiX S8R is quadratic.",
                "The residual fine-mesh model-form difference is accepted below 3 percent.",
                "The comparison covers weighted edge displacements, not ply stresses.",
                "Damage, delamination and interlaminar stresses remain outside scope.",
            ],
            "recommendations": [
                {
                    "id": "REC-COMP-CURVED-MODELFORM-001",
                    "text": (
                        "Retain a 3 percent cross-element allowance for oblique curved "
                        "laminates until a same-order shell oracle or an analytical "
                        "curved-laminate reference is available."
                    ),
                }
            ],
        }
        if self.faceted_geometry:
            summary["limitations"] = [
                "S8R midside nodes are placed on the same faceted bilinear midsurface as the MITC4 corner mesh.",
                "The comparison remains an independent S8R/MITC4 formulation correlation.",
                "Damage, delamination and interlaminar stresses remain outside scope.",
            ]
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        if fine_payload is not None:
            self._plot_deformation(*fine_payload)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_mesh(
        self,
        nx: int,
        ny: int,
    ) -> tuple[dict[str, object], tuple[CurvedS8RMesh, np.ndarray]]:
        qf = _solve_qf(nx, ny, self.angles, self.reference_direction)
        mesh = build_curved_s8r_mesh(nx, ny, faceted=self.faceted_geometry)
        stem = f"curved_orientation_s8r_{nx}x{ny}"
        orientations = write_tangent_oriented_input(
            self.output_dir / f"{stem}.inp",
            mesh,
            nx=nx,
            ny=ny,
            angles=self.angles,
            reference_direction=self.reference_direction,
        )
        self._execute(stem)
        displacement = parse_original_frd_displacement(
            self.output_dir / f"{stem}.frd",
            len(mesh.nodes),
        )
        tip_indices = np.asarray(mesh.tip_nodes, dtype=int) - 1
        calculix = np.array(
            [
                mesh.tip_weights @ displacement[tip_indices, 0],
                mesh.tip_weights @ displacement[tip_indices, 2],
            ],
            dtype=float,
        )
        qf_vector = np.array([qf["ux"], qf["uz"]], dtype=float)
        row = {
            "nx": nx,
            "ny": ny,
            "elements": nx * ny,
            "qf_ux": float(qf_vector[0]),
            "qf_uz": float(qf_vector[1]),
            "calculix_ux": float(calculix[0]),
            "calculix_uz": float(calculix[1]),
            "ux_difference": _relative(float(qf_vector[0]), float(calculix[0])),
            "uz_difference": _relative(float(qf_vector[1]), float(calculix[1])),
            "vector_difference": float(
                np.linalg.norm(qf_vector - calculix)
                / max(np.linalg.norm(calculix), np.finfo(float).tiny)
            ),
            "orientation_error": _orientation_error(orientations),
        }
        return row, (mesh, displacement)

    def _execute(self, stem: str) -> None:
        completed = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{self.output_dir}:/work",
                "-w",
                "/work",
                self.image,
                stem,
            ],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        (self.output_dir / f"{stem}.log").write_text(
            completed.stdout + completed.stderr,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-50:])
            raise RuntimeError(f"CalculiX curved-orientation run failed for {stem}:\n{tail}")

    def _plot(self, rows: list[dict[str, object]]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        elements = [int(row["elements"]) for row in rows]
        figure, axes = plt.subplots(1, 2, figsize=(10.6, 4.5))
        axes[0].semilogx(elements, [abs(float(row["qf_uz"])) for row in rows], "o-", label="QF MITC4")
        axes[0].semilogx(
            elements,
            [abs(float(row["calculix_uz"])) for row in rows],
            "s-",
            label="CalculiX S8R",
        )
        axes[0].set(xlabel="Elements", ylabel="|UZ pondere| [m]", title="Convergence oblique")
        axes[0].grid(True, which="both", alpha=0.25)
        axes[0].legend()
        axes[1].loglog(
            elements,
            [float(row["vector_difference"]) for row in rows],
            "^-",
            color="#2a9d3f",
        )
        axes[1].axhline(0.03, color="#bc4749", linestyle="--", linewidth=1.0, label="seuil fin")
        axes[1].set(xlabel="Elements", ylabel="Ecart vectoriel relatif", title="QF / CalculiX")
        axes[1].grid(True, which="both", alpha=0.25)
        axes[1].legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "curved_orientation_correlation.png", dpi=180)
        plt.close(figure)

    def _plot_deformation(self, mesh: CurvedS8RMesh, displacement: np.ndarray) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        scale = 0.15 / max(float(np.max(np.linalg.norm(displacement, axis=1))), 1.0e-30)
        deformed = mesh.nodes + scale * displacement
        figure = plt.figure(figsize=(8.4, 4.8))
        axis = figure.add_subplot(111, projection="3d")
        for quad_one_based in mesh.corner_quads:
            quad = quad_one_based - 1
            loop = np.append(quad, quad[0])
            axis.plot(
                mesh.nodes[loop, 0],
                mesh.nodes[loop, 1],
                mesh.nodes[loop, 2],
                color="#999999",
                linewidth=0.25,
            )
            axis.plot(
                deformed[loop, 0],
                deformed[loop, 1],
                deformed[loop, 2],
                color="#bc4749",
                linewidth=0.45,
            )
        axis.set_title(f"CalculiX S8R, axes tangents, amplification x{scale:.1f}")
        axis.set(xlabel="X", ylabel="Y", zlabel="Z")
        axis.set_box_aspect((1.0, 0.6, 0.35))
        axis.view_init(elev=24.0, azim=-58.0)
        figure.tight_layout()
        figure.savefig(self.output_dir / "curved_orientation_deformation.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Empilement `[0/+45/-45/90]`, direction globale `[1,1,0]` projetee",
            "dans chaque plan tangent, puis rotation intrinseque de chaque pli.",
            "",
            "| Maillage | UZ QF | UZ CalculiX | Ecart UZ | Ecart vectoriel |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["rows"]:
            lines.append(
                f"| {row['nx']}x{row['ny']} | {row['qf_uz']:.8e} | "
                f"{row['calculix_uz']:.8e} | {100 * row['uz_difference']:.4f} % | "
                f"{100 * row['vector_difference']:.4f} % |"
            )
        lines.extend(
            [
                "",
                "La definition CalculiX initiale tournait d'abord le repere 3D puis",
                "le projetait sur la coque. Cette operation ne commute pas avec la",
                "rotation intrinseque du pli dans le plan tangent. Le present jeu",
                "construit directement les axes physiques par rangee et par pli.",
                "",
                "Le seuil de `3 %` couvre l'ecart de modele entre une coque MITC4",
                "lineaire facettisee et une coque S8R quadratique. Il ne constitue",
                "pas une tolerance generale sur les resultats composites.",
                "",
                "![Correlation](curved_orientation_correlation.png)",
                "",
                "![Deformee](curved_orientation_deformation.png)",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def tangent_orientations(
    ny: int,
    angles: tuple[float, ...],
    reference_direction: np.ndarray,
) -> tuple[OrientationDefinition, ...]:
    """Build row-wise physical ply axes on the cylindrical midsurface."""
    if ny <= 0:
        raise ValueError("ny must be positive.")
    reference = np.asarray(reference_direction, dtype=float)
    if reference.shape != (3,) or not np.all(np.isfinite(reference)):
        raise ValueError("reference_direction must contain three finite values.")
    reference /= max(float(np.linalg.norm(reference)), np.finfo(float).tiny)
    definitions = []
    opening = pi / 3.0
    for row in range(ny):
        theta = -0.5 * opening + opening * (row + 0.5) / ny
        normal = np.array([0.0, sin(theta), cos(theta)])
        projected = reference - np.dot(reference, normal) * normal
        projected /= np.linalg.norm(projected)
        for ply, angle_deg in enumerate(angles):
            angle = angle_deg * pi / 180.0
            first = cos(angle) * projected + sin(angle) * np.cross(normal, projected)
            first /= np.linalg.norm(first)
            second = np.cross(normal, first)
            second /= np.linalg.norm(second)
            definitions.append(
                OrientationDefinition(
                    name=f"R{row}P{ply}",
                    first_axis=first,
                    second_axis=second,
                    normal=normal,
                )
            )
    return tuple(definitions)


def write_tangent_oriented_input(
    path: str | Path,
    mesh: CurvedS8RMesh,
    *,
    nx: int,
    ny: int,
    angles: tuple[float, ...],
    reference_direction: np.ndarray,
) -> tuple[OrientationDefinition, ...]:
    """Write an S8R deck with intrinsic tangent orientation for every ply."""
    if len(mesh.elements) != nx * ny:
        raise ValueError("Mesh dimensions do not match the S8R connectivity.")
    target = Path(path)
    orientations = tangent_orientations(ny, angles, reference_direction)
    lines = ["*HEADING", "QF_solver intrinsic curved laminate orientation", "*NODE"]
    lines.extend(
        f"{index},{point[0]:.14g},{point[1]:.14g},{point[2]:.14g}"
        for index, point in enumerate(mesh.nodes, start=1)
    )
    lines.append("*ELEMENT,TYPE=S8R,ELSET=EALL")
    lines.extend(
        f"{index}," + ",".join(str(node) for node in element)
        for index, element in enumerate(mesh.elements, start=1)
    )
    for row in range(ny):
        lines.extend(
            [
                f"*ELSET,ELSET=ROW{row}",
                *_csv_lines(tuple(range(row * nx + 1, (row + 1) * nx + 1))),
            ]
        )
    lines.extend(["*NSET,NSET=FIXED", *_csv_lines(mesh.fixed_nodes)])
    for orientation in orientations:
        values = (*orientation.first_axis, *orientation.second_axis)
        lines.extend(
            [
                f"*ORIENTATION,NAME={orientation.name}",
                ",".join(f"{float(value):.9g}" for value in values),
            ]
        )
    lines.extend(
        [
            "*MATERIAL,NAME=LAMINA",
            "*ELASTIC,TYPE=ENGINEERING CONSTANTS",
            "1.35e11,1.0e10,1.0e10,0.3,0.3,0.4,5.0e9,4.5e9",
            "3.8e9",
            "*DENSITY",
            "1600.",
        ]
    )
    for row in range(ny):
        lines.append(f"*SHELL SECTION,ELSET=ROW{row},COMPOSITE")
        lines.extend(
            f"{8.0e-3 / len(angles):.9g},,LAMINA,R{row}P{ply}"
            for ply in range(len(angles))
        )
    lines.extend(["*BOUNDARY", "FIXED,1,6", "*STEP", "*STATIC", "*CLOAD"])
    for node, weight in zip(mesh.tip_nodes, mesh.tip_weights, strict=True):
        lines.append(f"{node},1,{1000.0 * weight:.16g}")
        lines.append(f"{node},3,{-20.0 * weight:.16g}")
    lines.extend(["*NODE FILE,OUTPUT=2D", "U", "*END STEP"])
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return orientations


def _solve_qf(
    nx: int,
    ny: int,
    angles: tuple[float, ...],
    reference_direction: np.ndarray,
) -> dict[str, float]:
    mesh = _cylindrical_panel(nx, ny)
    material = _laminate_definition(list(angles), 8.0e-3)
    material["reference_direction"] = np.asarray(reference_direction, dtype=float).tolist()
    left = _nodes_at_x(mesh, 0.0)
    right = _nodes_at_x(mesh, 1.0)
    weights = _edge_weights_3d(mesh, right)
    loads = []
    for index, node in enumerate(right):
        loads.extend(
            (
                {"node": node, "dof": "UX", "value": 1000.0 * weights[index]},
                {"node": node, "dof": "UZ", "value": -20.0 * weights[index]},
            )
        )
    model = FiniteElementModel.from_raw(
        nodes=mesh.nodes,
        elements=[
            {"type": "MITC4", "nodes": quad, "material": "laminate"}
            for quad in mesh.quads
        ],
        materials={"laminate": material},
        fixed_dofs=[
            {"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
            for node in left
        ],
        loads=loads,
    )
    result = solve_model(model)
    return {
        "ux": _weighted_qf_displacement(result, right, weights, "UX"),
        "uz": _weighted_qf_displacement(result, right, weights, "UZ"),
    }


def _orientation_error(orientations: tuple[OrientationDefinition, ...]) -> float:
    errors = []
    identity = np.eye(3)
    for orientation in orientations:
        frame = np.vstack(
            (orientation.first_axis, orientation.second_axis, orientation.normal)
        )
        errors.append(float(np.linalg.norm(frame @ frame.T - identity)))
        errors.append(abs(float(np.linalg.det(frame)) - 1.0))
    return max(errors, default=0.0)
