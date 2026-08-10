"""Analytical harmonic-response verification for a condensed MITC4 model."""

from __future__ import annotations

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
from solveur.verification.mitc4_newmark import _tip_midline_node
from solveur.verification.mitc4_newmark_extended import modal_nodal_loads


PROJECT_ROOT = Path(__file__).resolve().parents[2]
STUDY_ID = "VNV-MITC4-HARMONIC-MODAL-001"


class Mitc4HarmonicModalStudy:
    """Check static limit, resonance, phase and damping on one shell mode."""

    damping_ratio = 0.02
    response_error_limit = 1.0e-6
    static_error_limit = 1.0e-9
    residual_limit = 1.0e-7

    def __init__(
        self,
        frequency_ratios: tuple[float, ...] | None = None,
        *,
        mesh: tuple[int, int] = (8, 2),
    ) -> None:
        self.frequency_ratios = frequency_ratios or tuple(np.linspace(0.0, 2.0, 81))
        self.mesh = mesh

    def run(self) -> dict[str, Any]:
        model, nodes = Mitc4ModalCantileverStudy().build_model(*self.mesh)
        modal = solve_model(model, enforce_policy=False)
        frequency = float(modal.frequencies_hz[0])
        omega = 2.0 * math.pi * frequency
        mode = np.asarray(modal.modes[:, 0], dtype=float)
        tip = _tip_midline_node(nodes)
        tip_mode = float(mode[modal.dofs.index(tip, "UZ")])
        model.loads = modal_nodal_loads(model, modal.dofs, mode)
        frequencies = np.asarray(self.frequency_ratios, dtype=float) * frequency
        alpha = 2.0 * self.damping_ratio * omega
        model.analysis = AnalysisSettings.from_raw(
            {
                "type": "harmonic_response",
                "method": "direct_frequency",
                "frequencies_hz": frequencies.tolist(),
                "rayleigh_alpha": alpha,
                "rayleigh_beta": 0.0,
            }
        )
        result = solve_model(model, enforce_policy=False)
        tip_index = result.dofs.index(tip, "UZ")
        numerical = np.asarray([response[tip_index] for response in result.responses], dtype=complex)
        analytical = _analytical_response(tip_mode, omega, frequencies, alpha)
        relative_errors = np.abs(numerical - analytical) / np.maximum(np.abs(analytical), 1.0e-30)
        static_error = self._static_error(modal, mode, tip, numerical[0])
        damping = self._damping_sensitivity(frequency, omega, tip_mode, modal, mode)
        amplitudes = np.abs(numerical)
        phases = np.degrees(np.angle(numerical))
        peak_index = int(np.argmax(amplitudes))
        before = int(np.argmin(np.abs(np.asarray(self.frequency_ratios) - 0.5)))
        after = int(np.argmin(np.abs(np.asarray(self.frequency_ratios) - 1.5)))
        checks = {
            "analytical_complex_response": float(np.max(relative_errors)) <= self.response_error_limit,
            "zero_hz_static_limit": bool(static_error <= self.static_error_limit),
            "resonance_location": bool(0.95 <= self.frequency_ratios[peak_index] <= 1.05),
            "phase_before_resonance": bool(-15.0 <= phases[before] <= 0.0),
            "phase_after_resonance": bool(-180.0 <= phases[after] <= -165.0),
            "damping_limits_peak": all(
                current["amplitude_m"] < previous["amplitude_m"]
                for previous, current in zip(damping, damping[1:])
            ),
            "harmonic_residual": float(result.solver["max_residual_norm"]) <= self.residual_limit,
            "drilling_condensed": result.solver["dynamic_reduction"]["condensed_drilling_dof_count"] > 0,
        }
        return {
            "study_id": STUDY_ID,
            "reference": {
                "type": "single mass-normalized mode harmonic response",
                "equation": "u_tip=phi_tip/(omega1^2-Omega^2+i*alpha*Omega)",
                "natural_frequency_hz": frequency,
                "natural_omega_rad_s": omega,
                "damping_ratio": self.damping_ratio,
                "rayleigh_alpha": alpha,
                "modal_load": "F0=M*phi1",
            },
            "model": {
                "mesh": list(self.mesh),
                "element_count": self.mesh[0] * self.mesh[1],
                "probe": {"node": tip, "dof": "UZ"},
                "condensed_drilling_dofs": result.solver["dynamic_reduction"]["condensed_drilling_dof_count"],
            },
            "acceptance": {
                "complex_response_relative_error_max": self.response_error_limit,
                "static_relative_error_max": self.static_error_limit,
                "residual_norm_max": self.residual_limit,
                "peak_frequency_ratio_range": [0.95, 1.05],
            },
            "frequency_ratios": [float(value) for value in self.frequency_ratios],
            "frequencies_hz": frequencies.tolist(),
            "numerical_real_m": numerical.real.tolist(),
            "numerical_imag_m": numerical.imag.tolist(),
            "analytical_real_m": analytical.real.tolist(),
            "analytical_imag_m": analytical.imag.tolist(),
            "amplitudes_m": amplitudes.tolist(),
            "phases_degrees": phases.tolist(),
            "relative_errors": relative_errors.tolist(),
            "maximum_relative_error": float(np.max(relative_errors)),
            "zero_hz_static_relative_error": static_error,
            "peak": {
                "frequency_hz": float(frequencies[peak_index]),
                "frequency_ratio": float(self.frequency_ratios[peak_index]),
                "amplitude_m": float(amplitudes[peak_index]),
                "phase_degrees": float(phases[peak_index]),
            },
            "damping_sensitivity": damping,
            "maximum_residual_norm": float(result.solver["max_residual_norm"]),
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "limitations": [
                "The load is proportional to the first numerical mode and does not exercise broadband modal coupling.",
                "Only mass-proportional Rayleigh damping is accepted while drilling condensation is active.",
                "A same-mesh commercial-solver correlation remains pending.",
            ],
        }

    def _static_error(
        self,
        modal: object,
        mode: np.ndarray,
        tip: int,
        harmonic_zero: complex,
    ) -> float:
        model, _ = Mitc4ModalCantileverStudy().build_model(*self.mesh)
        model.loads = modal_nodal_loads(model, modal.dofs, mode)
        model.analysis = AnalysisSettings.from_raw({"type": "linear_static", "method": "direct"})
        static = solve_model(model, enforce_policy=False)
        expected = float(static.displacements[static.dofs.index(tip, "UZ")])
        return abs(harmonic_zero.real - expected) / max(abs(expected), 1.0e-30)

    def _damping_sensitivity(
        self,
        frequency: float,
        omega: float,
        tip_mode: float,
        modal: object,
        mode: np.ndarray,
    ) -> list[dict[str, float]]:
        rows = []
        for ratio in (0.01, 0.02, 0.05):
            model, _ = Mitc4ModalCantileverStudy().build_model(*self.mesh)
            model.loads = modal_nodal_loads(model, modal.dofs, mode)
            alpha = 2.0 * ratio * omega
            model.analysis = AnalysisSettings.from_raw(
                {
                    "type": "harmonic_response",
                    "method": "direct_frequency",
                    "frequencies_hz": [frequency],
                    "rayleigh_alpha": alpha,
                    "rayleigh_beta": 0.0,
                }
            )
            result = solve_model(model, enforce_policy=False)
            value = result.responses[0][result.dofs.index(_tip_midline_node(model.nodes), "UZ")]
            expected = tip_mode / complex(0.0, alpha * omega)
            rows.append(
                {
                    "damping_ratio": ratio,
                    "amplitude_m": float(abs(value)),
                    "phase_degrees": float(np.degrees(np.angle(value))),
                    "analytical_amplitude_m": float(abs(expected)),
                    "relative_error": float(abs(value - expected) / abs(expected)),
                }
            )
        return rows


def write_mitc4_harmonic_evidence(output: str | Path) -> dict[str, Any]:
    """Write harmonic V&V JSON, Markdown, figures and manifest."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4HarmonicModalStudy().run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_response(summary, target / f"{STUDY_ID}-response.png")
    _plot_damping(summary, target / f"{STUDY_ID}-damping.png")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                target,
                lambda _: "mitc4_harmonic_vnv",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def _analytical_response(
    tip_mode: float,
    omega: float,
    frequencies_hz: np.ndarray,
    alpha: float,
) -> np.ndarray:
    forcing = 2.0 * math.pi * frequencies_hz
    return tip_mode / (omega**2 - forcing**2 + 1j * alpha * forcing)


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    damping_rows = "\n".join(
        f"| {row['damping_ratio']:.3f} | {row['amplitude_m']:.6e} | "
        f"{row['phase_degrees']:.3f} | {row['relative_error']:.3e} |"
        for row in summary["damping_sensitivity"]
    )
    path.write_text(
        f"""# {STUDY_ID}

## Objet

Balayage harmonique du premier mode MITC4 avec charge `F0=M*phi1`.

- erreur complexe maximale : `{summary['maximum_relative_error']:.3e}`;
- erreur limite statique : `{summary['zero_hz_static_relative_error']:.3e}`;
- pic : `{summary['peak']['frequency_hz']:.6f} Hz`;
- residu maximal : `{summary['maximum_residual_norm']:.3e}`.

| Amortissement | Amplitude a f1 (m) | Phase (deg) | Erreur analytique |
| ---: | ---: | ---: | ---: |
{damping_rows}

Statut : **{summary['status']}**.

![Reponse harmonique]({STUDY_ID}-response.png)

![Sensibilite amortissement]({STUDY_ID}-damping.png)
""",
        encoding="utf-8",
    )


def _plot_response(summary: dict[str, Any], path: Path) -> None:
    ratios = summary["frequency_ratios"]
    amplitudes = summary["amplitudes_m"]
    phases = summary["phases_degrees"]
    figure, axes = plt.subplots(2, 1, figsize=(7.2, 6.2), sharex=True)
    axes[0].semilogy(ratios, amplitudes, color="#006d77")
    axes[0].set_ylabel("amplitude UZ (m)")
    axes[1].plot(ratios, phases, color="#ae2012")
    axes[1].set_ylabel("phase (deg)")
    axes[1].set_xlabel("frequence / f1")
    for axis in axes:
        axis.grid(True, alpha=0.25)
        axis.axvline(1.0, color="black", linestyle="--", linewidth=0.8)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_damping(summary: dict[str, Any], path: Path) -> None:
    rows = summary["damping_sensitivity"]
    figure, axis = plt.subplots(figsize=(7.2, 4.4))
    axis.plot(
        [row["damping_ratio"] for row in rows],
        [row["amplitude_m"] for row in rows],
        "o-",
        color="#006d77",
    )
    axis.set_xlabel("taux d'amortissement du premier mode")
    axis.set_ylabel("amplitude a f1 (m)")
    axis.grid(True, alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
