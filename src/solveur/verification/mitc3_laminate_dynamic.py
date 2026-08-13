"""Internal static and dynamic V&V campaign for a MITC3+ laminate.

The campaign deliberately combines an analytical in-plane laminate patch with
first-eigenmode temporal and harmonic invariants.  It proves that the MITC3+
element, its consistent mass and the global drilling reduction operate
coherently for one flat symmetric laminate.  It is not an external structural
correlation and must not be used to close an Owner review on its own.
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

from solveur.api import solve_model
from solveur.core.analysis import AnalysisSettings
from solveur.core.model import FiniteElementModel
from solveur.io.manifest import discovered_file_entries, git_source_state, write_json_file
from solveur.materials.factory import MaterialFactory
from solveur.verification.mitc3_models import cantilever_model, rectangular_tri_mesh
from solveur.verification.mitc4_harmonic import _analytical_response
from solveur.verification.mitc4_newmark import _initial_state
from solveur.verification.mitc4_newmark_extended import modal_nodal_loads


PROJECT_ROOT = project_root()
STUDY_ID = "VNV-MITC3-LAMINATE-DYNAMIC-001"


class Mitc3LaminateDynamicStudy:
    """Verify a flat [0/90/90/0] MITC3+ laminate in four analysis routes."""

    amplitude = 1.0e-4
    damping_ratio = 0.02
    residual_limit = 1.0e-7
    orthogonality_limit = 1.0e-7
    static_patch_limit = 1.0e-10
    newmark_rms_limit = 1.0e-2
    energy_drift_limit = 1.0e-4
    harmonic_error_limit = 1.0e-6

    def __init__(
        self,
        *,
        mesh: tuple[int, int] = (8, 2),
        static_meshes: tuple[tuple[int, int], ...] = ((1, 1), (2, 1), (4, 2), (8, 4)),
        steps_per_period: tuple[int, ...] = (20, 40, 80),
        frequency_ratios: tuple[float, ...] = (0.0, 0.5, 0.95, 1.0, 1.05, 1.5, 2.0),
    ) -> None:
        self.mesh = mesh
        self.static_meshes = static_meshes
        self.steps_per_period = steps_per_period
        self.frequency_ratios = frequency_ratios

    def run(self) -> dict[str, Any]:
        """Execute static, modal, transient and harmonic internal checks."""
        static = self._static_patch()
        model = self._dynamic_model({"type": "modal", "method": "eigh", "modes": 4})
        modal = solve_model(model, enforce_policy=False)
        frequency = float(modal.frequencies_hz[0])
        omega = 2.0 * math.pi * frequency
        tip = _tip_midline_node(model.nodes)
        mode = np.asarray(modal.modes[:, 0], dtype=float)
        tip_index = modal.dofs.index(tip, "UZ")
        initial = _initial_state(modal.dofs, mode * (self.amplitude / mode[tip_index]))
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
            "energy_conservation": max(row["maximum_relative_energy_drift"] for row in newmark)
            <= self.energy_drift_limit,
            "residual": max(row["maximum_dynamic_residual_norm"] for row in newmark) <= self.residual_limit,
            "time_step_convergence": all(
                current["normalized_rms_error"] < previous["normalized_rms_error"]
                for previous, current in zip(newmark, newmark[1:])
            ),
            "final_ply_postprocess": bool(newmark[-1]["ply_count_at_final_time"] == 4),
        }
        checks = {
            **{f"static_{key}": bool(value) for key, value in static["checks"].items()},
            **{f"modal_{key}": bool(value) for key, value in modal_checks.items()},
            **{f"newmark_{key}": bool(value) for key, value in newmark_checks.items()},
            **{f"harmonic_{key}": bool(value) for key, value in harmonic["checks"].items()},
        }
        return {
            "study_id": STUDY_ID,
            "status": "PASS_INTERNAL" if all(checks.values()) else "FAIL",
            "maturity": "verified_development",
            "scope": "internal flat symmetric MITC3 laminate consistency",
            "model": {
                "dynamic_mesh": list(self.mesh),
                "dynamic_element_count": 2 * self.mesh[0] * self.mesh[1],
                "static_meshes": [list(mesh) for mesh in self.static_meshes],
                "layup": [0.0, 90.0, 90.0, 0.0],
                "ply_thickness_m": 2.5e-3,
                "total_thickness_m": 1.0e-2,
                "probe": {"node": tip, "dof": "UZ"},
            },
            "static": static,
            "modal": {
                "frequencies_hz": [float(value) for value in modal.frequencies_hz],
                "max_relative_residual": float(modal.solver["max_relative_residual"]),
                "mass_orthogonality_error": float(modal.solver["mass_orthogonality_error"]),
                "stiffness_orthogonality_error": float(modal.solver["stiffness_diagonal_error"]),
                "dynamic_reduction": dict(modal.solver["dynamic_reduction"]),
                "checks": modal_checks,
            },
            "newmark": {
                "reference": "u_tip(t)=u0*cos(2*pi*f1*t)",
                "points": newmark,
                "checks": newmark_checks,
            },
            "harmonic": harmonic,
            "checks": checks,
            "limitations": [
                "The static oracle is an affine membrane field and the dynamic oracle is the first computed mode; neither is an external structural comparison.",
                "No same-mesh Code_Aster, CalculiX, Abaqus or published ply-level dynamic correlation is supplied.",
                "The layup is planar and symmetric. Curved laminates, non-zero B coupling, offsets, damage, delamination, large rotations and nonlinear dynamics are outside this evidence.",
                "Nodal dynamic shell-stress histories are intentionally not requested for MITC3+ across non-aligned local frames; element and ply results remain available at each stored state.",
            ],
        }

    @staticmethod
    def laminate_data() -> dict[str, object]:
        """Return the traceable raw material description shared by the cases."""
        ply = {
            "E1": 130.0e9,
            "E2": 9.0e9,
            "nu12": 0.28,
            "G12": 5.0e9,
            "G13": 4.0e9,
            "G23": 3.5e9,
            "density": 1550.0,
            "thickness": 2.5e-3,
        }
        return {
            "type": "shell_laminate",
            "reference_direction": [1.0, 0.0, 0.0],
            "drilling_scale": 1.0e-4,
            "shear_factor": 5.0 / 6.0,
            "plies": [{"name": f"ply-{index + 1}", **ply, "angle_deg": angle} for index, angle in enumerate((0.0, 90.0, 90.0, 0.0))],
        }

    def _static_patch(self) -> dict[str, Any]:
        resultant = np.array([1000.0, 0.0, 0.0])
        material = MaterialFactory.create(self.laminate_data())
        expected_strain = np.linalg.solve(material.membrane_matrix, resultant)
        points: list[dict[str, float | int]] = []
        ply_count = 0
        for nx, ny in self.static_meshes:
            model = self._static_model(nx, ny, float(resultant[0]))
            result = solve_model(model, enforce_policy=False)
            expected = np.zeros_like(result.displacements)
            for index, (x, y, _) in enumerate(model.nodes):
                expected[result.dofs.index(index, "UX")] = expected_strain[0] * x + 0.5 * expected_strain[2] * y
                expected[result.dofs.index(index, "UY")] = expected_strain[1] * y + 0.5 * expected_strain[2] * x
            error = float(np.max(np.abs(result.displacements - expected)))
            scale = max(float(np.max(np.abs(expected))), 1.0e-30)
            rows = result.element_results[0].get("ply_results", [])
            ply_count = len({int(row["ply_index"]) for row in rows})
            points.append(
                {
                    "nx": nx,
                    "ny": ny,
                    "element_count": len(model.elements),
                    "maximum_absolute_displacement_error_m": error,
                    "maximum_relative_displacement_error": error / scale,
                    "ply_count": ply_count,
                }
            )
        maximum = max(float(row["maximum_relative_displacement_error"]) for row in points)
        checks = {
            "affine_membrane_patch": maximum <= self.static_patch_limit,
            "ply_postprocess": ply_count == 4,
        }
        return {
            "reference": "epsilon0 = A^-1 N for a symmetric flat laminate",
            "resultant_n_per_m": resultant.tolist(),
            "expected_midplane_strain": expected_strain.tolist(),
            "points": points,
            "checks": {key: bool(value) for key, value in checks.items()},
        }

    def _static_model(self, nx: int, ny: int, traction: float) -> FiniteElementModel:
        nodes, triangles, node = rectangular_tri_mesh(1.0, 0.2, nx, ny)
        edge = [node(nx, j) for j in range(ny + 1)]
        weights = np.ones(len(edge))
        weights[[0, -1]] = 0.5
        weights /= weights.sum()
        fixed = [
            {"node": index, "dofs": ["UZ", "RX", "RY", "RZ"]}
            for index in range(len(nodes))
        ]
        fixed.extend({"node": node(0, j), "dofs": ["UX"]} for j in range(ny + 1))
        fixed.append({"node": node(0, 0), "dofs": ["UY"]})
        return FiniteElementModel.from_raw(
            analysis="linear_static",
            nodes=nodes.tolist(),
            elements=[{"type": "MITC3", "nodes": triangle.tolist(), "material": "skin"} for triangle in triangles],
            materials={"skin": self.laminate_data()},
            fixed_dofs=fixed,
            loads=[
                {"node": int(current), "dof": "UX", "value": traction * 0.2 * float(weight)}
                for current, weight in zip(edge, weights, strict=True)
            ],
            verification_profile="quick",
        )

    def _dynamic_model(self, analysis: dict[str, object]) -> FiniteElementModel:
        return cantilever_model(
            *self.mesh,
            laminate=True,
            transverse_force=0.0,
            analysis={**analysis, "dense_modal_max_dofs": 6000, "modal_residual_failure_tolerance": self.residual_limit},
        )

    def _newmark_point(
        self,
        model: FiniteElementModel,
        tip: int,
        initial: list[dict[str, object]],
        frequency: float,
        steps_per_period: int,
    ) -> dict[str, Any]:
        step = 1.0 / frequency / steps_per_period
        model.analysis = AnalysisSettings.from_raw(
            {
                "type": "transient_dynamic", "method": "newmark", "time_step": step,
                "steps": 2 * steps_per_period, "newmark_beta": 0.25, "newmark_gamma": 0.5,
                "load_factors": [0.0], "initial_displacements": initial,
                "history_probes": [{"node": tip, "dof": "UZ", "label": "tip_uz"}],
            }
        )
        result = solve_model(model, enforce_policy=False)
        history = result.solver["time_history"]
        times = np.asarray([row["time"] for row in history], dtype=float)
        response = np.asarray([row["probes"]["tip_uz"]["displacement"] for row in history], dtype=float)
        expected = self.amplitude * np.cos(2.0 * math.pi * frequency * times)
        rows = result.element_results[0].get("ply_results", [])
        return {
            "steps_per_period": steps_per_period,
            "time_step_s": step,
            "normalized_rms_error": float(np.sqrt(np.mean((response - expected) ** 2)) / self.amplitude),
            "maximum_relative_energy_drift": max(abs(float(row["relative_energy_drift"])) for row in history),
            "maximum_dynamic_residual_norm": max(float(row["dynamic_residual_norm"]) for row in history),
            "ply_count_at_final_time": len({int(row["ply_index"]) for row in rows}),
            "times_s": times.tolist(), "tip_uz_m": response.tolist(), "reference_tip_uz_m": expected.tolist(),
        }

    def _harmonic(self, model: FiniteElementModel, modal: Any, tip: int, frequency: float, omega: float, mode: np.ndarray) -> dict[str, Any]:
        model.loads = modal_nodal_loads(model, modal.dofs, mode)
        frequencies = np.asarray(self.frequency_ratios, dtype=float) * frequency
        alpha = 2.0 * self.damping_ratio * omega
        model.analysis = AnalysisSettings.from_raw(
            {"type": "harmonic_response", "method": "direct_frequency", "frequencies_hz": frequencies.tolist(), "rayleigh_alpha": alpha, "rayleigh_beta": 0.0}
        )
        result = solve_model(model, enforce_policy=False)
        index = result.dofs.index(tip, "UZ")
        numerical = np.asarray([response[index] for response in result.responses], dtype=complex)
        reference = _analytical_response(float(mode[modal.dofs.index(tip, "UZ")]), omega, frequencies, alpha)
        errors = np.abs(numerical - reference) / np.maximum(np.abs(reference), 1.0e-30)
        static_error = self._static_limit(modal, mode, tip, numerical[0])
        rows = result.shell_stress_response[0]["element_results"][0].get("ply_results", [])
        ply_count = len({int(row["ply_index"]) for row in rows})
        peak = int(np.argmax(np.abs(numerical)))
        checks = {
            "complex_modal_response": float(np.max(errors)) <= self.harmonic_error_limit,
            "zero_hz_static_limit": static_error <= 1.0e-9,
            "residual": float(result.solver["max_relative_residual_norm"]) <= self.residual_limit,
            "drilling_condensed": bool(result.solver["dynamic_reduction"]["condensed_drilling_dof_count"] > 0),
            "ply_stress_postprocess": ply_count == 4,
            "resonance_peak": bool(0.95 <= self.frequency_ratios[peak] <= 1.05),
        }
        return {
            "frequencies_hz": frequencies.tolist(), "frequency_ratios": list(self.frequency_ratios),
            "amplitudes_m": np.abs(numerical).tolist(), "phases_degrees": np.degrees(np.angle(numerical)).tolist(),
            "maximum_relative_error": float(np.max(errors)), "zero_hz_static_relative_error": static_error,
            "maximum_relative_residual": float(result.solver["max_relative_residual_norm"]),
            "ply_count_at_first_frequency": ply_count,
            "checks": {key: bool(value) for key, value in checks.items()},
        }

    def _static_limit(self, modal: Any, mode: np.ndarray, tip: int, value: complex) -> float:
        model = self._dynamic_model({"type": "linear_static", "method": "direct"})
        model.loads = modal_nodal_loads(model, modal.dofs, mode)
        static = solve_model(model, enforce_policy=False)
        expected = float(static.displacements[static.dofs.index(tip, "UZ")])
        return abs(value.real - expected) / max(abs(expected), 1.0e-30)


def write_mitc3_laminate_dynamic_evidence(output: str | Path) -> dict[str, Any]:
    """Write the internal evidence bundle and its deterministic figures."""
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    summary = Mitc3LaminateDynamicStudy().run()
    write_json_file(target / "summary.json", summary)
    _write_report(target / f"{STUDY_ID}.md", summary)
    _plot_newmark(summary, target / f"{STUDY_ID}-newmark.png")
    _plot_harmonic(summary, target / f"{STUDY_ID}-harmonic.png")
    write_json_file(
        target / "vnv_manifest.json",
        {"schema_version": 1, "study_id": STUDY_ID, "source": git_source_state(PROJECT_ROOT), "files": discovered_file_entries(target, lambda _: "mitc3_laminate_dynamic_vnv", exclude_names=("vnv_manifest.json",))},
    )
    return summary


def _tip_midline_node(nodes: np.ndarray) -> int:
    x_max = float(np.max(nodes[:, 0]))
    y_mid = 0.5 * (float(np.min(nodes[:, 1])) + float(np.max(nodes[:, 1])))
    candidates = np.flatnonzero(np.isclose(nodes[:, 0], x_max))
    return int(candidates[np.argmin(np.abs(nodes[candidates, 1] - y_mid))])


def _write_report(path: Path, summary: dict[str, Any]) -> None:
    static = summary["static"]
    modal = summary["modal"]
    lines = [
        f"# {STUDY_ID}", "", "## Objet", "",
        "Verification interne MITC3+ multicouche plane symetrique `[0/90/90/0]`. La campagne combine un patch membranaire analytique et des invariants modaux/dynamiques. Elle ne constitue pas une correlation externe.", "",
        "## Statique", "", "| Elements | Erreur relative deplacement | Plis post-traites |", "| ---: | ---: | ---: |",
    ]
    lines.extend(f"| {row['element_count']} | {row['maximum_relative_displacement_error']:.3e} | {row['ply_count']} |" for row in static["points"])
    lines.extend(["", "## Modal", "", f"Frequence fondamentale : `{modal['frequencies_hz'][0]:.6f}` Hz. Residu relatif : `{modal['max_relative_residual']:.3e}`. Orthogonalites masse/raideur : `{modal['mass_orthogonality_error']:.3e}` / `{modal['stiffness_orthogonality_error']:.3e}`.", "", "## Newmark", "", "| Pas/periode | Erreur RMS | Derive energie | Residu | Plis finaux |", "| ---: | ---: | ---: | ---: | ---: |"])
    lines.extend(f"| {row['steps_per_period']} | {row['normalized_rms_error']:.3e} | {row['maximum_relative_energy_drift']:.3e} | {row['maximum_dynamic_residual_norm']:.3e} | {row['ply_count_at_final_time']} |" for row in summary["newmark"]["points"])
    harmonic = summary["harmonic"]
    lines.extend(["", "## Harmonique", "", f"Erreur complexe maximale : `{harmonic['maximum_relative_error']:.3e}`. Limite statique a 0 Hz : `{harmonic['zero_hz_static_relative_error']:.3e}`. Post-traitement : `{harmonic['ply_count_at_first_frequency']}` plis.", "", f"![Newmark]({STUDY_ID}-newmark.png)", "", f"![Harmonique]({STUDY_ID}-harmonic.png)", "", "## Limites ouvertes", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.extend(["", f"Statut interne : **{summary['status']}**. Maturite : `{summary['maturity']}`.", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def _plot_newmark(summary: dict[str, Any], path: Path) -> None:
    coarse, fine = summary["newmark"]["points"][0], summary["newmark"]["points"][-1]
    figure, axis = plt.subplots(figsize=(7.2, 4.4))
    axis.plot(fine["times_s"], fine["reference_tip_uz_m"], "k--", label="reference modale")
    axis.plot(coarse["times_s"], coarse["tip_uz_m"], color="#bc4749", alpha=0.75, label=f"T/{coarse['steps_per_period']}")
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
