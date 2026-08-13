"""Broadband multimodal verification of the MITC4 direct harmonic solver."""

from __future__ import annotations

from solveur.paths import project_root

import cmath
import math
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np
from scipy.linalg import eigh
from scipy.signal import find_peaks

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.api import solve_model
from solveur.core.assembler import GlobalAssembler
from solveur.core.dynamic_reduction import DynamicDofReducer
from solveur.core.model import NodalLoad
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.mitc4_harmonic_nafems import build_nafems_13h_model


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC4-HARMONIC-BROADBAND-003"


class Mitc4HarmonicBroadbandStudy:
    """Compare direct and complete modal response across four resonances."""

    alpha = 0.299
    beta = 1.339e-3
    response_error_limit = 1.0e-6
    residual_limit = 1.0e-8
    peak_frequency_error_limit = 0.01

    def __init__(self, *, frequency_count: int = 600) -> None:
        self.frequency_count = frequency_count

    def run(self) -> dict[str, Any]:
        frequencies = np.linspace(0.1, 16.0, self.frequency_count)
        model, quads = build_nafems_13h_model(
            analysis={
                "type": "harmonic_response",
                "method": "direct_frequency",
                "frequencies_hz": frequencies.tolist(),
                "rayleigh_alpha": self.alpha,
                "rayleigh_beta": self.beta,
            },
            pressure=False,
        )
        load_node = _nearest_node(model.nodes, 3.75, 3.75)
        model.loads = [NodalLoad(node=load_node, dof="UZ", value=100.0)]
        result = solve_model(model, enforce_policy=False)
        oracle = _complete_modal_oracle(model, frequencies, self.alpha, self.beta)
        probe = result.dofs.index(load_node, "UZ")
        direct_values = np.asarray([response[probe] for response in result.responses], dtype=complex)
        modal_values = np.asarray([response[probe] for response in oracle["responses"]], dtype=complex)
        response_errors = [
            _relative_norm(
                direct[oracle["free"]] - modal[oracle["free"]],
                modal[oracle["free"]],
            )
            for direct, modal in zip(result.responses, oracle["responses"], strict=True)
        ]
        amplitudes = np.abs(direct_values)
        peak_indices, _ = find_peaks(amplitudes, prominence=float(np.max(amplitudes)) * 1.0e-3)
        expected_frequencies = _unique_frequencies(oracle["eigenfrequencies_hz"], 16.0)[:4]
        peaks = _matched_peaks(frequencies, amplitudes, peak_indices, expected_frequencies)
        maximum_peak_error = max(peak["relative_frequency_error"] for peak in peaks)
        maximum_response_error = max(response_errors)
        maximum_probe_error = max(
            _relative_norm(np.asarray([direct - modal]), np.asarray([modal]))
            for direct, modal in zip(direct_values, modal_values, strict=True)
        )
        checks = {
            "four_resonance_families": len(peaks) == 4,
            "peak_frequency_locations": maximum_peak_error <= self.peak_frequency_error_limit,
            "direct_matches_complete_modal": maximum_response_error <= self.response_error_limit,
            "probe_matches_complete_modal": maximum_probe_error <= self.response_error_limit,
            "harmonic_residual": float(result.solver["max_relative_residual_norm"])
            <= self.residual_limit,
            "finite_response": bool(np.all(np.isfinite(direct_values))),
            "complete_modal_basis": oracle["mode_count"] == oracle["reduced_dof_count"],
        }
        return {
            "study_id": STUDY_ID,
            "status": "PASS" if all(checks.values()) else "FAIL",
            "model": {
                "mesh": [8, 8],
                "node_count": model.node_count,
                "element_count": len(model.elements),
                "load": {"node": load_node, "dof": "UZ", "amplitude_n": 100.0},
                "probe": {"node": load_node, "dof": "UZ"},
            },
            "frequency_band": {
                "start_hz": float(frequencies[0]),
                "stop_hz": float(frequencies[-1]),
                "count": int(frequencies.size),
                "resonance_family_count": len(peaks),
            },
            "damping": {"rayleigh_alpha": self.alpha, "rayleigh_beta": self.beta},
            "oracle": {
                "type": "complete mass-orthonormal modal superposition",
                "mode_count": oracle["mode_count"],
                "reduced_dof_count": oracle["reduced_dof_count"],
                "first_eigenfrequencies_hz": oracle["eigenfrequencies_hz"][:10].tolist(),
            },
            "acceptance": {
                "complex_response_relative_error_max": self.response_error_limit,
                "relative_residual_max": self.residual_limit,
                "peak_frequency_relative_error_max": self.peak_frequency_error_limit,
                "resonance_family_count_min": 4,
            },
            "metrics": {
                "maximum_complex_response_relative_error": maximum_response_error,
                "maximum_probe_relative_error": maximum_probe_error,
                "maximum_peak_frequency_relative_error": maximum_peak_error,
                "maximum_relative_residual": float(result.solver["max_relative_residual_norm"]),
            },
            "peaks": peaks,
            "frequency_response": [
                {
                    "frequency_hz": float(frequency),
                    "direct_amplitude_m": float(abs(direct)),
                    "direct_phase_degrees": float(np.degrees(cmath.phase(direct))),
                    "modal_amplitude_m": float(abs(modal)),
                    "modal_phase_degrees": float(np.degrees(cmath.phase(modal))),
                    "full_field_relative_error": float(error),
                }
                for frequency, direct, modal, error in zip(
                    frequencies,
                    direct_values,
                    modal_values,
                    response_errors,
                    strict=True,
                )
            ],
            "checks": checks,
            "limitations": [
                "The broadband oracle uses the same assembled K and M but an independent complete modal algorithm.",
                "The point load is deliberately off-center to activate several mode families.",
                "This study verifies deterministic harmonic response, not random vibration or PSD analysis.",
            ],
            "_plot_data": {
                "nodes": model.nodes,
                "quads": quads,
                "responses": result.responses,
                "dofs": result.dofs,
                "peak_indices": peak_indices.tolist(),
            },
        }


def write_mitc4_harmonic_broadband_evidence(output: str | Path) -> dict[str, Any]:
    """Write broadband JSON, Markdown, figures and manifest."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4HarmonicBroadbandStudy().run()
    plot_data = summary.pop("_plot_data")
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_response(summary, target / f"{STUDY_ID}-response.png")
    _plot_agreement(summary, target / f"{STUDY_ID}-agreement.png")
    _plot_peak_shapes(plot_data, summary, target / f"{STUDY_ID}-peak-shapes.png")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                target,
                lambda _: "mitc4_harmonic_broadband_vnv",
                exclude_names=("vnv_manifest.json",),
            ),
        },
    )
    return summary


def _complete_modal_oracle(
    model: object,
    frequencies: np.ndarray,
    alpha: float,
    beta: float,
) -> dict[str, Any]:
    dofs = model.dof_manager()
    assembler = GlobalAssembler()
    stiffness = assembler.assemble_stiffness(model, dofs)
    mass = assembler.assemble_mass(model, dofs)
    loads = assembler.assemble_loads(model, dofs)
    fixed = assembler.fixed_indices(model, dofs)
    reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)
    eigenvalues, modes = eigh(reducer.stiffness.toarray(), reducer.mass.toarray())
    modal_loads = modes.T @ reducer.reduce_load(loads)
    responses = []
    for frequency in frequencies:
        omega = 2.0 * math.pi * frequency
        denominator = eigenvalues - omega**2 + 1j * omega * (alpha + beta * eigenvalues)
        reduced = modes @ (modal_loads / denominator)
        responses.append(
            reducer.expand_complex_state(
                reduced,
                loads,
                stiffness_factor=1.0 + 1j * omega * beta,
            )
        )
    return {
        "responses": responses,
        "free": reducer.free,
        "mode_count": int(eigenvalues.size),
        "reduced_dof_count": reducer.reduced_size,
        "eigenfrequencies_hz": np.sqrt(np.maximum(eigenvalues, 0.0)) / (2.0 * math.pi),
    }


def _unique_frequencies(values: np.ndarray, maximum: float) -> list[float]:
    unique: list[float] = []
    for value in values:
        frequency = float(value)
        if frequency > maximum:
            break
        if not unique or abs(frequency - unique[-1]) / max(frequency, 1.0) > 1.0e-6:
            unique.append(frequency)
    return unique


def _matched_peaks(
    frequencies: np.ndarray,
    amplitudes: np.ndarray,
    peak_indices: np.ndarray,
    expected: list[float],
) -> list[dict[str, float]]:
    if len(peak_indices) < len(expected):
        return []
    rows = []
    available = list(int(index) for index in peak_indices)
    for modal_frequency in expected:
        index = min(available, key=lambda item: abs(float(frequencies[item]) - modal_frequency))
        available.remove(index)
        rows.append(
            {
                "modal_frequency_hz": modal_frequency,
                "direct_peak_frequency_hz": float(frequencies[index]),
                "direct_peak_amplitude_m": float(amplitudes[index]),
                "relative_frequency_error": abs(float(frequencies[index]) - modal_frequency)
                / modal_frequency,
                "frequency_index": index,
            }
        )
    return rows


def _nearest_node(nodes: np.ndarray, x: float, y: float) -> int:
    return int(np.argmin((nodes[:, 0] - x) ** 2 + (nodes[:, 1] - y) ** 2))


def _relative_norm(error: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(error) / max(float(np.linalg.norm(reference)), 1.0e-30))


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    rows = "\n".join(
        f"| {index + 1} | {peak['modal_frequency_hz']:.6f} | "
        f"{peak['direct_peak_frequency_hz']:.6f} | {peak['direct_peak_amplitude_m']:.6e} | "
        f"{100.0 * peak['relative_frequency_error']:.3f} % |"
        for index, peak in enumerate(summary["peaks"])
    )
    metrics = summary["metrics"]
    path.write_text(
        f"""# {STUDY_ID}

## Objet

Balayage direct de 0,1 a 16 Hz sous force `UZ` decentree. Une decomposition
modale complete de {summary['oracle']['mode_count']} modes fournit un second
algorithme de reference sur le meme systeme discret.

| Famille | Frequence modale (Hz) | Pic direct (Hz) | Amplitude (m) | Ecart |
| ---: | ---: | ---: | ---: | ---: |
{rows}

- erreur complexe plein champ maximale: `{metrics['maximum_complex_response_relative_error']:.3e}`;
- erreur complexe a la sonde maximale: `{metrics['maximum_probe_relative_error']:.3e}`;
- residu relatif maximal: `{metrics['maximum_relative_residual']:.3e}`.

Statut : **{summary['status']}**.

![Reponse large bande]({STUDY_ID}-response.png)

![Accord direct-modal]({STUDY_ID}-agreement.png)

![Deformees aux pics]({STUDY_ID}-peak-shapes.png)
""",
        encoding="utf-8",
    )


def _plot_response(summary: dict[str, Any], path: Path) -> None:
    rows = summary["frequency_response"]
    figure, axes = plt.subplots(2, 1, figsize=(7.5, 6.2), sharex=True)
    axes[0].semilogy(
        [row["frequency_hz"] for row in rows],
        [row["direct_amplitude_m"] for row in rows],
        color="#006d77",
        label="direct",
    )
    axes[0].semilogy(
        [row["frequency_hz"] for row in rows],
        [row["modal_amplitude_m"] for row in rows],
        "--",
        color="#ca6702",
        label="modal complet",
    )
    axes[1].plot(
        [row["frequency_hz"] for row in rows],
        [row["direct_phase_degrees"] for row in rows],
        color="#ae2012",
    )
    axes[0].set_ylabel("amplitude UZ (m)")
    axes[1].set_ylabel("phase (deg)")
    axes[1].set_xlabel("frequence (Hz)")
    axes[0].legend()
    for axis in axes:
        axis.grid(True, alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_agreement(summary: dict[str, Any], path: Path) -> None:
    rows = summary["frequency_response"]
    figure, axis = plt.subplots(figsize=(7.4, 4.5))
    axis.semilogy(
        [row["frequency_hz"] for row in rows],
        [max(row["full_field_relative_error"], 1.0e-18) for row in rows],
        color="#006d77",
    )
    axis.axhline(
        summary["acceptance"]["complex_response_relative_error_max"],
        color="#ae2012",
        linestyle="--",
        label="limite",
    )
    axis.set_xlabel("frequence (Hz)")
    axis.set_ylabel("erreur relative direct / modal complet")
    axis.grid(True, which="both", alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def _plot_peak_shapes(plot_data: dict[str, Any], summary: dict[str, Any], path: Path) -> None:
    nodes = np.asarray(plot_data["nodes"], dtype=float)
    quads = np.asarray(plot_data["quads"], dtype=int)
    dofs = plot_data["dofs"]
    probe = int(summary["model"]["probe"]["node"])
    figure = plt.figure(figsize=(10.0, 8.0))
    for plot_index, peak in enumerate(summary["peaks"], start=1):
        response = np.asarray(plot_data["responses"][int(peak["frequency_index"])], dtype=complex)
        phase = cmath.phase(response[dofs.index(probe, "UZ")])
        aligned = response * np.exp(-1j * phase)
        uz = np.asarray([aligned[dofs.index(node, "UZ")].real for node in range(nodes.shape[0])])
        scale = 1.2 / max(float(np.max(np.abs(uz))), 1.0e-30)
        deformed = nodes.copy()
        deformed[:, 2] += scale * uz
        axis = figure.add_subplot(2, 2, plot_index, projection="3d")
        for quad in quads:
            closed = np.append(quad, quad[0])
            axis.plot(*deformed[closed].T, color="#006d77", linewidth=0.65)
        axis.set_title(f"pic {plot_index}: {peak['direct_peak_frequency_hz']:.3f} Hz")
        axis.set_xlabel("x")
        axis.set_ylabel("y")
        axis.set_zlabel("UZ amplifie")
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)
