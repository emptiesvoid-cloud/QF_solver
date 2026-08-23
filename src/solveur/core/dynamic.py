"""Linear transient dynamic solver using Newmark time integration."""

from __future__ import annotations

import math
from dataclasses import asdict

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.assembler import GlobalAssembler
from solveur.core.audit import SolverAudit
from solveur.core.dofs import DofManager
from solveur.core.dynamic_checkpoint import DynamicCheckpoint, DynamicCheckpointSettings, DynamicCheckpointStore
from solveur.core.dynamic_controls import (
    component_load_factors,
    rayleigh_damping_definition,
    validate_per_load_factors,
)
from solveur.core.dynamic_history import history_row, validated_history_probes, validated_shell_stress_probes
from solveur.core.dynamic_reduction import DynamicDofReducer
from solveur.core.errors import InfrastructureError, InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.linear_methods import LinearSystemSolver, ReusableSparseFactorization
from solveur.core.linear_policy import LinearSolverPolicy, linear_execution_settings
from solveur.core.model import FiniteElementModel
from solveur.core.results import DynamicResult
from solveur.core.solver_backend import select_backend
from solveur.mesh.validation import MeshValidator
from solveur.post.audit import PostProcessingAuditor
from solveur.post.harmonic_shell import HarmonicShellStressPostProcessor
from solveur.post.stress import StressPostProcessor


class NewmarkDynamicSolver:
    """Implicit Newmark solver for small-displacement linear dynamics."""

    supported_methods = ("newmark", "newmark_average_acceleration")

    def __init__(self, checkpoint_store: DynamicCheckpointStore | None = None) -> None:
        self.validator = MeshValidator()
        self.assembler = GlobalAssembler()
        self.linear_solver = LinearSystemSolver()
        self.post = StressPostProcessor()
        self.post_auditor = PostProcessingAuditor()
        self.checkpoint_store = checkpoint_store

    def solve(self, model: FiniteElementModel) -> DynamicResult:
        if model.analysis.method not in self.supported_methods:
            raise InputValidationError(f"Unsupported dynamic method {model.analysis.method!r}.")
        report = self.validator.validate(model)
        if report.status == "FAIL":
            raise MeshValidationError("Mesh validation failed: " + "; ".join(report.errors))

        dofs = model.dof_manager()
        stiffness, mass, stiffness_assembly, mass_assembly = self.assembler.assemble_stiffness_and_mass(model, dofs)
        params = model.analysis.parameters
        damping_definition = rayleigh_damping_definition(params)
        damping = (
            damping_definition.alpha * mass + damping_definition.beta * stiffness
        ).tocsr()
        load_vectors = self.assembler.assemble_load_vectors(model, dofs)
        validate_per_load_factors(params.get("load_factors_by_load"), len(load_vectors))
        loads = np.zeros(dofs.ndof, dtype=float)
        for vector in load_vectors:
            loads += vector
        fixed = self.assembler.fixed_indices(model, dofs)
        reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)
        free = reducer.free

        dt, steps, beta, gamma = _validated_newmark_parameters(params)
        _validate_load_table(params.get("load_table"))
        _validate_load_function(params)
        history_probes = validated_history_probes(dofs, params.get("history_probes", []))
        shell_stress_probes = validated_shell_stress_probes(
            model,
            params.get("history_shell_stress_probes", []),
        )
        shell_stress_post = HarmonicShellStressPostProcessor() if shell_stress_probes else None
        rayleigh_alpha = damping_definition.alpha
        rayleigh_beta = damping_definition.beta
        if reducer.has_condensation and rayleigh_beta > 0.0:
            raise InputValidationError(
                "Shell Newmark with condensed drilling currently requires rayleigh_beta=0; "
                "use mass-proportional damping in the qualified scope."
            )
        reduced_mass = reducer.mass
        reduced_stiffness = reducer.stiffness
        reduced_damping = (rayleigh_alpha * reduced_mass + rayleigh_beta * reduced_stiffness).tocsr()
        checkpoint_settings = DynamicCheckpointSettings.from_parameters(params, steps)
        if checkpoint_settings.requires_store and self.checkpoint_store is None:
            raise InfrastructureError("Dynamic checkpoint persistence is not configured for this solver instance.")
        signature = self.checkpoint_store.signature(_checkpoint_signature_payload(model)) if self.checkpoint_store else ""

        restart_step = 0
        if checkpoint_settings.restart_from is not None:
            checkpoint = self.checkpoint_store.load(checkpoint_settings.restart_from)  # type: ignore[union-attr]
            _validate_restart(checkpoint, signature, dofs.ndof, steps, dt, beta, gamma)
            displacement = checkpoint.displacement.copy()
            velocity = checkpoint.velocity.copy()
            acceleration = checkpoint.acceleration.copy()
            reduced_displacement = reducer.reduce_state(displacement)
            reduced_velocity = reducer.reduce_state(velocity)
            reduced_acceleration = reducer.reduce_state(acceleration)
            initial_energy = checkpoint.initial_energy
            restart_step = checkpoint.completed_step
        else:
            displacement = _initial_vector(dofs, params.get("initial_displacements", []))
            velocity = _initial_vector(dofs, params.get("initial_velocities", []))
            reduced_displacement = reducer.reduce_state(displacement)
            reduced_velocity = reducer.reduce_state(velocity)
            initial_force = self._dynamic_load(params, 0, 0.0, steps, dt, loads, load_vectors)
            reduced_force = reducer.reduce_load(initial_force)
            reduced_acceleration = self._initial_acceleration(
                reduced_mass,
                reduced_damping,
                reduced_stiffness,
                np.arange(reducer.reduced_size, dtype=int),
                reduced_displacement,
                reduced_velocity,
                reduced_force,
            )
            displacement = reducer.expand_state(reduced_displacement, initial_force)
            velocity = reducer.expand_state(reduced_velocity)
            acceleration = reducer.expand_state(reduced_acceleration)
            initial_energy = _total_energy(displacement, velocity, stiffness, mass)

        reduced = (reduced_mass, reduced_damping, reduced_stiffness)
        effective = self._effective_stiffness(*reduced, dt=dt, beta=beta, gamma=gamma)
        requested_linear_method = str(params.get("linear_method", "direct")).lower()
        linear_selection = LinearSolverPolicy.assess(effective, requested_linear_method, params)
        LinearSolverPolicy.enforce_method_contract(linear_selection, params)
        linear_method = (
            linear_selection.recommended_method
            if requested_linear_method in LinearSolverPolicy._AUTO
            else requested_linear_method
        )
        backend_selection = select_backend(
            params.get("backend", "auto"),
            problem_size=reducer.reduced_size,
            parameters=params,
        )
        effective_factorization = (
            None
            if backend_selection.selected == "petsc"
            else self._factorize_effective(effective, linear_method, params)
        )
        history = []
        residual_history = []
        linear_iteration_history: list[int] = []
        linear_relative_residual_history: list[float] = []
        linear_backends: set[str] = set()
        checkpoint_files: list[str] = []
        for step in range(restart_step + 1, steps + 1):
            time = step * dt
            factor = self._load_factor(params, step, time, steps, dt)
            component_factors = self._component_load_factors(
                params, step, time, steps, dt, len(load_vectors)
            )
            force = sum(
                (factor * vector for factor, vector in zip(component_factors, load_vectors, strict=True)),
                np.zeros_like(loads),
            )
            reduced_force = reducer.reduce_load(force)
            rhs = self._effective_rhs(
                reduced[0],
                reduced[1],
                reduced_displacement,
                reduced_velocity,
                reduced_acceleration,
                reduced_force,
                dt=dt,
                beta=beta,
                gamma=gamma,
            )
            if effective_factorization is None:
                next_u, info = self.linear_solver.solve(effective, rhs, method=linear_method, parameters=params)
            else:
                next_u, info = effective_factorization.solve(rhs)
            if not info.converged:
                raise NumericalConvergenceError(
                    f"Dynamic linear solve did not converge; residual={info.residual_norm:.6e}."
                )
            linear_iteration_history.append(int(info.iterations))
            linear_relative_residual_history.append(float(info.relative_residual_norm))
            linear_backends.add(info.backend)
            next_a = (next_u - reduced_displacement) / (beta * dt**2)
            next_a -= reduced_velocity / (beta * dt)
            next_a -= (1.0 / (2.0 * beta) - 1.0) * reduced_acceleration
            next_v = reduced_velocity + dt * ((1.0 - gamma) * reduced_acceleration + gamma * next_a)
            reduced_displacement = next_u
            reduced_velocity = next_v
            reduced_acceleration = next_a
            displacement = reducer.expand_state(reduced_displacement, force)
            velocity = reducer.expand_state(reduced_velocity)
            acceleration = reducer.expand_state(reduced_acceleration)
            if not all(np.all(np.isfinite(vector)) for vector in (displacement, velocity, acceleration)):
                raise NumericalConvergenceError(f"Newmark produced a non-finite state at step {step}.")
            dynamic_residual = mass @ acceleration + damping @ velocity + stiffness @ displacement - force
            residual_norm = float(np.linalg.norm(dynamic_residual[free]))
            dynamic_reference = max(
                float(np.linalg.norm(force[free])),
                float(np.linalg.norm((mass @ acceleration)[free])),
                float(np.linalg.norm((damping @ velocity)[free])),
                float(np.linalg.norm((stiffness @ displacement)[free])),
                1.0,
            )
            relative_dynamic_residual = residual_norm / dynamic_reference
            residual_limit = float(params.get("dynamic_residual_failure_tolerance", 1.0e-7))
            if not np.isfinite(relative_dynamic_residual) or relative_dynamic_residual > residual_limit:
                raise NumericalConvergenceError(
                    f"Newmark residual is abnormal at step {step}: relative={relative_dynamic_residual:.6e}, "
                    f"allowed={residual_limit:.6e}."
                )
            residual_history.append(residual_norm)
            row = history_row(
                    step,
                    time,
                    factor,
                    displacement,
                    velocity,
                    acceleration,
                    stiffness,
                    mass,
                    damping,
                    residual_norm,
                    initial_energy,
                    history_probes,
                    model=model,
                    dofs=dofs,
                    shell_stress_probes=shell_stress_probes,
                    shell_stress_post=shell_stress_post,
                )
            row["load_component_factors"] = component_factors
            history.append(row)
            if checkpoint_settings.should_save(step, steps):
                state = DynamicCheckpoint(
                    model_signature=signature,
                    completed_step=step,
                    time=time,
                    time_step=dt,
                    beta=beta,
                    gamma=gamma,
                    initial_energy=initial_energy,
                    displacement=displacement.copy(),
                    velocity=velocity.copy(),
                    acceleration=acceleration.copy(),
                )
                written = self.checkpoint_store.save(  # type: ignore[union-attr]
                    checkpoint_settings.path, state, keep_step=checkpoint_settings.keep_steps
                )
                checkpoint_files.extend(str(path) for path in written if str(path) not in checkpoint_files)

        final_force = self._dynamic_load(params, steps, steps * dt, steps, dt, loads, load_vectors)
        internal = stiffness @ displacement
        inertial = mass @ acceleration
        damping_force = damping @ velocity
        residual = inertial + damping_force + internal - final_force
        reactions = np.zeros_like(residual)
        reactions[fixed] = residual[fixed]
        postprocess_mode = str(params.get("postprocess_mode", "full")).lower()
        if postprocess_mode not in {"full", "summary"}:
            raise InputValidationError("Dynamic postprocess_mode must be 'full' or 'summary'.")
        element_results: list[dict[str, object]] = []
        nodal_results: list[dict[str, object]] = []
        post_results: list[dict[str, object]] = []
        if postprocess_mode == "full":
            element_results = self.post.element_results(model, dofs, displacement)
            nodal_results = self.post.nodal_results(model, element_results)
            post_results = self.post_auditor.element_audits(model, dofs, displacement, element_results)
        audit = SolverAudit.from_state(
            model=model,
            dofs=dofs,
            report=report,
            fixed=fixed,
            free=free,
            method=model.analysis.method,
            vectors={
                "reference_loads": loads,
                "final_external_load": final_force,
                "final_displacement": displacement,
                "final_velocity": velocity,
                "final_acceleration": acceleration,
                "final_internal_force": internal,
                "final_inertial_force": inertial,
                "final_damping_force": damping_force,
                "dynamic_residual": residual,
                "reactions": reactions,
            },
            load_assembly=self.assembler.last_load_diagnostics,
            matrices={
                "stiffness": stiffness,
                "mass": mass,
                "damping": damping,
                "effective_stiffness": effective,
            },
            equilibrium=_dynamic_equilibrium_summary(dofs, final_force, residual, fixed, free),
            post_results=post_results,
            solver_selection=linear_selection.to_dict(used_method=linear_method),
            notes=[
                "Transient dynamic audit uses the final Newmark state.",
                *( [f"Restarted from completed step {restart_step}."] if restart_step else []),
            ],
        )
        return DynamicResult(
            status="PASS",
            displacements=displacement,
            velocities=velocity,
            accelerations=acceleration,
            dofs=dofs,
            mesh_report=report,
            node_count=model.node_count,
            element_count=len(model.elements),
            method=model.analysis.method,
            solver={
                "method": model.analysis.method,
                "time_step": dt,
                "step_count": steps,
                "newmark_beta": beta,
                "newmark_gamma": gamma,
                "linear_method": linear_method,
                "requested_linear_method": requested_linear_method,
                "backend": backend_selection.to_dict(),
                "linear_selection": linear_selection.to_dict(used_method=linear_method),
                "linear_execution": {
                    **linear_execution_settings(requested_linear_method, params, used_method=linear_method),
                    "used_method": "splu_reuse" if effective_factorization is not None else linear_method,
                    "effective_matrix": "K + gamma/(beta*dt)*C + 1/(beta*dt^2)*M",
                    "effective_matrix_nnz": int(getattr(effective, "nnz", 0)),
                    "factorization_reused": effective_factorization is not None,
                    "backend_used": sorted(linear_backends),
                    "iteration_count_total": int(sum(linear_iteration_history)),
                    "max_relative_residual_norm": max(linear_relative_residual_history, default=0.0),
                },
                "postprocess_mode": postprocess_mode,
                "effective_factorization_reused": effective_factorization is not None,
                "effective_factorization_count": (
                    effective_factorization.factorization_count if effective_factorization is not None else 0
                ),
                "effective_factorization_solve_count": (
                    effective_factorization.solve_count if effective_factorization is not None else 0
                ),
                "effective_factorization_seconds": (
                    effective_factorization.factorization_seconds if effective_factorization is not None else 0.0
                ),
                "effective_factorization_solve_seconds_total": (
                    effective_factorization.solve_seconds_total if effective_factorization is not None else 0.0
                ),
                "effective_factorization_last_solve_seconds": (
                    effective_factorization.last_solve_seconds if effective_factorization is not None else 0.0
                ),
                "assembly": {"stiffness": stiffness_assembly, "mass": mass_assembly},
                "dynamic_reduction": dict(reducer.diagnostics),
                "load_assembly": dict(self.assembler.last_load_diagnostics),
                "restart_used": restart_step > 0,
                "restart_step": restart_step,
                "history_is_partial": restart_step > 0,
                "checkpoint_path": checkpoint_settings.path,
                "checkpoint_interval": checkpoint_settings.interval if checkpoint_settings.path else None,
                "checkpoint_files": checkpoint_files,
                "rayleigh_alpha": rayleigh_alpha,
                "rayleigh_beta": rayleigh_beta,
                "damping_definition": damping_definition.to_dict(),
                "load_definition": self._load_definition(params),
                "load_component_count": len(load_vectors),
                "residual_history": residual_history,
                "time_history": history,
            },
            element_results=element_results,
            nodal_results=nodal_results,
            audit=audit,
        )

    def _initial_acceleration(
        self,
        mass: csr_matrix,
        damping: csr_matrix,
        stiffness: csr_matrix,
        free: np.ndarray,
        displacement: np.ndarray,
        velocity: np.ndarray,
        force: np.ndarray,
    ) -> np.ndarray:
        rhs = force[free] - (damping @ velocity + stiffness @ displacement)[free]
        factorization = self.linear_solver.factorize(mass[free, :][:, free])
        acceleration, _ = factorization.solve(rhs)
        return acceleration

    def _factorize_effective(
        self,
        effective: csr_matrix,
        linear_method: str,
        parameters: dict[str, object],
    ) -> ReusableSparseFactorization | None:
        if linear_method not in {"direct", "spsolve"} or str(parameters.get("backend", "auto")).lower() == "petsc":
            return None
        return self.linear_solver.factorize(effective, parameters=parameters)

    @staticmethod
    def _effective_stiffness(
        mass: csr_matrix,
        damping: csr_matrix,
        stiffness: csr_matrix,
        *,
        dt: float,
        beta: float,
        gamma: float,
    ) -> csr_matrix:
        return (stiffness + gamma / (beta * dt) * damping + 1.0 / (beta * dt**2) * mass).tocsr()

    @staticmethod
    def _effective_rhs(
        mass: csr_matrix,
        damping: csr_matrix,
        displacement: np.ndarray,
        velocity: np.ndarray,
        acceleration: np.ndarray,
        force: np.ndarray,
        *,
        dt: float,
        beta: float,
        gamma: float,
    ) -> np.ndarray:
        mass_term = mass @ (
            displacement / (beta * dt**2) + velocity / (beta * dt) + (1.0 / (2.0 * beta) - 1.0) * acceleration
        )
        damping_term = damping @ (
            gamma * displacement / (beta * dt)
            + (gamma / beta - 1.0) * velocity
            + dt * (gamma / (2.0 * beta) - 1.0) * acceleration
        )
        return force + mass_term + damping_term

    @staticmethod
    def _load_factor(params: dict[str, object], step: int, time: float, steps: int, dt: float) -> float:
        if "load_factors" in params:
            return _factor_from_sequence(params["load_factors"], step)
        if "load_table" in params:
            return _factor_from_table(params["load_table"], time)
        kind = str(params.get("load_function", "constant")).lower()
        if kind == "linear_ramp":
            return min(time / max(steps * dt, dt), 1.0)
        if kind == "sine":
            frequency = float(params.get("load_frequency_hz", 1.0))
            return math.sin(2.0 * math.pi * frequency * time)
        if kind == "half_sine_pulse":
            duration = float(params["pulse_duration"])
            return math.sin(math.pi * time / duration) if 0.0 <= time <= duration else 0.0
        if kind == "linear_chirp":
            duration = float(params["chirp_duration"])
            if not 0.0 <= time <= duration:
                return 0.0
            start = float(params["chirp_start_hz"])
            stop = float(params["chirp_end_hz"])
            sweep_rate = (stop - start) / duration
            phase = 2.0 * math.pi * (start * time + 0.5 * sweep_rate * time**2)
            return math.sin(phase)
        return 1.0

    def _dynamic_load(
        self,
        params: dict[str, object],
        step: int,
        time: float,
        steps: int,
        dt: float,
        loads: np.ndarray,
        load_vectors: list[np.ndarray],
    ) -> np.ndarray:
        factors = self._component_load_factors(
            params, step, time, steps, dt, len(load_vectors)
        )
        return sum(
            (factor * vector for factor, vector in zip(factors, load_vectors, strict=True)),
            np.zeros_like(loads),
        )

    def _component_load_factors(
        self,
        params: dict[str, object],
        step: int,
        time: float,
        steps: int,
        dt: float,
        load_count: int,
    ) -> list[float]:
        fallback = self._load_factor(params, step, time, steps, dt)
        return component_load_factors(
            params.get("load_factors_by_load"), load_count, step, fallback
        )

    @staticmethod
    def _load_definition(params: dict[str, object]) -> str:
        if "load_factors_by_load" in params:
            return "per_load_factors"
        if "load_table" in params:
            return "load_table"
        if "load_factors" in params:
            return "load_factors"
        return str(params.get("load_function", "constant"))


def _reduced_matrices(
    mass: csr_matrix,
    damping: csr_matrix,
    stiffness: csr_matrix,
    free: np.ndarray,
) -> tuple[csr_matrix, csr_matrix, csr_matrix]:
    return mass[free, :][:, free], damping[free, :][:, free], stiffness[free, :][:, free]


def _initial_vector(dofs: DofManager, entries: object) -> np.ndarray:
    vector = np.zeros(dofs.ndof, dtype=float)
    if not isinstance(entries, list):
        return vector
    for entry in entries:
        if isinstance(entry, dict):
            vector[dofs.index(int(entry["node"]), entry["dof"])] = float(entry["value"])
    return vector


def _dynamic_equilibrium_summary(
    dofs: DofManager,
    loads: np.ndarray,
    residual: np.ndarray,
    fixed: np.ndarray,
    free: np.ndarray,
) -> dict[str, float | int]:
    free_norm = float(np.linalg.norm(residual[free]))
    reference = max(float(np.linalg.norm(loads[free])), 1.0)
    return {
        "ndof": dofs.ndof,
        "fixed_dof_count": int(fixed.size),
        "free_dof_count": int(free.size),
        "free_residual_norm": free_norm,
        "free_relative_residual": free_norm / reference,
        "reaction_norm": float(np.linalg.norm(residual[fixed])) if fixed.size else 0.0,
    }


def _total_energy(displacement: np.ndarray, velocity: np.ndarray, stiffness: csr_matrix, mass: csr_matrix) -> float:
    return float(0.5 * displacement @ (stiffness @ displacement) + 0.5 * velocity @ (mass @ velocity))


def _factor_from_sequence(values: object, step: int) -> float:
    factors = list(values)
    if not factors:
        return 0.0
    if step < len(factors):
        return float(factors[step])
    return float(factors[-1])


def _factor_from_table(values: object, time: float) -> float:
    table = sorted(
        (float(item["time"]), float(item["factor"]))
        for item in values
        if isinstance(item, dict) and "time" in item and "factor" in item
    )
    if not table:
        return 0.0
    if time <= table[0][0]:
        return table[0][1]
    if time >= table[-1][0]:
        return table[-1][1]
    for left, right in zip(table, table[1:]):
        if left[0] <= time <= right[0]:
            ratio = (time - left[0]) / max(right[0] - left[0], 1.0e-30)
            return float(left[1] + ratio * (right[1] - left[1]))
    return table[-1][1]


def _validated_newmark_parameters(params: dict[str, object]) -> tuple[float, int, float, float]:
    try:
        dt = float(params.get("time_step", params.get("dt", 0.01)))
        steps = int(params.get("steps", params.get("time_steps", 1)))
        beta = float(params.get("newmark_beta", 0.25))
        gamma = float(params.get("newmark_gamma", 0.5))
    except (TypeError, ValueError) as exc:
        raise InputValidationError("Newmark time_step, steps, beta and gamma must be numeric.") from exc
    if not np.isfinite(dt) or dt <= 0.0 or steps <= 0:
        raise InputValidationError("Newmark time_step and steps must be positive.")
    minimum_beta = 0.25 * (gamma + 0.5) ** 2
    if not np.isfinite(beta) or not np.isfinite(gamma) or gamma < 0.5 or beta < minimum_beta:
        raise InputValidationError(
            "Unstable Newmark parameters: require gamma >= 0.5 and beta >= 0.25 * (gamma + 0.5)^2."
        )
    return dt, steps, beta, gamma


def _validate_load_table(value: object | None) -> None:
    if value is None:
        return
    if not isinstance(value, list) or not value:
        raise InputValidationError("Dynamic load_table must be a non-empty list.")
    previous = -np.inf
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != {"time", "factor"}:
            raise InputValidationError(f"Dynamic load_table[{index}] must contain exactly time and factor.")
        try:
            time = float(item["time"])
            factor = float(item["factor"])
        except (TypeError, ValueError) as exc:
            raise InputValidationError(f"Dynamic load_table[{index}] values must be numeric.") from exc
        if not np.isfinite(time) or not np.isfinite(factor) or time < 0.0 or time <= previous:
            raise InputValidationError("Dynamic load_table times must be finite, non-negative and strictly increasing.")
        previous = time


def _validate_load_function(params: dict[str, object]) -> None:
    if any(key in params for key in ("load_table", "load_factors", "load_factors_by_load")):
        return
    kind = str(params.get("load_function", "constant")).lower()
    supported = {"constant", "linear_ramp", "sine", "half_sine_pulse", "linear_chirp"}
    if kind not in supported:
        raise InputValidationError(
            f"Unsupported dynamic load_function {kind!r}; allowed: {', '.join(sorted(supported))}."
        )
    required = {
        "sine": ("load_frequency_hz",),
        "half_sine_pulse": ("pulse_duration",),
        "linear_chirp": ("chirp_start_hz", "chirp_end_hz", "chirp_duration"),
    }.get(kind, ())
    for key in required:
        if key not in params:
            raise InputValidationError(f"Dynamic load_function {kind!r} requires {key}.")
        try:
            value = float(params[key])
        except (TypeError, ValueError) as exc:
            raise InputValidationError(f"Dynamic parameter {key} must be numeric.") from exc
        allow_zero = key in {"load_frequency_hz", "chirp_start_hz"}
        if not np.isfinite(value) or value < 0.0 or (value == 0.0 and not allow_zero):
            qualifier = "non-negative" if allow_zero else "positive"
            raise InputValidationError(f"Dynamic parameter {key} must be finite and {qualifier}.")


def _checkpoint_signature_payload(model: FiniteElementModel) -> dict[str, object]:
    excluded = {"checkpoint_path", "checkpoint_interval", "checkpoint_keep_steps", "restart_from"}
    parameters = {key: value for key, value in model.analysis.parameters.items() if key not in excluded}
    return {
        "schema_version": model.schema_version,
        "units": model.units,
        "nodes": model.nodes.tolist(),
        "elements": [asdict(element) for element in model.elements],
        "materials": model.materials,
        "fixed_dofs": [asdict(condition) for condition in model.fixed_dofs],
        "loads": [asdict(load) for load in model.loads],
        "distributed_loads": [asdict(load) for load in model.distributed_loads],
        "analysis": {"type": model.analysis.type, "method": model.analysis.method, "parameters": parameters},
    }


def _validate_restart(
    checkpoint: DynamicCheckpoint,
    signature: str,
    ndof: int,
    total_steps: int,
    dt: float,
    beta: float,
    gamma: float,
) -> None:
    checkpoint.validate(ndof)
    if checkpoint.model_signature != signature:
        raise InputValidationError("Dynamic checkpoint does not match the current physical model or analysis settings.")
    if checkpoint.completed_step > total_steps:
        raise InputValidationError("Dynamic checkpoint is beyond the requested final step.")
    expected = checkpoint.completed_step * dt
    values_match = (
        np.isclose(checkpoint.time_step, dt)
        and np.isclose(checkpoint.beta, beta)
        and np.isclose(checkpoint.gamma, gamma)
        and np.isclose(checkpoint.time, expected)
    )
    if not values_match:
        raise InputValidationError("Dynamic checkpoint time integration metadata is inconsistent.")
