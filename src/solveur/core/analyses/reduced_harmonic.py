"""Experimental reduced modal-superposition harmonic response.

This route composes the WP02 prepared operators, WP03 excitation channels and
WP04 modal basis. It does not replace or alter the historical direct route.
"""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import math
import os
from pathlib import Path
import platform
import subprocess
from time import perf_counter
from typing import Any

import numpy as np
import scipy
from scipy.sparse import csr_matrix

from solveur.core.analyses.dynamic_controls import rayleigh_damping_definition
from solveur.core.analyses.excitation_channels import (
    ExcitationChannelSet,
)
from solveur.core.analyses.harmonic import frequency_grid
from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.analyses.uniform_base_acceleration import (
    UniformBaseAcceleration,
    combined_excitation_identity,
    prepare_base_acceleration,
)
from solveur.core.dofs import DOF_ORDER, DofManager
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.results import ReducedHarmonicResult
from solveur.core.solvers.linear import LinearSystemSolver
from solveur.io.checkpoint_common import checkpoint_signature
from solveur.mesh.validation import MeshValidator
from solveur.version import __version__


REDUCED_HARMONIC_CONTRACT = "qf-reduced-harmonic/v1"
_NUMERICAL_POLICY_ID = "qf-reduced-harmonic-numerics/v1"
_CONDITIONING_WARNING = 1.0e-8
_CONDITIONING_FAILURE = 1.0e-12
_BACKWARD_ERROR_MAX = 1.0e-8
_FLOAT_TINY: float = float(np.finfo(np.float64).tiny)


class ReducedHarmonicResponseSolver:
    """Solve harmonic response in a reusable, explicitly selected modal basis."""

    def __init__(self) -> None:
        self.mesh_validator = MeshValidator()
        self.linear_solver = LinearSystemSolver()

    def solve(
        self,
        model: FiniteElementModel,
        *,
        source_sha: str | None = None,
        prepared: PreparedDynamicSystem | None = None,
        basis: ModalBasis | None = None,
        excitation_channels: ExcitationChannelSet | Mapping[float, ExcitationChannelSet] | None = None,
    ) -> ReducedHarmonicResult:
        """Solve one model while permitting explicit instance-local reuse.

        A clean checkout or an explicit ``QF_SOURCE_SHA``/``GITHUB_SHA`` is
        required when this method has to create PreparedDynamicSystem itself.
        Installed/API callers may pass the exact source SHA or a compatible
        prepared object; no synthetic source identity is substituted.
        """
        if not isinstance(model, FiniteElementModel):
            raise InputValidationError("modal_superposition requires a FiniteElementModel.")
        model.analysis.validate()
        if model.analysis.type != "harmonic_response" or model.analysis.method != "modal_superposition":
            raise InputValidationError(
                "ReducedHarmonicResponseSolver requires analysis='harmonic_response', method='modal_superposition'."
            )

        mesh_report = self.mesh_validator.validate(model)
        if mesh_report.status == "FAIL":
            raise MeshValidationError("Mesh validation failed: " + "; ".join(mesh_report.errors))

        preparation_seconds = 0.0
        if prepared is None:
            resolved_source_sha = _resolve_source_sha(source_sha)
            prepare_started = perf_counter()
            prepared = PreparedDynamicSystem.prepare(model, source_sha=resolved_source_sha)
            preparation_seconds = perf_counter() - prepare_started
        else:
            prepared.require_compatible(model)
            if source_sha is not None and source_sha.lower() != prepared.source_sha:
                raise InputValidationError("Explicit source SHA does not match the supplied prepared system.")

        parameters = model.analysis.parameters
        basis_seconds = 0.0
        if basis is None:
            mode_count = parameters.get("modal_mode_count")
            if isinstance(mode_count, bool) or not isinstance(mode_count, (int, np.integer)) or mode_count <= 0:
                raise InputValidationError(
                    "modal_superposition requires an explicit positive modal_mode_count when no ModalBasis is supplied."
                )
            basis_started = perf_counter()
            basis = ModalBasis.from_prepared(
                prepared,
                mode_count=int(mode_count),
                method=str(parameters.get("modal_extraction_method", "eigsh")),
                dense_limit=int(parameters.get("modal_dense_limit", 2000)),
            )
            basis_seconds = perf_counter() - basis_started
        else:
            basis.assert_compatible(prepared)
            declared_count = parameters.get("modal_mode_count")
            if declared_count is not None and int(declared_count) != basis.mode_count:
                raise InputValidationError("Supplied ModalBasis mode count conflicts with modal_mode_count.")

        frequencies = frequency_grid(parameters)
        damping, physical_rayleigh = _resolve_damping(basis, prepared, parameters)
        frequency_channels = _resolve_channels(model, prepared, excitation_channels, frequencies)
        base_specification = (
            None
            if "uniform_base_acceleration" not in parameters
            else UniformBaseAcceleration.from_mapping(
                parameters["uniform_base_acceleration"], route="harmonic", model=model
            )
        )
        base_motion = (
            None
            if base_specification is None
            else prepare_base_acceleration(base_specification, model, prepared, basis.modes)
        )
        if base_specification is not None and {frequency for frequency, _ in base_specification.harmonic_phasors} != {
            float(item) for item in frequencies
        }:
            raise InputValidationError(
                "Base-acceleration harmonic phasors must match the requested frequency set exactly."
            )
        dofs = DofManager.from_node_requirements({int(node): set(names) for node, names in prepared.dof_signature})
        actual_signature = tuple(sorted((int(node), tuple(names)) for node, names in dofs.node_dofs.items()))
        if actual_signature != prepared.dof_signature:
            raise InputValidationError("Prepared operator and response DOF maps are inconsistent.")

        probe_indices, output_signature = _response_selection(parameters, dofs, prepared.dof_signature)
        mr = np.asarray(basis.projected_mass, dtype=np.float64)
        kr = np.asarray(basis.projected_stiffness, dtype=np.float64)
        cr = np.asarray(damping.matrix, dtype=np.float64)
        modes = np.asarray(basis.modes, dtype=np.float64)
        if mr.shape != kr.shape or cr.shape != mr.shape or modes.shape != (prepared.reduced_size, basis.mode_count):
            raise InputValidationError("Prepared modal basis and projected operator dimensions are inconsistent.")

        responses: list[np.ndarray] = []
        absolute_responses: list[np.ndarray | None] = []
        absolute_velocity_responses: list[np.ndarray | None] = []
        relative_velocity_responses: list[np.ndarray] = []
        relative_acceleration_responses: list[np.ndarray] = []
        absolute_acceleration_responses: list[np.ndarray] = []
        modal_coordinates: list[np.ndarray] = []
        frequency_records: list[dict[str, Any]] = []
        projection_seconds: list[float] = []
        solve_seconds: list[float] = []
        reconstruction_seconds: list[float] = []
        excitation_identities_by_frequency: dict[float, str] = {}
        bound_memory = 0
        bound_nnz = 0
        physical_k = prepared.stiffness_full
        physical_m = prepared.mass_full
        physical_c = None
        if physical_rayleigh is not None:
            alpha, beta = physical_rayleigh
            physical_c = (alpha * physical_m + beta * physical_k).tocsr()
        free = prepared.free_dof_indices

        for frequency in frequencies:
            frequency_value = float(frequency)
            channel_set = frequency_channels[frequency_value]
            bound = channel_set.bind(prepared)
            bound_memory = max(bound_memory, bound.distribution_storage_bytes)
            bound_nnz = max(bound_nnz, bound.distribution_nnz)

            projection_started = perf_counter()
            full_force = bound.full_harmonic_rhs(prepared, frequency_hz=frequency_value)
            force_channel_identity = bound.channel_identity
            combined_identity = combined_excitation_identity(force_channel_identity, base_motion)
            excitation_identities_by_frequency[frequency_value] = combined_identity
            effective_full_force = np.asarray(full_force, dtype=np.complex128)
            base_phasor: complex | None = None
            base_displacement: complex | None = None
            base_velocity: complex | None = None
            if base_motion is not None and base_specification is not None:
                base_phasor = base_specification.phasor_at(frequency_value)
                effective_full_force = effective_full_force + (base_motion.inertial_load_full_per_m_s2 * base_phasor)
                projected_force = (
                    basis.project_harmonic_excitation(bound, prepared, frequency_hz=frequency_value)
                    + base_motion.modal_load_per_m_s2 * base_phasor
                )
            else:
                projected_force = basis.project_harmonic_excitation(bound, prepared, frequency_hz=frequency_value)
            projection_seconds.append(perf_counter() - projection_started)

            omega = 2.0 * math.pi * frequency_value
            if not math.isfinite(omega):
                raise InputValidationError("Resolved angular frequency is not finite.")
            impedance = kr.astype(np.complex128) + 1j * omega * cr - omega**2 * mr
            solve_started = perf_counter()
            coordinates, solve_info, impedance_diagnostics = _solve_reduced_impedance(
                impedance,
                projected_force,
                kr,
                self.linear_solver,
                parameters,
            )
            solve_seconds.append(perf_counter() - solve_started)

            reconstruct_started = perf_counter()
            physical_state = np.asarray(modes @ coordinates, dtype=np.complex128)
            stiffness_factor = (
                complex(1.0, omega * physical_rayleigh[1]) if physical_rayleigh is not None else 1.0 + 0.0j
            )
            full_response = prepared.expand_complex_state(
                physical_state,
                effective_full_force,
                stiffness_factor=stiffness_factor,
            )
            reduced_residual = _relative_backward_error(impedance, coordinates, projected_force)
            if reduced_residual > _BACKWARD_ERROR_MAX:
                raise NumericalConvergenceError(
                    f"Reduced harmonic backward error at {frequency_value:.9g} Hz is "
                    f"{reduced_residual:.3e}, above {_BACKWARD_ERROR_MAX:.3e}."
                )

            physical_residual: float | None = None
            physical_residual_status = "UNAVAILABLE"
            physical_residual_reason = damping.reaction_reason
            if physical_c is not None:
                residual_vector = (
                    physical_k @ full_response
                    + 1j * omega * (physical_c @ full_response)
                    - omega**2 * (physical_m @ full_response)
                    - effective_full_force
                )
                physical_residual = _physical_free_backward_error(
                    physical_k,
                    physical_m,
                    physical_c,
                    full_response,
                    effective_full_force,
                    omega,
                    free,
                    residual_vector,
                )
                physical_residual_status = "AVAILABLE"
                physical_residual_reason = "Computed on free physical equations using the full Rayleigh C operator."
                if basis.is_full_basis and physical_residual > _BACKWARD_ERROR_MAX:
                    raise NumericalConvergenceError(
                        f"Full-basis physical harmonic backward error at {frequency_value:.9g} Hz is "
                        f"{physical_residual:.3e}, above {_BACKWARD_ERROR_MAX:.3e}."
                    )

            if not np.all(np.isfinite(full_response)) or not np.all(np.isfinite(coordinates)):
                raise NumericalConvergenceError(
                    f"Reduced harmonic response contains non-finite values at {frequency_value:.9g} Hz."
                )
            selected_response = full_response[probe_indices].copy()
            selected_response.setflags(write=False)
            if base_motion is None or base_phasor is None:
                selected_absolute_response = None
                selected_absolute_velocity = None
            else:
                relative_velocity_full = 1j * omega * full_response
                relative_acceleration_full = -(omega**2) * full_response
                absolute_acceleration_full = relative_acceleration_full + base_motion.influence_full * base_phasor
                selected_relative_velocity = relative_velocity_full[probe_indices].copy()
                selected_relative_acceleration = relative_acceleration_full[probe_indices].copy()
                selected_absolute_acceleration = absolute_acceleration_full[probe_indices].copy()
                for state in (
                    selected_relative_velocity,
                    selected_relative_acceleration,
                    selected_absolute_acceleration,
                ):
                    state.setflags(write=False)
                relative_velocity_responses.append(selected_relative_velocity)
                relative_acceleration_responses.append(selected_relative_acceleration)
                absolute_acceleration_responses.append(selected_absolute_acceleration)
                if omega == 0.0:
                    # Acceleration at DC does not determine the base's unknown
                    # displacement/velocity integration constants, even when
                    # the acceleration phasor itself is zero.
                    selected_absolute_response = None
                    selected_absolute_velocity = None
                else:
                    base_displacement = -base_phasor / (omega**2)
                    base_velocity = base_phasor / (1j * omega)
                    absolute_full_response = full_response + base_motion.influence_full * base_displacement
                    absolute_velocity_full = full_response * (1j * omega) + base_motion.influence_full * base_velocity
                    selected_absolute_response = absolute_full_response[probe_indices].copy()
                    selected_absolute_velocity = absolute_velocity_full[probe_indices].copy()
                    selected_absolute_response.setflags(write=False)
                    selected_absolute_velocity.setflags(write=False)
            coordinates = np.asarray(coordinates, dtype=np.complex128).copy()
            coordinates.setflags(write=False)
            responses.append(selected_response)
            absolute_responses.append(selected_absolute_response)
            absolute_velocity_responses.append(selected_absolute_velocity)
            modal_coordinates.append(coordinates)
            reconstruction_seconds.append(perf_counter() - reconstruct_started)

            frequency_records.append(
                {
                    "frequency_hz": frequency_value,
                    "omega_rad_s": omega,
                    "channel_identity": combined_identity,
                    "channel_count": bound.channel_count,
                    "channel_ids": list(bound.channel_ids),
                    "reduced_backward_error": reduced_residual,
                    "reduced_residual_status": "AVAILABLE",
                    "physical_free_backward_error": physical_residual,
                    "physical_residual_status": physical_residual_status,
                    "physical_residual_reason": physical_residual_reason,
                    "physical_residual_assessment": (
                        "FULL_BASIS_CHECKED"
                        if basis.is_full_basis and physical_residual is not None
                        else "TRUNCATION_DIAGNOSTIC_ONLY"
                        if physical_residual is not None
                        else "UNAVAILABLE"
                    ),
                    "scaled_impedance_reciprocal_condition": impedance_diagnostics["scaled_reciprocal_condition"],
                    "scaled_impedance_singular_floor": impedance_diagnostics["scaled_singular_floor"],
                    "conditioning_indicator": impedance_diagnostics["conditioning_indicator"],
                    "conditioning_status": impedance_diagnostics["conditioning_status"],
                    "linear_solver_relative_residual": float(solve_info.relative_residual_norm),
                    **(
                        {}
                        if (base_motion is None or base_specification is None or base_phasor is None)
                        else {
                            "base_acceleration_phasor_m_s2": {
                                "real": float(base_phasor.real),
                                "imag": float(base_phasor.imag),
                            },
                            "base_displacement_phasor_m": (
                                None
                                if base_displacement is None
                                else {"real": float(base_displacement.real), "imag": float(base_displacement.imag)}
                            ),
                            "base_velocity_phasor_m_s": (
                                None
                                if base_velocity is None
                                else {"real": float(base_velocity.real), "imag": float(base_velocity.imag)}
                            ),
                            "absolute_kinematics_status": (
                                "UNAVAILABLE_ZERO_FREQUENCY_INTEGRATION_CONSTANTS" if omega == 0.0 else "AVAILABLE"
                            ),
                            "base_acceleration_identity": base_specification.identity,
                        }
                    ),
                }
            )
            if base_motion is not None and base_specification is not None and base_phasor is not None:
                frequency_records[-1]["force_channel_identity"] = force_channel_identity

        excitation_by_frequency = [
            {"frequency_hz": frequency, "identity": excitation_identities_by_frequency[frequency]}
            for frequency in sorted(set(float(item) for item in frequencies))
        ]
        execution_identity, provenance = _execution_identity(
            prepared=prepared,
            basis=basis,
            damping=damping,
            frequencies=frequencies,
            excitation_by_frequency=excitation_by_frequency,
            response_probes=(
                None
                if "response_probes" not in parameters
                else [{"node": node, "dof": dof} for node, names in output_signature for dof in names]
            ),
            preparation_seconds=preparation_seconds,
            basis_seconds=basis_seconds,
        )
        if base_motion is not None and base_specification is not None:
            execution_identity["uniform_base_acceleration_identity"] = base_specification.identity
            execution_identity["uniform_base_acceleration_contract"] = base_specification.identity_payload()
            provenance["uniform_base_acceleration_identity"] = base_specification.identity
            provenance["uniform_base_acceleration_contract"] = base_specification.identity_payload()
        execution_key = checkpoint_signature(execution_identity, label="Reduced harmonic execution identity")
        qualification_scope = {
            "scope_schema": "qf-method-qualification-scope/v1",
            "analysis": "harmonic_response",
            "method": "modal_superposition",
            "element_families": list(prepared.element_families),
            "material_scope": "linear_isotropic_elastic",
            "damping_scope": damping.source,
            "excitation_scope": "identified_WP03_channels",
            "formulation_scope": REDUCED_HARMONIC_CONTRACT,
        }
        if base_motion is not None:
            qualification_scope["base_excitation_scope"] = "WP07_uniform_translational_base_acceleration"
        qualification_scope_id = checkpoint_signature(
            qualification_scope,
            label="Reduced harmonic qualification scope",
        )

        response_is_full = "response_probes" not in parameters
        reaction_availability = damping.reaction_availability
        reaction_reason = damping.reaction_reason
        result_availability = {
            "complex_displacements": {
                "status": "AVAILABLE" if response_is_full else "PARTIALLY_AVAILABLE",
                "computed": True,
                "retained": True,
                "scope": "full physical DOFs" if response_is_full else "explicit response_probes only",
                "reconstructible": response_is_full,
                "reason": None if response_is_full else "Unselected full-field response entries were not retained.",
            },
            "complex_modal_coordinates": {
                "status": "AVAILABLE",
                "computed": True,
                "retained": True,
                "reconstructible": True,
                "scope": "selected modal basis coordinates by requested frequency",
            },
            "reduced_equation_residual": {
                "status": "AVAILABLE",
                "computed": True,
                "retained": True,
                "scope": "normalized backward error of Zr*Q-Fr",
            },
            "physical_free_equation_residual": {
                "status": "AVAILABLE" if physical_rayleigh is not None else "UNAVAILABLE",
                "computed": physical_rayleigh is not None,
                "retained": physical_rayleigh is not None,
                "reason": (
                    "For a truncated basis this residual is a diagnostic only, not a pass threshold or truncation-error estimate."
                    if physical_rayleigh is not None and not basis.is_full_basis
                    else None
                    if physical_rayleigh is not None
                    else "Prescribed modal damping has no complete physical C operator."
                ),
            },
            "physical_reactions": {
                "status": reaction_availability,
                "computed": False,
                "retained": False,
                "reason": reaction_reason,
            },
            "stress": {
                "status": "NOT_COMPUTED",
                "computed": False,
                "retained": False,
                "reason": "Stress recovery is outside WP05; no stress result is inferred from displacement amplitudes.",
            },
            "physical_truncation_error": {
                "status": "UNAVAILABLE",
                "computed": False,
                "retained": False,
                "reason": "A small reduced residual does not estimate full physical modal truncation error.",
            },
        }
        if base_motion is not None:
            absolute_response_count = sum(item is not None for item in absolute_responses)
            absolute_status = (
                "AVAILABLE"
                if absolute_response_count == len(absolute_responses)
                else "PARTIALLY_AVAILABLE"
                if absolute_response_count
                else "UNAVAILABLE"
            )
            absolute_reason = (
                None
                if absolute_status == "AVAILABLE"
                else "At 0 Hz, acceleration alone does not determine base displacement/velocity integration constants."
            )
            result_availability["complex_displacements"] = {
                "status": "AVAILABLE" if response_is_full else "PARTIALLY_AVAILABLE",
                "computed": True,
                "retained": True,
                "scope": "full physical DOFs" if response_is_full else "explicit response_probes only",
                "reconstructible": response_is_full,
                "frame": "RELATIVE_RESPONSE",
                "reason": None if response_is_full else "Unselected relative response entries were not retained.",
            }
            result_availability.update(
                {
                    "relative_complex_displacements": {
                        "status": "AVAILABLE" if response_is_full else "PARTIALLY_AVAILABLE",
                        "computed": True,
                        "retained": True,
                        "frame": "RELATIVE_RESPONSE",
                        "scope": "full physical DOFs" if response_is_full else "explicit response_probes only",
                        "reconstructible": response_is_full,
                        "reason": None
                        if response_is_full
                        else "Unselected relative response entries were not retained.",
                    },
                    "absolute_complex_displacements": {
                        "status": absolute_status
                        if response_is_full
                        else "PARTIALLY_AVAILABLE"
                        if absolute_response_count
                        else "UNAVAILABLE",
                        "computed": bool(absolute_response_count),
                        "retained": True,
                        "frame": "ABSOLUTE_RESPONSE",
                        "scope": "positive-frequency kinematic reconstruction from the acceleration phasor",
                        "reconstructible": response_is_full and absolute_status == "AVAILABLE",
                        "reason": absolute_reason
                        if absolute_status != "AVAILABLE"
                        else None
                        if response_is_full
                        else "Unselected absolute response entries were not retained.",
                    },
                    "absolute_complex_velocities": {
                        "status": absolute_status
                        if response_is_full
                        else "PARTIALLY_AVAILABLE"
                        if absolute_response_count
                        else "UNAVAILABLE",
                        "computed": bool(absolute_response_count),
                        "retained": True,
                        "frame": "ABSOLUTE_RESPONSE",
                        "scope": "i*omega times the absolute displacement phasor",
                        "reconstructible": response_is_full and absolute_status == "AVAILABLE",
                        "reason": absolute_reason
                        if absolute_status != "AVAILABLE"
                        else None
                        if response_is_full
                        else "Unselected absolute response entries were not retained.",
                    },
                    "relative_complex_velocities": {
                        "status": "AVAILABLE" if response_is_full else "PARTIALLY_AVAILABLE",
                        "computed": True,
                        "retained": True,
                        "frame": "RELATIVE_RESPONSE",
                        "reconstructible": response_is_full,
                        "reason": None
                        if response_is_full
                        else "Unselected relative velocity entries were not retained.",
                    },
                    "relative_complex_accelerations": {
                        "status": "AVAILABLE" if response_is_full else "PARTIALLY_AVAILABLE",
                        "computed": True,
                        "retained": True,
                        "frame": "RELATIVE_RESPONSE",
                        "reconstructible": response_is_full,
                        "reason": None
                        if response_is_full
                        else "Unselected relative acceleration entries were not retained.",
                    },
                    "absolute_complex_accelerations": {
                        "status": "AVAILABLE" if response_is_full else "PARTIALLY_AVAILABLE",
                        "computed": True,
                        "retained": True,
                        "frame": "ABSOLUTE_RESPONSE",
                        "reconstructible": response_is_full,
                        "reason": None
                        if response_is_full
                        else "Unselected absolute acceleration entries were not retained.",
                    },
                }
            )

        modal_storage = int(basis.dense_storage_bytes["modes"])
        reduced_matrix_storage = int(mr.nbytes + kr.nbytes + cr.nbytes)
        response_storage = int(
            sum(item.nbytes for item in responses)
            + sum(item.nbytes for item in modal_coordinates)
            + sum(item.nbytes for item in absolute_responses if item is not None)
            + sum(item.nbytes for item in absolute_velocity_responses if item is not None)
            + sum(item.nbytes for item in relative_velocity_responses)
            + sum(item.nbytes for item in relative_acceleration_responses)
            + sum(item.nbytes for item in absolute_acceleration_responses)
        )
        solver_metadata = {
            "contract": REDUCED_HARMONIC_CONTRACT,
            "numerical_policy_id": _NUMERICAL_POLICY_ID,
            "maturity": "EXPERIMENTAL",
            "qualification_decision": "NOT_ASSESSED",
            "frequency_count": int(frequencies.size),
            "modal_mode_count": int(basis.mode_count),
            "basis_identity": basis.basis_identity,
            "operator_identity": prepared.operator_identity,
            "physical_identity": prepared.physical_identity,
            "excitation_identity_by_frequency": excitation_by_frequency,
            "damping": {
                "identity": damping.identity,
                "source": damping.source,
                "parameters": damping.parameters,
                "matrix": "explicit projected/reduced Cr used without diagonal replacement",
                "reaction_availability": damping.reaction_availability,
                "reaction_reason": damping.reaction_reason,
                "physical_rayleigh_coefficients": (
                    None
                    if physical_rayleigh is None
                    else {"alpha_s_inv": physical_rayleigh[0], "beta_s": physical_rayleigh[1]}
                ),
            },
            "projected_operator_checks": {
                "Mr_shape": list(mr.shape),
                "Kr_shape": list(kr.shape),
                "Cr_shape": list(cr.shape),
                "Mr_relative_identity_error": float(np.linalg.norm(mr - np.eye(basis.mode_count), ord="fro")),
                "Kr_relative_diagonal_error": float(
                    np.linalg.norm(kr - np.diag(np.diag(kr)), ord="fro")
                    / max(float(np.linalg.norm(kr, ord="fro")), _FLOAT_TINY)
                ),
                "operators_used_as_projected": True,
            },
            "modal_basis_diagnostics": basis.diagnostics,
            "frequency_records": frequency_records,
            "timing_seconds": {
                "preparation": preparation_seconds,
                "modal_basis_extraction": basis_seconds,
                "rhs_projection_by_frequency": projection_seconds,
                "reduced_solve_by_frequency": solve_seconds,
                "reconstruction_by_frequency": reconstruction_seconds,
            },
            "storage_bytes": {
                "modal_basis_modes": modal_storage,
                "projected_Mr_Kr_Cr": reduced_matrix_storage,
                "retained_complex_responses_and_coordinates": response_storage,
                "bound_channel_distribution_max": bound_memory,
                "bound_channel_distribution_nnz_max": bound_nnz,
            },
            "truncation": {
                **basis.diagnostics["truncation"],
                "response_error_estimate": "NOT_PROVIDED",
                "residual_flexibility": "NOT_IMPLEMENTED; OPTION-A is outside WP05",
                "mass_participation_interpretation": "not a guarantee of local displacement, stress, or response accuracy",
            },
            "phase_convention": "u(t) = Re[U(omega) exp(+i*omega*t)]",
            "frequency_conversion": "omega_rad_s = 2*pi*frequency_hz",
            "residual_limits": {
                "reduced_backward_error_max": _BACKWARD_ERROR_MAX,
                "full_basis_physical_free_backward_error_max": _BACKWARD_ERROR_MAX,
            },
        }
        if base_motion is not None and base_specification is not None:
            solver_metadata["uniform_base_acceleration"] = {
                "identity": base_specification.identity,
                "contract": base_specification.identity_payload(),
                "equivalent_inertial_load": "-P.T @ M_full @ r_full * A_g",
                "mass_formed_before_constraint_reduction": True,
                "stiffness_and_damping": "relative structural operators; comoving references; no rigid-base K/C forcing",
                "reactions": "NOT_COMPUTED_BY_REDUCED_HARMONIC_RESULT",
            }
            solver_metadata["response_frames"] = {
                "responses": "RELATIVE_RESPONSE",
                "relative_velocities": "i*omega*U_rel",
                "relative_accelerations": "-omega^2*U_rel",
                "absolute_accelerations": "-omega^2*U_rel + r_full*A_g",
                "absolute_displacements": "AVAILABLE_ONLY_FOR_POSITIVE_FREQUENCY; X_g=-A_g/omega^2",
                "absolute_velocities": "AVAILABLE_ONLY_FOR_POSITIVE_FREQUENCY; V_g=A_g/(i*omega)",
                "zero_frequency_absolute_displacement_velocity": "UNAVAILABLE; integration constants are not defined",
            }
        return ReducedHarmonicResult(
            numerical_status="PASS",
            frequencies_hz=frequencies,
            responses=tuple(responses),
            modal_coordinates=tuple(modal_coordinates),
            dof_signature=output_signature,
            full_dof_count=sum(len(names) for _, names in prepared.dof_signature),
            node_count=model.node_count,
            element_count=len(model.elements),
            solver=solver_metadata,
            provenance=provenance,
            result_availability=result_availability,
            execution_identity=execution_identity,
            execution_key=execution_key,
            qualification_scope_id=qualification_scope_id,
            mesh_report=mesh_report.to_dict(),
            absolute_responses=tuple(absolute_responses) if base_motion is not None else None,
            absolute_velocity_responses=(tuple(absolute_velocity_responses) if base_motion is not None else None),
            relative_velocity_responses=(tuple(relative_velocity_responses) if base_motion is not None else None),
            relative_acceleration_responses=(
                tuple(relative_acceleration_responses) if base_motion is not None else None
            ),
            absolute_acceleration_responses=(
                tuple(absolute_acceleration_responses) if base_motion is not None else None
            ),
        )


def _resolve_damping(
    basis: ModalBasis,
    prepared: PreparedDynamicSystem,
    parameters: Mapping[str, Any],
) -> tuple[Any, tuple[float, float] | None]:
    model = str(parameters.get("reduced_damping_model", "rayleigh_physical_projected")).strip().lower()
    if model == "rayleigh_physical_projected":
        if "modal_damping_ratios" in parameters:
            raise InputValidationError("modal_damping_ratios require reduced_damping_model='prescribed_modal'.")
        definition = rayleigh_damping_definition(dict(parameters))
        damping = basis.rayleigh_damping_from_parameters(prepared, parameters)
        return damping, (definition.alpha, definition.beta)
    if model != "prescribed_modal":
        raise InputValidationError("reduced_damping_model must be 'rayleigh_physical_projected' or 'prescribed_modal'.")
    conflicts = {"rayleigh_alpha", "rayleigh_beta", "modal_damping_targets", "damping_model"}.intersection(parameters)
    if conflicts:
        raise InputValidationError(
            "Prescribed modal damping cannot be combined with physical Rayleigh settings: "
            + ", ".join(sorted(conflicts))
            + "."
        )
    if "modal_damping_ratios" not in parameters:
        raise InputValidationError("prescribed_modal damping requires modal_damping_ratios.")
    damping = basis.prescribed_modal_damping(parameters["modal_damping_ratios"])
    return damping, None


def _resolve_channels(
    model: FiniteElementModel,
    prepared: PreparedDynamicSystem,
    channels: ExcitationChannelSet | Mapping[float, ExcitationChannelSet] | None,
    frequencies: np.ndarray,
) -> dict[float, ExcitationChannelSet]:
    unique_frequencies = tuple(sorted(set(float(item) for item in frequencies)))
    if channels is None:
        selected = ExcitationChannelSet.from_model_inputs(model, prepared)
        return {frequency: selected for frequency in unique_frequencies}

    if isinstance(channels, Mapping):
        normalized: dict[float, ExcitationChannelSet] = {}
        for raw_frequency, channel_set in channels.items():
            if isinstance(raw_frequency, bool):
                raise InputValidationError("Explicit excitation-map frequencies must be finite Hz values.")
            try:
                frequency = float(raw_frequency)
            except (TypeError, ValueError, OverflowError) as exc:
                raise InputValidationError("Explicit excitation-map frequencies must be finite Hz values.") from exc
            if not math.isfinite(frequency) or frequency < 0.0 or frequency in normalized:
                raise InputValidationError(
                    "Explicit excitation-map frequencies must be unique finite non-negative Hz values."
                )
            if not isinstance(channel_set, ExcitationChannelSet) or channel_set.source_mode != "explicit":
                raise InputValidationError("Each frequency mapping must contain an explicit ExcitationChannelSet.")
            normalized[frequency] = _validate_explicit_channels(model, prepared, channel_set)
        if set(normalized) != set(unique_frequencies):
            raise InputValidationError(
                "Explicit excitation-channel frequency keys must match the requested unique frequencies exactly."
            )
        return normalized

    if not isinstance(channels, ExcitationChannelSet):
        raise InputValidationError("excitation_channels must be an ExcitationChannelSet or a frequency mapping.")
    if channels.source_mode == "legacy_adapter":
        current = ExcitationChannelSet.from_legacy_model(model, prepared)
        if current.identity != channels.identity:
            raise InputValidationError("Supplied legacy excitation channels are stale for current model loads.")
        selected = current
    else:
        selected = _validate_explicit_channels(model, prepared, channels)

    harmonic_frequencies = {
        float(channel.harmonic.frequency_hz) for channel in selected.channels if channel.harmonic is not None
    }
    if harmonic_frequencies and len(unique_frequencies) != 1:
        raise InputValidationError(
            "A frequency-bound ExcitationChannelSet serves one requested frequency; provide a frequency mapping for a sweep."
        )
    if harmonic_frequencies and harmonic_frequencies != set(unique_frequencies):
        raise InputValidationError("Explicit harmonic channel frequency must exactly match the requested frequency.")
    return {frequency: selected for frequency in unique_frequencies}


def _validate_explicit_channels(
    model: FiniteElementModel,
    prepared: PreparedDynamicSystem,
    channels: ExcitationChannelSet,
) -> ExcitationChannelSet:
    if model.loads or model.distributed_loads:
        raise InputValidationError(
            "Legacy model loads and explicit WP03 channels cannot be combined in modal_superposition."
        )
    if model.analysis.parameters.get("excitation_channels") is not None:
        raise InputValidationError("New excitation channels must be supplied through the solver API, not model JSON.")
    legacy_control_keys = {
        "load_function",
        "load_frequency_hz",
        "chirp_start_hz",
        "chirp_end_hz",
        "load_table",
        "load_factors",
        "load_factors_by_load",
        "pulse_duration",
    }
    conflicting = legacy_control_keys.intersection(model.analysis.parameters)
    if conflicting:
        raise InputValidationError(
            "Explicit WP03 channels cannot be combined with legacy time-load controls: "
            + ", ".join(sorted(conflicting))
            + "."
        )
    prepared.require_compatible(model)
    canonical = ExcitationChannelSet(channels.channels)
    if canonical.identity != channels.identity:
        raise InputValidationError("Explicit excitation identity changed during canonical validation.")
    return channels


def _response_selection(
    parameters: Mapping[str, Any],
    dofs: DofManager,
    full_signature: tuple[tuple[int, tuple[str, ...]], ...],
) -> tuple[np.ndarray, tuple[tuple[int, tuple[str, ...]], ...]]:
    raw = parameters.get("response_probes")
    if raw is None:
        return np.arange(dofs.ndof, dtype=int), full_signature
    if not isinstance(raw, list) or not raw:
        raise InputValidationError("response_probes must be a non-empty list of {node,dof} objects.")
    selected: dict[int, set[str]] = {}
    seen: set[tuple[int, str]] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, Mapping) or set(item) != {"node", "dof"}:
            raise InputValidationError(f"response_probes[{index}] must contain exactly node and dof.")
        node = item["node"]
        dof = item["dof"]
        if isinstance(node, bool) or not isinstance(node, (int, np.integer)) or int(node) < 0:
            raise InputValidationError(f"response_probes[{index}].node must be a non-negative integer.")
        if not isinstance(dof, str) or dof.upper() not in DOF_ORDER:
            raise InputValidationError(f"response_probes[{index}].dof must be an active named degree of freedom.")
        node_value = int(node)
        dof_value = dof.upper()
        pair = (node_value, dof_value)
        if pair in seen:
            raise InputValidationError(f"response_probes contains duplicate entry {pair!r}.")
        seen.add(pair)
        try:
            dofs.index(node_value, dof_value)
        except ValueError as exc:
            raise InputValidationError(f"response_probes references inactive DOF {pair!r}.") from exc
        selected.setdefault(node_value, set()).add(dof_value)
    signature = tuple(
        (node, tuple(dof for dof in DOF_ORDER if dof in names)) for node, names in sorted(selected.items())
    )
    selected_indices: list[int] = [dofs.index(node, dof) for node, names in signature for dof in names]
    return np.asarray(selected_indices, dtype=int), signature


def _solve_reduced_impedance(
    impedance: np.ndarray,
    rhs: np.ndarray,
    stiffness: np.ndarray,
    solver: LinearSystemSolver,
    parameters: Mapping[str, Any],
) -> tuple[np.ndarray, Any, dict[str, object]]:
    matrix = np.asarray(impedance, dtype=np.complex128)
    force = np.asarray(rhs, dtype=np.complex128)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1] or force.shape != (matrix.shape[0],):
        raise InputValidationError("Reduced harmonic impedance and RHS dimensions are inconsistent.")
    if not np.all(np.isfinite(matrix)) or not np.all(np.isfinite(force)):
        raise InputValidationError("Reduced harmonic impedance and RHS must contain finite values.")
    diagonal = np.asarray(np.diag(stiffness), dtype=np.float64)
    if diagonal.shape != (matrix.shape[0],) or not np.all(np.isfinite(diagonal)) or np.any(diagonal <= 0.0):
        raise InputValidationError("Projected stiffness diagonal must be finite and positive for impedance scaling.")
    scale = 1.0 / np.sqrt(diagonal)
    scaled = scale[:, None] * matrix * scale[None, :]
    try:
        singular_values = np.linalg.svd(scaled, compute_uv=False)
    except np.linalg.LinAlgError as exc:
        raise NumericalConvergenceError("Reduced harmonic impedance condition estimate did not converge.") from exc
    if singular_values.size == 0 or not np.all(np.isfinite(singular_values)) or singular_values[0] <= 0.0:
        raise NumericalConvergenceError("Reduced harmonic impedance has no finite non-zero singular scale.")
    rcond = float(singular_values[-1] / singular_values[0])
    singular_floor = float(singular_values[-1] / max(1.0, singular_values[0]))
    indicator = min(rcond, singular_floor)
    if not math.isfinite(indicator) or indicator <= _CONDITIONING_FAILURE:
        raise NumericalConvergenceError(
            "Reduced harmonic impedance is singular or beyond the preregistered conditioning limit "
            f"(indicator={indicator:.3e}, limit>{_CONDITIONING_FAILURE:.3e})."
        )
    conditioning_status = "NEAR_SINGULAR_WARNING" if indicator <= _CONDITIONING_WARNING else "ACCEPTED"
    try:
        solution, info = solver.solve_complex(
            csr_matrix(matrix),
            force,
            parameters={**dict(parameters), "backend": "scipy"},
        )
    except NumericalConvergenceError:
        raise
    if not np.all(np.isfinite(solution)):
        raise NumericalConvergenceError("Reduced harmonic solver returned a non-finite modal response.")
    return (
        solution,
        info,
        {
            "scaled_reciprocal_condition": rcond,
            "scaled_singular_floor": singular_floor,
            "conditioning_indicator": indicator,
            "conditioning_status": conditioning_status,
            "warning_threshold": _CONDITIONING_WARNING,
            "failure_threshold": _CONDITIONING_FAILURE,
        },
    )


def _relative_backward_error(matrix: np.ndarray, solution: np.ndarray, rhs: np.ndarray) -> float:
    residual = np.asarray(matrix @ solution - rhs, dtype=np.complex128)
    denominator = float(np.linalg.norm(matrix, ord="fro") * np.linalg.norm(solution) + np.linalg.norm(rhs))
    if not np.all(np.isfinite(residual)) or not math.isfinite(denominator):
        return math.inf
    return float(np.linalg.norm(residual) / max(denominator, _FLOAT_TINY))


def _physical_free_backward_error(
    stiffness: csr_matrix,
    mass: csr_matrix,
    damping: csr_matrix,
    response: np.ndarray,
    force: np.ndarray,
    omega: float,
    free: np.ndarray,
    residual: np.ndarray,
) -> float:
    numerator = float(np.linalg.norm(np.asarray(residual)[free]))
    denominator = float(
        np.linalg.norm(np.asarray(stiffness @ response)[free])
        + omega * np.linalg.norm(np.asarray(damping @ response)[free])
        + omega**2 * np.linalg.norm(np.asarray(mass @ response)[free])
        + np.linalg.norm(np.asarray(force)[free])
    )
    if not math.isfinite(numerator) or not math.isfinite(denominator):
        return math.inf
    return numerator / max(denominator, _FLOAT_TINY)


def _execution_identity(
    *,
    prepared: PreparedDynamicSystem,
    basis: ModalBasis,
    damping: Any,
    frequencies: np.ndarray,
    excitation_by_frequency: list[dict[str, Any]],
    response_probes: list[dict[str, object]] | None,
    preparation_seconds: float,
    basis_seconds: float,
) -> tuple[dict[str, Any], dict[str, Any]]:
    implementation_files = (
        Path(__file__),
        Path(__file__).with_name("prepared_dynamic_system.py"),
        Path(__file__).with_name("modal_basis.py"),
        Path(__file__).with_name("excitation_channels.py"),
        Path(__file__).parents[1] / "results.py",
        Path(__file__).parents[1] / "router.py",
        Path(__file__).parents[1] / "qualification.py",
        Path(__file__).parents[1] / "solvers" / "linear.py",
        Path(__file__).resolve().parents[4] / "src" / "solveur" / "compatibility" / "preflight.py",
    )
    implementation_hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in implementation_files}
    contract_path = (
        Path(__file__).resolve().parents[4] / "qualification" / "0_2_12" / "wp05_reduced_harmonic_contract.json"
    )
    contract_hash = hashlib.sha256(contract_path.read_bytes()).hexdigest() if contract_path.is_file() else None
    environment = {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "platform": platform.platform(),
        "execution": "serial",
    }
    identity: dict[str, Any] = {
        "schema_version": 1,
        "case_contract_version": REDUCED_HARMONIC_CONTRACT,
        "case_definition": {
            "analysis": "harmonic_response",
            "method": "modal_superposition",
            "physical_identity": prepared.physical_identity,
            "operator_identity": prepared.operator_identity,
            "basis_identity": basis.basis_identity,
            "dof_signature": [[node, list(names)] for node, names in prepared.dof_signature],
            "frequencies_hz": [float(item) for item in frequencies],
            "excitation_identity_by_frequency": excitation_by_frequency,
            "damping_identity": damping.identity,
            "damping_source": damping.source,
            "response_probes": response_probes,
            "frequency_convention": "Hz input; omega=2*pi*f rad/s",
            "phase_convention": "u(t) = Re[U(omega) exp(+i*omega*t)]",
        },
        "tolerance_policy": {
            "policy_id": _NUMERICAL_POLICY_ID,
            "scaled_impedance_conditioning_warning_max": _CONDITIONING_WARNING,
            "scaled_impedance_conditioning_failure_max": _CONDITIONING_FAILURE,
            "reduced_backward_error_max": _BACKWARD_ERROR_MAX,
            "full_basis_physical_free_backward_error_max": _BACKWARD_ERROR_MAX,
        },
        "source_sha": prepared.source_sha,
        "software_versions": {"qf_solver": __version__, **environment},
        "contract_sha256": contract_hash,
        "implementation_sha256": implementation_hashes,
    }
    provenance = {
        "schema_version": 1,
        "source_sha": prepared.source_sha,
        "source_sha_availability": "AVAILABLE_AND_REPRODUCIBLE",
        "physical_identity": prepared.physical_identity,
        "operator_identity": prepared.operator_identity,
        "basis_identity": basis.basis_identity,
        "excitation_identity_by_frequency": excitation_by_frequency,
        "damping_identity": damping.identity,
        "contract_sha256": contract_hash,
        "implementation_sha256": implementation_hashes,
        "environment": environment,
        "evidence_availability": "AVAILABLE_AND_REPRODUCIBLE",
        "preparation_time_is_scientific_identity": False,
        "basis_extraction_time_is_scientific_identity": False,
        "timestamp_excluded_from_execution_identity": True,
        "output_paths_excluded_from_execution_identity": True,
        "timing_seconds_for_record": {
            "preparation": preparation_seconds,
            "basis_extraction": basis_seconds,
        },
    }
    return identity, provenance


def _resolve_source_sha(explicit: str | None) -> str:
    candidate: str | None
    if explicit is not None:
        candidate = explicit
    else:
        candidate = os.environ.get("QF_SOURCE_SHA") or os.environ.get("GITHUB_SHA") or _clean_checkout_sha()
    if (
        not isinstance(candidate, str)
        or len(candidate) not in {40, 64}
        or any(character not in "0123456789abcdef" for character in candidate.lower())
    ):
        raise InputValidationError(
            "Prepared reduced harmonic analysis requires an explicit full source SHA, "
            "QF_SOURCE_SHA/GITHUB_SHA, or a clean Git checkout."
        )
    return candidate.lower()


def _clean_checkout_sha() -> str | None:
    repository = Path(__file__).resolve().parents[4]
    try:
        status = subprocess.run(
            ["git", "-C", str(repository), "status", "--porcelain"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
        if status.stdout.strip():
            return None
        result = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = result.stdout.strip().lower()
    return value if len(value) == 40 and all(character in "0123456789abcdef" for character in value) else None
