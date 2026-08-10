"""Pinned same-mesh CalculiX S3 correlation for MITC3+."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_composite import parse_original_frd_displacement
from solveur.verification.code_aster_mitc3 import (
    _check,
    _plot_deformations,
    _qf_model,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


class CalculixMitc3Correlation:
    """Compare MITC3+ with the CalculiX linear triangular shell."""

    study_id = "VNV-MITC3-CALCULIX-S3-014"

    def __init__(
        self,
        output_dir: str | Path,
        *,
        nx: int = 32,
        ny: int = 8,
        image: str = "qf-solver/calculix-nafems13h:2.20",
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        self.nx = int(nx)
        self.ny = int(ny)
        self.image = image

    def run(self) -> dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_case("membrane", "UX", 1000.0), self._run_case("bending", "UZ", -1.0)]
        checks = [
            _check("membrane_difference", float(rows[0]["difference"]), 1.0e-3),
            _check("bending_difference", float(rows[1]["difference"]), 0.15),
        ]
        summary = {
            "study_id": self.study_id,
            "status": (
                "PASS_EXTERNAL_CORRELATION"
                if all(check["status"] == "PASS" for check in checks)
                else "WARNING"
            ),
            "maturity": "experimental",
            "qf_element": "MITC3+ Reissner-Mindlin",
            "external_solver": {
                "name": "CalculiX",
                "version": "2.20",
                "image": self.image,
                "element": "S3",
            },
            "same_mesh": True,
            "mesh": {"nx": self.nx, "ny": self.ny, "triangles": 2 * self.nx * self.ny},
            "cases": rows,
            "checks": checks,
            "limitations": [
                "CalculiX S3 and QF_solver MITC3+ are distinct shell formulations.",
                "Only two global displacement observables are compared.",
                "Curved shells, stress recovery, dynamics and laminates remain outside this study.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_markdown(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_case(self, name: str, dof: str, total_load: float) -> dict[str, Any]:
        work = self.output_dir / name
        work.mkdir(exist_ok=True)
        model, triangles, root, tip = _qf_model(
            self.nx,
            self.ny,
            dof=dof,
            total_load=total_load,
        )
        qf = solve_model(model, enforce_policy=False)
        component = 0 if dof == "UX" else 2
        qf_values = np.asarray(
            [qf.displacements[qf.dofs.index(int(node), dof)] for node in tip]
        )
        stem = f"mitc3_{name}"
        (work / f"{stem}.inp").write_text(
            calculix_triangle_input(model.nodes, triangles, root, tip, dof, total_load),
            encoding="ascii",
        )
        self._execute(work, stem)
        displacement = parse_original_frd_displacement(
            work / f"{stem}.frd",
            model.node_count,
        )
        calculix_value = float(np.mean(displacement[tip, component]))
        qf_value = float(np.mean(qf_values))
        qf_displacement = np.asarray(
            [
                [
                    qf.displacements[qf.dofs.index(node, component_name)]
                    for component_name in ("UX", "UY", "UZ")
                ]
                for node in range(model.node_count)
            ],
            dtype=float,
        )
        _plot_deformations(
            model.nodes,
            triangles,
            qf_displacement,
            displacement,
            work / f"{name}_deformation.png",
            external_label="CalculiX S3",
        )
        return {
            "id": name,
            "dof": dof,
            "total_load": total_load,
            "qf_value": qf_value,
            "calculix_value": calculix_value,
            "difference": abs(qf_value - calculix_value)
            / max(abs(calculix_value), 1.0e-30),
            "vector_difference": float(
                np.linalg.norm(qf_displacement - displacement)
                / max(np.linalg.norm(displacement), 1.0e-30)
            ),
        }

    def _execute(self, work: Path, stem: str) -> None:
        completed = subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{work}:/work",
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
        (work / f"{stem}.log").write_text(
            completed.stdout + completed.stderr,
            encoding="utf-8",
        )
        if completed.returncode:
            tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-40:])
            raise RuntimeError(f"CalculiX S3 failed for {stem}:\n{tail}")


def calculix_triangle_input(
    nodes: np.ndarray,
    triangles: np.ndarray,
    root: np.ndarray,
    tip: np.ndarray,
    dof: str,
    total_load: float,
) -> str:
    """Return a same-mesh S3 input deck."""
    component = {"UX": 1, "UZ": 3}[dof]
    lines = ["*HEADING", "QF_solver MITC3+ same-mesh CalculiX correlation", "*NODE"]
    lines.extend(
        f"{index + 1},{point[0]:.16g},{point[1]:.16g},{point[2]:.16g}"
        for index, point in enumerate(nodes)
    )
    lines.extend(["*ELEMENT,TYPE=S3,ELSET=EALL"])
    lines.extend(
        f"{index + 1}," + ",".join(str(int(node) + 1) for node in triangle)
        for index, triangle in enumerate(triangles)
    )
    lines.extend(["*NSET,NSET=ROOT", ",".join(str(int(node) + 1) for node in root)])
    lines.extend(["*MATERIAL,NAME=ALUMINIUM", "*ELASTIC", "7.0e10,0.3", "*DENSITY", "2700.0"])
    lines.extend(["*SHELL SECTION,ELSET=EALL,MATERIAL=ALUMINIUM", "0.01"])
    lines.extend(["*BOUNDARY", "ROOT,1,6", "*STEP", "*STATIC", "*CLOAD"])
    nodal = total_load / len(tip)
    lines.extend(f"{int(node) + 1},{component},{nodal:.16g}" for node in tip)
    lines.extend(["*NODE FILE,OUTPUT=2D", "U", "*END STEP", ""])
    return "\n".join(lines)


def _markdown(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut: **{summary['status']}**.",
        "",
        "| Cas | DDL | QF_solver | CalculiX S3 | Ecart |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in summary["cases"]:
        lines.append(
            f"| {row['id']} | {row['dof']} | {row['qf_value']:.12e} | "
            f"{row['calculix_value']:.12e} | {100.0 * row['difference']:.5f} % |"
        )
    return "\n".join(lines) + "\n"
