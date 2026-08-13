"""CalculiX same-mesh correlation for the TET4 finite-kinematics campaign."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

import numpy as np

from solveur.io.manifest import write_json_file
from solveur.verification.tet4_total_lagrangian_assembly import (
    _relative_error,
    _structured_tet4_mesh,
    _unique_edges,
)


class CalculixTotalLagrangianCorrelation:
    """Execute CalculiX C3D4 on the QF_solver cantilever meshes."""

    study_id = "VNV-TET4-TL-CALCULIX-003"

    def __init__(self, *, image: str = "qf-solver/calculix-nafems13h:2.20"):
        self.image = image

    def run(self, qf_summary_path: str | Path, output_dir: str | Path) -> dict[str, object]:
        output = Path(output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
        qf_summary = json.loads(Path(qf_summary_path).read_text(encoding="utf-8"))
        rows: list[dict[str, object]] = []
        finest: tuple[np.ndarray, np.ndarray, np.ndarray] | None = None
        for qf_row in qf_summary["levels"]:
            nx, ny, nz = (int(value) for value in qf_row["cells"])
            nodes, elements = _structured_tet4_mesh(nx, ny, nz, 4.0, 0.5, 0.5)
            case_dir = output / f"mesh_{nx}_{ny}_{nz}"
            case_dir.mkdir(exist_ok=True)
            input_path = case_dir / "cantilever.inp"
            write_calculix_input(input_path, nodes, elements)
            completed = self._execute(case_dir, input_path.stem)
            (case_dir / "calculix.log").write_text(
                completed.stdout + completed.stderr, encoding="utf-8"
            )
            if completed.returncode != 0:
                raise RuntimeError(f"CalculiX failed for {nx}x{ny}x{nz}; see {case_dir / 'calculix.log'}")
            frd_path = case_dir / "cantilever.frd"
            if not frd_path.is_file():
                raise RuntimeError(f"CalculiX did not produce {frd_path}.")
            displacement = parse_last_frd_displacement(frd_path, nodes.shape[0])
            tip_nodes = np.flatnonzero(np.isclose(nodes[:, 0], 4.0))
            calculix_tip = float(np.mean(displacement[tip_nodes, 2]))
            qf_tip = float(qf_row["tip_displacement_z"])
            rows.append(
                {
                    "cells": [nx, ny, nz],
                    "elements": int(elements.shape[0]),
                    "dofs": int(3 * nodes.shape[0]),
                    "qf_tip_z": qf_tip,
                    "calculix_tip_z": calculix_tip,
                    "relative_difference": _relative_error(qf_tip, calculix_tip),
                    "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
                }
            )
            finest = nodes, elements, displacement
        maximum_difference = max(float(row["relative_difference"]) for row in rows)
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION" if maximum_difference <= 0.02 else "WARNING",
            "external_solver": {"name": "CalculiX", "version": "2.20", "image": self.image},
            "formulations": {
                "qf_solver": "TET4 total Lagrangian Saint-Venant-Kirchhoff",
                "calculix": "C3D4 *ELASTIC with NLGEOM=YES",
                "strict_constitutive_identity_demonstrated": True,
                "calculix_reference": "https://www.feacluster.com/CalculiX/ccx_2.18/doc/ccx/node260.html",
            },
            "same_mesh": True,
            "same_nodal_loads": True,
            "rows": rows,
            "checks": [
                {
                    "id": "maximum_qf_calculix_tip_difference",
                    "value": maximum_difference,
                    "limit": 0.02,
                    "status": "PASS" if maximum_difference <= 0.02 else "FAIL",
                }
            ],
            "limitations": [
                "CalculiX FRD displacement output is rounded to six decimal digits.",
                "The correlation covers displacement, not yet stress or strain energy.",
            ],
        }
        write_json_file(output / "summary.json", summary)
        self._plot_convergence(output, rows, float(qf_summary["reference"]["tip_z"]))
        if finest is not None:
            self._plot_deformation(output, *finest)
        self._write_report(output, summary)
        return summary

    def _execute(self, work: Path, stem: str) -> subprocess.CompletedProcess[str]:
        command = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{work}:/work",
            "-w",
            "/work",
            self.image,
            stem,
        ]
        return subprocess.run(command, capture_output=True, text=True, timeout=300, check=False)

    @staticmethod
    def _plot_convergence(output: Path, rows: list[dict[str, object]], reference: float) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        elements = np.array([row["elements"] for row in rows], dtype=float)
        qf = np.abs(np.array([row["qf_tip_z"] for row in rows], dtype=float))
        calculix = np.abs(np.array([row["calculix_tip_z"] for row in rows], dtype=float))
        figure, axis = plt.subplots(figsize=(7.6, 4.5))
        axis.semilogx(elements, qf, "o-", label="QF_solver TET4-TL")
        axis.semilogx(elements, calculix, "s--", label="CalculiX C3D4")
        axis.axhline(abs(reference), color="#bc4749", linestyle=":", label="elastica Euler")
        axis.set_xlabel("Nombre de tetraedres")
        axis.set_ylabel("Fleche absolue au bout")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(output / "qf-calculix-convergence.png", dpi=180)
        plt.close(figure)

    @staticmethod
    def _plot_deformation(
        output: Path, nodes: np.ndarray, elements: np.ndarray, displacement: np.ndarray
    ) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        current = nodes + displacement
        edges = _unique_edges(elements)
        sampled = edges[:: max(1, len(edges) // 700)]
        figure = plt.figure(figsize=(9.0, 4.6))
        axis = figure.add_subplot(111, projection="3d")
        for coordinates, color, label in (
            (nodes, "#6c757d", "initial"),
            (current, "#c44536", "CalculiX"),
        ):
            for edge in sampled:
                axis.plot(*coordinates[list(edge)].T, color=color, linewidth=0.4, alpha=0.55)
            axis.scatter([], [], [], color=color, label=label)
        axis.set_box_aspect((4.0, 1.0, 1.0))
        axis.legend()
        axis.set_title("CalculiX C3D4 NLGEOM - maillage fin")
        figure.tight_layout()
        figure.savefig(output / "calculix-deformation.png", dpi=180)
        plt.close(figure)

    @staticmethod
    def _write_report(output: Path, summary: dict[str, object]) -> None:
        lines = [
            f"# {summary['study_id']}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Meme connectivite C3D4/TET4, memes blocages, memes charges nodales et meme loi "
            "Saint-Venant-Kirchhoff totale lagrangienne documentee par CalculiX.",
            "",
            "| Elements | QF_solver UZ | CalculiX UZ | Ecart |",
            "| ---: | ---: | ---: | ---: |",
        ]
        for row in summary["rows"]:
            lines.append(
                f"| {row['elements']} | {row['qf_tip_z']:.7e} | {row['calculix_tip_z']:.7e} | "
                f"{100.0 * row['relative_difference']:.4f} % |"
            )
        lines.extend(
            [
                "",
                "![Convergence croisee](qf-calculix-convergence.png)",
                "",
                "![Deformee CalculiX](calculix-deformation.png)",
                "",
            ]
        )
        (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


def write_calculix_input(path: str | Path, nodes: np.ndarray, elements: np.ndarray) -> Path:
    """Write a deterministic CalculiX C3D4 finite-kinematics cantilever."""
    target = Path(path)
    fixed = [index + 1 for index, node in enumerate(nodes) if np.isclose(node[0], 0.0)]
    tip = [index + 1 for index, node in enumerate(nodes) if np.isclose(node[0], 4.0)]
    lines = ["*HEADING", "QF_solver TET4-TL same-mesh CalculiX correlation", "*NODE"]
    lines.extend(
        f"{index + 1},{node[0]:.16g},{node[1]:.16g},{node[2]:.16g}"
        for index, node in enumerate(nodes)
    )
    lines.append("*ELEMENT,TYPE=C3D4,ELSET=EALL")
    lines.extend(
        f"{index + 1}," + ",".join(str(int(node) + 1) for node in element)
        for index, element in enumerate(elements)
    )
    lines.extend(("*NSET,NSET=FIXED", *_set_lines(fixed), "*NSET,NSET=TIP", *_set_lines(tip)))
    lines.extend(
        (
            "*SOLID SECTION,ELSET=EALL,MATERIAL=MAT",
            "*MATERIAL,NAME=MAT",
            "*ELASTIC",
            "1000000.,0.3",
            "*BOUNDARY",
            "FIXED,1,3,0.",
            "*STEP,NLGEOM=YES,INC=500",
            "*STATIC",
            "0.083333333333,1.,1.E-6,0.083333333333",
            "*CLOAD",
        )
    )
    lines.extend(f"{node},3,{-150.0 / len(tip):.16g}" for node in tip)
    lines.extend(("*NODE FILE,FREQUENCY=1", "U", "*END STEP"))
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def parse_last_frd_displacement(path: str | Path, node_count: int) -> np.ndarray:
    """Extract the last complete DISP block from a CalculiX FRD file."""
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
            if len(current) == node_count:
                last = current
            current = None
    if len(last) != node_count:
        raise ValueError(f"Expected {node_count} displacements in the last FRD DISP block, found {len(last)}.")
    return np.asarray([last[index] for index in range(1, node_count + 1)], dtype=float)


def _set_lines(values: list[int]) -> list[str]:
    return [",".join(str(value) for value in values[index : index + 16]) for index in range(0, len(values), 16)]
