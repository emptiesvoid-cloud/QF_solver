"""CalculiX S8R correlation for a curved MITC4 laminate panel."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from math import cos, radians, sin
from pathlib import Path

import numpy as np

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_composite import parse_original_frd_displacement
from solveur.verification.composite_curved_assembly import (
    _cylindrical_panel,
    _edge_weights_3d,
    _nodes_at_x,
)
from solveur.verification.composite_structural import _laminate_definition
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class CurvedS8RMesh:
    """Quadratic cylindrical shell mesh and controlled boundary metadata."""

    nodes: np.ndarray
    elements: tuple[tuple[int, ...], ...]
    fixed_nodes: tuple[int, ...]
    tip_nodes: tuple[int, ...]
    tip_weights: np.ndarray
    corner_quads: np.ndarray


class CalculixCurvedCompositeCorrelation:
    """Compare projected-axis MITC4 with CalculiX S8R COMPOSITE."""

    study_id = "VNV-COMP-CURVED-CALCULIX-S8R-007"
    meshes = ((8, 4), (16, 8), (24, 12))

    def __init__(
        self,
        output_dir: str | Path,
        *,
        image: str = "qf-solver/calculix-nafems13h:2.20",
        layup: tuple[float, ...] = (0.0, 90.0, 90.0, 0.0),
    ):
        self.output_dir = Path(output_dir).resolve()
        self.image = image
        self.layup = tuple(float(angle) for angle in layup)
        if not self.layup:
            raise ValueError("Curved composite correlation requires at least one ply.")

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_mesh(nx, ny) for nx, ny in self.meshes]
        checks = [
            _upper("fine_displacement_vector_difference", rows[-1]["vector_difference"], 0.05),
            _upper("fine_uz_difference", rows[-1]["uz_difference"], 0.05),
            _upper("maximum_displacement_vector_difference", max(row["vector_difference"] for row in rows), 0.10),
            _upper("qf_final_mesh_increment", _last_increment(rows, "qf_uz"), 0.03),
            _upper("calculix_final_mesh_increment", _last_increment(rows, "calculix_uz"), 0.03),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if passed else "WARNING",
            "maturity": "experimental",
            "external_solver": {
                "name": "CalculiX",
                "version": "2.20",
                "image": self.image,
                "element": "S8R COMPOSITE",
            },
            "qf_element": "MITC4 shell_laminate with projected reference_direction",
            "layup_deg": list(self.layup),
            "comparison_basis": (
                f"Same cylindrical mid-surface, layup {list(self.layup)}, "
                "global axial reference direction, clamp, edge traction and "
                "transverse edge load."
            ),
            "qualified_orientation_scope": (
                "Material reference direction parallel to the cylinder generatrix."
            ),
            "open_anomaly": {
                "id": "ANOM-COMP-CURVED-ORIENTATION-001",
                "status": "OPEN",
                "description": (
                    "A non-axial projected global reference direction on the curved "
                    "surface is not externally correlated. The exploratory "
                    "[0/+45/-45/90] case produced a large QF/CalculiX response gap "
                    "and must not be used as qualification evidence."
                ),
            },
            "rows": rows,
            "checks": checks,
            "limitations": [
                "MITC4 is linear and S8R is quadratic; this is a cross-code convergence study.",
                "The comparison covers weighted edge displacements, not ply stresses.",
                "CalculiX expands composite shells internally through the thickness.",
                "Non-axial projected material axes remain outside the accepted scope.",
                "No damage, delamination or interlaminar-stress claim is made.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        self._plot_deformation(rows[-1])
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_mesh(self, nx: int, ny: int) -> dict[str, object]:
        qf = _solve_qf_curved(nx, ny, self.layup)
        mesh = build_curved_s8r_mesh(nx, ny)
        stem = f"curved_composite_s8r_{nx}x{ny}"
        write_curved_calculix_input(
            self.output_dir / f"{stem}.inp", mesh, layup=self.layup
        )
        self._execute(stem)
        displacement = parse_original_frd_displacement(
            self.output_dir / f"{stem}.frd",
            len(mesh.nodes),
        )
        tip_indices = np.asarray(mesh.tip_nodes, dtype=int) - 1
        calculix_ux = float(mesh.tip_weights @ displacement[tip_indices, 0])
        calculix_uz = float(mesh.tip_weights @ displacement[tip_indices, 2])
        qf_vector = np.asarray([qf["ux"], qf["uz"]])
        calculix_vector = np.asarray([calculix_ux, calculix_uz])
        return {
            "nx": nx,
            "ny": ny,
            "qf_elements": nx * ny,
            "calculix_elements": nx * ny,
            "qf_ux": float(qf["ux"]),
            "qf_uz": float(qf["uz"]),
            "calculix_ux": calculix_ux,
            "calculix_uz": calculix_uz,
            "ux_difference": _relative(float(qf["ux"]), calculix_ux),
            "uz_difference": _relative(float(qf["uz"]), calculix_uz),
            "vector_difference": float(
                np.linalg.norm(qf_vector - calculix_vector)
                / max(np.linalg.norm(calculix_vector), np.finfo(float).tiny)
            ),
            "calculix_nodes": mesh.nodes.tolist() if (nx, ny) == self.meshes[-1] else [],
            "calculix_quads": mesh.corner_quads.tolist() if (nx, ny) == self.meshes[-1] else [],
            "calculix_displacement": displacement.tolist() if (nx, ny) == self.meshes[-1] else [],
        }

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
            raise RuntimeError(f"CalculiX curved composite run failed for {stem}:\n{tail}")

    def _plot(self, rows: list[dict[str, object]]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        elements = [int(row["qf_elements"]) for row in rows]
        figure, axes = plt.subplots(1, 2, figsize=(10.6, 4.5))
        axes[0].semilogx(elements, [abs(float(row["qf_uz"])) for row in rows], "o-", label="QF MITC4")
        axes[0].semilogx(
            elements,
            [abs(float(row["calculix_uz"])) for row in rows],
            "s-",
            label="CalculiX S8R",
        )
        axes[0].set(xlabel="Elements", ylabel="|UZ pondere| [m]", title="Convergence")
        axes[0].grid(True, which="both", alpha=0.25)
        axes[0].legend()
        axes[1].loglog(
            elements,
            [float(row["vector_difference"]) for row in rows],
            "^-",
            color="#2a9d3f",
        )
        axes[1].set(xlabel="Elements", ylabel="Ecart vectoriel relatif", title="QF / CalculiX")
        axes[1].grid(True, which="both", alpha=0.25)
        figure.tight_layout()
        figure.savefig(self.output_dir / "curved_composite_calculix_correlation.png", dpi=180)
        plt.close(figure)

    def _plot_deformation(self, fine: dict[str, object]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        nodes = np.asarray(fine["calculix_nodes"], dtype=float)
        quads = np.asarray(fine["calculix_quads"], dtype=int) - 1
        displacement = np.asarray(fine["calculix_displacement"], dtype=float)
        scale = 0.15 / max(float(np.max(np.linalg.norm(displacement, axis=1))), 1.0e-30)
        deformed = nodes + scale * displacement
        figure = plt.figure(figsize=(8.4, 4.8))
        axis = figure.add_subplot(111, projection="3d")
        for quad in quads:
            loop = np.append(quad, quad[0])
            axis.plot(nodes[loop, 0], nodes[loop, 1], nodes[loop, 2], color="#999999", linewidth=0.3)
            axis.plot(
                deformed[loop, 0],
                deformed[loop, 1],
                deformed[loop, 2],
                color="#bc4749",
                linewidth=0.55,
            )
        axis.set_title(f"CalculiX S8R composite, amplification x{scale:.1f}")
        axis.set(xlabel="X", ylabel="Y", zlabel="Z")
        axis.set_box_aspect((1.0, 0.6, 0.35))
        axis.view_init(elev=24.0, azim=-58.0)
        figure.tight_layout()
        figure.savefig(self.output_dir / "curved_composite_calculix_deformation.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "| Maillage | UZ QF | UZ CalculiX | Ecart UZ | Ecart vectoriel UX/UZ |",
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
                "Les deux solveurs utilisent la meme surface moyenne cylindrique, le",
                "meme empilement symetrique [0/90/90/0], la meme direction materiau",
                "axiale projetee et les memes",
                "resultantes de bord. Les interpolations MITC4 et S8R restent differentes.",
                "",
                "## Limite d'acceptation",
                "",
                "Cette correlation accepte uniquement une direction de reference parallele",
                "a la generatrice du cylindre. Le cas exploratoire avec direction globale",
                "oblique et empilement non symetrique reste ouvert sous",
                "`ANOM-COMP-CURVED-ORIENTATION-001`; il ne constitue pas une preuve",
                "de qualification.",
                "",
                "![Correlation](curved_composite_calculix_correlation.png)",
                "",
                "![Deformee CalculiX](curved_composite_calculix_deformation.png)",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def build_curved_s8r_mesh(nx: int, ny: int, *, faceted: bool = False) -> CurvedS8RMesh:
    if nx <= 0 or ny <= 0:
        raise ValueError("Curved S8R mesh dimensions must be positive.")
    length, radius, opening = 1.0, 0.5, radians(60.0)
    node_ids: dict[tuple[int, int], int] = {}
    coordinates: list[tuple[float, float, float]] = []
    for j in range(2 * ny + 1):
        theta = -0.5 * opening + opening * j / (2 * ny)
        for i in range(2 * nx + 1):
            if i % 2 and j % 2:
                continue
            node_ids[(i, j)] = len(coordinates) + 1
            coordinates.append(
                (
                    length * i / (2 * nx),
                    radius * sin(theta),
                    radius * (cos(theta) - cos(0.5 * opening)),
                )
            )
    if faceted:
        for j in range(0, 2 * ny + 1, 2):
            for i in range(1, 2 * nx, 2):
                left = np.asarray(coordinates[node_ids[(i - 1, j)] - 1])
                right = np.asarray(coordinates[node_ids[(i + 1, j)] - 1])
                coordinates[node_ids[(i, j)] - 1] = tuple(0.5 * (left + right))
        for j in range(1, 2 * ny, 2):
            for i in range(0, 2 * nx + 1, 2):
                lower = np.asarray(coordinates[node_ids[(i, j - 1)] - 1])
                upper = np.asarray(coordinates[node_ids[(i, j + 1)] - 1])
                coordinates[node_ids[(i, j)] - 1] = tuple(0.5 * (lower + upper))
    elements = []
    corner_quads = []
    for j in range(ny):
        for i in range(nx):
            corners = (
                node_ids[(2 * i, 2 * j)],
                node_ids[(2 * i + 2, 2 * j)],
                node_ids[(2 * i + 2, 2 * j + 2)],
                node_ids[(2 * i, 2 * j + 2)],
            )
            corner_quads.append(corners)
            elements.append(
                corners
                + (
                    node_ids[(2 * i + 1, 2 * j)],
                    node_ids[(2 * i + 2, 2 * j + 1)],
                    node_ids[(2 * i + 1, 2 * j + 2)],
                    node_ids[(2 * i, 2 * j + 1)],
                )
            )
    fixed = tuple(node_ids[(0, j)] for j in range(2 * ny + 1))
    tip = tuple(node_ids[(2 * nx, j)] for j in range(2 * ny + 1))
    weights = _quadratic_edge_weights(ny)
    return CurvedS8RMesh(
        np.asarray(coordinates),
        tuple(elements),
        fixed,
        tip,
        weights,
        np.asarray(corner_quads, dtype=int),
    )


def write_curved_calculix_input(
    path: str | Path,
    mesh: CurvedS8RMesh,
    *,
    layup: tuple[float, ...] = (0.0, 90.0, 90.0, 0.0),
) -> Path:
    """Write a CalculiX composite-shell deck for the requested layup."""
    if not layup:
        raise ValueError("layup must contain at least one ply")
    target = Path(path)
    lines = ["*HEADING", "QF_solver curved composite correlation", "*NODE"]
    lines.extend(
        f"{index},{point[0]:.14g},{point[1]:.14g},{point[2]:.14g}"
        for index, point in enumerate(mesh.nodes, start=1)
    )
    lines.append("*ELEMENT,TYPE=S8R,ELSET=EALL")
    lines.extend(
        f"{index}," + ",".join(str(node) for node in element)
        for index, element in enumerate(mesh.elements, start=1)
    )
    lines.extend(["*NSET,NSET=FIXED", *_csv_lines(mesh.fixed_nodes)])
    orientations = {}
    for angle in layup:
        name = f"P{angle:g}".replace("-", "M").replace(".", "_")
        orientations.setdefault(name, angle)
    for name, angle in orientations.items():
        lines.extend(
            [
                f"*ORIENTATION,NAME=ORI{name}",
                "1.,0.,0.,0.,1.,0.",
                f"3,{angle:.1f}",
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
            "*SHELL SECTION,ELSET=EALL,COMPOSITE",
        ]
    )
    ply_thickness = 8.0e-3 / len(layup)
    for angle in layup:
        name = f"P{angle:g}".replace("-", "M").replace(".", "_")
        lines.append(f"{ply_thickness:.12g},,LAMINA,ORI{name}")
    lines.extend(
        [
            "*BOUNDARY",
            "FIXED,1,6",
            "*STEP",
            "*STATIC",
            "*CLOAD",
        ]
    )
    for node, weight in zip(mesh.tip_nodes, mesh.tip_weights, strict=True):
        lines.append(f"{node},1,{1000.0 * weight:.16g}")
        lines.append(f"{node},3,{-20.0 * weight:.16g}")
    lines.extend(["*NODE FILE,OUTPUT=2D", "U", "*END STEP"])
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def _solve_qf_curved(nx: int, ny: int, layup: tuple[float, ...]) -> dict[str, float]:
    mesh = _cylindrical_panel(nx, ny)
    material = _laminate_definition(list(layup), 8.0e-3)
    material["reference_direction"] = [1.0, 0.0, 0.0]
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


def _quadratic_edge_weights(ny: int) -> np.ndarray:
    weights = np.zeros(2 * ny + 1)
    for index in range(ny):
        weights[2 * index] += 1.0 / 6.0
        weights[2 * index + 1] += 4.0 / 6.0
        weights[2 * index + 2] += 1.0 / 6.0
    return weights / np.sum(weights)


def _weighted_qf_displacement(
    result: object,
    nodes: list[int],
    weights: np.ndarray,
    dof: str,
) -> float:
    return float(
        sum(
            weights[index] * result.displacements[result.dofs.index(node, dof)]
            for index, node in enumerate(nodes)
        )
    )


def _csv_lines(values: tuple[int, ...]) -> list[str]:
    return [
        ",".join(str(value) for value in values[index : index + 16])
        for index in range(0, len(values), 16)
    ]


def _last_increment(rows: list[dict[str, object]], key: str) -> float:
    return _relative(float(rows[-1][key]), float(rows[-2][key]))


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _upper(identifier: str, value: object, limit: float) -> dict[str, object]:
    measured = float(value)
    return {
        "id": identifier,
        "value": measured,
        "limit": limit,
        "status": "PASS" if measured <= limit else "FAIL",
    }
