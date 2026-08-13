"""Load-increment sensitivity campaign for the cyclic J2 TET4 bar."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np

from solveur.api import solve_model
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.io.manifest import write_json_file
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.j2_structural import J2StructuralCyclicCampaign


class J2StepSensitivityCampaign:
    """Compare three discretizations of one signed rate-independent path."""

    campaign_id = "VNV-J2-STEP-SENSITIVITY-005"
    subdivisions = (4, 8, 16)
    turning_points = (0.0, 1.0, -1.2, 1.4)

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        mesh = BenchmarkMeshFactory().box_tetra(
            self.output_dir / "j2_step_sensitivity.msh",
            length=1.0,
            width=0.2,
            height=0.2,
            mesh_size=0.18,
            anchors=True,
        )
        setup = J2StructuralCyclicCampaign._setup()
        setup_path = self.output_dir / "model.setup.json"
        write_json_file(setup_path, setup)
        base_model = GmshModelImporter().import_model(mesh, setup_path).model
        rows = [self._solve_level(base_model, subdivisions) for subdivisions in self.subdivisions]
        reference = rows[-1]
        for row in rows:
            row["relative_errors_to_finest"] = {
                key: _relative(float(row[key]), float(reference[key]))
                for key in ("final_axial_displacement", "final_axial_stress", "final_equivalent_plastic_strain")
            }
            row["turning_point_plastic_error"] = _array_relative(
                row["turning_point_equivalent_plastic_strain"],
                reference["turning_point_equivalent_plastic_strain"],
            )
            row["relative_work_errors_to_finest"] = {
                key: _relative(float(row[key]), float(reference[key]))
                for key in ("total_external_work", "total_internal_work")
            }
        maximum_state_error = max(
            max([*row["relative_errors_to_finest"].values(), row["turning_point_plastic_error"]])
            for row in rows
        )
        medium_work_error = max(rows[-2]["relative_work_errors_to_finest"].values())
        summary: dict[str, object] = {
            "campaign_id": self.campaign_id,
            "status": (
                "PASS_INTERNAL" if maximum_state_error <= 1.0e-8 and medium_work_error <= 2.0e-2 else "FAIL"
            ),
            "maturity": "experimental",
            "mesh": {"nodes": base_model.node_count, "elements": len(base_model.elements)},
            "subdivisions_per_branch": list(self.subdivisions),
            "turning_points": list(self.turning_points),
            "levels": rows,
            "maximum_state_relative_sensitivity": maximum_state_error,
            "medium_to_fine_work_relative_sensitivity": medium_work_error,
            "state_acceptance_limit": 1.0e-8,
            "work_acceptance_limit": 2.0e-2,
            "interpretation": (
                "The tested small-strain isotropic J2 response is increment-insensitive on this proportional "
                "cyclic path. This does not qualify arbitrary non-proportional paths or geometric nonlinearity."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        self._plot(summary)
        return summary

    def _solve_level(self, base_model, subdivisions: int) -> dict[str, object]:
        model = deepcopy(base_model)
        path = _subdivided_path(self.turning_points, subdivisions)
        model.analysis.parameters["load_path"] = path
        model.analysis.parameters["load_steps"] = len(path)
        result = solve_model(model)
        data = result.to_dict()
        steps = data["solver"]["steps"]
        x_max = float(np.max(model.nodes[:, 0]))
        loaded_nodes = np.flatnonzero(np.isclose(model.nodes[:, 0], x_max))
        axial_dofs = [result.dofs.node_indices(int(node), ("UX",))[0] for node in loaded_nodes]
        turn_indices = [(index + 1) * subdivisions - 1 for index in range(3)]
        return {
            "subdivisions_per_branch": subdivisions,
            "increments": len(path),
            "maximum_step_residual": max(float(step["relative_residual"]) for step in steps),
            "final_axial_displacement": float(np.mean(result.displacements[axial_dofs])),
            "final_axial_stress": float(np.mean([row["stress"][0] for row in data["element_results"]])),
            "final_equivalent_plastic_strain": float(steps[-1]["equivalent_plastic_strain_max"]),
            "turning_point_equivalent_plastic_strain": [
                float(steps[index]["equivalent_plastic_strain_max"]) for index in turn_indices
            ],
            "total_external_work": float(sum(step["incremental_external_work"] for step in steps)),
            "total_internal_work": float(sum(step["incremental_internal_work"] for step in steps)),
        }

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.campaign_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "| Subdivisions/branche | Increments | UX final | S11 final [Pa] | PEEQ final | Ecart etat | Ecart travail |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        for row in summary["levels"]:
            error = max([*row["relative_errors_to_finest"].values(), row["turning_point_plastic_error"]])
            work_error = max(row["relative_work_errors_to_finest"].values())
            lines.append(
                f"| {row['subdivisions_per_branch']} | {row['increments']} | "
                f"{row['final_axial_displacement']:.6e} | {row['final_axial_stress']:.6e} | "
                f"{row['final_equivalent_plastic_strain']:.6e} | {error:.6e} | {work_error:.6e} |"
            )
        lines.extend(["", "![Sensibilite au pas](step_sensitivity.png)", "", str(summary["interpretation"]), ""])
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")

    def _plot(self, summary: dict[str, object]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        levels = summary["levels"]
        increments = [row["increments"] for row in levels]
        state_errors = [
            max([*row["relative_errors_to_finest"].values(), row["turning_point_plastic_error"]])
            for row in levels
        ]
        work_errors = [max(row["relative_work_errors_to_finest"].values()) for row in levels]
        floor = np.finfo(float).eps
        fig, axis = plt.subplots(figsize=(7.2, 4.4))
        axis.semilogy(increments, np.maximum(state_errors, floor), "o-", color="#006d77", label="etat")
        axis.semilogy(increments, np.maximum(work_errors, floor), "s-", color="#bb3e03", label="travail")
        axis.axhline(float(summary["state_acceptance_limit"]), color="#006d77", linestyle="--")
        axis.axhline(float(summary["work_acceptance_limit"]), color="#bb3e03", linestyle="--")
        axis.set(xlabel="Nombre total d'increments", ylabel="Sensibilite relative maximale")
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
        fig.tight_layout()
        fig.savefig(self.output_dir / "step_sensitivity.png", dpi=180)
        plt.close(fig)


def _subdivided_path(turning_points: tuple[float, ...], subdivisions: int) -> list[float]:
    path: list[float] = []
    for start, end in zip(turning_points[:-1], turning_points[1:], strict=True):
        path.extend(start + (end - start) * index / subdivisions for index in range(1, subdivisions + 1))
    return path


def _relative(value: float, reference: float) -> float:
    return abs(value - reference) / max(abs(reference), np.finfo(float).tiny)


def _array_relative(values: object, reference: object) -> float:
    left = np.asarray(values, dtype=float)
    right = np.asarray(reference, dtype=float)
    return float(np.linalg.norm(left - right) / max(float(np.linalg.norm(right)), np.finfo(float).tiny))
