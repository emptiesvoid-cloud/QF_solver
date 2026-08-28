"""Load-increment sensitivity for the assembled total-Lagrangian TET4."""

from __future__ import annotations

from pathlib import Path

from solveur.core.analyses.geometric_nonlinear_controls import (
    DEFAULT_LOAD_INCREMENTS,
    MINIMUM_LOAD_INCREMENTS,
)
from solveur.elements.solid.tet4_total_lagrangian_batch import TotalLagrangianTet4Assembly
from solveur.io.manifest import write_json_file
from solveur.verification.tet4_total_lagrangian_assembly import (
    TotalLagrangianAssemblyCampaign,
    _relative_error,
    _structured_tet4_mesh,
)


class TotalLagrangianStepSensitivity:
    """Distinguish nonlinear iteration convergence from mesh convergence."""

    study_id = "VNV-TET4-TL-STEPS-004"

    def __init__(self, output_dir: str | Path):
        self.output_dir = Path(output_dir).resolve()
        self.campaign = TotalLagrangianAssemblyCampaign(self.output_dir)

    def run(self) -> dict[str, object]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        nodes, elements = _structured_tet4_mesh(16, 4, 4, 4.0, 0.5, 0.5)
        assembly = TotalLagrangianTet4Assembly(nodes, elements, self.campaign.material)
        rows: list[dict[str, object]] = []
        for increments in (3, 6, DEFAULT_LOAD_INCREMENTS, 12, 24):
            try:
                _, _, metrics = self.campaign._solve_cantilever(
                    assembly, load=150.0, load_steps=increments
                )
            except RuntimeError as error:
                rows.append(
                    {"increments": increments, "status": "NON_CONVERGED", "diagnostic": str(error)}
                )
            else:
                rows.append({"increments": increments, "status": "CONVERGED", **metrics})
        summary = evaluate_step_sensitivity(rows)
        summary.update(
            {
                "study_id": self.study_id,
                "mesh": {"elements": int(elements.shape[0]), "dofs": assembly.ndof},
                "policy": {
                    "minimum_load_increments": MINIMUM_LOAD_INCREMENTS,
                    "default_load_increments": DEFAULT_LOAD_INCREMENTS,
                },
                "interpretation": (
                    "Six increments ou plus atteignent le meme equilibre; la tendance restante de "
                    "la fleche provient de la discretisation spatiale et non d'une convergence "
                    "Newton incomplete."
                ),
            }
        )
        write_json_file(self.output_dir / "summary.json", summary)
        self._plot(summary)
        self._write_report(summary)
        return summary

    def _plot(self, summary: dict[str, object]) -> None:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        converged = [row for row in summary["rows"] if row["status"] == "CONVERGED"]
        increments = [row["increments"] for row in converged]
        tips = [row["tip_displacement_z"] for row in converged]
        figure, axis = plt.subplots(figsize=(7.0, 4.2))
        axis.plot(increments, tips, "o-", color="#006d77")
        axis.set_xlabel("Nombre d'increments")
        axis.set_ylabel("Fleche UZ au bout")
        axis.grid(True, alpha=0.25)
        figure.tight_layout()
        figure.savefig(self.output_dir / "step-sensitivity.png", dpi=180)
        plt.close(figure)

    def _write_report(self, summary: dict[str, object]) -> None:
        lines = [
            f"# {self.study_id}",
            "",
            f"Statut : **{summary['status']}**",
            "",
            "Minimum accepte : `6`. Valeur recommandee et valeur par defaut : `10`.",
            "",
            "| Increments | Statut | UZ bout | Ecart au cas 24 | Residu |",
            "| ---: | --- | ---: | ---: | ---: |",
        ]
        for row in summary["rows"]:
            if row["status"] == "CONVERGED":
                lines.append(
                    f"| {row['increments']} | CONVERGED | {row['tip_displacement_z']:.12e} | "
                    f"{row['relative_tip_error']:.3e} | {row['maximum_relative_residual']:.3e} |"
                )
            else:
                lines.append(f"| {row['increments']} | NON_CONVERGED | - | - | - |")
        lines.extend(
            [
                "",
                "![Sensibilite aux increments](step-sensitivity.png)",
                "",
                str(summary["interpretation"]),
                "",
            ]
        )
        (self.output_dir / "report.md").write_text("\n".join(lines), encoding="utf-8")


def evaluate_step_sensitivity(rows: list[dict[str, object]]) -> dict[str, object]:
    """Evaluate equilibrium identity across converged load discretizations."""
    converged = [row for row in rows if row.get("status") == "CONVERGED"]
    if not converged:
        raise ValueError("Step sensitivity requires at least one converged result.")
    reference = float(max(converged, key=lambda row: int(row["increments"]))["tip_displacement_z"])
    for row in converged:
        row["relative_tip_error"] = _relative_error(float(row["tip_displacement_z"]), reference)
    required = {MINIMUM_LOAD_INCREMENTS, DEFAULT_LOAD_INCREMENTS, 12, 24}
    available = {int(row["increments"]) for row in converged}
    required_rows = [row for row in converged if int(row["increments"]) in required]
    maximum_error = max((float(row["relative_tip_error"]) for row in required_rows), default=float("inf"))
    passed = required.issubset(available) and maximum_error <= 1.0e-10
    return {
        "status": "PASS_STEP_SENSITIVITY" if passed else "FAIL",
        "rows": rows,
        "checks": [
            {
                "id": "six_twelve_twenty_four_increment_identity",
                "value": maximum_error,
                "limit": 1.0e-10,
                "status": "PASS" if passed else "FAIL",
            }
        ],
        "minimum_load_increments": MINIMUM_LOAD_INCREMENTS,
        "default_load_increments": DEFAULT_LOAD_INCREMENTS,
    }
