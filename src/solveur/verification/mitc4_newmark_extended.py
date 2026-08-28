"""Damped and forced analytical Newmark verification for MITC4."""

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
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel, NodalLoad
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.mitc4_modal import Mitc4ModalCantileverStudy
from solveur.verification.mitc4_newmark import _initial_state, _tip_midline_node


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC4-NEWMARK-DAMPED-FORCED-003"


class Mitc4NewmarkDampedForcedStudy:
    """Check damped decay and sinusoidal modal forcing against closed forms."""

    amplitude = 1.0e-4
    damping_ratio = 0.02
    forcing_frequency_ratio = 0.7
    rms_error_limit = 0.01
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
        omega = 2.0 * math.pi * frequency
        period = 1.0 / frequency
        tip = _tip_midline_node(nodes)
        tip_index = modal.dofs.index(tip, "UZ")
        mode = np.asarray(modal.modes[:, 0], dtype=float)
        scaled_mode = mode * (self.amplitude / mode[tip_index])
        damped = [
            self._damped_point(model, tip, scaled_mode, omega, period, count)
            for count in self.steps_per_period
        ]
        model, _ = Mitc4ModalCantileverStudy().build_model(*self.mesh)
        model.loads = modal_nodal_loads(model, modal.dofs, mode)
        forced = [
            self._forced_point(model, tip, mode[tip_index], omega, period, count)
            for count in self.steps_per_period
        ]
        damped_orders = _observed_orders(damped)
        forced_orders = _observed_orders(forced)
        checks = {
            "damped_rms_history": damped[-1]["normalized_rms_error"] <= self.rms_error_limit,
            "forced_rms_history": forced[-1]["normalized_rms_error"] <= self.rms_error_limit,
            "damped_second_order": min(damped_orders) >= self.minimum_observed_order,
            "forced_second_order": min(forced_orders) >= self.minimum_observed_order,
            "damped_energy_decay": all(point["final_to_first_energy_ratio"] < 1.0 for point in damped),
            "nonnegative_damping_power": min(point["minimum_damping_power"] for point in damped) >= -1.0e-14,
            "monotonic_convergence": _monotonic(damped) and _monotonic(forced),
        }
        return {
            "study_id": STUDY_ID,
            "reference": {
                "natural_frequency_hz": frequency,
                "natural_period_s": period,
                "damped_free": {
                    "damping_ratio": self.damping_ratio,
                    "rayleigh_alpha": 2.0 * self.damping_ratio * omega,
                    "equation": "u0*exp(-zeta*omega*t)*(cos(omega_d*t)+zeta/sqrt(1-zeta^2)*sin(omega_d*t))",
                },
                "forced": {
                    "frequency_ratio": self.forcing_frequency_ratio,
                    "load_vector": "F0 = M*phi1",
                    "equation": "q=(sin(Omega*t)-(Omega/omega)*sin(omega*t))/(omega^2-Omega^2)",
                },
            },
            "model": {
                "mesh": list(self.mesh),
                "element_count": self.mesh[0] * self.mesh[1],
                "probe": {"node": tip, "dof": "UZ", "label": "tip_uz"},
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
            },
            "acceptance": {
                "normalized_rms_error_max": self.rms_error_limit,
                "observed_order_min": self.minimum_observed_order,
                "damped_energy_must_decay": True,
                "damping_power_min": -1.0e-14,
            },
            "damped_points": damped,
            "forced_points": forced,
            "damped_observed_orders": damped_orders,
            "forced_observed_orders": forced_orders,
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "limitations": [
                "Mass-proportional Rayleigh damping is verified only for the first isolated mode.",
                "The forced case is non-resonant and uses a modal load to provide a closed-form oracle.",
                "Broadband, nonlinear and commercial-solver correlations remain outside this study.",
            ],
        }

    def _damped_point(
        self,
        model: FiniteElementModel,
        tip: int,
        scaled_mode: np.ndarray,
        omega: float,
        period: float,
        steps_per_period: int,
    ) -> dict[str, Any]:
        time_step = period / steps_per_period
        model.loads = []
        model.analysis = AnalysisSettings.from_raw(
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": time_step,
                "steps": self.periods * steps_per_period,
                "rayleigh_alpha": 2.0 * self.damping_ratio * omega,
                "rayleigh_beta": 0.0,
                "load_factors": [0.0],
                "initial_displacements": _initial_state(model.dof_manager(), scaled_mode),
                "history_probes": [{"node": tip, "dof": "UZ", "label": "tip_uz"}],
            }
        )
        result = solve_model(model, enforce_policy=False)
        times, response = _probe_history(result)
        damped_omega = omega * math.sqrt(1.0 - self.damping_ratio**2)
        ratio = self.damping_ratio / math.sqrt(1.0 - self.damping_ratio**2)
        analytical = self.amplitude * np.exp(-self.damping_ratio * omega * times) * (
            np.cos(damped_omega * times) + ratio * np.sin(damped_omega * times)
        )
        point = _point_metrics(result, steps_per_period, time_step, times, response, analytical)
        history = result.solver["time_history"]
        point["final_to_first_energy_ratio"] = float(
            history[-1]["total_energy"] / max(float(history[0]["total_energy"]), 1.0e-30)
        )
        point["minimum_damping_power"] = min(float(row["damping_power"]) for row in history)
        return point

    def _forced_point(
        self,
        model: FiniteElementModel,
        tip: int,
        probe_mode_value: float,
        omega: float,
        period: float,
        steps_per_period: int,
    ) -> dict[str, Any]:
        time_step = period / steps_per_period
        forcing_omega = self.forcing_frequency_ratio * omega
        duration = self.periods * 2.0 * math.pi / forcing_omega
        steps = int(round(duration / time_step))
        model.analysis = AnalysisSettings.from_raw(
            {
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": time_step,
                "steps": steps,
                "load_function": "sine",
                "load_frequency_hz": forcing_omega / (2.0 * math.pi),
                "history_probes": [{"node": tip, "dof": "UZ", "label": "tip_uz"}],
            }
        )
        result = solve_model(model, enforce_policy=False)
        times, response = _probe_history(result)
        generalized = (
            np.sin(forcing_omega * times)
            - self.forcing_frequency_ratio * np.sin(omega * times)
        ) / (omega**2 - forcing_omega**2)
        analytical = probe_mode_value * generalized
        return _point_metrics(result, steps_per_period, time_step, times, response, analytical)


def write_mitc4_newmark_extended_evidence(output: str | Path) -> dict[str, Any]:
    """Write the extended Newmark V&V evidence bundle."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4NewmarkDampedForcedStudy().run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_convergence(summary, target / f"{STUDY_ID}-convergence.png")
    _plot_histories(summary, target / f"{STUDY_ID}-histories.png")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                target,
                lambda _: "mitc4_newmark_extended_vnv",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def modal_nodal_loads(
    model: FiniteElementModel,
    dofs: object,
    mode: np.ndarray,
) -> list[NodalLoad]:
    assembler = GlobalAssembler()
    force = np.asarray(assembler.assemble_mass(model, dofs) @ mode, dtype=float)
    fixed = set(int(value) for value in assembler.fixed_indices(model, dofs))
    loads = []
    for node, names in dofs.node_dofs.items():
        for name in names:
            index = dofs.index(node, name)
            if index not in fixed and abs(force[index]) > 1.0e-16:
                loads.append(NodalLoad(node=node, dof=name, value=float(force[index])))
    return loads


def _probe_history(result: object) -> tuple[np.ndarray, np.ndarray]:
    history = result.solver["time_history"]
    times = np.asarray([row["time"] for row in history], dtype=float)
    response = np.asarray(
        [row["probes"]["tip_uz"]["displacement"] for row in history],
        dtype=float,
    )
    return times, response


def _point_metrics(
    result: object,
    steps_per_period: int,
    time_step: float,
    times: np.ndarray,
    response: np.ndarray,
    analytical: np.ndarray,
) -> dict[str, Any]:
    scale = max(float(np.max(np.abs(analytical))), 1.0e-30)
    return {
        "steps_per_period": steps_per_period,
        "time_step_s": time_step,
        "step_count": int(times.size),
        "normalized_rms_error": float(np.sqrt(np.mean((response - analytical) ** 2)) / scale),
        "maximum_dynamic_residual_norm": max(
            float(row["dynamic_residual_norm"]) for row in result.solver["time_history"]
        ),
        "times_s": times.tolist(),
        "probe_displacements_m": response.tolist(),
        "analytical_displacements_m": analytical.tolist(),
    }


def _observed_orders(points: list[dict[str, Any]]) -> list[float]:
    return [
        math.log(previous["normalized_rms_error"] / current["normalized_rms_error"])
        / math.log(current["steps_per_period"] / previous["steps_per_period"])
        for previous, current in zip(points, points[1:])
    ]


def _monotonic(points: list[dict[str, Any]]) -> bool:
    return all(
        current["normalized_rms_error"] < previous["normalized_rms_error"]
        for previous, current in zip(points, points[1:])
    )


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    rows = []
    for family, points in (("amorti", summary["damped_points"]), ("force", summary["forced_points"])):
        rows.extend(
            f"| {family} | {point['steps_per_period']} | {point['time_step_s']:.6e} | "
            f"{100.0 * point['normalized_rms_error']:.4f} % | "
            f"{point['maximum_dynamic_residual_norm']:.3e} |"
            for point in points
        )
    rows_text = "\n".join(rows)
    path.write_text(
        f"""# {STUDY_ID}

## Objet

Verification analytique de Newmark MITC4 en vibration libre amortie et sous
chargement modal sinusoidal non resonant.

| Cas | Pas/periode | Delta t (s) | Erreur RMS | Residu max |
| --- | ---: | ---: | ---: | ---: |
{rows_text}

Statut : **{summary['status']}**.

![Convergence]({STUDY_ID}-convergence.png)

![Historiques]({STUDY_ID}-histories.png)
""",
        encoding="utf-8",
    )


def _plot_convergence(summary: dict[str, Any], path: Path) -> None:
    figure, axis = plt.subplots(figsize=(7.2, 4.4))
    for label, points, style in (
        ("libre amorti", summary["damped_points"], "o-"),
        ("force sinusoidal", summary["forced_points"], "s-"),
    ):
        axis.loglog(
            [point["steps_per_period"] for point in points],
            [point["normalized_rms_error"] for point in points],
            style,
            label=label,
        )
    axis.set_xlabel("pas par periode naturelle")
    axis.set_ylabel("erreur RMS normalisee")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_histories(summary: dict[str, Any], path: Path) -> None:
    damped = summary["damped_points"][-1]
    forced = summary["forced_points"][-1]
    figure, axes = plt.subplots(2, 1, figsize=(7.2, 6.4), sharex=False)
    for axis, point, title in (
        (axes[0], damped, "vibration libre amortie"),
        (axes[1], forced, "chargement modal sinusoidal"),
    ):
        axis.plot(point["times_s"], point["analytical_displacements_m"], "k--", label="analytique")
        axis.plot(point["times_s"], point["probe_displacements_m"], color="#006d77", label="QF_solver")
        axis.set_ylabel("UZ (m)")
        axis.set_title(title)
        axis.grid(True, alpha=0.25)
        axis.legend()
    axes[-1].set_xlabel("temps (s)")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
