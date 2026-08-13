"""Time-step verification of MITC4 free vibration with Newmark integration."""

from __future__ import annotations

from solveur.paths import project_root

import math
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.analysis import AnalysisSettings
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.mitc4_modal import Mitc4ModalCantileverStudy


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC4-NEWMARK-FREE-002"


class Mitc4NewmarkFreeVibrationStudy:
    """Compare modal free vibration with the analytical cosine response."""

    amplitude = 1.0e-4
    rms_error_limit = 0.01
    period_return_error_limit = 0.02
    energy_drift_limit = 1.0e-4
    minimum_observed_order = 1.8

    def __init__(
        self,
        steps_per_period: tuple[int, ...] = (20, 40, 80, 160),
        *,
        periods: int = 3,
        mesh: tuple[int, int] = (8, 2),
    ) -> None:
        self.steps_per_period = steps_per_period
        self.periods = periods
        self.mesh = mesh

    def run(self) -> dict[str, Any]:
        model, nodes = Mitc4ModalCantileverStudy().build_model(*self.mesh)
        modal = solve_model(model, enforce_policy=False)
        frequency = float(modal.frequencies_hz[0])
        period = 1.0 / frequency
        tip = _tip_midline_node(nodes)
        tip_index = modal.dofs.index(tip, "UZ")
        initial_mode = np.asarray(modal.modes[:, 0], dtype=float)
        initial_mode *= self.amplitude / initial_mode[tip_index]
        initial = _initial_state(modal.dofs, initial_mode)
        points = [
            self._point(model, tip, initial, frequency, period, count)
            for count in self.steps_per_period
        ]
        orders = [
            math.log(previous["normalized_rms_error"] / current["normalized_rms_error"])
            / math.log(current["steps_per_period"] / previous["steps_per_period"])
            for previous, current in zip(points, points[1:])
        ]
        final = points[-1]
        checks = {
            "rms_history": final["normalized_rms_error"] <= self.rms_error_limit,
            "period_return": final["period_return_error"] <= self.period_return_error_limit,
            "energy_conservation": max(point["maximum_relative_energy_drift"] for point in points)
            <= self.energy_drift_limit,
            "second_order_convergence": min(orders) >= self.minimum_observed_order,
            "monotonic_time_step_convergence": all(
                current["normalized_rms_error"] < previous["normalized_rms_error"]
                for previous, current in zip(points, points[1:])
            ),
        }
        return {
            "study_id": STUDY_ID,
            "reference": {
                "type": "undamped first-mode free vibration",
                "equation": "u(t) = u0*cos(2*pi*f1*t)",
                "frequency_hz": frequency,
                "period_s": period,
                "amplitude_m": self.amplitude,
                "modal_source": "VNV-MITC4-MODAL-CANTILEVER-002",
            },
            "model": {
                "mesh": list(self.mesh),
                "element_count": self.mesh[0] * self.mesh[1],
                "period_count": self.periods,
                "probe": {"node": tip, "dof": "UZ", "label": "tip_uz"},
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
            },
            "acceptance": {
                "normalized_rms_error_max": self.rms_error_limit,
                "period_return_error_max": self.period_return_error_limit,
                "relative_energy_drift_max": self.energy_drift_limit,
                "observed_order_min": self.minimum_observed_order,
            },
            "points": points,
            "observed_orders": orders,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "limitations": [
                "The response is linear, undamped and initialized with one numerical eigenmode.",
                "Forced response, broadband content and commercial-solver correlation are separate studies.",
            ],
        }

    def _point(
        self,
        model: object,
        tip: int,
        initial: list[dict[str, object]],
        frequency: float,
        period: float,
        steps_per_period: int,
    ) -> dict[str, Any]:
        time_step = period / steps_per_period
        model.analysis = AnalysisSettings.from_raw(
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": time_step,
                "steps": self.periods * steps_per_period,
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "load_factors": [0.0],
                "initial_displacements": initial,
                "history_probes": [{"node": tip, "dof": "UZ", "label": "tip_uz"}],
            }
        )
        result = solve_model(model, enforce_policy=False)
        history = result.solver["time_history"]
        times = np.asarray([row["time"] for row in history], dtype=float)
        response = np.asarray(
            [row["probes"]["tip_uz"]["displacement"] for row in history],
            dtype=float,
        )
        analytical = self.amplitude * np.cos(2.0 * math.pi * frequency * times)
        normalized_rms = float(np.sqrt(np.mean((response - analytical) ** 2)) / self.amplitude)
        return {
            "steps_per_period": steps_per_period,
            "time_step_s": time_step,
            "step_count": len(history),
            "normalized_rms_error": normalized_rms,
            "period_return_error": abs(float(response[-1]) - self.amplitude) / self.amplitude,
            "maximum_relative_energy_drift": max(
                abs(float(row["relative_energy_drift"])) for row in history
            ),
            "maximum_dynamic_residual_norm": max(
                float(row["dynamic_residual_norm"]) for row in history
            ),
            "times_s": times.tolist(),
            "probe_displacements_m": response.tolist(),
            "analytical_displacements_m": analytical.tolist(),
        }


def write_mitc4_newmark_evidence(output: str | Path) -> dict[str, Any]:
    """Generate JSON, Markdown, convergence/history figures and manifest."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4NewmarkFreeVibrationStudy().run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_convergence(summary, target / f"{STUDY_ID}-convergence.png")
    _plot_history(summary, target / f"{STUDY_ID}-history.png")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                target,
                lambda _: "mitc4_newmark_vnv",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def _tip_midline_node(nodes: np.ndarray) -> int:
    candidates = np.flatnonzero(
        np.isclose(nodes[:, 0], np.max(nodes[:, 0])) & np.isclose(nodes[:, 1], 0.0)
    )
    if candidates.size != 1:
        raise ValueError("The controlled Newmark mesh must contain one tip midline node.")
    return int(candidates[0])


def _initial_state(dofs: object, vector: np.ndarray) -> list[dict[str, object]]:
    entries = []
    for node, names in dofs.node_dofs.items():
        for name in names:
            value = float(vector[dofs.index(node, name)])
            if abs(value) > 1.0e-18:
                entries.append({"node": node, "dof": name, "value": value})
    return entries


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    rows = "\n".join(
        f"| {point['steps_per_period']} | {point['time_step_s']:.6e} | "
        f"{100.0 * point['normalized_rms_error']:.4f} % | "
        f"{100.0 * point['period_return_error']:.4f} % | "
        f"{point['maximum_relative_energy_drift']:.3e} | "
        f"{point['maximum_dynamic_residual_norm']:.3e} |"
        for point in summary["points"]
    )
    orders = ", ".join(f"{value:.4f}" for value in summary["observed_orders"])
    path.write_text(
        f"""# {STUDY_ID}

## Objet

Vibration libre MITC4 initialisee par le premier mode verifie. La sonde signee
est comparee a `u0*cos(2*pi*f1*t)` sur trois periodes.

| Pas/periode | Delta t (s) | Erreur RMS | Erreur retour | Derive energie | Residu absolu max |
| ---: | ---: | ---: | ---: | ---: | ---: |
{rows}

Ordres observes : `{orders}`. Statut : **{summary['status']}**.

![Convergence temporelle]({STUDY_ID}-convergence.png)

![Historique temporel]({STUDY_ID}-history.png)
""",
        encoding="utf-8",
    )


def _plot_convergence(summary: dict[str, Any], path: Path) -> None:
    points = summary["points"]
    figure, axis = plt.subplots(figsize=(7.2, 4.4))
    axis.loglog(
        [point["steps_per_period"] for point in points],
        [point["normalized_rms_error"] for point in points],
        "o-",
        color="#006d77",
        label="erreur RMS normalisee",
    )
    axis.set_xlabel("pas par periode")
    axis.set_ylabel("erreur RMS")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_history(summary: dict[str, Any], path: Path) -> None:
    coarse = summary["points"][0]
    fine = summary["points"][-1]
    figure, axis = plt.subplots(figsize=(7.2, 4.4))
    axis.plot(fine["times_s"], fine["analytical_displacements_m"], "k--", label="analytique")
    axis.plot(coarse["times_s"], coarse["probe_displacements_m"], "o", markersize=2.5, label="T/20")
    axis.plot(fine["times_s"], fine["probe_displacements_m"], color="#006d77", label="T/160")
    axis.set_xlabel("temps (s)")
    axis.set_ylabel("UZ sonde (m)")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
