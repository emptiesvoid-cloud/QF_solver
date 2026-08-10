"""Same-mesh CalculiX C3D10 correlation for the curved TET10 torsion case."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np

from solveur.io.json_reader import JsonModelReader
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_total_lagrangian import parse_last_frd_displacement
from solveur.verification.tet10_structural_convergence import plot_tetra_vector
from solveur.verification.vnv_manifest import write_vnv_manifest


class CalculixTet10Correlation:
    """Compare QF_solver TET10 and CalculiX C3D10 on an identical curved shaft."""

    study_id = "VNV-TET10-CALCULIX-C3D10-014"

    def __init__(
        self,
        output_dir: str | Path,
        model_path: str | Path,
        qf_result_path: str | Path,
        *,
        image: str = "qf-solver/calculix-nafems13h:2.20",
    ):
        self.output_dir = Path(output_dir).resolve()
        self.model_path = Path(model_path).resolve()
        self.qf_result_path = Path(qf_result_path).resolve()
        self.image = image

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        model = JsonModelReader().read(self.model_path)
        if {element.type for element in model.elements} != {"TET10"}:
            raise ValueError("CalculiX TET10 correlation requires a pure TET10 model.")
        qf_data = json.loads(self.qf_result_path.read_text(encoding="utf-8"))
        qf_displacement = _qf_displacement(qf_data, model.node_count)
        deck = write_calculix_tet10_input(self.output_dir / "tet10_torsion.inp", model)
        self._execute(deck.stem)
        calculix_displacement = parse_last_frd_displacement(
            self.output_dir / "tet10_torsion.frd",
            model.node_count,
        )
        qf_twist = _end_twist(np.asarray(model.nodes), qf_displacement)
        calculix_twist = _end_twist(np.asarray(model.nodes), calculix_displacement)
        displacement_difference = float(
            np.linalg.norm(qf_displacement - calculix_displacement)
            / max(np.linalg.norm(calculix_displacement), np.finfo(float).tiny)
        )
        twist_difference = _relative(qf_twist, calculix_twist)
        checks = [
            _upper("full_displacement_same_mesh", displacement_difference, 1.0e-4),
            _upper("end_twist_same_mesh", twist_difference, 1.0e-4),
        ]
        passed = all(check["status"] == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if passed else "FAIL",
            "maturity": "experimental",
            "external_solver": {
                "name": "CalculiX",
                "version": "2.20",
                "image": self.image,
                "element": "C3D10",
            },
            "same_mesh": True,
            "same_nodal_loads": True,
            "node_count": model.node_count,
            "element_count": len(model.elements),
            "qf_twist": qf_twist,
            "calculix_twist": calculix_twist,
            "full_displacement_relative_difference": displacement_difference,
            "twist_relative_difference": twist_difference,
            "checks": checks,
            "limitations": [
                "The correlation covers global displacement and end twist, not integration-point stress.",
                "CalculiX FRD output precision bounds the measurable displacement agreement.",
                "Only one curved circular-shaft mesh is covered.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        plot_tetra_vector(
            self.output_dir / "calculix_c3d10_deformation.png",
            model,
            calculix_displacement.reshape(-1),
            "CalculiX C3D10 - torsion courbe",
        )
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

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
        (self.output_dir / "calculix.log").write_text(
            completed.stdout + completed.stderr,
            encoding="utf-8",
        )
        if completed.returncode != 0:
            tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-40:])
            raise RuntimeError(f"CalculiX C3D10 failed:\n{tail}")

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Meme connectivite quadratique, memes coordonnees courbes, memes blocages et charges nodales.",
            "",
            "| Grandeur | QF_solver | CalculiX | Ecart relatif |",
            "| --- | ---: | ---: | ---: |",
            f"| rotation terminale | {summary['qf_twist']:.9e} | {summary['calculix_twist']:.9e} | "
            f"{summary['twist_relative_difference']:.3e} |",
            f"| champ deplacement L2 | - | - | {summary['full_displacement_relative_difference']:.3e} |",
            "",
            "![Deformee CalculiX C3D10](calculix_c3d10_deformation.png)",
            "",
        ]
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def write_calculix_tet10_input(path: str | Path, model: object) -> Path:
    """Write one deterministic linear C3D10 deck from a QF_solver model."""
    target = Path(path)
    material_name = model.elements[0].material
    material = model.materials[material_name]
    lines = ["*HEADING", "QF_solver TET10 same-mesh CalculiX correlation", "*NODE"]
    lines.extend(
        f"{index + 1},{_calculix_number(node[0])},{_calculix_number(node[1])},"
        f"{_calculix_number(node[2])}"
        for index, node in enumerate(model.nodes)
    )
    lines.append("*ELEMENT,TYPE=C3D10,ELSET=EALL")
    lines.extend(
        f"{index + 1}," + ",".join(str(int(node) + 1) for node in element.nodes)
        for index, element in enumerate(model.elements)
    )
    lines.extend(
        [
            "*SOLID SECTION,ELSET=EALL,MATERIAL=MAT",
            "*MATERIAL,NAME=MAT",
            "*ELASTIC",
            f"{_calculix_number(material['E'])},{_calculix_number(material['nu'])}",
            "*BOUNDARY",
        ]
    )
    component = {"UX": 1, "UY": 2, "UZ": 3}
    for constraint in model.fixed_dofs:
        for dof in constraint.dofs:
            lines.append(f"{constraint.node + 1},{component[dof]},{component[dof]},0.")
    lines.extend(["*STEP", "*STATIC", "0.1,1.0,1.E-8,0.1", "*CLOAD"])
    for load in model.loads:
        if abs(float(load.value)) > 1.0e-12:
            lines.append(
                f"{load.node + 1},{component[load.dof]},{_calculix_number(load.value)}"
            )
    lines.extend(["*NODE FILE,FREQUENCY=1", "U", "*END STEP"])
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def _calculix_number(value: object) -> str:
    """Emit compact free-field values and remove trigonometric round-off zeros."""
    number = float(value)
    if abs(number) < 1.0e-12:
        number = 0.0
    return f"{number:.12g}"


def _qf_displacement(data: dict[str, object], node_count: int) -> np.ndarray:
    displacement = np.zeros((node_count, 3), dtype=float)
    component = {"UX": 0, "UY": 1, "UZ": 2}
    for row in data["displacements"]:
        node = int(row["node"])
        for dof, value in row["dofs"].items():
            displacement[node, component[dof]] = float(value)
    return displacement


def _end_twist(nodes: np.ndarray, displacement: np.ndarray) -> float:
    selected = np.where(np.isclose(nodes[:, 0], np.max(nodes[:, 0])))[0]
    y = nodes[selected, 1]
    z = nodes[selected, 2]
    return float(
        np.sum(y * displacement[selected, 2] - z * displacement[selected, 1])
        / np.sum(y * y + z * z)
    )


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
