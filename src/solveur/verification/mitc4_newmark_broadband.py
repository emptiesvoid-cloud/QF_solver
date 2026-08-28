"""Wideband MITC4 Newmark verification against exact modal propagation."""

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
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import NodalLoad
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.post.harmonic_shell import HarmonicShellStressPostProcessor
from solveur.verification.mitc4_harmonic_nafems import build_nafems_13h_model
from solveur.verification.transient_modal_oracle import PiecewiseLinearModalOracle


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC4-NEWMARK-BROADBAND-004"


class Mitc4NewmarkBroadbandStudy:
    """Verify pulse, linear chirp and arbitrary tabulated excitation."""

    force_amplitude = 100.0
    damping_ratio = 0.02
    rms_limit = 0.02
    peak_limit = 0.03
    energy_balance_limit = 0.02
    minimum_smooth_order = 1.8
    minimum_pulse_order = 0.8
    minimum_pulse_asymptotic_order = 1.5

    def __init__(
        self,
        steps_per_period: tuple[int, ...] = (40, 80, 160),
        *,
        period_count: float = 4.0,
    ) -> None:
        self.steps_per_period = steps_per_period
        self.period_count = period_count

    def run(self) -> dict[str, Any]:
        base, _ = build_nafems_13h_model(
            analysis={"type": "modal", "method": "eigh", "modes": 8},
            pressure=False,
        )
        center = _center_node(base.nodes)
        base.loads = [NodalLoad(node=center, dof="UZ", value=self.force_amplitude)]
        modal = solve_model(base, enforce_policy=False)
        frequency = float(modal.frequencies_hz[0])
        period = 1.0 / frequency
        alpha = 2.0 * self.damping_ratio * 2.0 * math.pi * frequency
        cases: dict[str, list[dict[str, Any]]] = {name: [] for name in ("pulse", "chirp", "tabulated")}
        for resolution in self.steps_per_period:
            for name in cases:
                cases[name].append(
                    self._point(name, center, frequency, period, alpha, resolution)
                )
        orders = {name: _orders(points) for name, points in cases.items()}
        final = {name: points[-1] for name, points in cases.items()}
        checks = {
            "displacement_rms": max(point["displacement_rms_error"] for point in final.values())
            <= self.rms_limit,
            "stress_rms": max(point["stress_rms_error"] for point in final.values()) <= self.rms_limit,
            "displacement_peak": max(point["displacement_peak_error"] for point in final.values())
            <= self.peak_limit,
            "stress_peak": max(point["stress_peak_error"] for point in final.values()) <= self.peak_limit,
            "energy_balance": max(point["energy_balance_error"] for point in final.values())
            <= self.energy_balance_limit,
            "smooth_second_order": min(
                min(orders["chirp"]), min(orders["tabulated"])
            )
            >= self.minimum_smooth_order,
            "pulse_monotonic_convergence": all(
                current["displacement_rms_error"] < previous["displacement_rms_error"]
                for previous, current in zip(cases["pulse"], cases["pulse"][1:])
            ),
            "pulse_expected_reduced_order": min(orders["pulse"]) >= self.minimum_pulse_order
            and orders["pulse"][-1] >= self.minimum_pulse_asymptotic_order,
            "finite_residual": max(point["maximum_relative_residual"] for point in final.values())
            <= 1.0e-7,
        }
        return {
            "study_id": STUDY_ID,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "reference": {
                "type": "exact mass-normalized modal state-space propagation",
                "load_interpolation": "piecewise linear on every Newmark interval",
                "temporal_integrator": "matrix exponential of augmented [q, qdot, p, pdot] state",
                "independence": "does not call or reproduce the Newmark recurrence",
                "first_frequency_hz": frequency,
            },
            "model": {
                "geometry": "NAFEMS 13H square plate 10 m x 10 m x 0.05 m",
                "mesh": [8, 8],
                "element_count": 64,
                "probe_node": center,
                "probe_displacement": "UZ",
                "probe_stress": "top S11",
                "force_amplitude_n": self.force_amplitude,
                "damping_ratio_at_first_mode": self.damping_ratio,
                "rayleigh_alpha_s_inv": alpha,
            },
            "acceptance": {
                "normalized_rms_error_max": self.rms_limit,
                "relative_peak_error_max": self.peak_limit,
                "energy_balance_error_max": self.energy_balance_limit,
                "smooth_observed_order_min": self.minimum_smooth_order,
                "pulse_observed_order_min": self.minimum_pulse_order,
                "pulse_asymptotic_order_min": self.minimum_pulse_asymptotic_order,
                "relative_residual_max": 1.0e-7,
            },
            "cases": cases,
            "observed_orders": orders,
            "checks": checks,
            "limitations": [
                "The exact oracle shares the assembled MITC4 mass and stiffness, so it isolates temporal error only.",
                "The Code_Aster same-mesh comparison is stored as a separate external correlation.",
                "Small-displacement linear dynamics and mass-proportional damping only.",
            ],
        }

    def _point(
        self,
        case: str,
        center: int,
        frequency: float,
        period: float,
        alpha: float,
        steps_per_period: int,
    ) -> dict[str, Any]:
        dt = period / steps_per_period
        steps = int(round(self.period_count * steps_per_period))
        times = dt * np.arange(steps + 1, dtype=float)
        factors, load_parameters = _excitation(case, times, frequency, period)
        model, _ = build_nafems_13h_model(
            analysis={
                "type": "transient_dynamic",
                "method": "newmark",
                "time_step": dt,
                "steps": steps,
                "newmark_beta": 0.25,
                "newmark_gamma": 0.5,
                "rayleigh_alpha": alpha,
                "rayleigh_beta": 0.0,
                "history_probes": [{"node": center, "dof": "UZ", "label": "center_uz"}],
                "history_shell_stress_probes": [
                    {"node": center, "face": "top", "component": "S11", "label": "center_top_s11"}
                ],
                **load_parameters,
            },
            pressure=False,
        )
        model.loads = [NodalLoad(node=center, dof="UZ", value=self.force_amplitude)]
        result = solve_model(model, enforce_policy=False)
        history = result.solver["time_history"]
        qf_u = np.asarray([row["probes"]["center_uz"]["displacement"] for row in history])
        qf_v = np.asarray([row["probes"]["center_uz"]["velocity"] for row in history])
        qf_s = np.asarray([row["shell_stress_probes"]["center_top_s11"] for row in history])
        assembler = GlobalAssembler()
        full_load = assembler.assemble_loads(model, result.dofs)
        post = HarmonicShellStressPostProcessor()
        oracle = PiecewiseLinearModalOracle(model, rayleigh_alpha=alpha)
        exact = oracle.propagate(
            full_load,
            factors,
            dt,
            displacement_probe_index=result.dofs.index(center, "UZ"),
            stress_probe=lambda vector: float(
                post.averaged_nodal_stress(model, result.dofs, vector, center, face="top")[0].real
            ),
        )
        assert exact.stress_probe is not None
        work = _external_work(factors, qf_v, dt, self.force_amplitude)
        damping = _damping_dissipation(history, dt)
        final_energy = float(history[-1]["total_energy"])
        energy_reference = max(abs(work), final_energy, damping, 1.0e-30)
        return {
            "steps_per_period": steps_per_period,
            "time_step_s": dt,
            "step_count": steps,
            "load_parameters": load_parameters,
            "displacement_rms_error": _normalized_rms(qf_u, exact.displacement_probe),
            "stress_rms_error": _normalized_rms(qf_s, exact.stress_probe),
            "displacement_peak_error": _relative_peak(qf_u, exact.displacement_probe),
            "stress_peak_error": _relative_peak(qf_s, exact.stress_probe),
            "energy_balance_error": abs(final_energy + damping - work) / energy_reference,
            "external_work_j": work,
            "damping_dissipation_j": damping,
            "final_mechanical_energy_j": final_energy,
            "maximum_relative_residual": max(float(value) for value in result.solver["residual_history"])
            / max(self.force_amplitude, 1.0),
            "times_s": exact.times.tolist(),
            "load_factors": factors[1:].tolist(),
            "qf_displacement_m": qf_u.tolist(),
            "oracle_displacement_m": exact.displacement_probe.tolist(),
            "qf_top_s11_pa": qf_s.tolist(),
            "oracle_top_s11_pa": exact.stress_probe.tolist(),
        }


def write_mitc4_newmark_broadband_evidence(output: str | Path) -> dict[str, Any]:
    """Write controlled JSON, Markdown, PNG and SHA-256 manifest evidence."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4NewmarkBroadbandStudy().run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_excitation(summary, target / f"{STUDY_ID}-excitations.png")
    _plot_response(summary, target / f"{STUDY_ID}-displacement.png", stress=False)
    _plot_response(summary, target / f"{STUDY_ID}-stress.png", stress=True)
    _plot_convergence(summary, target / f"{STUDY_ID}-convergence.png")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                target, lambda _: "mitc4_newmark_broadband_vnv", exclude_names=("vnv_manifest.json",)
            ),
        },
    )
    return summary


def _center_node(nodes: np.ndarray) -> int:
    center = np.mean(nodes, axis=0)
    distances = np.linalg.norm(nodes - center, axis=1)
    return int(np.argmin(distances))


def _excitation(
    case: str, times: np.ndarray, frequency: float, period: float
) -> tuple[np.ndarray, dict[str, Any]]:
    if case == "pulse":
        duration = 0.5 * period
        factors = np.where(times <= duration, np.sin(np.pi * times / duration), 0.0)
        return factors, {"load_function": "half_sine_pulse", "pulse_duration": duration}
    if case == "chirp":
        duration = float(times[-1])
        start = 0.2 * frequency
        stop = 4.0 * frequency
        rate = (stop - start) / duration
        factors = np.sin(2.0 * np.pi * (start * times + 0.5 * rate * times**2))
        return factors, {
            "load_function": "linear_chirp",
            "chirp_start_hz": start,
            "chirp_end_hz": stop,
            "chirp_duration": duration,
        }
    duration = float(times[-1])
    envelope = np.sin(np.pi * times / duration) ** 2
    factors = envelope * (
        np.sin(2.0 * np.pi * 0.7 * frequency * times)
        + 0.45 * np.sin(2.0 * np.pi * 2.3 * frequency * times)
        + 0.25 * np.sin(2.0 * np.pi * 3.7 * frequency * times)
    )
    factors /= max(float(np.max(np.abs(factors))), 1.0)
    table = [{"time": float(time), "factor": float(value)} for time, value in zip(times, factors, strict=True)]
    return factors, {"load_table": table}


def _normalized_rms(values: np.ndarray, reference: np.ndarray) -> float:
    return float(np.sqrt(np.mean((values - reference) ** 2)) / max(np.max(np.abs(reference)), 1.0e-30))


def _relative_peak(values: np.ndarray, reference: np.ndarray) -> float:
    peak = float(np.max(np.abs(values)))
    reference_peak = max(float(np.max(np.abs(reference))), 1.0e-30)
    return abs(peak - reference_peak) / reference_peak


def _external_work(factors: np.ndarray, velocities: np.ndarray, dt: float, force: float) -> float:
    power = force * factors * np.concatenate(([0.0], velocities))
    return float(np.trapezoid(power, dx=dt))


def _damping_dissipation(history: list[dict[str, Any]], dt: float) -> float:
    power = np.asarray([0.0, *(float(row["damping_power"]) for row in history)])
    return float(np.trapezoid(power, dx=dt))


def _orders(points: list[dict[str, Any]]) -> list[float]:
    return [
        math.log(previous["displacement_rms_error"] / current["displacement_rms_error"])
        / math.log(current["steps_per_period"] / previous["steps_per_period"])
        for previous, current in zip(points, points[1:])
    ]


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    rows = []
    for case, points in summary["cases"].items():
        rows.extend(
            f"| {case} | {point['steps_per_period']} | {100*point['displacement_rms_error']:.4f} % | "
            f"{100*point['stress_rms_error']:.4f} % | {100*point['energy_balance_error']:.4f} % | "
            f"{point['maximum_relative_residual']:.3e} |"
            for point in points
        )
    path.write_text(
        "\n".join(
            [
                f"# {STUDY_ID}", "", "## Objet", "",
                "Verification MITC4/Newmark sous impulsion demi-sinus, chirp lineaire et table arbitraire.",
                "La reference temporelle est une propagation modale exacte par exponentielle de matrice.", "",
                "| Cas | Pas/periode | RMS UZ | RMS S11 | Bilan energie | Residu relatif |",
                "| --- | ---: | ---: | ---: | ---: | ---: |", *rows, "",
                f"Verdict automatique : **{summary['status']}**.", "",
                f"![Excitations]({STUDY_ID}-excitations.png)", "",
                f"![Deplacement]({STUDY_ID}-displacement.png)", "",
                f"![Contrainte]({STUDY_ID}-stress.png)", "",
                f"![Convergence]({STUDY_ID}-convergence.png)", "",
                "## Portee", "",
                "L'oracle partage les matrices EF et isole donc l'erreur temporelle. La correlation spatiale",
                "independante Code_Aster est conduite dans une etude externe separee.", "",
            ]
        ),
        encoding="utf-8",
    )


def _plot_excitation(summary: dict[str, Any], path: Path) -> None:
    figure, axis = plt.subplots(figsize=(8.2, 4.5))
    for case, points in summary["cases"].items():
        point = points[-1]
        axis.plot(point["times_s"], point["load_factors"], label=case)
    axis.set(xlabel="temps [s]", ylabel="facteur de charge", title="Excitations large bande controlees")
    axis.grid(True, alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _plot_response(summary: dict[str, Any], path: Path, *, stress: bool) -> None:
    figure, axes = plt.subplots(3, 1, figsize=(8.2, 8.8), sharex=False)
    for axis, (case, points) in zip(axes, summary["cases"].items(), strict=True):
        point = points[-1]
        qf_key = "qf_top_s11_pa" if stress else "qf_displacement_m"
        oracle_key = "oracle_top_s11_pa" if stress else "oracle_displacement_m"
        scale = 1.0e-6 if stress else 1000.0
        axis.plot(point["times_s"], scale * np.asarray(point[oracle_key]), "k--", label="oracle exact")
        axis.plot(point["times_s"], scale * np.asarray(point[qf_key]), color="#087f5b", label="QF_solver")
        axis.set_title(case)
        axis.set_ylabel("S11 [MPa]" if stress else "UZ [mm]")
        axis.grid(True, alpha=0.25)
        axis.legend()
    axes[-1].set_xlabel("temps [s]")
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _plot_convergence(summary: dict[str, Any], path: Path) -> None:
    figure, axes = plt.subplots(1, 2, figsize=(10.5, 4.3))
    for case, points in summary["cases"].items():
        resolution = [point["steps_per_period"] for point in points]
        axes[0].loglog(resolution, [point["displacement_rms_error"] for point in points], "o-", label=case)
        axes[1].loglog(resolution, [point["stress_rms_error"] for point in points], "o-", label=case)
    axes[0].set(title="Convergence deplacement", xlabel="pas/periode", ylabel="erreur RMS normalisee")
    axes[1].set(title="Convergence contrainte", xlabel="pas/periode", ylabel="erreur RMS normalisee")
    for axis in axes:
        axis.grid(True, which="both", alpha=0.25)
        axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=170)
    plt.close(figure)
