"""Reusable internal V&V campaign for linear modal and dynamic element routes.

The campaign deliberately projects an element assembly on its first computed
mode.  This gives an independent closed-form oscillator response for Newmark
without hiding an assembly or mass-matrix defect behind an arbitrary load
history.  It complements, but never replaces, an external-oracle comparison.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np

from solveur.api import solve_model
from solveur.core.assembly.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel, NodalLoad
from solveur.elements.shell.mitc4.mesh import MeshFactory
from solveur.io.manifest import write_json_file
from solveur.verification.mitc3_models import cantilever_model
from solveur.verification.mitc4_newmark_extended import modal_nodal_loads
from solveur.verification.vnv_manifest import write_vnv_manifest


SUPPORTED_FAMILIES = (
    "TET4",
    "TET10",
    "HEX8",
    "HEX20",
    "BEAM2",
    "MITC3",
    "MITC4",
    "DISCRETE",
    "SPRING_MASS",
)


class LinearDynamicFamilyCampaign:
    """Produce reproducible modal, Newmark and harmonic evidence per family.

    This is a controlled internal campaign.  Its oscillator oracle validates
    the assembled ``K`` and ``M`` paths, boundary-condition reduction and time
    or frequency integration.  The element formulation itself still requires
    the static and external correlations declared in its own scope.
    """

    def __init__(
        self,
        family: str,
        output_dir: str | Path,
        *,
        variant: str = "baseline",
        modal_modes: int = 3,
        time_levels: tuple[int, ...] = (30, 60, 120, 240),
        harmonic_frequency_ratios: tuple[float, ...] = (0.0, 0.8, 1.0, 1.2),
    ) -> None:
        name = str(family).upper()
        if name not in SUPPORTED_FAMILIES:
            raise ValueError(f"Unsupported dynamic V&V family {family!r}.")
        self.family = name
        self.output_dir = Path(output_dir).resolve()
        self.variant = str(variant).lower().replace(" ", "-")
        self.modal_modes = int(modal_modes)
        self.time_levels = tuple(int(level) for level in time_levels)
        self.harmonic_frequency_ratios = tuple(float(value) for value in harmonic_frequency_ratios)
        if self.modal_modes < 1:
            raise ValueError("modal_modes must be positive.")
        if len(self.time_levels) < 2 or any(level <= 0 for level in self.time_levels):
            raise ValueError("time_levels must contain at least two positive values.")
        if not self.harmonic_frequency_ratios or self.harmonic_frequency_ratios[0] != 0.0:
            raise ValueError("harmonic_frequency_ratios must start at zero frequency.")

    @property
    def study_id(self) -> str:
        suffix = "" if self.variant == "baseline" else f"-{self.variant.upper()}"
        return f"VNV-{self.family}-LINEAR-DYNAMICS-001{suffix}"

    def run(self) -> dict[str, Any]:
        """Run the three analysis paths and write a compact review bundle."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        modal_model = self._model({"type": "modal", "method": "eigh", "modes": self.modal_modes})
        modal = solve_model(modal_model, enforce_policy=False)
        frequency = float(modal.frequencies_hz[0])
        mode = np.asarray(modal.modes[:, 0], dtype=float)
        probe_index = int(np.argmax(np.abs(mode)))
        probe_node, probe_dof = _index_to_dof(modal.dofs, probe_index)
        mode_scale = 1.0e-5 / max(float(np.max(np.abs(mode))), 1.0e-30)
        initial = _state_entries(modal.dofs, mode * mode_scale)

        modal_study = self._modal_study(modal, frequency)
        newmark_study = self._newmark_study(
            frequency, initial, probe_node, probe_dof, float(mode[probe_index] * mode_scale)
        )
        harmonic_study = self._harmonic_study(modal_model, modal, frequency)
        studies = {"modal": modal_study, "newmark": newmark_study, "harmonic": harmonic_study}
        status = "PASS" if all(row["status"] == "PASS" for row in studies.values()) else "FAIL"
        summary: dict[str, Any] = {
            "schema_version": 1,
            "study_id": self.study_id,
            "family": self.family,
            "variant": self.variant,
            "configuration": {
                "modal_modes": self.modal_modes,
                "newmark_time_levels_steps": list(self.time_levels),
                "harmonic_frequency_ratios": list(self.harmonic_frequency_ratios),
            },
            "status": status,
            "maturity": "technical_verification",
            "scope": _scope_for(self.family),
            "reference": {
                "type": "first_eigenmode_closed_form_oscillator",
                "description": "q(t)=q0 cos(2 pi f1 t) for undamped free vibration",
            },
            "qualification_status": "INTERNAL_PREQUALIFICATION_ONLY",
            "studies": studies,
            "limitations": [
                "The modal oscillator oracle validates the assembled linear dynamic route, not a complete external element correlation.",
                "Damping, multi-mode modal truncation, non-proportional damping and nonlinear dynamics are outside this compact campaign.",
                "Owner acceptance requires the family-specific static evidence and external comparison policy to be reviewed separately.",
            ],
        }
        write_json_file(self.output_dir / "summary.json", summary)
        (self.output_dir / "report.md").write_text(_report(summary), encoding="utf-8")
        write_vnv_manifest(self.output_dir, self.study_id)
        return summary

    @staticmethod
    def _modal_study(result: Any, frequency: float) -> dict[str, Any]:
        solver = result.solver
        residual = float(solver.get("max_relative_residual", math.inf))
        mass_error = float(solver.get("mass_orthogonality_error", math.inf))
        stiffness_error = float(solver.get("stiffness_diagonal_error", math.inf))
        residual_limit = 1.0e-7
        passed = (
            frequency > 0.0
            and np.isfinite(frequency)
            and residual <= residual_limit
            and mass_error <= 1.0e-8
            and stiffness_error <= 1.0e-8
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "first_frequency_hz": frequency,
            "max_relative_residual": residual,
            "residual_limit": residual_limit,
            "mass_orthogonality_error": mass_error,
            "stiffness_orthogonality_error": stiffness_error,
        }

    def _newmark_study(
        self,
        frequency: float,
        initial: list[dict[str, Any]],
        probe_node: int,
        probe_dof: str,
        probe_initial: float,
    ) -> dict[str, Any]:
        period = 1.0 / frequency
        time_levels = self.time_levels
        histories: dict[int, tuple[np.ndarray, np.ndarray, Any]] = {}
        for steps in time_levels:
            model = self._model(
                {
                    "type": "transient_dynamic",
                    "method": "newmark",
                    "time_step": period / steps,
                    "steps": steps,
                    "newmark_beta": 0.25,
                    "newmark_gamma": 0.5,
                    "rayleigh_alpha": 0.0,
                    "rayleigh_beta": 0.0,
                    "load_factors": [0.0],
                    "initial_displacements": initial,
                    "history_probes": [{"node": probe_node, "dof": probe_dof, "label": "modal_probe"}],
                }
            )
            result = solve_model(model, enforce_policy=False)
            history = result.solver["time_history"]
            times = np.asarray([row["time"] for row in history], dtype=float)
            values = np.asarray(
                [row["probes"]["modal_probe"]["displacement"] for row in history], dtype=float
            )
            histories[steps] = (times, values, result)

        steps = time_levels[-1]
        times, values, result = histories[steps]
        expected = probe_initial * np.cos(2.0 * math.pi * frequency * times)
        scale = max(float(np.max(np.abs(expected))), 1.0e-18)
        relative_rms = float(np.sqrt(np.mean((values - expected) ** 2)) / scale)
        energy_drift = float(max(abs(row["relative_energy_drift"]) for row in result.solver["time_history"]))
        residual = float(max(result.solver["residual_history"], default=0.0))
        refinement_errors = []
        for coarse_steps, fine_steps in zip(time_levels[:-1], time_levels[1:]):
            coarse_times, coarse_values, _ = histories[coarse_steps]
            fine_times, fine_history_values, _ = histories[fine_steps]
            fine_values = np.interp(coarse_times, fine_times, fine_history_values)
            reference_scale = max(float(np.max(np.abs(fine_values))), 1.0e-30)
            refinement_errors.append(
                float(np.linalg.norm(fine_values - coarse_values) / reference_scale)
            )
        # The promotion metric is the final adjacent-level increment. Earlier
        # levels remain diagnostic because they intentionally include the
        # coarse transient start-up error.
        time_refinement_error = refinement_errors[-1] if refinement_errors else 0.0
        passed = (
            relative_rms <= 2.0e-3
            and energy_drift <= 1.0e-4
            and residual <= 1.0e-7
            and time_refinement_error <= 1.0e-2
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "period_s": period,
            "time_step_s": period / steps,
            "steps": steps,
            "probe": {"node": probe_node, "dof": probe_dof},
            "relative_rms_error_to_single_mode": relative_rms,
            "maximum_energy_drift": energy_drift,
            "maximum_dynamic_residual": residual,
            "time_level_count": len(time_levels),
            "time_levels_steps": list(time_levels),
            "time_refinement_error_max": time_refinement_error,
            "time_refinement_error_all_levels_max": max(refinement_errors, default=0.0),
        }

    def _harmonic_study(
        self,
        modal_model: FiniteElementModel,
        modal: Any,
        frequency: float,
    ) -> dict[str, Any]:
        mode = np.asarray(modal.modes[:, 0], dtype=float)
        if self.family == "MITC4":
            loads = [
                {"node": load.node, "dof": load.dof, "value": load.value}
                for load in modal_nodal_loads(modal_model, modal.dofs, mode)
            ]
        else:
            mass = GlobalAssembler().assemble_mass(modal_model, modal.dofs)
            modal_force = np.asarray(mass @ mode).ravel()
            loads = _state_entries(modal.dofs, modal_force)
        damping_alpha = 0.04 * (2.0 * math.pi * frequency) if self.family == "MITC4" else 0.02
        frequencies = [ratio * frequency for ratio in self.harmonic_frequency_ratios]
        harmonic_model = self._model(
            {
                "type": "harmonic_response",
                "method": "direct_frequency",
                "frequencies_hz": frequencies,
                "rayleigh_alpha": damping_alpha,
                "rayleigh_beta": 0.0,
            },
            loads=loads,
        )
        harmonic = solve_model(harmonic_model, enforce_policy=False)
        static = solve_model(self._model("linear_static", loads=loads), enforce_policy=False)
        zero = np.asarray(harmonic.responses[0], dtype=complex)
        static_error = float(
            np.linalg.norm(zero.real - static.displacements)
            / max(np.linalg.norm(static.displacements), 1.0e-30)
        )
        amplitudes = [float(np.max(np.abs(response))) for response in harmonic.responses]
        finite = bool(np.all(np.isfinite(np.asarray(harmonic.responses))))
        resonance_index = min(
            range(len(self.harmonic_frequency_ratios)),
            key=lambda index: abs(self.harmonic_frequency_ratios[index] - 1.0),
        )
        off_resonance = [value for index, value in enumerate(amplitudes) if index != resonance_index]
        resonance_ratio = amplitudes[resonance_index] / max(*off_resonance, 1.0e-30)
        residual = float(harmonic.solver["max_relative_residual_norm"])
        passed = finite and static_error <= 1.0e-8 and resonance_ratio > 1.0 and residual <= 1.0e-7
        return {
            "status": "PASS" if passed else "FAIL",
            "frequencies_hz": frequencies,
            "zero_frequency_static_error": static_error,
            "resonance_amplitude_ratio": resonance_ratio,
            "resonance_frequency_ratio": self.harmonic_frequency_ratios[resonance_index],
            "frequency_grid_count": len(self.harmonic_frequency_ratios),
            "frequency_ratio_step_min": min(
                np.diff(self.harmonic_frequency_ratios), default=0.0
            ),
            "maximum_relative_residual": residual,
            "finite_response": finite,
        }

    def _model(
        self,
        analysis: str | dict[str, Any],
        *,
        loads: list[dict[str, Any]] | None = None,
    ) -> FiniteElementModel:
        if self.family in {"TET4", "TET10"}:
            return _solid_model(self.family, analysis, loads or [])
        if self.family == "MITC3":
            model = cantilever_model(4, 1, analysis=analysis, transverse_force=0.0)
            model.loads = [NodalLoad(**item) for item in (loads or [])]
            return model
        if self.family == "MITC4":
            model = _mitc4_model(analysis, loads or [])
            return model
        if self.family == "BEAM2":
            return _beam_model(analysis, loads or [])
        return _spring_mass_model(analysis, loads or [])


def _solid_model(
    family: str,
    analysis: str | dict[str, Any],
    loads: list[dict[str, Any]],
) -> FiniteElementModel:
    if family == "TET4":
        nodes = [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        element_nodes = list(range(4))
        fixed_nodes = (0, 2, 3)
    elif family == "TET10":
        nodes = [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
            [0.5, 0.0, 0.0], [0.5, 0.5, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 0.5],
            [0.5, 0.0, 0.5], [0.0, 0.5, 0.5],
        ]
        element_nodes = list(range(10))
        fixed_nodes = (0, 2, 3, 4, 5, 6, 7, 8, 9)
    elif family == "HEX8":
        nodes = [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
        ]
        element_nodes = list(range(8))
        fixed_nodes = (0, 3, 4, 7)
    else:
        nodes = [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [1.0, 1.0, 0.0], [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0], [1.0, 0.0, 1.0], [1.0, 1.0, 1.0], [0.0, 1.0, 1.0],
            [0.5, 0.0, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 0.5], [1.0, 0.5, 0.0],
            [1.0, 0.0, 0.5], [0.5, 1.0, 0.0], [1.0, 1.0, 0.5], [0.0, 1.0, 0.5],
            [0.5, 0.0, 1.0], [0.0, 0.5, 1.0], [1.0, 0.5, 1.0], [0.5, 1.0, 1.0],
        ]
        element_nodes = list(range(20))
        fixed_nodes = (0, 3, 4, 7, 9, 10, 15, 17)
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=[{"type": family, "nodes": element_nodes, "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 70.0e9, "nu": 0.3, "density": 2700.0}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
        loads=loads,
        analysis=analysis,
        verification_profile="quick",
    )


def _mitc4_model(analysis: str | dict[str, Any], loads: list[dict[str, Any]]) -> FiniteElementModel:
    """Build the small isotropic MITC4 cantilever used by the family campaign."""
    mesh = MeshFactory.rectangular_plate(4, 2, 1.0, 0.2)
    root = np.flatnonzero(np.isclose(mesh.nodes[:, 0], 0.0))
    if isinstance(analysis, dict) and str(analysis.get("type", "")).lower() == "modal":
        analysis = {
            **analysis,
            "modal_eigenpair_refinement_iterations": 3,
        }
    return FiniteElementModel.from_raw(
        nodes=mesh.nodes.tolist(),
        elements=[{"type": "MITC4", "nodes": quad.tolist(), "material": "shell"} for quad in mesh.quads],
        materials={
            "shell": {
                "type": "shell_isotropic",
                "E": 70.0e9,
                "nu": 0.3,
                "t": 0.01,
                "density": 2700.0,
                "drilling_scale": 1.0e-4,
            }
        },
        fixed_dofs=[
            {"node": int(node), "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}
            for node in root
        ],
        loads=loads,
        analysis=analysis,
        verification_profile="quick",
    )


def _beam_model(analysis: str | dict[str, Any], loads: list[dict[str, Any]]) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0]],
        elements=[
            {"type": "BEAM2", "nodes": [0, 1], "material": "beam"},
            {"type": "BEAM2", "nodes": [1, 2], "material": "beam"},
        ],
        materials={
            "beam": {
                "type": "beam_isotropic", "E": 210.0e9, "nu": 0.3, "A": 0.01,
                "Iy": 2.0e-6, "Iz": 3.0e-6, "J": 5.0e-6, "density": 7800.0,
                "reference_vector": [0.0, 1.0, 0.0],
            }
        },
        fixed_dofs=[{"node": 0, "dofs": ["UX", "UY", "UZ", "RX", "RY", "RZ"]}],
        loads=loads,
        analysis=analysis,
        verification_profile="quick",
    )


def _spring_mass_model(analysis: str | dict[str, Any], loads: list[dict[str, Any]]) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0]],
        elements=[],
        materials={},
        springs=[{"node_a": 0, "dofs": ["UX", "UY", "UZ"], "stiffness": [1000.0, 4000.0, 9000.0]}],
        concentrated_masses=[{"node": 0, "mass": 10.0}],
        fixed_dofs=[{"node": 0, "dofs": ["UY", "UZ"]}],
        loads=loads,
        analysis=analysis,
        verification_profile="quick",
    )


def _index_to_dof(dofs: Any, index: int) -> tuple[int, str]:
    for node, names in dofs.node_dofs.items():
        for name in names:
            if dofs.index(node, name) == index:
                return int(node), str(name)
    raise ValueError(f"Cannot map dynamic probe index {index}.")


def _state_entries(dofs: Any, values: np.ndarray) -> list[dict[str, Any]]:
    entries = []
    for node, names in dofs.node_dofs.items():
        for name in names:
            value = float(values[dofs.index(node, name)])
            if abs(value) > 1.0e-18:
                entries.append({"node": int(node), "dof": str(name), "value": value})
    return entries


def _scope_for(family: str) -> str:
    return {
        "TET4": "linear-dynamics",
        "TET10": "tet10-linear-dynamics",
            "MITC3": "mitc3-linear-dynamics",
            "MITC4": "mitc4-linear-dynamics",
            "HEX8": "hex8-linear-dynamics",
            "HEX20": "hex20-linear-dynamics",
            "BEAM2": "beam2-linear-dynamics",
        "DISCRETE": "discrete-linear-dynamics",
        "SPRING_MASS": "discrete-linear-dynamics",
    }[family]


def _report(summary: dict[str, Any]) -> str:
    lines = [
        f"# {summary['study_id']}",
        "",
        f"Statut automatise : **{summary['status']}**.",
        "",
        "| Analyse | Verdict | Indicateur principal |",
        "| --- | --- | ---: |",
        f"| Modal | {summary['studies']['modal']['status']} | residu = {summary['studies']['modal']['max_relative_residual']:.3e} |",
        f"| Newmark | {summary['studies']['newmark']['status']} | erreur RMS = {summary['studies']['newmark']['relative_rms_error_to_single_mode']:.3e} |",
        f"| Harmonique | {summary['studies']['harmonic']['status']} | erreur statique a 0 Hz = {summary['studies']['harmonic']['zero_frequency_static_error']:.3e} |",
        "",
        "Le cas est internalise et reproductible. Il ne remplace pas la correlation externe et ne couvre pas la dynamique non lineaire.",
        "",
    ]
    return "\n".join(lines)
