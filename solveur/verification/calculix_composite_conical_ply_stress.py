"""Distance-controlled ply-stress correlation on the composite conical shell."""

from __future__ import annotations

import subprocess
from pathlib import Path

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import write_json_file
from solveur.verification.calculix_composite_conical_cutout import (
    build_conical_s8r_mesh,
    build_loaded_qf_model,
    parse_calculix_composite_ply_stresses,
    write_conical_s8r_input,
)
from solveur.verification.vnv_manifest import write_vnv_manifest


STUDY_ID = "VNV-COMP-CONICAL-CUTOUT-PLY-STRESS-CALCULIX-S8R-012"


class CompositeConicalPlyStressCalculixCorrelation:
    """Compare lamina stresses over a regular annular path, never at the edge."""

    study_id = STUDY_ID
    meshes = ((8, 24), (12, 36), (16, 48))
    path_center = 0.50
    path_half_width = 0.12

    def __init__(self, output_dir: str | Path, *, image: str = "qf-solver/calculix-nafems13h:2.20"):
        self.output_dir = Path(output_dir).resolve()
        self.image = image

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        rows = [self._run_mesh(radial, circumferential) for radial, circumferential in self.meshes]
        fine_error = float(rows[-1]["stress_l2_difference"])
        qf_increment = _relative_vectors(rows[-1]["qf_stress_vector"], rows[-2]["qf_stress_vector"])
        calculix_increment = _relative_vectors(rows[-1]["calculix_stress_vector"], rows[-2]["calculix_stress_vector"])
        checks = [
            _upper("fine_tangential_ply_stress_difference", fine_error, 0.10),
            _upper("qf_final_path_increment", qf_increment, 0.10),
            _upper("calculix_final_path_increment", calculix_increment, 0.10),
        ]
        passed = all(str(check["status"]) == "PASS" for check in checks)
        summary: dict[str, object] = {
            "study_id": STUDY_ID,
            "status": "PASS_EXTERNAL_CORRELATION" if passed else "WARNING",
            "maturity": "experimental",
            "external_solver": {"name": "CalculiX", "version": "2.20", "element": "S8R COMPOSITE"},
            "comparison_basis": (
                "Same conical corner mesh and QF-consistent nodal pressure vector. "
                "For every selected element, QF material-axis stresses are compared directly "
                "with CalculiX orientation-output stresses, then averaged by ply over all integration points."
            ),
            "path": {
                "coordinate": "eta=(radius-0.20 m)/(0.55 m)",
                "accepted_interval": [self.path_center - self.path_half_width, self.path_center + self.path_half_width],
                "reason": "The fixed-distance annular band excludes the central free edge and the clamped outer rim.",
            },
            "stress_components": ["S11_material", "S22_material", "S12_material"],
            "rows": rows,
            "checks": checks,
            "limitations": [
                "This is a tangent in-plane lamina-stress comparison, not an acceptance of S13 or free-edge peaks.",
                "MITC4 is planar and linear while CalculiX S8R is quadratic; convergence is required on both formulations.",
                "The deck receives QF's already-integrated pressure vector and therefore does not validate native CalculiX pressure quadrature.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(rows)
        self._write_report(summary)
        write_vnv_manifest(self.output_dir, STUDY_ID)
        return summary

    def _run_mesh(self, radial: int, circumferential: int) -> dict[str, object]:
        model, _ = build_loaded_qf_model(radial, circumferential)
        qf_result = solve_model(model)
        mesh = build_conical_s8r_mesh(radial, circumferential)
        stem = f"composite_conical_ply_stress_{radial}x{circumferential}"
        write_conical_s8r_input(
            self.output_dir / f"{stem}.inp", mesh, model, include_ply_stress_output=True
        )
        self._execute(stem)
        records = parse_calculix_composite_ply_stresses(self.output_dir / f"{stem}.dat")
        selected = _path_elements(model, self.path_center, self.path_half_width)
        qf_by_ply = _qf_path_stresses(qf_result.element_results, selected)
        calculix_by_ply = _calculix_path_stresses(records, selected)
        qf_vector = np.asarray(qf_by_ply, dtype=float).reshape(-1)
        calculix_vector = np.asarray(calculix_by_ply, dtype=float).reshape(-1)
        return {
            "radial_elements": radial,
            "circumferential_elements": circumferential,
            "elements": radial * circumferential,
            "path_elements": len(selected),
            "qf_stress_by_ply_pa": qf_by_ply,
            "calculix_stress_by_ply_pa": calculix_by_ply,
            "qf_stress_vector": qf_vector.tolist(),
            "calculix_stress_vector": calculix_vector.tolist(),
            "stress_l2_difference": _relative_vectors(qf_vector, calculix_vector),
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
            raise RuntimeError("CalculiX conical ply-stress run failed: " + completed.stderr[-2000:])

    def _plot(self, rows: list[dict[str, object]]) -> None:
        figure, axis = plt.subplots(figsize=(7.4, 4.5))
        axis.semilogx(
            [int(row["elements"]) for row in rows],
            [100.0 * float(row["stress_l2_difference"]) for row in rows],
            "o-",
            label="QF MITC4 / CalculiX S8R",
        )
        axis.axhline(10.0, color="#555555", linestyle="--", linewidth=1.0, label="Seuil borne 10 %")
        axis.set(
            xlabel="Elements coque",
            ylabel="Ecart L2 contraintes tangentielles [%]",
            title="Contraintes par pli sur chemin annulaire interieur",
        )
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        figure.tight_layout()
        figure.savefig(self.output_dir / "conical_ply_stress_calculix_convergence.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {STUDY_ID}",
            "",
            f"Statut automatise : **{summary['status']}**",
            "",
            "Les contraintes de chaque pli sont comparees dans ses axes materiau, apres",
            "moyenne sur une couronne `0,38 <= eta <= 0,62`.",
            "Cette bande reste a distance de l'ouverture libre et de l'encastrement.",
            "",
            "| Maillage | Elements chemin | Ecart L2 QF/CalculiX |",
            "| --- | ---: | ---: |",
        ]
        for row in summary["rows"]:
            lines.append(
                f"| {row['radial_elements']}x{row['circumferential_elements']} | {row['path_elements']} | "
                f"{100.0 * float(row['stress_l2_difference']):.3f} % |"
            )
        lines.extend(
            [
                "",
                "![Convergence contraintes par pli](conical_ply_stress_calculix_convergence.png)",
                "",
                "Les valeurs S13, les pics de bord libre, les effets interlaminaires et les",
                "criteres de rupture restent hors du present critere d'acceptation.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _path_elements(model: FiniteElementModel, center: float, half_width: float) -> set[int]:
    selected: set[int] = set()
    for index, element in enumerate(model.elements):
        point = np.mean(model.nodes[np.asarray(element.nodes, dtype=int)], axis=0)
        eta = (float(np.hypot(point[0], point[1])) - 0.20) / 0.55
        if abs(eta - center) <= half_width:
            selected.add(index)
    if not selected:
        raise ValueError("The controlled conical stress path contains no shell elements.")
    return selected


def _qf_path_stresses(element_results: list[dict[str, object]], selected: set[int]) -> list[list[float]]:
    values: dict[int, list[np.ndarray]] = {ply: [] for ply in range(4)}
    for index in selected:
        for result in element_results[index]["ply_results"]:
            if result["location"] == "middle":
                values[int(result["ply_index"])].append(np.asarray(result["material_stress"], dtype=float))
    return [_mean(values[ply]).tolist() for ply in range(4)]


def _calculix_path_stresses(records: list[dict[str, object]], selected: set[int]) -> list[list[float]]:
    values: dict[int, list[np.ndarray]] = {ply: [] for ply in range(4)}
    for record in records:
        index = int(record["element"]) - 1
        if index not in selected:
            continue
        # CalculiX *EL PRINT writes this composite stress in the element
        # orientation. QF exposes the same axes as material_stress.
        stress = np.asarray(record["stress_output"], dtype=float)
        values[int(record["ply_index"])].append(np.array([stress[0], stress[1], stress[3]]))
    return [_mean(values[ply]).tolist() for ply in range(4)]


def _mean(values: list[np.ndarray]) -> np.ndarray:
    if not values:
        raise ValueError("Missing stress samples for a laminate ply on the controlled path.")
    return np.mean(np.asarray(values, dtype=float), axis=0)


def _relative_vectors(left: object, right: object) -> float:
    numerator = float(np.linalg.norm(np.asarray(left, dtype=float) - np.asarray(right, dtype=float)))
    denominator = max(float(np.linalg.norm(np.asarray(right, dtype=float))), np.finfo(float).tiny)
    return numerator / denominator


def _upper(identifier: str, value: float, limit: float) -> dict[str, object]:
    return {"id": identifier, "value": value, "limit": limit, "status": "PASS" if value <= limit else "FAIL"}
