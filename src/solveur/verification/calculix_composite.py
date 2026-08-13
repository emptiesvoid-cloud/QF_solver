"""CalculiX S8R correlation for the experimental MITC4 laminate."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from mitc4.mesh import MeshFactory

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.composite_structural import _laminate_definition
from solveur.verification.vnv_manifest import write_vnv_manifest


@dataclass(frozen=True)
class S8RMesh:
    """Structured quadratic shell mesh with CalculiX one-based connectivity."""

    nodes: np.ndarray
    elements: tuple[tuple[int, ...], ...]
    fixed_nodes: tuple[int, ...]
    tip_node: int


class CalculixCompositeCorrelation:
    """Compare MITC4 and CalculiX S8R laminate cantilevers."""

    study_id = "VNV-COMP-CALCULIX-S8R-003"
    meshes = ((8, 2), (16, 4), (32, 8))

    def __init__(
        self,
        output_dir: str | Path,
        *,
        image: str = "qf-solver/calculix-nafems13h:2.20",
    ):
        self.output_dir = Path(output_dir).resolve()
        self.image = image

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_mesh(nx, ny) for nx, ny in self.meshes]
        checks = [
            _upper("fine_tip_displacement_difference", float(rows[-1]["relative_difference"]), 0.02),
            _upper("maximum_tip_displacement_difference", max(float(row["relative_difference"]) for row in rows), 0.05),
        ]
        status = "PASS_EXTERNAL_CORRELATION" if all(row["status"] == "PASS" for row in checks) else "FAIL"
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": status,
            "maturity": "experimental",
            "external_solver": {
                "name": "CalculiX",
                "version": "2.20",
                "image": self.image,
                "element": "S8R COMPOSITE",
            },
            "qf_element": "MITC4 laminate",
            "comparison_basis": "same_geometry_layup_boundary_conditions_and_point_load",
            "same_element": False,
            "rows": rows,
            "checks": checks,
            "limitations": [
                "CalculiX composite shells support S8R/S6, not a four-node MITC4 equivalent.",
                "The comparison is a cross-code convergence correlation, not a same-element identity test.",
                "Only linear static flat symmetric laminates and center-edge displacement are covered.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_mesh(self, nx: int, ny: int) -> dict[str, object]:
        qf_tip = _solve_qf_tip(nx, ny)
        mesh = build_s8r_mesh(nx, ny)
        stem = f"composite_s8r_{nx}x{ny}"
        write_calculix_composite_input(self.output_dir / f"{stem}.inp", mesh)
        self._execute(stem)
        displacement = parse_original_frd_displacement(self.output_dir / f"{stem}.frd", len(mesh.nodes))
        calculix_tip = float(displacement[mesh.tip_node - 1, 2])
        difference = abs(qf_tip - calculix_tip) / max(abs(calculix_tip), np.finfo(float).tiny)
        return {
            "nx": nx,
            "ny": ny,
            "qf_elements": nx * ny,
            "calculix_elements": nx * ny,
            "qf_tip_uz": qf_tip,
            "calculix_tip_uz": calculix_tip,
            "relative_difference": difference,
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
            tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-40:])
            raise RuntimeError(f"CalculiX composite shell failed for {stem}:\n{tail}")

    def _plot(self, rows: list[dict[str, object]]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        elements = [int(row["qf_elements"]) for row in rows]
        qf = [abs(float(row["qf_tip_uz"])) for row in rows]
        calculix = [abs(float(row["calculix_tip_uz"])) for row in rows]
        figure, axes = plt.subplots(1, 2, figsize=(10.6, 4.5))
        axes[0].semilogx(elements, qf, "o-", label="QF_solver MITC4")
        axes[0].semilogx(elements, calculix, "s-", label="CalculiX S8R")
        axes[0].set(xlabel="Nombre d'elements", ylabel="|UZ pointe| [m]", title="Reponse structurelle")
        axes[0].grid(True, which="both", alpha=0.25)
        axes[0].legend()
        axes[1].loglog(
            elements,
            [float(row["relative_difference"]) for row in rows],
            "^-",
            color="#2a9d3f",
        )
        axes[1].set(xlabel="Nombre d'elements", ylabel="Ecart relatif", title="Correlation croisee")
        axes[1].grid(True, which="both", alpha=0.25)
        figure.tight_layout()
        figure.savefig(self.output_dir / "calculix_composite_correlation.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Comparaison de convergence sur meme geometrie, empilement [0/90]s,",
            "encastrement et force ponctuelle. Les interpolations sont differentes:",
            "MITC4 lineaire contre S8R quadratique composite.",
            "",
            "| Maillage | QF MITC4 UZ | CalculiX S8R UZ | Ecart relatif |",
            "| --- | ---: | ---: | ---: |",
        ]
        for row in summary["rows"]:
            lines.append(
                f"| {row['nx']}x{row['ny']} | {row['qf_tip_uz']:.9e} | "
                f"{row['calculix_tip_uz']:.9e} | {row['relative_difference']:.3e} |"
            )
        lines.extend(
            [
                "",
                "Cette correlation ne prouve pas une identite elementaire: CalculiX ne",
                "propose son composite multicouche que pour S8R et S6.",
                "",
                "![Correlation CalculiX composite](calculix_composite_correlation.png)",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def build_s8r_mesh(nx: int, ny: int, *, length: float = 1.0, width: float = 0.1) -> S8RMesh:
    """Build an S8R mesh sharing the Q4 corner grid and edge midpoint nodes."""
    if nx <= 0 or ny <= 0 or ny % 2:
        raise ValueError("S8R correlation requires positive nx and positive even ny.")
    node_ids: dict[tuple[int, int], int] = {}
    coordinates: list[tuple[float, float, float]] = []
    for j in range(2 * ny + 1):
        for i in range(2 * nx + 1):
            if i % 2 and j % 2:
                continue
            node_ids[(i, j)] = len(coordinates) + 1
            coordinates.append((length * i / (2 * nx), width * j / (2 * ny) - width / 2.0, 0.0))
    elements = []
    for j in range(ny):
        for i in range(nx):
            elements.append(
                (
                    node_ids[(2 * i, 2 * j)],
                    node_ids[(2 * i + 2, 2 * j)],
                    node_ids[(2 * i + 2, 2 * j + 2)],
                    node_ids[(2 * i, 2 * j + 2)],
                    node_ids[(2 * i + 1, 2 * j)],
                    node_ids[(2 * i + 2, 2 * j + 1)],
                    node_ids[(2 * i + 1, 2 * j + 2)],
                    node_ids[(2 * i, 2 * j + 1)],
                )
            )
    fixed = tuple(node_ids[(0, j)] for j in range(2 * ny + 1))
    tip = node_ids[(2 * nx, ny)]
    return S8RMesh(np.asarray(coordinates, dtype=float), tuple(elements), fixed, tip)


def write_calculix_composite_input(path: str | Path, mesh: S8RMesh) -> Path:
    """Write the controlled [0/90]s CalculiX composite-shell deck."""
    target = Path(path)
    lines = ["*HEADING", "QF_solver composite cross-code correlation", "*NODE"]
    lines.extend(
        f"{index},{point[0]:.12g},{point[1]:.12g},{point[2]:.12g}"
        for index, point in enumerate(mesh.nodes, start=1)
    )
    lines.append("*ELEMENT,TYPE=S8R,ELSET=EALL")
    lines.extend(f"{index}," + ",".join(str(node) for node in element) for index, element in enumerate(mesh.elements, 1))
    lines.append("*NSET,NSET=FIXED")
    lines.extend(_csv_lines(mesh.fixed_nodes))
    lines.extend(["*NSET,NSET=TIP", str(mesh.tip_node)])
    for angle in (0, 90):
        lines.extend([f"*ORIENTATION,NAME=ORI{angle}", "1.,0.,0.,0.,1.,0.", f"3,{angle}"])
    lines.extend(
        [
            "*MATERIAL,NAME=LAMINA",
            "*ELASTIC,TYPE=ENGINEERING CONSTANTS",
            "1.35e11,1.0e10,1.0e10,0.3,0.3,0.4,5.0e9,4.5e9",
            "3.8e9",
            "*DENSITY",
            "1600.",
            "*SHELL SECTION,ELSET=EALL,COMPOSITE",
            "2.5e-3,,LAMINA,ORI0",
            "2.5e-3,,LAMINA,ORI90",
            "2.5e-3,,LAMINA,ORI90",
            "2.5e-3,,LAMINA,ORI0",
            "*BOUNDARY",
            "FIXED,1,6",
            "*STEP",
            "*STATIC",
            "*CLOAD",
            f"{mesh.tip_node},3,-1.",
            "*NODE FILE,OUTPUT=2D",
            "U",
            "*END STEP",
        ]
    )
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def parse_original_frd_displacement(path: str | Path, original_node_count: int) -> np.ndarray:
    """Read original shell nodes from a layer-expanded composite FRD block."""
    last: dict[int, tuple[float, float, float]] = {}
    current: dict[int, tuple[float, float, float]] | None = None
    number = re.compile(r"[-+]?\d+\.\d+E[-+]\d+")
    for line in Path(path).read_text(encoding="ascii", errors="replace").splitlines():
        if line.startswith(" -4  DISP"):
            current = {}
        elif current is not None and line.startswith(" -1"):
            node = int(line[3:13])
            values = [float(value) for value in number.findall(line[13:])]
            if len(values) >= 3:
                current[node] = (values[0], values[1], values[2])
        elif current is not None and line.startswith(" -3"):
            last = current
            current = None
    missing = [node for node in range(1, original_node_count + 1) if node not in last]
    if missing:
        raise ValueError(f"Missing {len(missing)} original shell nodes in the CalculiX FRD DISP block.")
    return np.asarray([last[node] for node in range(1, original_node_count + 1)], dtype=float)


def _solve_qf_tip(nx: int, ny: int) -> float:
    mesh = MeshFactory.rectangular_plate(nx, ny, 1.0, 0.1)
    material = _laminate_definition([0.0, 90.0, 90.0, 0.0], 1.0e-2)
    left = [index for index, point in enumerate(mesh.nodes) if abs(float(point[0])) <= 1.0e-12]
    tip = next(
        index
        for index, point in enumerate(mesh.nodes)
        if abs(float(point[0]) - 1.0) <= 1.0e-12 and abs(float(point[1])) <= 1.0e-12
    )
    model = FiniteElementModel.from_raw(
        nodes=mesh.nodes,
        elements=[{"type": "MITC4", "nodes": quad, "material": "laminate"} for quad in mesh.quads],
        materials={"laminate": material},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in left],
        loads=[{"node": tip, "dof": "UZ", "value": -1.0}],
    )
    result = solve_model(model)
    return float(result.displacements[result.dofs.index(tip, "UZ")])


def _csv_lines(values: tuple[int, ...]) -> list[str]:
    return [
        ",".join(str(value) for value in values[index : index + 16])
        for index in range(0, len(values), 16)
    ]


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
