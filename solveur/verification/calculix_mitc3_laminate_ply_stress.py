"""External per-ply membrane-stress correlation for MITC3+ laminates.

The protocol intentionally uses a flat affine membrane patch.  It avoids
free-edge and point-load singularities, lets both formulations represent a
constant mid-plane strain field, and compares the material-axis stresses of
all four plies against CalculiX S6 COMPOSITE integration-point output.
"""

from __future__ import annotations

import shutil
import subprocess
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.materials.factory import MaterialFactory
from solveur.verification.mitc3_laminate_dynamic import Mitc3LaminateDynamicStudy
from solveur.verification.mitc3_models import rectangular_tri_mesh
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-MITC3-LAMINATE-PLY-STRESS-CALCULIX-S6-020"
_FLOAT = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?"
_S6_PLY_STRESS_LINE = re.compile(
    rf"^\s*(?P<element>\d+)\s+(?P<point>\d+)\s+"
    rf"(?P<sxx>{_FLOAT})\s+(?P<syy>{_FLOAT})\s+(?P<szz>{_FLOAT})\s+"
    rf"(?P<sxy>{_FLOAT})\s+(?P<sxz>{_FLOAT})\s+(?P<syz>{_FLOAT})\s+"
    rf"P(?P<ply>\d+)_shell_\d+\s*$"
)


@dataclass(frozen=True)
class S6Mesh:
    """A quadratic triangle mesh with its matching QF corner nodes."""

    nodes: np.ndarray
    elements: tuple[tuple[int, ...], ...]
    root_nodes: tuple[int, ...]
    all_nodes: tuple[int, ...]
    origin_node: int
    tip_corner_nodes: tuple[int, ...]


class CalculixMitc3LaminatePlyStressCorrelation:
    """Compare MITC3+ material-axis ply stresses with CalculiX S6."""

    study_id = STUDY_ID
    meshes = ((4, 1), (8, 2), (16, 4))
    stress_limit = 0.02
    qf_increment_limit = 1.0e-8
    external_increment_limit = 0.002

    def __init__(self, output_dir: str | Path, *, image: str = "qf-solver/calculix-nafems13h:2.20") -> None:
        self.output_dir = Path(output_dir).resolve()
        self.image = image

    def run(self) -> dict[str, Any]:
        """Run the affine membrane patch for each controlled refinement."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_mesh(nx, ny) for nx, ny in self.meshes]
        fine = rows[-1]
        checks = [
            _check("fine_material_ply_stress_difference", float(fine["stress_l2_difference"]), self.stress_limit),
            _check("qf_final_stress_increment", _relative_vector(rows[-1]["qf_stress_vector"], rows[-2]["qf_stress_vector"]), self.qf_increment_limit),
            _check("calculix_final_stress_increment", _relative_vector(rows[-1]["calculix_stress_vector"], rows[-2]["calculix_stress_vector"]), self.external_increment_limit),
            _check("qf_patch_error", float(fine["qf_patch_error"]), 1.0e-10),
        ]
        summary: dict[str, Any] = {
            "study_id": STUDY_ID,
            "status": "PASS_EXTERNAL_CORRELATION" if all(item["status"] == "PASS" for item in checks) else "WARNING",
            "maturity": "verified_development_external_correlation",
            "external_solver": {"name": "CalculiX", "version": "2.20", "image": self.image, "element": "S6 COMPOSITE"},
            "qf_element": "MITC3+ shell_laminate",
            "comparison_basis": {
                "geometry": "flat 1.0 m x 0.2 m membrane patch",
                "same_corner_mesh": True,
                "layup": [0.0, 90.0, 90.0, 0.0],
                "load": "constant resultant N11 = 1000 N/m transferred as matching edge nodal forces",
                "observable": "mean material-axis [S11, S22, S12] at middle position of each ply",
                "excluded": "free edges, transverse shear S13/S23, bending, interlaminar stresses and nodal extrapolation",
                "refinement_thresholds": {
                    "qf_affine_patch": self.qf_increment_limit,
                    "calculix_s6_final_increment": self.external_increment_limit,
                    "rationale": "The controlled QF affine patch is exact to numerical precision; the independently discretised S6 result must remain below 0.2 percent between the final two meshes.",
                },
            },
            "rows": rows,
            "checks": checks,
            "limitations": [
                "The affine membrane patch proves material-axis stress projection on a regular plane, not curved laminate behaviour.",
                "MITC3+ is a Reissner-Mindlin triangle and S6 is a quadratic shell; equality of element formulations is not claimed.",
                "Only middle-ply in-plane stress is compared. S13/S23, free-edge peaks, damage and delamination are excluded.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, STUDY_ID)
        self._publish_reference()
        return summary

    def _run_mesh(self, nx: int, ny: int) -> dict[str, Any]:
        model, triangles, expected = _qf_affine_model(nx, ny)
        qf = solve_model(model, enforce_policy=False)
        qf_stress = _qf_ply_stresses(qf.element_results)
        qf_displacement = np.asarray(qf.displacements, dtype=float)
        patch_error = float(np.max(np.abs(qf_displacement - expected)) / max(float(np.max(np.abs(expected))), 1.0e-30))
        mesh = build_s6_mesh(model.nodes, triangles)
        stem = f"mitc3_laminate_ply_{nx}x{ny}"
        write_s6_composite_input(self.output_dir / f"{stem}.inp", mesh, nx, ny)
        self._execute(stem)
        records = parse_s6_composite_ply_stresses(self.output_dir / f"{stem}.dat")
        calculix_stress = _calculix_ply_stresses(records)
        qf_vector = np.asarray(qf_stress, dtype=float).reshape(-1)
        calculix_vector = np.asarray(calculix_stress, dtype=float).reshape(-1)
        return {
            "nx": nx,
            "ny": ny,
            "tria3_elements": len(model.elements),
            "s6_elements": len(mesh.elements),
            "qf_patch_error": patch_error,
            "qf_material_stress_by_ply_pa": qf_stress,
            "calculix_material_stress_by_ply_pa": calculix_stress,
            "qf_stress_vector": qf_vector.tolist(),
            "calculix_stress_vector": calculix_vector.tolist(),
            "stress_l2_difference": _relative_vector(qf_vector, calculix_vector),
        }

    def _execute(self, stem: str) -> None:
        completed = subprocess.run(
            ["docker", "run", "--rm", "-v", f"{self.output_dir}:/work", "-w", "/work", self.image, stem],
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        (self.output_dir / f"{stem}.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
        if completed.returncode:
            tail = (completed.stdout + completed.stderr)[-2000:]
            raise RuntimeError(f"CalculiX MITC3 laminate stress run failed:\n{tail}")

    def _plot(self, rows: list[dict[str, Any]]) -> None:
        figure, axis = plt.subplots(figsize=(7.4, 4.5))
        elements = [int(row["tria3_elements"]) for row in rows]
        errors = [100.0 * float(row["stress_l2_difference"]) for row in rows]
        axis.semilogx(elements, errors, "o-", color="#087f5b", label="QF_solver MITC3+ / CalculiX S6")
        axis.axhline(100.0 * self.stress_limit, color="#c92a2a", linestyle="--", label="Seuil 2 %")
        axis.set(xlabel="Elements TRIA3 QF_solver", ylabel="Ecart L2 contraintes par pli [%]", title="Patch membranaire multicouche")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "mitc3_laminate_ply_stress_calculix.png", dpi=180)
        plt.close(figure)

    def _publish_reference(self) -> None:
        root = Path(__file__).resolve().parents[2]
        reference = root / "qualification" / "vnv" / "external" / "calculix_mitc3_laminate_ply_stress" / "reference"
        reference.mkdir(parents=True, exist_ok=True)
        for name in ("summary.json", "report.md", "vnv_manifest.json", "mitc3_laminate_ply_stress_calculix.png"):
            shutil.copy2(self.output_dir / name, reference / name)
        assets = root / "docs" / "assets" / "reviews"
        assets.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.output_dir / "mitc3_laminate_ply_stress_calculix.png", assets / "mitc3_laminate_ply_stress_calculix.png")


def _qf_affine_model(nx: int, ny: int) -> tuple[FiniteElementModel, np.ndarray, np.ndarray]:
    study = Mitc3LaminateDynamicStudy()
    model = study._static_model(nx, ny, 1000.0)
    _, triangles, _ = rectangular_tri_mesh(1.0, 0.2, nx, ny)
    material = MaterialFactory.create(study.laminate_data())
    expected_strain = np.linalg.solve(material.membrane_matrix, np.array([1000.0, 0.0, 0.0]))
    dofs = model.dof_manager()
    expected = np.zeros(dofs.ndof, dtype=float)
    for index, (x, y, _) in enumerate(model.nodes):
        expected[dofs.index(index, "UX")] = expected_strain[0] * x + 0.5 * expected_strain[2] * y
        expected[dofs.index(index, "UY")] = expected_strain[1] * y + 0.5 * expected_strain[2] * x
    return model, triangles, expected


def build_s6_mesh(nodes: np.ndarray, triangles: np.ndarray) -> S6Mesh:
    """Upgrade a QF TRIA3 corner mesh to the CalculiX S6 topology."""
    coordinates = [tuple(float(value) for value in point) for point in np.asarray(nodes, dtype=float)]
    edge_nodes: dict[tuple[int, int], int] = {}

    def midpoint(first: int, second: int) -> int:
        edge = (min(first, second), max(first, second))
        if edge not in edge_nodes:
            coordinates.append(tuple(0.5 * (nodes[first] + nodes[second])))
            edge_nodes[edge] = len(coordinates)
        return edge_nodes[edge]

    elements = []
    for triangle in np.asarray(triangles, dtype=int):
        first, second, third = (int(value) for value in triangle)
        elements.append((first + 1, second + 1, third + 1, midpoint(first, second), midpoint(second, third), midpoint(third, first)))
    coordinate_array = np.asarray(coordinates, dtype=float)
    root = tuple(int(index + 1) for index in np.flatnonzero(np.isclose(coordinate_array[:, 0], 0.0)))
    tip = tuple(int(index + 1) for index in range(len(nodes)) if np.isclose(nodes[index, 0], 1.0))
    origin = int(np.flatnonzero(np.isclose(coordinate_array[:, 0], 0.0) & np.isclose(coordinate_array[:, 1], 0.0))[0] + 1)
    return S6Mesh(coordinate_array, tuple(elements), root, tuple(range(1, len(coordinates) + 1)), origin, tip)


def write_s6_composite_input(path: str | Path, mesh: S6Mesh, nx: int, ny: int) -> Path:
    """Write an S6 laminate membrane deck with per-element ply labels."""
    target = Path(path)
    lines = ["*HEADING", "QF_solver MITC3 laminate ply stress correlation", "*NODE"]
    lines.extend(f"{index},{point[0]:.14g},{point[1]:.14g},{point[2]:.14g}" for index, point in enumerate(mesh.nodes, 1))
    lines.append("*ELEMENT,TYPE=S6,ELSET=EALL")
    lines.extend(f"{index}," + ",".join(str(node) for node in element) for index, element in enumerate(mesh.elements, 1))
    lines.extend(["*NSET,NSET=ALL", *_csv(mesh.all_nodes), "*NSET,NSET=ROOT", *_csv(mesh.root_nodes), "*NSET,NSET=ORIGIN", str(mesh.origin_node)])
    lines.extend(["*MATERIAL,NAME=LAMINA", "*ELASTIC,TYPE=ENGINEERING CONSTANTS", "1.30e11,9.0e9,9.0e9,0.28,0.28,0.28,5.0e9,4.0e9", "3.5e9", "*DENSITY", "1550."])
    for ply, angle in enumerate((0.0, 90.0, 90.0, 0.0)):
        lines.extend([f"*ORIENTATION,NAME=P{ply}", "1.,0.,0.,0.,1.,0.", f"3,{angle:.1f}"])
    for index in range(1, len(mesh.elements) + 1):
        lines.extend([f"*ELSET,ELSET=E{index}", str(index), f"*SHELL SECTION,ELSET=E{index},COMPOSITE", "0.0025,,LAMINA,P0", "0.0025,,LAMINA,P1", "0.0025,,LAMINA,P2", "0.0025,,LAMINA,P3"])
    weights: np.ndarray[Any, np.dtype[np.float64]] = np.ones(len(mesh.tip_corner_nodes), dtype=float)
    weights[[0, -1]] = 0.5
    weights /= weights.sum()
    lines.extend(["*BOUNDARY", "ALL,3,6", "ROOT,1,1", "ORIGIN,2,2", "*STEP", "*STATIC", "*CLOAD"])
    lines.extend(f"{node},1,{1000.0 * 0.2 * float(weight):.16g}" for node, weight in zip(mesh.tip_corner_nodes, weights, strict=True))
    lines.extend(["*EL PRINT,ELSET=EALL", "S", "*END STEP"])
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def _qf_ply_stresses(results: list[dict[str, Any]]) -> list[list[float]]:
    values: dict[int, list[np.ndarray]] = {ply: [] for ply in range(4)}
    for result in results:
        for ply in result["ply_results"]:
            if ply["location"] == "middle":
                values[int(ply["ply_index"])].append(np.asarray(ply["material_stress"], dtype=float))
    return [np.mean(values[ply], axis=0).tolist() for ply in range(4)]


def parse_s6_composite_ply_stresses(path: str | Path) -> list[dict[str, object]]:
    """Parse controlled S6 composite stresses labelled by ply orientation P0..P3."""
    records: list[dict[str, object]] = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        match = _S6_PLY_STRESS_LINE.match(line)
        if match is None:
            continue
        values = match.groupdict()
        records.append(
            {
                "element": int(values["element"]),
                "integration_point": int(values["point"]),
                "ply_index": int(values["ply"]),
                "stress_output": [float(values[name]) for name in ("sxx", "syy", "szz", "sxy", "sxz", "syz")],
            }
        )
    if not records:
        raise ValueError(f"No controlled S6 composite ply stresses found in {Path(path).name}.")
    return records


def _calculix_ply_stresses(records: list[dict[str, object]]) -> list[list[float]]:
    values: dict[int, list[np.ndarray]] = {ply: [] for ply in range(4)}
    for record in records:
        ply_index = record["ply_index"]
        if not isinstance(ply_index, int):
            raise TypeError("CalculiX ply index must be an integer")
        stress = np.asarray(record["stress_output"], dtype=float)
        values[ply_index].append(np.array([stress[0], stress[1], stress[3]]))
    return [np.mean(values[ply], axis=0).tolist() for ply in range(4)]


def _relative_vector(left: object, right: object) -> float:
    numerator = float(np.linalg.norm(np.asarray(left, dtype=float) - np.asarray(right, dtype=float)))
    denominator = max(float(np.linalg.norm(np.asarray(right, dtype=float))), float(np.finfo(float).tiny))
    return numerator / denominator


def _csv(values: tuple[int, ...]) -> list[str]:
    return [",".join(str(value) for value in values[index : index + 16]) for index in range(0, len(values), 16)]


def _check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL"}


def _report(summary: dict[str, Any]) -> str:
    lines = [f"# {summary['study_id']}", "", f"Statut automatise : **{summary['status']}**.", "", "| Maillage | Ecart L2 contraintes par pli | Erreur patch QF |", "| --- | ---: | ---: |"]
    for row in summary["rows"]:
        lines.append(f"| {row['nx']}x{row['ny']} | {100.0 * float(row['stress_l2_difference']):.5f} % | {float(row['qf_patch_error']):.3e} |")
    lines.extend(["", "Les composantes comparees sont `S11`, `S22`, `S12` dans les axes materiau, aux points d'integration CalculiX et a la position moyenne de pli QF_solver.", "", "![Correlation contraintes par pli MITC3+](mitc3_laminate_ply_stress_calculix.png)", ""])
    return "\n".join(lines)
