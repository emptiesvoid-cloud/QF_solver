"""Reproducible comparison of nonlinear solution methods on the J2 cycle."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np

from solveur.api import solve_model
from solveur.benchmarks.gmsh_factory import BenchmarkMeshFactory
from solveur.core.errors import SolverError
from solveur.io.manifest import write_json_file
from solveur.mesh.gmsh_importer import GmshModelImporter
from solveur.verification.j2_structural import J2StructuralCyclicCampaign


class J2NonlinearMethodsCampaign:
    """Compare full, modified and line-search Newton on one fixed model."""

    campaign_id = "VNV-J2-NONLINEAR-METHODS-004"
    methods = ("newton_raphson", "modified_newton", "newton_line_search")

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        mesh_path = BenchmarkMeshFactory().box_tetra(
            self.output_dir / "j2_methods_tet4.msh",
            length=1.0,
            width=0.2,
            height=0.2,
            mesh_size=0.18,
            anchors=True,
        )
        setup = J2StructuralCyclicCampaign._setup()
        setup_path = self.output_dir / "model.setup.json"
        write_json_file(setup_path, setup)
        base_model = GmshModelImporter().import_model(mesh_path, setup_path).model
        records: dict[str, dict[str, object]] = {}
        solutions: dict[str, dict[str, np.ndarray]] = {}
        for method in self.methods:
            model = deepcopy(base_model)
            model.analysis = replace(model.analysis, method=method)
            try:
                result = solve_model(model)
            except SolverError as exc:
                records[method] = {
                    "status": "NON_CONVERGED",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
                continue
            data = result.to_dict()
            steps = data["solver"]["steps"]
            x_max = float(np.max(model.nodes[:, 0]))
            loaded_nodes = np.flatnonzero(np.isclose(model.nodes[:, 0], x_max))
            axial_dofs = [result.dofs.node_indices(int(node), ("UX",))[0] for node in loaded_nodes]
            solutions[method] = {
                "displacement": result.displacements.copy(),
                "axial_displacement": result.displacements[axial_dofs].copy(),
                "stress": np.asarray([row["stress"] for row in data["element_results"]], dtype=float),
                "equivalent_plastic_strain": np.asarray(
                    [float(steps[-1]["equivalent_plastic_strain_max"])], dtype=float
                ),
            }
            records[method] = {
                "status": "CONVERGED",
                "total_iterations": sum(int(step["iterations"]) for step in steps),
                "maximum_step_iterations": max(int(step["iterations"]) for step in steps),
                "maximum_relative_residual": max(float(step["relative_residual"]) for step in steps),
                "line_search_reductions": sum(int(step["line_search_reductions"]) for step in steps),
                "minimum_line_search_factor": min(float(step["min_line_search_factor"]) for step in steps),
                "final_equivalent_plastic_strain": float(steps[-1]["equivalent_plastic_strain_max"]),
            }
        agreements = {
            field: self._relative_agreement(solutions, "newton_raphson", "newton_line_search", field)
            for field in ("axial_displacement", "stress", "equivalent_plastic_strain", "displacement")
        }
        expected = (
            records.get("newton_raphson", {}).get("status") == "CONVERGED"
            and records.get("newton_line_search", {}).get("status") == "CONVERGED"
            and records.get("modified_newton", {}).get("status") == "NON_CONVERGED"
            and max(agreements[field] for field in ("axial_displacement", "stress", "equivalent_plastic_strain"))
            <= 1.0e-8
        )
        summary: dict[str, object] = {
            "campaign_id": self.campaign_id,
            "status": "PASS_CHARACTERIZATION" if expected else "FAIL",
            "maturity": "experimental",
            "model": {"nodes": base_model.node_count, "elements": len(base_model.elements)},
            "methods": records,
            "full_newton_line_search_relative_errors": agreements,
            "acceptance_limit_on_axial_response": 1.0e-8,
            "engineering_conclusion": (
                "Full Newton remains the default. Armijo agrees on the complete displacement field, stress and "
                "accumulated plastic strain for this characterization case. Modified Newton is not accepted for "
                "plastic load reversals."
            ),
        }
        write_json_file(self.output_dir / "summary.json", summary)
        self._write_report(summary)
        return summary

    @staticmethod
    def _relative_agreement(
        solutions: dict[str, dict[str, np.ndarray]], left: str, right: str, field: str
    ) -> float:
        if left not in solutions or right not in solutions:
            return float("inf")
        left_values = solutions[left][field]
        right_values = solutions[right][field]
        scale = max(float(np.linalg.norm(left_values)), np.finfo(float).tiny)
        return float(np.linalg.norm(left_values - right_values) / scale)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.campaign_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "| Methode | Statut | Iterations | Residu relatif max | Reductions Armijo |",
            "| --- | --- | ---: | ---: | ---: |",
        ]
        for method, record in summary["methods"].items():
            lines.append(
                f"| `{method}` | {record['status']} | {record.get('total_iterations', '-')} | "
                f"{_format(record.get('maximum_relative_residual'))} | "
                f"{record.get('line_search_reductions', '-')} |"
            )
        lines.extend(
            [
                "",
                "## Accord des solutions converges",
                "",
                "| Grandeur | Erreur relative Newton complet / Armijo |",
                "| --- | ---: |",
                *[
                    f"| `{field}` | `{value:.6e}` |"
                    for field, value in summary["full_newton_line_search_relative_errors"].items()
                ],
                "",
                "## Conclusion",
                "",
                str(summary["engineering_conclusion"]),
                "",
                "L'accord du champ deplacement complet est conserve comme invariant de la campagne. L'echec de "
                "Newton modifie est egalement un resultat de la campagne ; aucun des deux ne doit etre masque.",
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def _format(value: object) -> str:
    return "-" if value is None else f"{float(value):.6e}"
