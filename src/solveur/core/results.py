"""Solve result DTOs and JSON conversion."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from solveur.core.audit import SolverAudit
from solveur.core.dofs import DofManager
from solveur.core.nonlinear.material_state import MaterialStateTable, material_states_to_dict
from solveur.core.qualification import RunVerdict, qualification_summary, run_verdict
from solveur.core.result_serialization import (
    complex_nodal_state,
    legacy_six_dof_vector,
    modal_shape,
    nodal_state,
)
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
class RotatingModalResult(QualificationAwareResult):
    """Complex single-speed QEP result; distinct from the real ``ModalResult``."""

    numerical_status: str
    maturity: str
    eigenvalues: np.ndarray
    modes: np.ndarray
    frequencies_hz: np.ndarray
    growth_rate_per_s: np.ndarray
    qep_residuals: np.ndarray
    selected_mode_indices: tuple[int, ...]
    dofs: DofManager
    mesh_report: MeshReport
    node_count: int
    element_count: int
    spin_speed_rad_s: float
    axis_global: tuple[float, float, float]
    frame_convention: str
    solver_metadata: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    provenance: dict[str, Any] = field(default_factory=dict)

    @property
    def status(self) -> str:
        """Compatibility alias for the numerical status, not a maturity claim."""
        return self.numerical_status

    @property
    def run_verdict(self) -> RunVerdict:
        """Keep a numerical pass visibly non-qualifying while maturity is experimental."""
        if self.numerical_status != "PASS":
            return RunVerdict.FAIL
        return RunVerdict.WARNING if self.maturity == "EXPERIMENTAL" else RunVerdict.FAIL

    @staticmethod
    def _complex_array(value: np.ndarray) -> dict[str, Any]:
        array = np.asarray(value, dtype=np.complex128)
        if not np.all(np.isfinite(array)):
            raise ValueError("Rotating modal result cannot serialize non-finite complex values.")
        return {"real": array.real.tolist(), "imag": array.imag.tolist()}

    @staticmethod
    def _decode_complex_array(value: Any) -> np.ndarray:
        if not isinstance(value, dict) or set(value) != {"real", "imag"}:
            raise ValueError("Complex result arrays require explicit real and imag fields.")
        real = np.asarray(value["real"], dtype=float)
        imag = np.asarray(value["imag"], dtype=float)
        if real.shape != imag.shape or not np.all(np.isfinite(real)) or not np.all(np.isfinite(imag)):
            raise ValueError("Complex result real/imag arrays must have matching finite shapes.")
        return real + 1j * imag

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis": "rotating_modal",
            "status": self.numerical_status,
            "numerical_status": self.numerical_status,
            "run_verdict": self.run_verdict.value,
            "maturity": self.maturity,
            "method": "dense_qep",
            "node_count": self.node_count,
            "element_count": self.element_count,
            "dof_map": [
                {"node": int(node), "dofs": list(names)} for node, names in sorted(self.dofs.node_dofs.items())
            ],
            "spin_speed_rad_s": float(self.spin_speed_rad_s),
            "axis_global": list(self.axis_global),
            "frame_convention": self.frame_convention,
            "raw_eigenvalues": self._complex_array(self.eigenvalues),
            "raw_modes": self._complex_array(self.modes),
            "frequency_hz": np.asarray(self.frequencies_hz, dtype=float).tolist(),
            "growth_rate_per_s": np.asarray(self.growth_rate_per_s, dtype=float).tolist(),
            "qep_residuals": np.asarray(self.qep_residuals, dtype=float).tolist(),
            "selected_mode_indices": list(self.selected_mode_indices),
            "solver_metadata": self.solver_metadata,
            "diagnostics": self.diagnostics,
            "provenance": self.provenance,
            "mesh_report": self.mesh_report.to_dict(),
        }

    @classmethod
    def complex_arrays_from_dict(cls, payload: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
        """Decode the complex spectral payload without discarding imaginary parts."""
        return cls._decode_complex_array(payload["raw_eigenvalues"]), cls._decode_complex_array(payload["raw_modes"])


@dataclass(frozen=True)
class CampbellResult(QualificationAwareResult):
    """Experimental speed-sweep result with explicit tracked branches and source solves."""

    numerical_status: str
    maturity: str
    spin_speeds_rad_s: tuple[float, ...]
    branches: list[dict[str, Any]]
    tracking_diagnostics: list[dict[str, Any]]
    source_result_keys: tuple[str, ...]
    source_result_hashes: tuple[str, ...]
    execution_identity: dict[str, Any]
    execution_key: str
    provenance: dict[str, Any]
    diagnostics: dict[str, Any] = field(default_factory=dict)
    source_results: tuple[RotatingModalResult, ...] = field(default_factory=tuple, repr=False, compare=False)

    @property
    def status(self) -> str:
        """Compatibility alias for the numerical status, not a maturity claim."""
        return self.numerical_status

    @property
    def run_verdict(self) -> RunVerdict:
        if self.numerical_status != "PASS":
            return RunVerdict.FAIL
        return RunVerdict.WARNING if self.maturity == "EXPERIMENTAL" else RunVerdict.FAIL

    @staticmethod
    def _complex_values(values: list[dict[str, Any]]) -> dict[str, list[float]]:
        return {
            "real": [float(item["real"]) for item in values],
            "imag": [float(item["imag"]) for item in values],
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis": "campbell",
            "status": self.numerical_status,
            "numerical_status": self.numerical_status,
            "run_verdict": self.run_verdict.value,
            "maturity": self.maturity,
            "spin_speeds_rad_s": list(self.spin_speeds_rad_s),
            "branches": [
                {
                    **{key: value for key, value in branch.items() if key != "samples"},
                    "samples": [
                        None
                        if sample is None
                        else {
                            **sample,
                            "eigenvalues": self._complex_values(sample["eigenvalues"]),
                        }
                        for sample in branch["samples"]
                    ],
                }
                for branch in self.branches
            ],
            "tracking_diagnostics": self.tracking_diagnostics,
            "source_result_keys": list(self.source_result_keys),
            "source_result_hashes": list(self.source_result_hashes),
            "execution_identity": self.execution_identity,
            "execution_key": self.execution_key,
            "provenance": self.provenance,
            "diagnostics": self.diagnostics,
        }

    @staticmethod
    def complex_eigenvalues_from_sample(sample: dict[str, Any]) -> np.ndarray:
        payload = sample["eigenvalues"]
        if not isinstance(payload, dict) or set(payload) != {"real", "imag"}:
            raise ValueError("Campbell complex eigenvalues require explicit real and imag arrays.")
        real = np.asarray(payload["real"], dtype=float)
        imag = np.asarray(payload["imag"], dtype=float)
        if real.shape != imag.shape or not np.all(np.isfinite(real)) or not np.all(np.isfinite(imag)):
            raise ValueError("Campbell complex eigenvalue arrays must have matching finite shapes.")
        return real + 1j * imag


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


@dataclass(frozen=True)
class ModalNewmarkResult(QualificationAwareResult):
    """Versioned transient result for experimental modal Newmark analysis."""

    numerical_status: str
    times: np.ndarray
    displacements: np.ndarray
    velocities: np.ndarray
    accelerations: np.ndarray
    modal_displacements: np.ndarray
    modal_velocities: np.ndarray
    modal_accelerations: np.ndarray
    dofs: DofManager
    node_count: int
    element_count: int
    solver: dict[str, Any]
    provenance: dict[str, Any]
    result_availability: dict[str, Any]
    execution_identity: dict[str, Any]
    execution_key: str
    qualification_scope_id: str
    mesh_report: dict[str, Any]
    time_history: tuple[dict[str, Any], ...] = ()
    modal_history: tuple[dict[str, Any], ...] = ()
    reactions: np.ndarray | None = None

    CONTRACT = "qf-modal-newmark-result/v1"

    def __post_init__(self) -> None:
        times = _readonly_real_vector(self.times, "modal Newmark times")
        if times.size == 0 or np.any(np.diff(times) <= 0.0) or times[0] < 0.0:
            raise ValueError("Modal Newmark result times must be non-empty, finite and strictly increasing.")
        vectors = {
            "displacements": _readonly_real_vector(self.displacements, "modal Newmark displacement"),
            "velocities": _readonly_real_vector(self.velocities, "modal Newmark velocity"),
            "accelerations": _readonly_real_vector(self.accelerations, "modal Newmark acceleration"),
            "modal_displacements": _readonly_real_vector(self.modal_displacements, "modal coordinates"),
            "modal_velocities": _readonly_real_vector(self.modal_velocities, "modal velocities"),
            "modal_accelerations": _readonly_real_vector(self.modal_accelerations, "modal accelerations"),
        }
        physical_size = self.dofs.ndof
        if any(vectors[name].size != physical_size for name in ("displacements", "velocities", "accelerations")):
            raise ValueError("Modal Newmark final physical state does not match the DOF map.")
        if (
            len({vectors[name].size for name in ("modal_displacements", "modal_velocities", "modal_accelerations")})
            != 1
        ):
            raise ValueError("Modal Newmark final reduced state vectors have inconsistent dimensions.")
        reactions = None if self.reactions is None else _readonly_real_vector(self.reactions, "modal Newmark reactions")
        if reactions is not None and reactions.size != physical_size:
            raise ValueError("Modal Newmark reaction vector does not match the DOF map.")
        if not isinstance(self.execution_key, str) or not self.execution_key:
            raise ValueError("Modal Newmark result requires an execution key.")
        object.__setattr__(self, "times", times)
        for name, value in vectors.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "reactions", reactions)
        object.__setattr__(self, "time_history", tuple(deepcopy(dict(row)) for row in self.time_history))
        object.__setattr__(self, "modal_history", tuple(deepcopy(dict(row)) for row in self.modal_history))
        object.__setattr__(self, "solver", deepcopy(self.solver))
        object.__setattr__(self, "provenance", deepcopy(self.provenance))
        object.__setattr__(self, "result_availability", deepcopy(self.result_availability))
        object.__setattr__(self, "execution_identity", deepcopy(self.execution_identity))
        object.__setattr__(self, "mesh_report", deepcopy(self.mesh_report))

    @property
    def analysis(self) -> str:
        return "transient_dynamic"

    @property
    def method(self) -> str:
        return "modal_newmark"

    @property
    def maturity(self) -> str:
        return "EXPERIMENTAL"

    @property
    def status(self) -> str:
        return self.numerical_status

    @property
    def run_verdict(self) -> RunVerdict:
        return RunVerdict.WARNING if self.numerical_status == "PASS" else RunVerdict.FAIL

    @property
    def ndof(self) -> int:
        return int(self.displacements.size)

    @property
    def max_displacement(self) -> float:
        return float(np.max(np.abs(self.displacements), initial=0.0))

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.CONTRACT,
            "analysis": self.analysis,
            "method": self.method,
            "status": self.numerical_status,
            "numerical_status": self.numerical_status,
            "run_verdict": self.run_verdict.value,
            "maturity": self.maturity,
            "qualification_decision": "NOT_ASSESSED",
            "qualification_scope_id": self.qualification_scope_id,
            "node_count": self.node_count,
            "element_count": self.element_count,
            "ndof": self.ndof,
            "dof_map": [
                {"node": int(node), "dofs": list(names)} for node, names in sorted(self.dofs.node_dofs.items())
            ],
            "times_s": self.times.tolist(),
            "final_state": {
                "displacement": self.displacements.tolist(),
                "velocity": self.velocities.tolist(),
                "acceleration": self.accelerations.tolist(),
                "modal_displacement": self.modal_displacements.tolist(),
                "modal_velocity": self.modal_velocities.tolist(),
                "modal_acceleration": self.modal_accelerations.tolist(),
                "reactions": None if self.reactions is None else self.reactions.tolist(),
            },
            "time_history": deepcopy(self.time_history),
            "modal_history": deepcopy(self.modal_history),
            "result_availability": deepcopy(self.result_availability),
            "execution_identity": deepcopy(self.execution_identity),
            "execution_key": self.execution_key,
            "solver": deepcopy(self.solver),
            "provenance": deepcopy(self.provenance),
            "mesh_report": deepcopy(self.mesh_report),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ModalNewmarkResult":
        if payload.get("schema") != cls.CONTRACT:
            raise ValueError(f"Unsupported modal Newmark result schema {payload.get('schema')!r}.")
        if payload.get("analysis") != "transient_dynamic" or payload.get("method") != "modal_newmark":
            raise ValueError("Serialized result is not a modal Newmark transient result.")
        try:
            raw_map = payload["dof_map"]
            if not isinstance(raw_map, list):
                raise ValueError("DOF map must be a list.")
            requirements = {int(item["node"]): set(str(dof) for dof in item["dofs"]) for item in raw_map}
            dofs = DofManager.from_node_requirements(requirements)
            state = payload["final_state"]
            reactions = state.get("reactions")
            return cls(
                numerical_status=str(payload["numerical_status"]),
                times=np.asarray(payload["times_s"], dtype=np.float64),
                displacements=np.asarray(state["displacement"], dtype=np.float64),
                velocities=np.asarray(state["velocity"], dtype=np.float64),
                accelerations=np.asarray(state["acceleration"], dtype=np.float64),
                modal_displacements=np.asarray(state["modal_displacement"], dtype=np.float64),
                modal_velocities=np.asarray(state["modal_velocity"], dtype=np.float64),
                modal_accelerations=np.asarray(state["modal_acceleration"], dtype=np.float64),
                reactions=None if reactions is None else np.asarray(reactions, dtype=np.float64),
                dofs=dofs,
                node_count=int(payload["node_count"]),
                element_count=int(payload["element_count"]),
                solver=dict(payload["solver"]),
                provenance=dict(payload["provenance"]),
                result_availability=dict(payload["result_availability"]),
                execution_identity=dict(payload["execution_identity"]),
                execution_key=str(payload["execution_key"]),
                qualification_scope_id=str(payload["qualification_scope_id"]),
                mesh_report=dict(payload["mesh_report"]),
                time_history=tuple(payload.get("time_history", ())),
                modal_history=tuple(payload.get("modal_history", ())),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Serialized modal Newmark result is incomplete or malformed.") from exc


@dataclass(frozen=True)
class ReducedHarmonicResult:
    """Versioned result for the method-specific experimental reduced route."""

    numerical_status: str
    frequencies_hz: np.ndarray
    responses: tuple[np.ndarray, ...]
    modal_coordinates: tuple[np.ndarray, ...]
    dof_signature: tuple[tuple[int, tuple[str, ...]], ...]
    full_dof_count: int
    node_count: int
    element_count: int
    solver: dict[str, Any]
    provenance: dict[str, Any]
    result_availability: dict[str, Any]
    execution_identity: dict[str, Any]
    execution_key: str
    qualification_scope_id: str
    mesh_report: dict[str, Any]

    CONTRACT = "qf-reduced-harmonic-result/v1"

    def __post_init__(self) -> None:
        frequencies = np.asarray(self.frequencies_hz, dtype=np.float64).copy()
        if frequencies.ndim != 1 or frequencies.size == 0 or not np.all(np.isfinite(frequencies)):
            raise ValueError("Reduced harmonic result frequencies must be a non-empty finite vector.")
        if np.any(frequencies < 0.0):
            raise ValueError("Reduced harmonic result frequencies must be non-negative.")
        responses = tuple(_readonly_complex_vector(value, "reduced harmonic response") for value in self.responses)
        coordinates = tuple(
            _readonly_complex_vector(value, "reduced harmonic modal coordinates") for value in self.modal_coordinates
        )
        if len(responses) != frequencies.size or len(coordinates) != frequencies.size:
            raise ValueError("Reduced harmonic response and modal-coordinate counts must match the frequency count.")
        dof_signature = tuple((int(node), tuple(str(name) for name in names)) for node, names in self.dof_signature)
        response_size = sum(len(names) for _, names in dof_signature)
        if any(value.size != response_size for value in responses):
            raise ValueError("Reduced harmonic response vectors do not match the serialized DOF map.")
        if isinstance(self.full_dof_count, bool) or self.full_dof_count < response_size:
            raise ValueError("Reduced harmonic full_dof_count is inconsistent with the response DOF map.")
        if not isinstance(self.execution_key, str) or not self.execution_key:
            raise ValueError("Reduced harmonic result requires an execution key.")
        frequencies.setflags(write=False)
        object.__setattr__(self, "frequencies_hz", frequencies)
        object.__setattr__(self, "responses", responses)
        object.__setattr__(self, "modal_coordinates", coordinates)
        object.__setattr__(self, "dof_signature", dof_signature)
        object.__setattr__(self, "solver", deepcopy(self.solver))
        object.__setattr__(self, "provenance", deepcopy(self.provenance))
        object.__setattr__(self, "result_availability", deepcopy(self.result_availability))
        object.__setattr__(self, "execution_identity", deepcopy(self.execution_identity))
        object.__setattr__(self, "mesh_report", deepcopy(self.mesh_report))

    @property
    def status(self) -> str:
        return self.numerical_status

    @property
    def method(self) -> str:
        return "modal_superposition"

    @property
    def analysis(self) -> str:
        return "harmonic_response"

    @property
    def maturity(self) -> str:
        return "EXPERIMENTAL"

    @property
    def run_verdict(self) -> RunVerdict:
        if self.numerical_status != "PASS":
            return RunVerdict.FAIL
        return RunVerdict.WARNING

    @property
    def max_displacement(self) -> float:
        return float(max((np.max(np.abs(row), initial=0.0) for row in self.responses), default=0.0))

    @staticmethod
    def _encode_complex(values: np.ndarray) -> dict[str, Any]:
        array = np.asarray(values, dtype=np.complex128)
        if not np.all(np.isfinite(array)):
            raise ValueError("Reduced harmonic result cannot serialize non-finite complex values.")
        return {"real": array.real.tolist(), "imag": array.imag.tolist()}

    @staticmethod
    def _decode_complex(payload: Any) -> np.ndarray:
        if not isinstance(payload, dict) or set(payload) != {"real", "imag"}:
            raise ValueError("Complex reduced harmonic values require explicit real and imag fields.")
        real = np.asarray(payload["real"], dtype=np.float64)
        imag = np.asarray(payload["imag"], dtype=np.float64)
        if real.shape != imag.shape or not np.all(np.isfinite(real)) or not np.all(np.isfinite(imag)):
            raise ValueError("Complex reduced harmonic real/imag values must have matching finite shapes.")
        return np.asarray(real + 1j * imag, dtype=np.complex128)

    def to_dict(self) -> dict[str, Any]:
        rows = []
        for index, (frequency, response, coordinates) in enumerate(
            zip(self.frequencies_hz, self.responses, self.modal_coordinates, strict=True)
        ):
            rows.append(
                {
                    "index": index,
                    "frequency_hz": float(frequency),
                    "omega_rad_s": float(2.0 * np.pi * frequency),
                    "max_displacement_amplitude": float(np.max(np.abs(response), initial=0.0)),
                    "displacements": _reduced_complex_nodal_state(self.dof_signature, response),
                    "modal_coordinates": self._encode_complex(coordinates),
                }
            )
        return {
            "schema": self.CONTRACT,
            "analysis": self.analysis,
            "method": self.method,
            "status": self.numerical_status,
            "numerical_status": self.numerical_status,
            "run_verdict": self.run_verdict.value,
            "maturity": self.maturity,
            "qualification_decision": "NOT_ASSESSED",
            "qualification_scope_id": self.qualification_scope_id,
            "node_count": self.node_count,
            "element_count": self.element_count,
            "full_dof_count": self.full_dof_count,
            "response_dof_count": sum(len(names) for _, names in self.dof_signature),
            "dof_map": [{"node": node, "dofs": list(names)} for node, names in self.dof_signature],
            "frequencies_hz": self.frequencies_hz.tolist(),
            "frequency_response": rows,
            "raw_complex_response_vectors": [self._encode_complex(row) for row in self.responses],
            "raw_complex_modal_coordinates": [self._encode_complex(row) for row in self.modal_coordinates],
            "execution_identity": deepcopy(self.execution_identity),
            "execution_key": self.execution_key,
            "result_availability": deepcopy(self.result_availability),
            "solver": deepcopy(self.solver),
            "provenance": deepcopy(self.provenance),
            "mesh_report": deepcopy(self.mesh_report),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ReducedHarmonicResult":
        if payload.get("schema") != cls.CONTRACT:
            raise ValueError(f"Unsupported reduced harmonic result schema {payload.get('schema')!r}.")
        if payload.get("analysis") != "harmonic_response" or payload.get("method") != "modal_superposition":
            raise ValueError("Serialized result is not a harmonic modal-superposition result.")
        raw_dof_map = payload.get("dof_map")
        if not isinstance(raw_dof_map, list):
            raise ValueError("Reduced harmonic result requires a DOF map.")
        try:
            signature = tuple((int(item["node"]), tuple(str(name) for name in item["dofs"])) for item in raw_dof_map)
            responses = tuple(cls._decode_complex(item) for item in payload["raw_complex_response_vectors"])
            coordinates = tuple(cls._decode_complex(item) for item in payload["raw_complex_modal_coordinates"])
            frequencies = np.asarray(payload["frequencies_hz"], dtype=np.float64)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Reduced harmonic result is incomplete or malformed.") from exc
        return cls(
            numerical_status=str(payload["numerical_status"]),
            frequencies_hz=frequencies,
            responses=responses,
            modal_coordinates=coordinates,
            dof_signature=signature,
            full_dof_count=int(payload["full_dof_count"]),
            node_count=int(payload["node_count"]),
            element_count=int(payload["element_count"]),
            solver=dict(payload["solver"]),
            provenance=dict(payload["provenance"]),
            result_availability=dict(payload["result_availability"]),
            execution_identity=dict(payload["execution_identity"]),
            execution_key=str(payload["execution_key"]),
            qualification_scope_id=str(payload["qualification_scope_id"]),
            mesh_report=dict(payload["mesh_report"]),
        )


def _readonly_complex_vector(values: np.ndarray, label: str) -> np.ndarray:
    array = np.asarray(values, dtype=np.complex128).copy()
    if array.ndim != 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must be a finite complex vector.")
    array.setflags(write=False)
    return array


def _readonly_real_vector(values: np.ndarray, label: str) -> np.ndarray:
    raw = np.asarray(values)
    if np.iscomplexobj(raw):
        raise ValueError(f"{label} must not contain complex values in a real time-domain result.")
    array = np.asarray(raw, dtype=np.float64).copy()
    if array.ndim != 1 or not np.all(np.isfinite(array)):
        raise ValueError(f"{label} must be a finite real vector.")
    array.setflags(write=False)
    return array


def _reduced_complex_nodal_state(
    signature: tuple[tuple[int, tuple[str, ...]], ...], response: np.ndarray
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    for node, names in signature:
        values: dict[str, Any] = {}
        for name in names:
            value = complex(response[offset])
            values[name] = {
                "real": float(value.real),
                "imag": float(value.imag),
                "amplitude": float(abs(value)),
                "phase_degrees": float(np.degrees(np.angle(value))),
            }
            offset += 1
        rows.append({"node": node, "dofs": values})
    return rows


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
