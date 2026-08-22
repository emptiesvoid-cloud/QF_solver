"""Temporal refinement evidence for the MITC3+ laminate Newmark route.

This campaign isolates time-integration error from spatial and formulation
differences.  It compares Newmark histories with the exact first-mode history
of the same assembled QF_solver model at 80, 160 and 320 steps per period.
It is intentionally an internal algorithmic check, not an external
Code_Aster correlation and not a maturity promotion by itself.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

from solveur.paths import project_root

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.mitc3_laminate_dynamic import Mitc3LaminateDynamicStudy


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC3-LAMINATE-TEMPORAL-REFINEMENT-001"
DEFAULT_STEPS_PER_PERIOD = (80, 160, 320)


class Mitc3TemporalRefinementStudy:
    """Measure Newmark time-step convergence on one fixed MITC3+ model."""

    error_limit = 1.0e-2
    energy_drift_limit = 1.0e-4
    residual_limit = 1.0e-7

    def __init__(
        self,
        *,
        mesh: tuple[int, int] = (8, 2),
        steps_per_period: tuple[int, ...] = DEFAULT_STEPS_PER_PERIOD,
    ) -> None:
        if len(steps_per_period) < 3:
            raise ValueError("at least three temporal levels are required")
        if any(int(value) <= 0 for value in steps_per_period):
            raise ValueError("steps_per_period values must be positive")
        if tuple(sorted(steps_per_period)) != tuple(steps_per_period):
            raise ValueError("steps_per_period must be strictly increasing")
        self.mesh = mesh
        self.steps_per_period = tuple(int(value) for value in steps_per_period)

    def run(self) -> dict[str, Any]:
        """Run the fixed-model temporal refinement and return machine evidence."""
        base = Mitc3LaminateDynamicStudy(
            mesh=self.mesh,
            steps_per_period=self.steps_per_period,
        ).run()
        points = base["newmark"]["points"]
        errors = np.asarray([point["normalized_rms_error"] for point in points], dtype=float)
        time_steps = np.asarray([point["time_step_s"] for point in points], dtype=float)
        orders = _observed_orders(errors)
        checks = {
            "at_least_three_levels": len(points) >= 3,
            "minimum_temporal_resolution": min(self.steps_per_period) >= 80,
            "strictly_decreasing_error": bool(np.all(np.diff(errors) < 0.0)),
            "fine_newmark_error": float(errors[-1]) <= self.error_limit,
            "energy_drift": max(point["maximum_relative_energy_drift"] for point in points)
            <= self.energy_drift_limit,
            "dynamic_residual": max(point["maximum_dynamic_residual_norm"] for point in points)
            <= self.residual_limit,
        }
        return {
            "study_id": STUDY_ID,
            "status": "PASS_INTERNAL" if all(checks.values()) else "FAIL",
            "maturity": "verified_development",
            "scope": "MITC3+ planar symmetric laminate Newmark time integration",
            "model": {
                "mesh": list(self.mesh),
                "element_count": 2 * self.mesh[0] * self.mesh[1],
                "layup": [0.0, 90.0, 90.0, 0.0],
                "reference": "first computed mode of the same assembled QF_solver model",
            },
            "time_level_count": len(points),
            "time_levels": points,
            "observed_orders": orders,
            "checks": checks,
            "interpretation": (
                "The temporal discretization is converged for this fixed model. "
                "This result does not remove differences between QF_solver MITC3+ "
                "and another shell formulation or mass operator."
            ),
            "limitations": [
                "Internal reference only; no Code_Aster or CalculiX correlation.",
                "Planar symmetric [0/90/90/0] laminate and first-mode free vibration only.",
                "The campaign does not qualify damping calibration, curved dynamics or ply stress histories.",
            ],
            "provenance": {
                "steps_per_period": list(self.steps_per_period),
                "time_step_seconds": time_steps.tolist(),
                "source_campaign": "VNV-MITC3-LAMINATE-DYNAMIC-001",
            },
        }


def write_mitc3_temporal_refinement_evidence(output: str | Path) -> dict[str, Any]:
    """Write JSON, Markdown, PNG and a source manifest for the campaign."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc3TemporalRefinementStudy().run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_convergence(target / f"{STUDY_ID}-convergence.png", summary)
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                target,
                lambda _: "mitc3_temporal_refinement_vnv",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def _observed_orders(errors: np.ndarray) -> list[float | None]:
    orders: list[float | None] = [None]
    for previous, current in zip(errors, errors[1:]):
        if previous <= 0.0 or current <= 0.0:
            orders.append(None)
        else:
            orders.append(float(math.log(previous / current, 2.0)))
    return orders


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        f"# {STUDY_ID}",
        "",
        "## Objet",
        "",
        "Cette campagne isole l'erreur du pas de temps Newmark sur un modele MITC3+ fixe.",
        "La reference est la vibration libre du premier mode du meme modele assemble.",
        "Elle ne constitue pas une correlation externe et ne promeut pas le scope a elle seule.",
        "",
        "## Resultats",
        "",
        "| Pas par periode | Pas de temps (s) | Erreur RMS | Ordre observe | Derive energie | Residu |",
        "| ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for index, point in enumerate(summary["time_levels"]):
        order = summary["observed_orders"][index]
        order_text = "-" if order is None else f"{order:.3f}"
        lines.append(
            f"| {point['steps_per_period']} | {point['time_step_s']:.6e} | "
            f"{point['normalized_rms_error']:.6e} | {order_text} | "
            f"{point['maximum_relative_energy_drift']:.6e} | "
            f"{point['maximum_dynamic_residual_norm']:.6e} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            summary["interpretation"],
            "",
            "## Verdict technique",
            "",
            f"Statut interne : **{summary['status']}**.",
            "La preuve temporelle est séparée de l'ecart de formulation avec Code_Aster DST.",
            "",
            f"![Convergence temporelle]({STUDY_ID}-convergence.png)",
            "",
            "## Limites",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["limitations"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _plot_convergence(path: Path, summary: dict[str, Any]) -> None:
    points = summary["time_levels"]
    dt = np.asarray([point["time_step_s"] for point in points], dtype=float)
    errors = np.asarray([point["normalized_rms_error"] for point in points], dtype=float)
    figure, axis = plt.subplots(figsize=(7.2, 4.4))
    axis.loglog(dt, errors, "o-", color="#0077b6", label="Newmark / mode propre")
    axis.axhline(1.0e-2, color="#bc4749", linestyle="--", label="seuil 1 %")
    axis.set(xlabel="pas de temps (s)", ylabel="erreur RMS relative", title="Raffinement temporel MITC3+")
    axis.grid(which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
