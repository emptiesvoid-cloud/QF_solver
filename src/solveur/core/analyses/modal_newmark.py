"""Experimental modal-superposition transient response using shared Newmark steps."""

from __future__ import annotations

from collections.abc import Mapping
import math
import platform
from time import perf_counter
from typing import Any, cast

import numpy as np
import scipy
from scipy.sparse import csr_matrix

from solveur.core.analyses.dynamic import (
    NewmarkDynamicSolver,
    _initial_vector,
    _total_energy,
    _validated_newmark_parameters,
)
from solveur.core.analyses.dynamic_checkpoint import DynamicCheckpointSettings
from solveur.core.analyses.dynamic_history import validated_history_probes
from solveur.core.analyses.excitation_channels import BoundExcitationChannels, ExcitationChannelSet
from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.modal_newmark_checkpoint import (
    MODAL_NEWMARK_CHECKPOINT_SCHEMA,
    ModalNewmarkCheckpoint,
    NpzModalNewmarkCheckpointStore,
)
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.analyses.reduced_harmonic import _resolve_damping, _resolve_source_sha
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.results import ModalNewmarkResult
from solveur.core.solvers.linear import LinearSystemSolver
from solveur.core.solvers.policy import LinearSolverPolicy, linear_execution_settings
from solveur.core.solvers.backend import select_backend
from solveur.io.checkpoint_common import checkpoint_signature
from solveur.mesh.validation import MeshValidator
from solveur.version import __version__


MODAL_NEWMARK_CONTRACT = "qf-modal-newmark/v1"
_NUMERICAL_POLICY_ID = "qf-modal-newmark-numerics/v1"
_REDUCED_EQUILIBRIUM_ERROR_MAX = 1.0e-7
_FULL_BASIS_PHYSICAL_RESIDUAL_MAX = 1.0e-7
_INITIAL_PROJECTION_EXACT_MAX = 1.0e-10
_FLOAT_TINY = float(np.finfo(np.float64).tiny)
_OUTPUT_ONLY_PARAMETERS = {
    "checkpoint_path",
    "checkpoint_interval",
    "checkpoint_keep_steps",
    "restart_from",
    "record_time_history",
    "store_modal_history",
    "history_probes",
    "postprocess_mode",
}


class ModalNewmarkTransientSolver:
    """Integrate a prepared reduced modal system with the shared Newmark core."""

    def __init__(self) -> None:
        self.mesh_validator = MeshValidator()
        self.newmark_core = NewmarkDynamicSolver()
        self.linear_solver = LinearSystemSolver()
        self.checkpoint_store = NpzModalNewmarkCheckpointStore()

    def solve(
        self,
        model: FiniteElementModel,
        *,
        source_sha: str | None = None,
        prepared: PreparedDynamicSystem | None = None,
        basis: ModalBasis | None = None,
        excitation_channels: ExcitationChannelSet | None = None,
    ) -> ModalNewmarkResult:
        """Run one explicit modal-Newmark route; no direct/reduced auto-selection."""
        if not isinstance(model, FiniteElementModel):
            raise InputValidationError("modal_newmark requires a FiniteElementModel.")
        model.analysis.validate()
        if model.analysis.type != "transient_dynamic" or model.analysis.method != "modal_newmark":
            raise InputValidationError(
                "ModalNewmarkTransientSolver requires analysis='transient_dynamic', method='modal_newmark'."
            )

        parameters = model.analysis.parameters
        _validate_modal_newmark_scope(parameters)
        mesh_report = self.mesh_validator.validate(model)
        if mesh_report.status == "FAIL":
            raise MeshValidationError("Mesh validation failed: " + "; ".join(mesh_report.errors))

        preparation_seconds = 0.0
        if prepared is None:
            resolved_source_sha = _resolve_source_sha(source_sha)
            started = perf_counter()
            prepared = PreparedDynamicSystem.prepare(model, source_sha=resolved_source_sha)
            preparation_seconds = perf_counter() - started
        else:
            prepared.require_compatible(model)
            if source_sha is not None and source_sha.lower() != prepared.source_sha:
                raise InputValidationError("Explicit source SHA does not match the supplied PreparedDynamicSystem.")

        basis_seconds = 0.0
        if basis is None:
            raw_count = parameters.get("modal_mode_count")
            if isinstance(raw_count, bool) or not isinstance(raw_count, (int, np.integer)) or raw_count <= 0:
                raise InputValidationError(
                    "modal_newmark requires an explicit positive modal_mode_count when no ModalBasis is supplied."
                )
            started = perf_counter()
            basis = ModalBasis.from_prepared(
                prepared,
                mode_count=int(raw_count),
                method=str(parameters.get("modal_extraction_method", "eigsh")),
                dense_limit=int(parameters.get("modal_dense_limit", 2000)),
            )
            basis_seconds = perf_counter() - started
        else:
            basis.assert_compatible(prepared)
            raw_count = parameters.get("modal_mode_count")
            if raw_count is not None and int(raw_count) != basis.mode_count:
                raise InputValidationError("Supplied ModalBasis mode count conflicts with modal_mode_count.")

        dt, steps, beta, gamma = _validated_newmark_parameters(parameters)
        if not math.isfinite(dt * steps):
            raise InputValidationError("Resolved Newmark duration is not finite.")
        damping, physical_rayleigh = _resolve_damping(basis, prepared, parameters)
        channels = _resolve_transient_channels(model, prepared, excitation_channels)
        bound = channels.bind(prepared)

        dofs = DofManager.from_node_requirements({int(node): set(names) for node, names in prepared.dof_signature})
        if tuple(sorted((int(node), tuple(names)) for node, names in dofs.node_dofs.items())) != prepared.dof_signature:
            raise InputValidationError("Prepared operator and transient response DOF mappings are inconsistent.")
        probe_indices = validated_history_probes(dofs, parameters.get("history_probes", []))
        record_history = parameters.get("record_time_history", bool(probe_indices))
        store_modal_history = parameters.get("store_modal_history", False)
        if not isinstance(record_history, bool) or not isinstance(store_modal_history, bool):
            raise InputValidationError("record_time_history and store_modal_history must be booleans.")
        if probe_indices and not record_history:
            raise InputValidationError("history_probes require record_time_history=true.")

        mr = np.asarray(basis.projected_mass, dtype=np.float64)
        kr = np.asarray(basis.projected_stiffness, dtype=np.float64)
        cr = np.asarray(damping.matrix, dtype=np.float64)
        modes = np.asarray(basis.modes, dtype=np.float64)
        mode_count = basis.mode_count
        if any(item.shape != (mode_count, mode_count) for item in (mr, kr, cr)):
            raise InputValidationError("Modal Newmark projected operators have inconsistent dimensions.")
        if modes.shape != (prepared.reduced_size, mode_count):
            raise InputValidationError("Modal Newmark basis does not match prepared reduced coordinates.")
        if not all(np.all(np.isfinite(item)) for item in (mr, kr, cr, modes)):
            raise InputValidationError("Modal Newmark projected operators and modes must be finite.")
        mr_sparse = csr_matrix(mr)
        kr_sparse = csr_matrix(kr)
        cr_sparse = csr_matrix(cr)

        fixed = prepared.fixed_dof_indices
        initial_u_full = _initial_vector(
            dofs,
            parameters.get("initial_displacements", []),
            fixed_indices=fixed,
            field_name="initial_displacements",
        )
        initial_v_full = _initial_vector(
            dofs,
            parameters.get("initial_velocities", []),
            fixed_indices=fixed,
            field_name="initial_velocities",
        )
        initial_u_reduced = prepared.reduce_state(initial_u_full)
        initial_v_reduced = prepared.reduce_state(initial_v_full)
        mass_reduced = prepared.mass
        q_initial = _mass_project_initial_state(modes, mr, mass_reduced, initial_u_reduced, "displacement")
        qdot_initial = _mass_project_initial_state(modes, mr, mass_reduced, initial_v_reduced, "velocity")
        displacement_projection_error = _mass_projection_error(initial_u_reduced, modes @ q_initial, mass_reduced)
        velocity_projection_error = _mass_projection_error(initial_v_reduced, modes @ qdot_initial, mass_reduced)
        projection_policy = str(parameters.get("modal_initial_projection_policy", "project_and_report")).lower()
        if projection_policy not in {"project_and_report", "reject_incompatible"}:
            raise InputValidationError(
                "modal_initial_projection_policy must be 'project_and_report' or 'reject_incompatible'."
            )
        if (
            projection_policy == "reject_incompatible"
            and max(displacement_projection_error, velocity_projection_error) > _INITIAL_PROJECTION_EXACT_MAX
        ):
            raise InputValidationError(
                "Initial physical state has a component outside the retained modal basis; projection policy rejects it."
            )

        full_mass = prepared.mass_full
        full_stiffness = prepared.stiffness_full
        full_damping = None
        if physical_rayleigh is not None:
            alpha, rayleigh_beta = physical_rayleigh
            full_damping = (alpha * full_mass + rayleigh_beta * full_stiffness).tocsr()

        physical_parameters = _execution_parameters(parameters)
        identity: dict[str, Any] = {
            "schema_version": 1,
            "case_contract_version": MODAL_NEWMARK_CONTRACT,
            "analysis": "transient_dynamic",
            "method": "modal_newmark",
            "source_sha": prepared.source_sha,
            "physical_identity": prepared.physical_identity,
            "operator_identity": prepared.operator_identity,
            "basis_identity": basis.basis_identity,
            "excitation_identity": bound.channel_identity,
            "damping_identity": damping.identity,
            "integration": {
                "scheme": "Newmark-implicit-constant-step",
                "time_step_s": dt,
                "steps": steps,
                "beta": beta,
                "gamma": gamma,
                "duration_s": dt * steps,
            },
            "initial_state_sha256": checkpoint_signature(
                {"displacement": initial_u_full.tolist(), "velocity": initial_v_full.tolist()},
                label="Modal Newmark initial state",
            ),
            "initial_projection_policy": projection_policy,
            "result_request": {
                "record_time_history": record_history,
                "store_modal_history": store_modal_history,
                "history_probes": [
                    {"label": label, "physical_dof_index": int(index)} for label, index in probe_indices
                ],
            },
            "numerical_parameters": physical_parameters,
            "tolerance_policy": {
                "policy_id": _NUMERICAL_POLICY_ID,
                "reduced_equilibrium_relative_error_max": float(
                    parameters.get("dynamic_residual_failure_tolerance", _REDUCED_EQUILIBRIUM_ERROR_MAX)
                ),
                "full_basis_physical_residual_max": _FULL_BASIS_PHYSICAL_RESIDUAL_MAX,
                "initial_projection_exact_max": _INITIAL_PROJECTION_EXACT_MAX,
            },
        }
        execution_key = self.checkpoint_store.signature(identity)
        checkpoint_settings = DynamicCheckpointSettings.from_parameters(parameters, steps)
        restart_step = 0
        if checkpoint_settings.restart_from is not None:
            checkpoint = self.checkpoint_store.load(checkpoint_settings.restart_from)
            _validate_modal_checkpoint(
                checkpoint,
                run_signature=execution_key,
                source_sha=prepared.source_sha,
                prepared=prepared,
                basis=basis,
                damping=damping,
                channels=bound,
                total_steps=steps,
                dt=dt,
                beta=beta,
                gamma=gamma,
            )
            q = checkpoint.coordinates.copy()
            qdot = checkpoint.velocity.copy()
            qddot = checkpoint.acceleration.copy()
            initial_energy = checkpoint.initial_energy
            restart_step = checkpoint.completed_step
        else:
            q = q_initial
            qdot = qdot_initial
            initial_force_full = bound.full_real_rhs(prepared, time_s=0.0, step=0, steps=steps, dt=dt)
            initial_force = basis.project_full_rhs(initial_force_full, prepared)
            qddot = self.newmark_core._initial_acceleration(
                mr_sparse,
                cr_sparse,
                kr_sparse,
                np.arange(mode_count, dtype=int),
                q,
                qdot,
                initial_force,
            )
            initial_energy = _total_energy(q, qdot, kr_sparse, mr_sparse)

        effective = NewmarkDynamicSolver._effective_stiffness(
            mr_sparse, cr_sparse, kr_sparse, dt=dt, beta=beta, gamma=gamma
        )
        requested_method = str(parameters.get("linear_method", "direct")).lower()
        selection = LinearSolverPolicy.assess(effective, requested_method, parameters)
        LinearSolverPolicy.enforce_method_contract(selection, parameters)
        linear_method = (
            selection.recommended_method if requested_method in LinearSolverPolicy._AUTO else requested_method
        )
        backend_selection = select_backend(
            parameters.get("backend", "auto"), problem_size=mode_count, parameters=parameters
        )
        if backend_selection.selected != "scipy":
            raise InputValidationError("modal_newmark currently supports the serial SciPy backend only.")
        factorization = self.newmark_core._factorize_effective(effective, linear_method, parameters)
        residual_limit = _finite_positive(
            parameters.get("dynamic_residual_failure_tolerance", _REDUCED_EQUILIBRIUM_ERROR_MAX),
            "dynamic_residual_failure_tolerance",
        )

        history: list[dict[str, Any]] = []
        modal_history: list[dict[str, Any]] = []
        times: list[float] = []
        residual_count = 0
        max_reduced_residual_norm = 0.0
        max_reduced_relative_error = 0.0
        linear_iteration_total = 0
        max_linear_relative_residual = 0.0
        integration_started = perf_counter()
        reconstruction_seconds = 0.0
        checkpoint_files: list[str] = []

        def sample_state(step: int, force_modal: np.ndarray) -> None:
            nonlocal reconstruction_seconds
            nonlocal residual_count, max_reduced_residual_norm, max_reduced_relative_error
            time_value = step * dt
            residual = mr @ qddot + cr @ qdot + kr @ q - force_modal
            relative_residual = _relative_equilibrium_error(mr, cr, kr, q, qdot, qddot, force_modal)
            if not math.isfinite(relative_residual) or relative_residual > residual_limit:
                raise NumericalConvergenceError(
                    f"Modal Newmark reduced equilibrium is abnormal at step {step}: "
                    f"relative={relative_residual:.6e}, allowed={residual_limit:.6e}."
                )
            residual_norm = float(np.linalg.norm(residual))
            residual_count += 1
            max_reduced_residual_norm = max(max_reduced_residual_norm, residual_norm)
            max_reduced_relative_error = max(max_reduced_relative_error, relative_residual)
            if record_history:
                reconstruction_started = perf_counter()
                full_u = prepared.expand_state(modes @ q)
                full_v = prepared.expand_state(modes @ qdot)
                full_a = prepared.expand_state(modes @ qddot)
                reconstruction_seconds += perf_counter() - reconstruction_started
                row: dict[str, Any] = {
                    "step": step,
                    "time_s": float(time_value),
                    "max_displacement": float(np.max(np.abs(full_u), initial=0.0)),
                    "max_velocity": float(np.max(np.abs(full_v), initial=0.0)),
                    "max_acceleration": float(np.max(np.abs(full_a), initial=0.0)),
                    "kinetic_energy": float(0.5 * qdot @ (mr @ qdot)),
                    "strain_energy": float(0.5 * q @ (kr @ q)),
                    "total_energy": float(0.5 * qdot @ (mr @ qdot) + 0.5 * q @ (kr @ q)),
                    "relative_energy_drift": _relative_energy_drift(
                        float(0.5 * qdot @ (mr @ qdot) + 0.5 * q @ (kr @ q)), initial_energy
                    ),
                    "damping_power_reduced": float(qdot @ (cr @ qdot)),
                    "reduced_equilibrium_residual_norm": residual_norm,
                    "reduced_equilibrium_relative_error": relative_residual,
                }
                if probe_indices:
                    row["probes"] = {
                        label: {
                            "displacement": float(full_u[index]),
                            "velocity": float(full_v[index]),
                            "acceleration": float(full_a[index]),
                        }
                        for label, index in probe_indices
                    }
                history.append(row)
                times.append(float(time_value))
            if store_modal_history:
                modal_history.append(
                    {
                        "step": step,
                        "time_s": float(time_value),
                        "q": q.tolist(),
                        "qdot": qdot.tolist(),
                        "qddot": qddot.tolist(),
                    }
                )

        if restart_step > 0:
            restart_force = bound.full_real_rhs(
                prepared, time_s=restart_step * dt, step=restart_step, steps=steps, dt=dt
            )
            sample_state(
                restart_step,
                basis.project_full_rhs(restart_force, prepared),
            )
        else:
            initial_force_full = bound.full_real_rhs(prepared, time_s=0.0, step=0, steps=steps, dt=dt)
            sample_state(0, basis.project_full_rhs(initial_force_full, prepared))

        for step in range(restart_step + 1, steps + 1):
            time_value = step * dt
            force_full = bound.full_real_rhs(prepared, time_s=time_value, step=step, steps=steps, dt=dt)
            force_modal = basis.project_full_rhs(force_full, prepared)
            rhs = NewmarkDynamicSolver._effective_rhs(
                mr_sparse,
                cr_sparse,
                q,
                qdot,
                qddot,
                force_modal,
                dt=dt,
                beta=beta,
                gamma=gamma,
            )
            if factorization is None:
                next_q, info = self.linear_solver.solve(
                    effective,
                    rhs,
                    method=linear_method,
                    parameters={**parameters, "backend": "scipy"},
                )
            else:
                next_q, info = factorization.solve(rhs)
            if not info.converged or not np.all(np.isfinite(next_q)):
                raise NumericalConvergenceError(
                    f"Modal Newmark linear solve did not converge at step {step}; residual={info.residual_norm:.6e}."
                )
            next_qdot, next_qddot = self.newmark_core._recover_newmark_state(
                next_q, q, qdot, qddot, dt=dt, beta=beta, gamma=gamma
            )
            q, qdot, qddot = next_q, next_qdot, next_qddot
            linear_iteration_total += int(info.iterations)
            max_linear_relative_residual = max(max_linear_relative_residual, float(info.relative_residual_norm))
            sample_state(step, force_modal)

            if checkpoint_settings.should_save(step, steps):
                state = ModalNewmarkCheckpoint(
                    run_signature=execution_key,
                    source_sha=prepared.source_sha,
                    physical_identity=prepared.physical_identity,
                    operator_identity=prepared.operator_identity,
                    excitation_identity=bound.channel_identity,
                    damping_identity=damping.identity,
                    basis_identity=basis.basis_identity,
                    completed_step=step,
                    total_steps=steps,
                    time=time_value,
                    time_step=dt,
                    beta=beta,
                    gamma=gamma,
                    initial_energy=initial_energy,
                    coordinates=q.copy(),
                    velocity=qdot.copy(),
                    acceleration=qddot.copy(),
                )
                written = self.checkpoint_store.save(
                    checkpoint_settings.path, state, keep_step=checkpoint_settings.keep_steps
                )
                checkpoint_files.extend(str(path) for path in written if str(path) not in checkpoint_files)

        integration_seconds = perf_counter() - integration_started
        final_time = steps * dt
        final_force = bound.full_real_rhs(prepared, time_s=final_time, step=steps, steps=steps, dt=dt)
        final_reduced_u = modes @ q
        final_reduced_v = modes @ qdot
        final_reduced_a = modes @ qddot
        final_u = prepared.expand_state(final_reduced_u)
        final_v = prepared.expand_state(final_reduced_v)
        final_a = prepared.expand_state(final_reduced_a)
        if not all(np.all(np.isfinite(item)) for item in (final_u, final_v, final_a)):
            raise NumericalConvergenceError("Modal Newmark reconstructed a non-finite final state.")

        physical_residual_norm: float | None = None
        physical_relative_residual: float | None = None
        reactions: np.ndarray | None = None
        reaction_status = damping.reaction_availability
        reaction_reason = damping.reaction_reason
        if full_damping is not None:
            physical_residual = full_mass @ final_a + full_damping @ final_v + full_stiffness @ final_u - final_force
            free = prepared.free_dof_indices
            physical_residual_norm = float(np.linalg.norm(physical_residual[free]))
            physical_relative_residual = _physical_relative_error(
                full_mass,
                full_damping,
                full_stiffness,
                final_a,
                final_v,
                final_u,
                final_force,
                free,
            )
            if basis.is_full_basis and physical_relative_residual > _FULL_BASIS_PHYSICAL_RESIDUAL_MAX:
                raise NumericalConvergenceError(
                    "Full-basis modal Newmark physical residual exceeds its preregistered limit: "
                    f"{physical_relative_residual:.3e} > {_FULL_BASIS_PHYSICAL_RESIDUAL_MAX:.3e}."
                )
            reactions = np.zeros(dofs.ndof, dtype=np.float64)
            reactions[fixed] = np.asarray(physical_residual)[fixed]
            reaction_status = "AVAILABLE" if fixed.size else "NOT_APPLICABLE"
            reaction_reason = (
                "Final support reactions are the fixed-DOF residual from the declared physical Rayleigh operator; "
                "a truncated basis can affect the reconstructed state."
                if fixed.size
                else "The model has no fixed DOFs at which support reactions apply."
            )

        environment = {
            "qf_solver": __version__,
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        }
        result_availability = {
            "final_displacement": _availability("AVAILABLE", True, True, "full physical DOF vector at final time"),
            "final_velocity": _availability("AVAILABLE", True, True, "full physical DOF vector at final time"),
            "final_acceleration": _availability("AVAILABLE", True, True, "full physical DOF vector at final time"),
            "modal_final_state": _availability("AVAILABLE", True, True, "retained basis coordinates at final time"),
            "requested_probe_history": _availability(
                "AVAILABLE" if record_history and probe_indices else "NOT_APPLICABLE",
                bool(record_history and probe_indices),
                bool(record_history and probe_indices),
                "selected physical DOFs only" if probe_indices else "no history probes requested",
            ),
            "full_physical_state_history": _availability(
                "UNAVAILABLE", False, False, "full physical fields are not stored at every step to bound memory"
            ),
            "modal_state_history": _availability(
                "AVAILABLE" if store_modal_history else "UNAVAILABLE",
                store_modal_history,
                store_modal_history,
                "explicit modal-coordinate history"
                if store_modal_history
                else "set store_modal_history=true to retain it",
            ),
            "reduced_equilibrium_residual": _availability(
                "AVAILABLE", True, True, "per accepted time state in the retained modal equations"
            ),
            "physical_free_equation_residual": _availability(
                "AVAILABLE" if full_damping is not None else "UNAVAILABLE",
                full_damping is not None,
                full_damping is not None,
                (
                    "computed on free physical DOFs; truncated-basis values are diagnostic only"
                    if full_damping is not None
                    else "prescribed modal damping does not define a complete physical C operator"
                ),
            ),
            "physical_reactions": _availability(
                reaction_status,
                reactions is not None,
                reactions is not None,
                reaction_reason,
            ),
            "stress": _availability("NOT_COMPUTED", False, False, "stress snapshots are outside WP06"),
            "physical_truncation_error": _availability(
                "UNAVAILABLE", False, False, "reduced equilibrium residual is not a physical truncation-error estimate"
            ),
        }
        qualification_scope_id = checkpoint_signature(
            {
                "schema": "qf-method-qualification-scope/v1",
                "analysis": "transient_dynamic",
                "method": "modal_newmark",
                "element_families": list(prepared.element_families),
                "material_scope": "linear_isotropic_elastic",
                "damping_scope": damping.source,
                "excitation_scope": "WP03 real identified time channels",
                "formulation_scope": MODAL_NEWMARK_CONTRACT,
            },
            label="Modal Newmark qualification scope",
        )
        basis_storage = basis.dense_storage_bytes
        modal_history_bytes = sum(
            np.asarray(row["q"], dtype=np.float64).nbytes
            + np.asarray(row["qdot"], dtype=np.float64).nbytes
            + np.asarray(row["qddot"], dtype=np.float64).nbytes
            for row in modal_history
        )
        solver_metadata: dict[str, Any] = {
            "contract": MODAL_NEWMARK_CONTRACT,
            "numerical_policy_id": _NUMERICAL_POLICY_ID,
            "method": "modal_newmark",
            "maturity": "EXPERIMENTAL",
            "qualification_decision": "NOT_ASSESSED",
            "source_sha": prepared.source_sha,
            "physical_identity": prepared.physical_identity,
            "operator_identity": prepared.operator_identity,
            "excitation_identity": bound.channel_identity,
            "basis_identity": basis.basis_identity,
            "damping": {
                "identity": damping.identity,
                "source": damping.source,
                "parameters": damping.parameters,
                "projected_matrix_used": "Cr explicitly projected/prescribed by WP04",
                "physical_full_space_C": full_damping is not None,
                "reaction_availability": reaction_status,
                "reaction_reason": reaction_reason,
                "rayleigh_coefficients": (
                    None
                    if physical_rayleigh is None
                    else {"alpha_s_inv": physical_rayleigh[0], "rayleigh_beta_s": physical_rayleigh[1]}
                ),
            },
            "integration": {
                "scheme": "Newmark-implicit-constant-step",
                "time_step_s": dt,
                "steps": steps,
                "duration_s": final_time,
                "beta": beta,
                "gamma": gamma,
                "second_order_claim": gamma == 0.5,
                "stability_validation": "existing Newmark condition gamma>=0.5 and beta>=0.25*(gamma+0.5)^2",
                "initial_projection": {
                    "policy": projection_policy,
                    "displacement_relative_mass_error": displacement_projection_error,
                    "velocity_relative_mass_error": velocity_projection_error,
                    "exact_reconstruction_claim": False,
                },
                "initial_acceleration": "solved from Mr*qddot=Fr(0)-Cr*qdot-Kr*q",
            },
            "operators": {
                "Mr_shape": list(mr.shape),
                "Cr_shape": list(cr.shape),
                "Kr_shape": list(kr.shape),
                "operators_used_as_projected": True,
                "effective_matrix": "Kr + gamma/(beta*dt)*Cr + 1/(beta*dt^2)*Mr",
                "factorization_reused": factorization is not None,
                "factorization_count": factorization.factorization_count if factorization is not None else 0,
                "factorization_solve_count": factorization.solve_count
                if factorization is not None
                else steps - restart_step,
            },
            "time_grid": {"start_s": 0.0, "end_s": final_time, "step_s": dt, "sample_count": steps + 1},
            "restart": {
                "schema": MODAL_NEWMARK_CHECKPOINT_SCHEMA,
                "used": restart_step > 0,
                "restart_step": restart_step,
                "history_is_partial": restart_step > 0,
                "checkpoint_path": checkpoint_settings.path,
                "checkpoint_interval": checkpoint_settings.interval if checkpoint_settings.path else None,
                "checkpoint_files": checkpoint_files,
                "fail_closed": True,
            },
            "reduced_equilibrium_diagnostics": {
                "sample_count": residual_count,
                "maximum_absolute_residual_norm": max_reduced_residual_norm,
                "maximum_relative_error": max_reduced_relative_error,
                "acceptance_limit": residual_limit,
            },
            "physical_free_residual_norm": physical_residual_norm,
            "physical_free_relative_error": physical_relative_residual,
            "truncation": {
                **basis.diagnostics["truncation"],
                "response_truncation_error_estimate": "NOT_PROVIDED",
                "low_reduced_residual_is_physical_accuracy_claim": False,
                "residual_flexibility": "NOT_IMPLEMENTED; OPTION-A is outside WP06",
            },
            "result_availability": result_availability,
            "execution": {
                "linear_method": linear_method,
                "backend": backend_selection.to_dict(),
                "linear_selection": selection.to_dict(used_method=linear_method),
                "linear_execution": {
                    **linear_execution_settings(requested_method, parameters, used_method=linear_method),
                    "effective_factorization_reused": factorization is not None,
                    "linear_iterations_total": linear_iteration_total,
                    "max_linear_relative_residual": max_linear_relative_residual,
                },
            },
            "timing_seconds": {
                "preparation": preparation_seconds,
                "modal_basis_extraction": basis_seconds,
                "integration": integration_seconds,
                "reconstruction": reconstruction_seconds,
                "factorization": factorization.factorization_seconds if factorization is not None else 0.0,
                "factorization_solve_total": factorization.solve_seconds_total if factorization is not None else 0.0,
            },
            "storage_bytes": {
                "modal_basis": int(basis_storage["total_basis_owned_arrays"]),
                "projected_Mr_Cr_Kr": int(mr.nbytes + cr.nbytes + kr.nbytes),
                "final_physical_state": int(final_u.nbytes + final_v.nbytes + final_a.nbytes),
                "retained_probe_history_records": len(history),
                "retained_modal_history_arrays": modal_history_bytes,
                "checkpoint_state_arrays": int(q.nbytes + qdot.nbytes + qddot.nbytes),
                "bound_excitation_distribution": bound.distribution_storage_bytes,
            },
            "tolerances": identity["tolerance_policy"],
            "phase_convention": "real time-domain amplitudes; no harmonic phasor coercion",
            "environment": environment,
        }
        provenance = {
            "schema_version": 1,
            "source_sha": prepared.source_sha,
            "source_sha_availability": "AVAILABLE_AND_REPRODUCIBLE",
            "physical_identity": prepared.physical_identity,
            "operator_identity": prepared.operator_identity,
            "basis_identity": basis.basis_identity,
            "excitation_identity": bound.channel_identity,
            "damping_identity": damping.identity,
            "execution_key": execution_key,
            "evidence_availability": "AVAILABLE_AND_REPRODUCIBLE",
            "environment": environment,
            "timestamp_excluded_from_execution_identity": True,
            "output_paths_excluded_from_execution_identity": True,
            "maturity": "EXPERIMENTAL",
        }
        if record_history:
            output_times = np.asarray(times, dtype=np.float64)
        else:
            output_times = np.asarray([final_time], dtype=np.float64)
        return ModalNewmarkResult(
            numerical_status="PASS",
            times=output_times,
            displacements=final_u,
            velocities=final_v,
            accelerations=final_a,
            modal_displacements=q,
            modal_velocities=qdot,
            modal_accelerations=qddot,
            dofs=dofs,
            node_count=model.node_count,
            element_count=len(model.elements),
            solver=solver_metadata,
            provenance=provenance,
            result_availability=result_availability,
            execution_identity=identity,
            execution_key=execution_key,
            qualification_scope_id=qualification_scope_id,
            mesh_report=mesh_report.to_dict(),
            time_history=tuple(history),
            modal_history=tuple(modal_history),
            reactions=reactions,
        )


def _resolve_transient_channels(
    model: FiniteElementModel,
    prepared: PreparedDynamicSystem,
    channels: ExcitationChannelSet | None,
) -> ExcitationChannelSet:
    if channels is None:
        return ExcitationChannelSet.from_model_inputs(model, prepared)
    if not isinstance(channels, ExcitationChannelSet):
        raise InputValidationError("modal_newmark excitation_channels must be an ExcitationChannelSet.")
    if channels.source_mode != "explicit":
        raise InputValidationError("Externally supplied modal_newmark channels must use the explicit WP03 contract.")
    if model.loads or model.distributed_loads:
        raise InputValidationError("Legacy model loads and explicit WP03 channels cannot be combined in modal_newmark.")
    if channels.channels and any(channel.harmonic is not None for channel in channels.channels):
        raise InputValidationError("Harmonic phasors cannot be used as real modal_newmark time histories.")
    controls = {
        "load_function",
        "load_frequency_hz",
        "chirp_start_hz",
        "chirp_end_hz",
        "load_table",
        "load_factors",
        "load_factors_by_load",
        "pulse_duration",
    }
    conflict = controls.intersection(model.analysis.parameters)
    if conflict:
        raise InputValidationError(
            "Explicit WP03 time channels cannot coexist with legacy temporal controls: "
            + ", ".join(sorted(conflict))
            + "."
        )
    normalized = ExcitationChannelSet(channels.channels)
    if normalized.identity != channels.identity:
        raise InputValidationError("Explicit modal_newmark excitation identity changed during validation.")
    prepared.require_compatible(model)
    return channels


def _validate_modal_newmark_scope(parameters: Mapping[str, Any]) -> None:
    unsupported = {
        "base_acceleration",
        "uniform_base_acceleration",
        "ground_motion",
        "multi_support_excitation",
        "time_varying_supports",
        "follower_loads",
    }.intersection(parameters)
    if unsupported:
        raise InputValidationError(
            "modal_newmark does not support base or moving-support excitation in WP06: "
            + ", ".join(sorted(unsupported))
            + "."
        )


def _mass_project_initial_state(
    modes: np.ndarray,
    projected_mass: np.ndarray,
    physical_mass: csr_matrix,
    state: np.ndarray,
    label: str,
) -> np.ndarray:
    right = np.asarray(modes.T @ (physical_mass @ state), dtype=np.float64)
    try:
        result = np.linalg.solve(projected_mass, right)
    except np.linalg.LinAlgError as exc:
        raise NumericalConvergenceError(f"Cannot mass-project the initial {label} onto the retained basis.") from exc
    if not np.all(np.isfinite(result)):
        raise NumericalConvergenceError(f"Initial {label} modal projection produced non-finite coordinates.")
    return result


def _mass_projection_error(original: np.ndarray, projected: np.ndarray, mass: csr_matrix) -> float:
    delta = np.asarray(original - projected, dtype=np.float64)
    original_norm_squared = float(original @ (mass @ original))
    error_norm_squared = float(delta @ (mass @ delta))
    if original_norm_squared < -1.0e-12 or error_norm_squared < -1.0e-12:
        raise NumericalConvergenceError("Mass metric became negative while evaluating initial-state projection.")
    if original_norm_squared <= _FLOAT_TINY:
        return 0.0 if error_norm_squared <= _FLOAT_TINY else math.inf
    return math.sqrt(max(error_norm_squared, 0.0) / original_norm_squared)


def _validate_modal_checkpoint(
    checkpoint: ModalNewmarkCheckpoint,
    *,
    run_signature: str,
    source_sha: str,
    prepared: PreparedDynamicSystem,
    basis: ModalBasis,
    damping: Any,
    channels: BoundExcitationChannels,
    total_steps: int,
    dt: float,
    beta: float,
    gamma: float,
) -> None:
    checkpoint.validate(basis.mode_count)
    fields_match = (
        checkpoint.run_signature == run_signature
        and checkpoint.source_sha == source_sha
        and checkpoint.physical_identity == prepared.physical_identity
        and checkpoint.operator_identity == prepared.operator_identity
        and checkpoint.excitation_identity == channels.channel_identity
        and checkpoint.damping_identity == damping.identity
        and checkpoint.basis_identity == basis.basis_identity
        and checkpoint.total_steps == total_steps
        and checkpoint.time_step == dt
        and checkpoint.beta == beta
        and checkpoint.gamma == gamma
    )
    if not fields_match:
        raise InputValidationError(
            "Modal Newmark restart is refused: physical/operator/excitation/damping/basis or integration identity differs."
        )
    if checkpoint.completed_step > total_steps:
        raise InputValidationError("Modal Newmark checkpoint is beyond the requested final step.")


def _execution_parameters(parameters: Mapping[str, Any]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in sorted(parameters.items())
        if key not in _OUTPUT_ONLY_PARAMETERS and key not in {"output_directory", "temporary_directory"}
    }


def _relative_equilibrium_error(
    mass: np.ndarray,
    damping: np.ndarray,
    stiffness: np.ndarray,
    displacement: np.ndarray,
    velocity: np.ndarray,
    acceleration: np.ndarray,
    force: np.ndarray,
) -> float:
    inertia = mass @ acceleration
    damping_force = damping @ velocity
    internal = stiffness @ displacement
    residual = inertia + damping_force + internal - force
    denominator = float(
        np.linalg.norm(inertia) + np.linalg.norm(damping_force) + np.linalg.norm(internal) + np.linalg.norm(force)
    )
    if not np.all(np.isfinite(residual)) or not math.isfinite(denominator):
        return math.inf
    return float(np.linalg.norm(residual) / max(denominator, _FLOAT_TINY))


def _physical_relative_error(
    mass: csr_matrix,
    damping: csr_matrix,
    stiffness: csr_matrix,
    acceleration: np.ndarray,
    velocity: np.ndarray,
    displacement: np.ndarray,
    force: np.ndarray,
    free: np.ndarray,
) -> float:
    inertia = np.asarray(mass @ acceleration)
    damping_force = np.asarray(damping @ velocity)
    internal = np.asarray(stiffness @ displacement)
    residual = inertia + damping_force + internal - force
    numerator = float(np.linalg.norm(residual[free]))
    denominator = float(
        np.linalg.norm(inertia[free])
        + np.linalg.norm(damping_force[free])
        + np.linalg.norm(internal[free])
        + np.linalg.norm(force[free])
    )
    return numerator / max(denominator, _FLOAT_TINY)


def _relative_energy_drift(energy: float, initial_energy: float) -> float | None:
    if abs(initial_energy) <= 1.0e-30:
        return 0.0 if abs(energy) <= 1.0e-30 else None
    return float((energy - initial_energy) / initial_energy)


def _availability(status: str, computed: bool, retained: bool, reason: str) -> dict[str, Any]:
    return {
        "status": status,
        "computed": computed,
        "retained": retained,
        "reconstructible": retained,
        "exportable": retained,
        "reason": reason,
    }


def _finite_positive(value: object, name: str) -> float:
    try:
        result = float(cast(Any, value))
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be a finite positive number.") from exc
    if not math.isfinite(result) or result <= 0.0:
        raise InputValidationError(f"{name} must be a finite positive number.")
    return result
