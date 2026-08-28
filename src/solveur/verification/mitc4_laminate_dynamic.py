"""Internal dynamic V&V campaign for a symmetric MITC4 laminate.

The campaign deliberately uses a numerical eigenmode as its temporal and
harmonic oracle.  It proves mass, drilling condensation and linear dynamics
are mutually consistent for a laminate; it is not an external shell-dynamics
correlation and cannot close an Owner review on its own.
"""

from __future__ import annotations

from solveur.paths import project_root

import math
from pathlib import Path
from typing import Any

import matplotlib
import numpy as np

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402

from solveur.elements.shell.mitc4.mesh import MeshFactory
from solveur.api import solve_model
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.verification.mitc4_harmonic import _analytical_response
from solveur.verification.mitc4_newmark import _initial_state, _tip_midline_node
from solveur.verification.mitc4_newmark_extended import modal_nodal_loads


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC4-LAMINATE-DYNAMIC-001"


class Mitc4LaminateDynamicStudy:
    """Verify modal, Newmark and harmonic paths on one [0/90/90/0] laminate."""

    amplitude = 1.0e-4
    damping_ratio = 0.02
    residual_limit = 1.0e-7
    orthogonality_limit = 1.0e-7
    newmark_rms_limit = 0.01
    energy_drift_limit = 1.0e-4
    harmonic_error_limit = 1.0e-6
    include_history_shell_stress_probe = True
    drilling_mass_tolerance: float | None = None
    dynamic_probe_dof = "UZ"

    def __init__(
        self,
        *,
        mesh: tuple[int, int] = (8, 2),
        layup: tuple[float, ...] = (0.0, 90.0, 90.0, 0.0),
        steps_per_period: tuple[int, ...] = (20, 40, 80),
        frequency_ratios: tuple[float, ...] = (0.0, 0.5, 0.95, 1.0, 1.05, 1.5, 2.0),
        modal_method: str = "eigh",
    ) -> None:
        self.mesh = mesh
        self.layup = tuple(float(angle) for angle in layup)
        if not self.layup:
            raise ValueError("MITC4 laminate dynamic study requires at least one ply.")
        self.steps_per_period = steps_per_period
        self.frequency_ratios = frequency_ratios
        self.modal_method = str(modal_method).lower()
        if self.modal_method not in {"eigh", "eigsh", "lanczos"}:
            raise ValueError("modal_method must be eigh, eigsh or lanczos.")

    def build_model(self) -> tuple[FiniteElementModel, np.ndarray]:
        """Build a planar cantilever with a symmetric carbon/epoxy layup."""
        nx, ny = self.mesh
        mesh = MeshFactory.rectangular_plate(nx, ny, 1.0, 0.2)
        root = np.flatnonzero(np.isclose(mesh.nodes[:, 0], 0.0))
        ply_thickness = 1.0e-2 if len(self.layup) == 1 else 2.5e-3
        ply = {
            "E1": 135.0e9,
            "E2": 10.0e9,
            "nu12": 0.3,
            "G12": 5.0e9,
            "G13": 4.5e9,
            "G23": 3.8e9,
            "density": 1600.0,
            "thickness": ply_thickness,
        }
        plies = [
            {"name": f"ply-{index + 1}", **ply, "angle_deg": angle}
            for index, angle in enumerate(self.layup)
        ]
        model = FiniteElementModel.from_raw(
            analysis={
                "type": "modal",
                "method": self.modal_method,
                "modes": 4,
                "dense_modal_max_dofs": 6000,
                "modal_residual_failure_tolerance": self.residual_limit,
                "modal_eigenpair_refinement_iterations": 2,
            },
            nodes=mesh.nodes.tolist(),
            elements=[{"type": "MITC4", "nodes": quad.tolist(), "material": "laminate"} for quad in mesh.quads],
            materials={
                "laminate": {
                    "type": "shell_laminate",
                    "drilling_scale": 1.0e-4,
                    "shear_factor": 5.0 / 6.0,
                    "plies": plies,
                }
            },
            fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]} for node in root],
        )
        return model, mesh.nodes

    def run(self) -> dict[str, Any]:
        model, nodes = self.build_model()
        modal = solve_model(model, enforce_policy=False)
        frequency = float(modal.frequencies_hz[0])
        omega = 2.0 * math.pi * frequency
        tip = _tip_midline_node(nodes)
        mode = np.asarray(modal.modes[:, 0], dtype=float)
        tip_index = modal.dofs.index(tip, self.dynamic_probe_dof)
        initial_mode = mode * (self.amplitude / mode[tip_index])
        initial = _initial_state(modal.dofs, initial_mode)
        newmark = [self._newmark_point(model, tip, initial, frequency, count) for count in self.steps_per_period]
        harmonic = self._harmonic(model, modal, tip, frequency, omega, mode)
        modal_checks = {
            "positive_frequencies": bool(np.all(np.asarray(modal.frequencies_hz) > 0.0)),
            "modal_residual": float(modal.solver["max_relative_residual"]) <= self.residual_limit,
            "mass_orthogonality": float(modal.solver["mass_orthogonality_error"]) <= self.orthogonality_limit,
            "stiffness_orthogonality": float(modal.solver["stiffness_diagonal_error"]) <= self.orthogonality_limit,
            "drilling_condensed": bool(modal.solver["dynamic_reduction"]["condensed_drilling_dof_count"] > 0),
        }
        newmark_checks = {
            "rms_history": newmark[-1]["normalized_rms_error"] <= self.newmark_rms_limit,
            "energy_conservation": max(point["maximum_relative_energy_drift"] for point in newmark)
            <= self.energy_drift_limit,
            "residual": max(point["maximum_dynamic_residual_norm"] for point in newmark) <= self.residual_limit,
            "time_step_convergence": all(
                current["normalized_rms_error"] < previous["normalized_rms_error"]
                for previous, current in zip(newmark, newmark[1:])
            ),
        }
        checks = {
            key: bool(value)
            for key, value in {
                **{f"modal_{key}": value for key, value in modal_checks.items()},
                **{f"newmark_{key}": value for key, value in newmark_checks.items()},
                **{f"harmonic_{key}": value for key, value in harmonic["checks"].items()},
            }.items()
        }
        modal_checks = {key: bool(value) for key, value in modal_checks.items()}
        newmark_checks = {key: bool(value) for key, value in newmark_checks.items()}
        harmonic["checks"] = {key: bool(value) for key, value in harmonic["checks"].items()}
        return {
            "study_id": STUDY_ID,
            "status": "PASS_INTERNAL" if all(checks.values()) else "FAIL",
            "maturity": "verified_development",
            "scope": "internal laminate dynamic consistency only",
            "model": {
                "mesh": list(self.mesh),
                "element_count": self.mesh[0] * self.mesh[1],
                "layup": list(self.layup),
                "ply_thickness_m": 2.5e-3,
                "total_thickness_m": sum(
                    1.0e-2 if len(self.layup) == 1 else 2.5e-3 for _ in self.layup
                ),
                "probe": {"node": tip, "dof": self.dynamic_probe_dof},
            },
            "modal": {
                "frequencies_hz": [float(value) for value in modal.frequencies_hz],
                "max_relative_residual": float(modal.solver["max_relative_residual"]),
                "mass_orthogonality_error": float(modal.solver["mass_orthogonality_error"]),
                "stiffness_orthogonality_error": float(modal.solver["stiffness_diagonal_error"]),
                "dynamic_reduction": dict(modal.solver["dynamic_reduction"]),
                "checks": modal_checks,
            },
            "newmark": {"reference": "u_tip(t)=u0*cos(2*pi*f1*t)", "points": newmark, "checks": newmark_checks},
            "harmonic": harmonic,
            "checks": checks,
            "limitations": [
                "The oracle is the first numerical laminate eigenmode; this is an algorithmic invariant, not an independent structural reference.",
                "No same-mesh Code_Aster, CalculiX, Abaqus or NAFEMS laminate-dynamics correlation is supplied.",
                "The layup is planar. Curved laminates, eccentric shell offsets, nonlinear plies, damage and delamination are outside this evidence.",
                "Only mass-proportional Rayleigh damping is exercised because drilling directions are statically condensed.",
            ],
        }

    def _newmark_point(
        self,
        model: FiniteElementModel,
        tip: int,
        initial: list[dict[str, object]],
        frequency: float,
        steps_per_period: int,
    ) -> dict[str, Any]:
        period = 1.0 / frequency
        step = period / steps_per_period
        probe_key = f"tip_{self.dynamic_probe_dof.lower()}"
        settings: dict[str, object] = {
            "type": "transient_dynamic",
            "method": "newmark",
            "time_step": step,
            "steps": 2 * steps_per_period,
            "newmark_beta": 0.25,
            "newmark_gamma": 0.5,
            "load_factors": [0.0],
            "initial_displacements": initial,
            "history_probes": [{"node": tip, "dof": self.dynamic_probe_dof, "label": probe_key}],
        }
        if self.include_history_shell_stress_probe:
            settings["history_shell_stress_probes"] = [
                {"node": tip, "face": "top", "component": "S11", "label": "tip_top_s11"}
            ]
        if self.drilling_mass_tolerance is not None:
            settings["drilling_mass_tolerance"] = self.drilling_mass_tolerance
        model.analysis = AnalysisSettings.from_raw(settings)
        result = solve_model(model, enforce_policy=False)
        history = result.solver["time_history"]
        times = np.asarray([row["time"] for row in history], dtype=float)
        response = np.asarray([row["probes"][probe_key]["displacement"] for row in history], dtype=float)
        expected = self.amplitude * np.cos(2.0 * math.pi * frequency * times)
        stresses = np.asarray(
            [row.get("shell_stress_probes", {}).get("tip_top_s11", 0.0) for row in history],
            dtype=float,
        )
        return {
            "steps_per_period": steps_per_period,
            "time_step_s": step,
            "normalized_rms_error": float(np.sqrt(np.mean((response - expected) ** 2)) / self.amplitude),
            "maximum_relative_energy_drift": max(abs(float(row["relative_energy_drift"])) for row in history),
            "maximum_dynamic_residual_norm": max(float(row["dynamic_residual_norm"]) for row in history),
            "maximum_top_s11_pa": float(np.max(np.abs(stresses))),
            "times_s": times.tolist(),
            f"{probe_key}_m": response.tolist(),
            f"reference_{probe_key}_m": expected.tolist(),
        }

    def _harmonic(
        self, model: FiniteElementModel, modal: object, tip: int, frequency: float, omega: float, mode: np.ndarray
    ) -> dict[str, Any]:
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
                **(
                    {"drilling_mass_tolerance": self.drilling_mass_tolerance}
                    if self.drilling_mass_tolerance is not None
                    else {}
                ),
            }
        )
        result = solve_model(model, enforce_policy=False)
        index = result.dofs.index(tip, self.dynamic_probe_dof)
        numerical = np.asarray([response[index] for response in result.responses], dtype=complex)
        tip_mode = float(mode[modal.dofs.index(tip, self.dynamic_probe_dof)])
        reference = _analytical_response(tip_mode, omega, frequencies, alpha)
        errors = np.abs(numerical - reference) / np.maximum(np.abs(reference), 1.0e-30)
        static_error = self._static_limit(modal, mode, tip, numerical[0])
        stress_rows = result.shell_stress_response
        ply_results = stress_rows[0]["element_results"][0].get("ply_results", []) if stress_rows else []
        ply_count = len({int(row["ply_index"]) for row in ply_results})
        amplitudes = np.abs(numerical)
        peak = int(np.argmax(amplitudes))
        checks = {
            "complex_modal_response": float(np.max(errors)) <= self.harmonic_error_limit,
            "zero_hz_static_limit": static_error <= 1.0e-9,
            "residual": float(result.solver["max_relative_residual_norm"]) <= self.residual_limit,
            "drilling_condensed": result.solver["dynamic_reduction"]["condensed_drilling_dof_count"] > 0,
            "ply_stress_postprocess": ply_count == len(self.layup),
            "resonance_peak": bool(0.95 <= self.frequency_ratios[peak] <= 1.05),
        }
        return {
            "frequencies_hz": frequencies.tolist(),
            "frequency_ratios": list(self.frequency_ratios),
            "amplitudes_m": amplitudes.tolist(),
            "phases_degrees": np.degrees(np.angle(numerical)).tolist(),
            "maximum_relative_error": float(np.max(errors)),
            "zero_hz_static_relative_error": static_error,
            "maximum_relative_residual": float(result.solver["max_relative_residual_norm"]),
            "ply_count_at_first_frequency": ply_count,
            "checks": checks,
        }

    def _static_limit(self, modal: object, mode: np.ndarray, tip: int, value: complex) -> float:
        model, _ = self.build_model()
        model.loads = modal_nodal_loads(model, modal.dofs, mode)
        model.analysis = AnalysisSettings.from_raw({"type": "linear_static", "method": "direct"})
        static = solve_model(model, enforce_policy=False)
        expected = float(static.displacements[static.dofs.index(tip, self.dynamic_probe_dof)])
        return abs(value.real - expected) / max(abs(expected), 1.0e-30)


def write_mitc4_laminate_dynamic_evidence(output: str | Path) -> dict[str, Any]:
    """Write reproducible, reviewable evidence without implying external validation."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc4LaminateDynamicStudy().run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_newmark(summary, target / f"{STUDY_ID}-newmark.png")
    _plot_harmonic(summary, target / f"{STUDY_ID}-harmonic.png")
    write_json_file(
        target / "vnv_manifest.json",
        {
            "schema_version": 1,
            "study_id": STUDY_ID,
            "source": git_source_state(PROJECT_ROOT),
            "files": discovered_file_entries(
                target, lambda _: "mitc4_laminate_dynamic_vnv", exclude_names=("vnv_manifest.json",)
            ),
        },
    )
    return summary


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    modal = summary["modal"]
    points = summary["newmark"]["points"]
    lines = [
        f"# {STUDY_ID}",
        "",
        "## Objet",
        "",
        "Coherence interne modal, Newmark et harmonique pour un porte-a-faux MITC4 stratifie symetrique `[0/90/90/0]`. Cette campagne ne constitue pas une correlation externe.",
        "",
        "## Modal",
        "",
        f"Frequence fondamentale : `{modal['frequencies_hz'][0]:.6f}` Hz. Residu relatif : `{modal['max_relative_residual']:.3e}`. Orthogonalites masse/raideur : `{modal['mass_orthogonality_error']:.3e}` / `{modal['stiffness_orthogonality_error']:.3e}`.",
        "",
        "## Newmark",
        "",
        "| Pas/periode | Erreur RMS | Derive energie | Residu dynamique | Max S11 face superieure (Pa) |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    lines.extend(
        f"| {row['steps_per_period']} | {row['normalized_rms_error']:.3e} | {row['maximum_relative_energy_drift']:.3e} | {row['maximum_dynamic_residual_norm']:.3e} | {row['maximum_top_s11_pa']:.3e} |"
        for row in points
    )
    harmonic = summary["harmonic"]
    lines.extend(
        [
            "",
            "## Harmonique",
            "",
            f"Erreur complexe maximale : `{harmonic['maximum_relative_error']:.3e}`. Limite statique a 0 Hz : `{harmonic['zero_hz_static_relative_error']:.3e}`. Post-traitement : `{harmonic['ply_count_at_first_frequency']}` plis.",
            "",
            f"![Newmark]({STUDY_ID}-newmark.png)",
            "",
            f"![Harmonique]({STUDY_ID}-harmonic.png)",
            "",
            "## Limites ouvertes",
            "",
        ]
    )
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.extend(["", f"Statut interne : **{summary['status']}**. Maturite : `{summary['maturity']}`.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _plot_newmark(summary: dict[str, Any], path: Path) -> None:
    coarse, fine = summary["newmark"]["points"][0], summary["newmark"]["points"][-1]
    figure, axis = plt.subplots(figsize=(7.2, 4.4))
    axis.plot(fine["times_s"], fine["reference_tip_uz_m"], "k--", label="reference modale")
    axis.plot(
        coarse["times_s"], coarse["tip_uz_m"], color="#bc4749", alpha=0.75, label=f"T/{coarse['steps_per_period']}"
    )
    axis.plot(fine["times_s"], fine["tip_uz_m"], color="#0077b6", label=f"T/{fine['steps_per_period']}")
    axis.set(xlabel="temps (s)", ylabel="UZ pointe (m)")
    axis.grid(alpha=0.25)
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)


def _plot_harmonic(summary: dict[str, Any], path: Path) -> None:
    harmonic = summary["harmonic"]
    figure, axes = plt.subplots(2, 1, figsize=(7.2, 6.0), sharex=True)
    axes[0].semilogy(harmonic["frequency_ratios"], harmonic["amplitudes_m"], color="#0077b6")
    axes[1].plot(harmonic["frequency_ratios"], harmonic["phases_degrees"], color="#bc4749")
    axes[0].set_ylabel("amplitude UZ (m)")
    axes[1].set_ylabel("phase (deg)")
    axes[1].set_xlabel("frequence / f1")
    for axis in axes:
        axis.axvline(1.0, color="#212529", linestyle="--", linewidth=0.9)
        axis.grid(alpha=0.25)
    figure.tight_layout()
    figure.savefig(path, dpi=180)
    plt.close(figure)
