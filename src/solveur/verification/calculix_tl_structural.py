"""CalculiX correlation for finite-strain stress and TET4 buckling."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import numpy as np

from solveur.io.manifest import write_json_file
from solveur.materials.solid import SolidMaterial
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh
from solveur.verification.tet4_total_lagrangian_buckling import (
    euler_cantilever_critical_load,
)
from solveur.verification.tet4_total_lagrangian_stress import analytical_svk_state
from solveur.verification.vnv_manifest import write_vnv_manifest


class CalculixTlStructuralCampaign:
    """Compare QF_solver references with independent CalculiX C3D4 runs."""

    study_id = "VNV-TET4-TL-CALCULIX-STRUCTURAL-008"

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
        stress = self._run_stress_patch()
        buckling = self._run_buckling()
        checks = [
            _check("cauchy_stress", float(stress["relative_error"]), 5.0e-5),
            _check(
                "finest_buckling_qf_calculix",
                float(buckling["levels"][-1]["qf_calculix_relative_difference"]),
                0.03,
            ),
            _check(
                "finest_buckling_calculix_euler",
                float(buckling["levels"][-1]["calculix_euler_relative_error"]),
                0.10,
            ),
        ]
        summary: dict[str, object] = {
            "study_id": self.study_id,
            "status": "PASS_EXTERNAL_CORRELATION"
            if all(item["status"] == "PASS" for item in checks)
            else "WARNING",
            "maturity": "research",
            "external_solver": {
                "name": "CalculiX",
                "version": "2.20",
                "image": self.image,
                "element": "C3D4",
            },
            "stress_patch": stress,
            "buckling": buckling,
            "checks": checks,
            "limitations": [
                "The stress patch is homogeneous and excludes singular stress recovery.",
                "Linear buckling compares eigenvalue factors, not an imperfect postcritical path.",
                "Both solid elements converge slowly in bending on coarse meshes.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    def _run_stress_patch(self) -> dict[str, object]:
        nodes, elements = _structured_tet4_mesh(4, 2, 2, 2.0, 1.0, 0.75)
        deformation = np.array(
            [[1.08, 0.06, 0.01], [0.02, 0.97, 0.03], [0.0, 0.01, 1.04]],
            dtype=float,
        )
        material = SolidMaterial(E=1.0e6, nu=0.3)
        reference = analytical_svk_state(deformation, material)
        work = self.output_dir / "stress_patch"
        work.mkdir(exist_ok=True)
        write_stress_patch_input(work / "stress_patch.inp", nodes, elements, deformation)
        self._execute(work, "stress_patch")
        stresses = parse_calculix_element_stresses(work / "stress_patch.dat")
        mean = np.mean(stresses, axis=0)
        expected = _tensor_to_calculix_vector(reference["cauchy_stress"])
        return {
            "elements": int(elements.shape[0]),
            "integration_points": int(stresses.shape[0]),
            "calculix_cauchy": mean.tolist(),
            "analytical_cauchy": expected.tolist(),
            "relative_error": _relative_norm(mean, expected),
        }

    def _run_buckling(self) -> dict[str, object]:
        young, length, height, depth = 1.0e6, 4.0, 0.5, 0.5
        euler = euler_cantilever_critical_load(
            young, depth * height**3 / 12.0, length
        )
        qf_values = {
            (16, 4, 4): 1115.4714943181057,
            (24, 6, 6): 941.2097726970968,
            (32, 8, 8): 879.4051555835825,
            (40, 10, 10): 850.3403479250943,
        }
        levels: list[dict[str, object]] = []
        for cells, qf_load in qf_values.items():
            nodes, elements = _structured_tet4_mesh(*cells, length, height, depth)
            work = self.output_dir / f"buckling_{cells[0]}_{cells[1]}_{cells[2]}"
            work.mkdir(exist_ok=True)
            write_buckling_input(work / "buckling.inp", nodes, elements)
            self._execute(work, "buckling", timeout=900)
            factors = parse_calculix_buckling_factors(work / "buckling.dat")
            critical = float(factors[0])
            levels.append(
                {
                    "cells": list(cells),
                    "elements": int(elements.shape[0]),
                    "qf_critical_load": qf_load,
                    "calculix_critical_load": critical,
                    "qf_calculix_relative_difference": _relative_norm(
                        np.array([qf_load]), np.array([critical])
                    ),
                    "calculix_euler_relative_error": abs(critical - euler) / euler,
                    "eigenvalues": factors,
                }
            )
        return {"euler_critical_load": euler, "levels": levels}

    def _execute(self, work: Path, stem: str, *, timeout: int = 300) -> None:
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
            timeout=timeout,
            check=False,
        )
        (work / "calculix.log").write_text(
            completed.stdout + completed.stderr, encoding="utf-8"
        )
        if completed.returncode != 0:
            tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-40:])
            raise RuntimeError(f"CalculiX failed for {stem}:\n{tail}")

    def _plot(self, summary: dict[str, object]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        levels = summary["buckling"]["levels"]
        elements = [row["elements"] for row in levels]
        qf = [row["qf_critical_load"] for row in levels]
        calculix = [row["calculix_critical_load"] for row in levels]
        euler = float(summary["buckling"]["euler_critical_load"])
        figure, axis = plt.subplots(figsize=(7.6, 4.5))
        axis.semilogx(elements, qf, "o-", label="QF_solver TET4-TL")
        axis.semilogx(elements, calculix, "s--", label="CalculiX C3D4")
        axis.axhline(euler, color="#bc4749", linestyle=":", label="Euler")
        axis.set(xlabel="Nombre de TET4/C3D4", ylabel="Charge critique")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "buckling_external_comparison.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        stress = summary["stress_patch"]
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "## Patch de contrainte finie",
            "",
            f"Ecart relatif Cauchy CalculiX/theorie : `{100 * stress['relative_error']:.6f} %`.",
            "",
            "## Flambement lineaire sur maillage identique",
            "",
            "| Maillage | Elements | QF_solver | CalculiX | Ecart QF/CCX | Ecart CCX/Euler |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["buckling"]["levels"]:
            lines.append(
                f"| {'x'.join(str(value) for value in row['cells'])} | {row['elements']} | "
                f"{row['qf_critical_load']:.6f} | {row['calculix_critical_load']:.6f} | "
                f"{100 * row['qf_calculix_relative_difference']:.3f} % | "
                f"{100 * row['calculix_euler_relative_error']:.3f} % |"
            )
        lines.extend(
            [
                "",
                "![Comparaison du flambement](buckling_external_comparison.png)",
                "",
                "CalculiX constitue ici une implementation externe sur la meme connectivite. "
                "La solution d'Euler reste l'oracle analytique principal.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def write_stress_patch_input(
    path: str | Path,
    nodes: np.ndarray,
    elements: np.ndarray,
    deformation: np.ndarray,
) -> Path:
    """Write a displacement-controlled homogeneous finite-strain patch."""
    displacement = nodes @ (np.asarray(deformation) - np.eye(3)).T
    lines = _mesh_lines(nodes, elements, "Finite strain C3D4 patch")
    lines.extend(["*BOUNDARY"])
    for index, values in enumerate(displacement, start=1):
        for component, value in enumerate(values, start=1):
            lines.append(f"{index},{component},{component},{value:.16g}")
    lines.extend(
        [
            "*STEP,NLGEOM=YES,INC=20",
            "*STATIC",
            "0.1,1.0,1.E-8,0.1",
            "*EL PRINT,ELSET=EALL,FREQUENCY=1",
            "S",
            "*END STEP",
        ]
    )
    return _write_ascii(path, lines)


def write_buckling_input(path: str | Path, nodes: np.ndarray, elements: np.ndarray) -> Path:
    """Write a unit-load linear buckling input for a clamped C3D4 column."""
    fixed = [i + 1 for i, node in enumerate(nodes) if np.isclose(node[0], 0.0)]
    tip = [i + 1 for i, node in enumerate(nodes) if np.isclose(node[0], 4.0)]
    lines = _mesh_lines(nodes, elements, "C3D4 Euler buckling")
    lines.extend(["*NSET,NSET=FIXED", *_set_lines(fixed), "*NSET,NSET=TIP", *_set_lines(tip)])
    lines.extend(
        [
            "*BOUNDARY",
            "FIXED,1,3,0.",
            "*STEP",
            "*BUCKLE",
            "3,0.001,30,1000",
            "*CLOAD",
        ]
    )
    lines.extend(f"{node},1,{-1.0 / len(tip):.16g}" for node in tip)
    lines.extend(["*NODE FILE", "U", "*END STEP"])
    return _write_ascii(path, lines)


def parse_calculix_element_stresses(path: str | Path) -> np.ndarray:
    """Extract the final CalculiX integration-point stress table."""
    blocks: list[list[list[float]]] = []
    current: list[list[float]] | None = None
    for line in Path(path).read_text(encoding="ascii", errors="replace").splitlines():
        lowered = line.strip().lower()
        if lowered.startswith("stresses (") and " time " in lowered:
            current = []
            blocks.append(current)
            continue
        if current is None or not lowered:
            continue
        fields = lowered.split()
        if len(fields) == 8 and all(_is_number(value) for value in fields):
            current.append([float(value) for value in fields[2:]])
        elif current:
            current = None
    if not blocks or not blocks[-1]:
        raise ValueError("CalculiX output does not contain integration-point stresses.")
    return np.asarray(blocks[-1], dtype=float)


def parse_calculix_buckling_factors(path: str | Path) -> list[float]:
    """Extract ordered buckling factors from the CalculiX DAT output."""
    text = Path(path).read_text(encoding="ascii", errors="replace")
    factors: list[float] = []
    active = False
    for line in text.splitlines():
        lowered = line.lower()
        compact = "".join(lowered.split())
        if (
            "bucklingfactoroutput" in compact
            or "bucklingfactors" in compact
            or "eigenvalues" in compact
        ):
            active = True
            continue
        if active:
            numbers = re.findall(r"[-+]?\d+(?:\.\d*)?(?:[Ee][-+]?\d+)?", line)
            if len(numbers) >= 2:
                factors.append(float(numbers[-1]))
            elif factors and not line.strip():
                continue
    if not factors:
        raise ValueError("CalculiX output does not contain buckling factors.")
    return factors


def run_calculix_buckling_level(
    work: str | Path,
    nodes: np.ndarray,
    elements: np.ndarray,
    *,
    image: str = "qf-solver/calculix-nafems13h:2.20",
    timeout: int = 1200,
) -> list[float]:
    """Run one independently controlled C3D4 buckling level."""
    root = Path(work).resolve()
    root.mkdir(parents=True, exist_ok=True)
    write_buckling_input(root / "buckling.inp", nodes, elements)
    completed = subprocess.run(
        ["docker", "run", "--rm", "-v", f"{root}:/work", "-w", "/work", image, "buckling"],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    (root / "calculix.log").write_text(completed.stdout + completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        tail = "\n".join((completed.stdout + completed.stderr).splitlines()[-40:])
        raise RuntimeError(f"CalculiX buckling failed:\n{tail}")
    return parse_calculix_buckling_factors(root / "buckling.dat")


def _mesh_lines(nodes: np.ndarray, elements: np.ndarray, title: str) -> list[str]:
    lines = ["*HEADING", title, "*NODE"]
    lines.extend(
        f"{i + 1},{node[0]:.16g},{node[1]:.16g},{node[2]:.16g}"
        for i, node in enumerate(nodes)
    )
    lines.append("*ELEMENT,TYPE=C3D4,ELSET=EALL")
    lines.extend(
        f"{i + 1}," + ",".join(str(int(node) + 1) for node in element)
        for i, element in enumerate(elements)
    )
    lines.extend(
        [
            "*SOLID SECTION,ELSET=EALL,MATERIAL=MAT",
            "*MATERIAL,NAME=MAT",
            "*ELASTIC",
            "1000000.,0.3",
        ]
    )
    return lines


def _tensor_to_calculix_vector(value: object) -> np.ndarray:
    tensor = np.asarray(value, dtype=float)
    return tensor[[0, 1, 2, 0, 0, 1], [0, 1, 2, 1, 2, 2]]


def _relative_norm(value: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(value - reference) / max(np.linalg.norm(reference), 1.0e-30))


def _check(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {
        "id": identifier,
        "value": value,
        "limit": limit,
        "status": "PASS" if np.isfinite(value) and value <= limit else "FAIL",
    }


def _set_lines(values: list[int]) -> list[str]:
    return [",".join(str(value) for value in values[i : i + 16]) for i in range(0, len(values), 16)]


def _write_ascii(path: str | Path, lines: list[str]) -> Path:
    target = Path(path)
    target.write_text("\n".join(lines) + "\n", encoding="ascii")
    return target


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True
