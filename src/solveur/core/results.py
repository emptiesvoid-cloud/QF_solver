"""Solve result DTOs and JSON conversion."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from solveur.core.audit import SolverAudit
from solveur.core.dofs import DofManager
from solveur.core.material_state import MaterialStateTable, material_states_to_dict
from solveur.core.qualification import RunVerdict, qualification_summary, run_verdict
from solveur.core.result_serialization import complex_nodal_state, legacy_six_dof_vector, modal_shape, nodal_state
from solveur.mesh.validation import MeshReport


class QualificationAwareResult:
    """Expose the qualification verdict without changing numerical status."""

    @property
    def run_verdict(self) -> RunVerdict:
        return run_verdict(self)


@dataclass(frozen=True)
class SolveResult(QualificationAwareResult):
    """Linear static solve result."""

    status: str
    displacements: np.ndarray
    dofs: DofManager
    mesh_report: MeshReport
    node_count: int
    element_count: int
    message: str = ""
    analysis: str = "linear_static"
    method: str = "direct"
    solver: dict[str, Any] = field(default_factory=dict)
    element_results: list[dict[str, object]] = field(default_factory=list)
    nodal_results: list[dict[str, object]] = field(default_factory=list)
    material_states: MaterialStateTable = field(default_factory=dict)
    audit: SolverAudit | None = None

    @property
    def ndof(self) -> int:
        return int(self.displacements.shape[0])

    @property
    def max_displacement(self) -> float:
        if self.displacements.size == 0:
            return 0.0
        return float(np.max(np.abs(self.displacements)))

    def displacements_for_plot(self) -> np.ndarray:
        """Return a legacy 6-dof-per-node vector for MITC4 plotting."""
        return legacy_six_dof_vector(self.dofs, self.displacements, self.node_count)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "status": self.status,
            "run_verdict": self.run_verdict.value,
            "analysis": self.analysis,
            "method": self.method,
            "message": self.message,
            "node_count": self.node_count,
            "element_count": self.element_count,
            "ndof": self.ndof,
            "max_displacement": self.max_displacement,
            "displacements": nodal_state(self.dofs, self.displacements),
            "element_results": self.element_results,
            "nodal_results": self.nodal_results,
            "solver": self.solver,
            "mesh_report": self.mesh_report.to_dict(),
        }
        if self.material_states:
            data["material_states"] = material_states_to_dict(self.material_states)
        if self.audit is not None:
            data["audit"] = self.audit.to_dict()
            data["qualification_summary"] = qualification_summary(self)
        return data


@dataclass(frozen=True)
class ModalResult(QualificationAwareResult):
    """Modal analysis result."""

    status: str
    eigenvalues: np.ndarray
    frequencies_hz: np.ndarray
    modes: np.ndarray
    dofs: DofManager
    mesh_report: MeshReport
    node_count: int
    element_count: int
    method: str = "eigh"
    message: str = ""
    solver: dict[str, Any] = field(default_factory=dict)
    audit: SolverAudit | None = None

    def to_dict(self) -> dict[str, Any]:
        mode_list: list[dict[str, Any]] = []
        for mode_index in range(self.modes.shape[1]):
            mode_list.append(
                {
                    "index": mode_index + 1,
                    "eigenvalue": float(self.eigenvalues[mode_index]),
                    "frequency_hz": float(self.frequencies_hz[mode_index]),
                    "shape": modal_shape(self.dofs, self.modes, mode_index),
                }
            )
        data = {
            "status": self.status,
            "run_verdict": self.run_verdict.value,
            "analysis": "modal",
            "method": self.method,
            "message": self.message,
            "node_count": self.node_count,
            "element_count": self.element_count,
            "ndof": int(self.modes.shape[0]),
            "modes": mode_list,
            "solver": self.solver,
            "mesh_report": self.mesh_report.to_dict(),
        }
        if self.audit is not None:
            data["audit"] = self.audit.to_dict()
            data["qualification_summary"] = qualification_summary(self)
        return data


@dataclass(frozen=True)
class DynamicResult(QualificationAwareResult):
    """Transient dynamic analysis result with final state and time history."""

    status: str
    displacements: np.ndarray
    velocities: np.ndarray
    accelerations: np.ndarray
    dofs: DofManager
    mesh_report: MeshReport
    node_count: int
    element_count: int
    method: str = "newmark"
    message: str = ""
    solver: dict[str, Any] = field(default_factory=dict)
    element_results: list[dict[str, object]] = field(default_factory=list)
    nodal_results: list[dict[str, object]] = field(default_factory=list)
    audit: SolverAudit | None = None

    @property
    def ndof(self) -> int:
        return int(self.displacements.shape[0])

    @property
    def max_displacement(self) -> float:
        if self.displacements.size == 0:
            return 0.0
        return float(np.max(np.abs(self.displacements)))

    def displacements_for_plot(self) -> np.ndarray:
        return legacy_six_dof_vector(self.dofs, self.displacements, self.node_count)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "status": self.status,
            "run_verdict": self.run_verdict.value,
            "analysis": "transient_dynamic",
            "method": self.method,
            "message": self.message,
            "node_count": self.node_count,
            "element_count": self.element_count,
            "ndof": self.ndof,
            "max_displacement": self.max_displacement,
            "displacements": nodal_state(self.dofs, self.displacements),
            "velocities": nodal_state(self.dofs, self.velocities),
            "accelerations": nodal_state(self.dofs, self.accelerations),
            "element_results": self.element_results,
            "nodal_results": self.nodal_results,
            "solver": self.solver,
            "mesh_report": self.mesh_report.to_dict(),
        }
        if self.audit is not None:
            data["audit"] = self.audit.to_dict()
            data["qualification_summary"] = qualification_summary(self)
        return data


@dataclass(frozen=True)
class HarmonicResult(QualificationAwareResult):
    """Steady-state harmonic response result."""

    status: str
    frequencies_hz: np.ndarray
    responses: list[np.ndarray]
    dofs: DofManager
    mesh_report: MeshReport
    node_count: int
    element_count: int
    method: str = "direct_frequency"
    message: str = ""
    solver: dict[str, Any] = field(default_factory=dict)
    shell_stress_response: list[dict[str, Any]] = field(default_factory=list)
    audit: SolverAudit | None = None

    @property
    def ndof(self) -> int:
        return self.dofs.ndof

    @property
    def max_displacement(self) -> float:
        if not self.responses:
            return 0.0
        return float(max(np.max(np.abs(response)) for response in self.responses))

    def to_dict(self) -> dict[str, Any]:
        rows = [
            _frequency_response_row(index, frequency, response, self.dofs)
            for index, (frequency, response) in enumerate(zip(self.frequencies_hz, self.responses))
        ]
        data = {
            "status": self.status,
            "run_verdict": self.run_verdict.value,
            "analysis": "harmonic_response",
            "method": self.method,
            "message": self.message,
            "node_count": self.node_count,
            "element_count": self.element_count,
            "ndof": self.ndof,
            "max_displacement": self.max_displacement,
            "frequency_response": rows,
            "peak_response": max(rows, key=lambda item: item["max_displacement_amplitude"]) if rows else {},
            "shell_stress_response": self.shell_stress_response,
            "peak_shell_stress": _peak_shell_stress(self.shell_stress_response),
            "solver": self.solver,
            "mesh_report": self.mesh_report.to_dict(),
        }
        if self.audit is not None:
            data["audit"] = self.audit.to_dict()
            data["qualification_summary"] = qualification_summary(self)
        return data


def _frequency_response_row(index: int, frequency: float, response: np.ndarray, dofs: DofManager) -> dict[str, Any]:
    return {
        "index": index,
        "frequency_hz": float(frequency),
        "omega_rad_s": float(2.0 * np.pi * frequency),
        "max_displacement_amplitude": float(np.max(np.abs(response))) if response.size else 0.0,
        "displacements": complex_nodal_state(dofs, response),
    }


def _peak_shell_stress(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    return max(rows, key=lambda row: float(row.get("peak_component", {}).get("amplitude", 0.0)))
