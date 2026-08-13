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
from solveur.core.assembler import GlobalAssembler
from solveur.core.model import FiniteElementModel, NodalLoad
from solveur.io.manifest import write_json_file
from solveur.verification.mitc3_models import cantilever_model
from solveur.verification.vnv_manifest import write_vnv_manifest


SUPPORTED_FAMILIES = ("TET4", "TET10", "MITC3", "BEAM2", "SPRING_MASS")


class LinearDynamicFamilyCampaign:
    """Produce reproducible modal, Newmark and harmonic evidence per family.

    This is a controlled internal campaign.  Its oscillator oracle validates
    the assembled ``K`` and ``M`` paths, boundary-condition reduction and time
    or frequency integration.  The element formulation itself still requires
    the static and external correlations declared in its own scope.
    """

    def __init__(self, family: str, output_dir: str | Path) -> None:
        name = str(family).upper()
        if name not in SUPPORTED_FAMILIES:
            raise ValueError(f"Unsupported dynamic V&V family {family!r}.")
        self.family = name
        self.output_dir = Path(output_dir).resolve()

    @property
    def study_id(self) -> str:
        return f"VNV-{self.family}-LINEAR-DYNAMICS-001"

    def run(self) -> dict[str, Any]:
        """Run the three analysis paths and write a compact review bundle."""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        modal_model = self._model({"type": "modal", "method": "eigh", "modes": 3})
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
            "status": status,
            "maturity": "technical_verification",
            "scope": _scope_for(self.family),
            "reference": {
                "type": "first_eigenmode_closed_form_oscillator",
                "description": "q(t)=q0 cos(2 pi f1 t) for undamped free vibration",
            },
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
        passed = (
            frequency > 0.0
            and np.isfinite(frequency)
            and residual <= 1.0e-8
            and mass_error <= 1.0e-8
            and stiffness_error <= 1.0e-8
        )
        return {
            "status": "PASS" if passed else "FAIL",
            "first_frequency_hz": frequency,
            "max_relative_residual": residual,
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
        steps = 120
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
        expected = probe_initial * np.cos(2.0 * math.pi * frequency * times)
        scale = max(float(np.max(np.abs(expected))), 1.0e-18)
        relative_rms = float(np.sqrt(np.mean((values - expected) ** 2)) / scale)
        energy_drift = float(max(abs(row["relative_energy_drift"]) for row in history))
        residual = float(max(result.solver["residual_history"], default=0.0))
        passed = relative_rms <= 2.0e-3 and energy_drift <= 1.0e-4 and residual <= 1.0e-7
        return {
            "status": "PASS" if passed else "FAIL",
            "period_s": period,
            "time_step_s": period / steps,
            "steps": steps,
            "probe": {"node": probe_node, "dof": probe_dof},
            "relative_rms_error_to_single_mode": relative_rms,
            "maximum_energy_drift": energy_drift,
            "maximum_dynamic_residual": residual,
        }

    def _harmonic_study(
        self,
        modal_model: FiniteElementModel,
        modal: Any,
        frequency: float,
    ) -> dict[str, Any]:
        mode = np.asarray(modal.modes[:, 0], dtype=float)
        mass = GlobalAssembler().assemble_mass(modal_model, modal.dofs)
        modal_force = np.asarray(mass @ mode).ravel()
        loads = _state_entries(modal.dofs, modal_force)
        frequencies = [0.0, 0.8 * frequency, frequency, 1.2 * frequency]
        harmonic_model = self._model(
            {
                "type": "harmonic_response",
                "method": "direct_frequency",
                "frequencies_hz": frequencies,
                "rayleigh_alpha": 0.02,
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
        resonance_ratio = amplitudes[2] / max(amplitudes[1], amplitudes[3], 1.0e-30)
        residual = float(harmonic.solver["max_relative_residual_norm"])
        passed = finite and static_error <= 1.0e-8 and resonance_ratio > 1.0 and residual <= 1.0e-7
        return {
            "status": "PASS" if passed else "FAIL",
            "frequencies_hz": frequencies,
            "zero_frequency_static_error": static_error,
            "resonance_amplitude_ratio": resonance_ratio,
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
    else:
        nodes = [
            [0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0],
            [0.5, 0.0, 0.0], [0.5, 0.5, 0.0], [0.0, 0.5, 0.0], [0.0, 0.0, 0.5],
            [0.5, 0.0, 0.5], [0.0, 0.5, 0.5],
        ]
        element_nodes = list(range(10))
        fixed_nodes = (0, 2, 3, 4, 5, 6, 7, 8, 9)
    return FiniteElementModel.from_raw(
        nodes=nodes,
        elements=[{"type": family, "nodes": element_nodes, "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 70.0e9, "nu": 0.3, "density": 2700.0}},
        fixed_dofs=[{"node": node, "dofs": ["UX", "UY", "UZ"]} for node in fixed_nodes],
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
        "BEAM2": "beam2-linear-dynamics",
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
