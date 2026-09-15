"""Sparse active-set solve for bounded node-to-triangle contact."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, cast
import numpy as np
from scipy.sparse import csr_matrix
from solveur.contact.entities import FrictionlessContact
from solveur.contact.evaluation import normalized_contact_diagnostics
from solveur.contact.slip_root import solve_active_slip_root
from solveur.core.constraints import ConstraintReduction
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.material_state import StateTransaction
from solveur.contact.support import (
    _ContactOperator,
    _FrictionIncrementState,
    _contact_convergence_diagnostics,
    _contact_force,
    _contact_load_path,
    _details,
    _dissipation_increment,
    _expanded_contacts,
    _finite_sliding,
    _friction_system,
    _friction_update,
    _operator,
    _positive_float,
    _positive_int,
    _pressures,
    _reseed_stick_predictor_after_normal_set_change,
    _proposed_active,
    _select_active_set_transition,
    _search_mode,
    _seed_stick_states,
    _solve_active_set,
    _tangential_contact_force,
)
from solveur.core.telemetry.events import EventStatus, EventType
from solveur.core.telemetry.observer import TelemetryHandle, emit_route_event_best_effort


ContactTrace = Callable[[str, Mapping[str, object]], None]

@dataclass(frozen=True)
class ContactSolveState:
    """Final active-set state and transparent contact diagnostics."""

    displacement: np.ndarray
    internal_force: np.ndarray
    reduced_stiffness: csr_matrix
    details: dict[str, object]
    applied_loads: np.ndarray


def assemble_penalty_contact(
    model: FiniteElementModel,
    dofs: DofManager,
    displacement: np.ndarray,
    *,
    penalty: float,
) -> tuple[np.ndarray, csr_matrix, dict[str, object]]:
    """Assemble an opt-in sparse frictionless penalty contribution.

    The contribution supports legacy single-node pairs and bounded slave-node
    patches against triangulated master surfaces. It remains frictionless and
    penalty-based; updated finite sliding recomputes the selected facet and
    normal from the current trial geometry. The contribution is composed with
    material and geometric residuals by the common Newton driver.
    """
    if penalty <= 0.0 or not np.isfinite(penalty):
        raise InputValidationError("Penalty contact stiffness must be finite and positive.")
    if any(contact.friction_coefficient > 0.0 for contact in model.contacts):
        raise InputValidationError("The common penalty contact contribution is frictionless only.")
    values = np.asarray(displacement, dtype=float)
    if values.shape != (dofs.ndof,) or not np.all(np.isfinite(values)):
        raise InputValidationError("Penalty contact displacement must be a finite global vector.")
    search_mode = str(model.analysis.parameters.get("contact_search_mode", "initial")).lower()
    if search_mode not in {"initial", "updated"}:
        raise InputValidationError("contact_search_mode must be 'initial' or 'updated'.")
    finite_sliding = _finite_sliding(model)
    if finite_sliding and search_mode != "updated":
        raise InputValidationError(
            "contact_finite_sliding requires contact_search_mode='updated'."
        )
    penetration_limit_value = model.analysis.parameters.get("contact_max_penetration")
    penetration_limit: float | None = None
    if penetration_limit_value is not None:
        if isinstance(penetration_limit_value, bool):
            raise InputValidationError("contact_max_penetration must be finite and positive when configured.")
        try:
            penetration_limit = float(penetration_limit_value)
        except (TypeError, ValueError) as error:
            raise InputValidationError(
                "contact_max_penetration must be finite and positive when configured."
            ) from error
        if not np.isfinite(penetration_limit) or penetration_limit <= 0.0:
            raise InputValidationError("contact_max_penetration must be finite and positive when configured.")
    reference = values if search_mode == "updated" else None
    contacts = _expanded_contacts(model.contacts)
    operators = [
        _operator(contact, model.nodes, dofs, reference, finite_sliding=finite_sliding)
        for contact in contacts
    ]
    internal = np.zeros(dofs.ndof, dtype=float)
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    gaps: list[float] = []
    active: list[int] = []
    for index, operator in enumerate(operators):
        gap = operator.gap(values)
        gaps.append(gap)
        if gap >= 0.0:
            continue
        active.append(index)
        internal += penalty * gap * operator.vector
        support = np.flatnonzero(operator.vector)
        local_vector = operator.vector[support]
        block = penalty * np.outer(local_vector, local_vector)
        local_rows, local_cols = np.nonzero(block)
        rows.extend(support[local_rows].tolist())
        cols.extend(support[local_cols].tolist())
        data.extend(block[local_rows, local_cols].tolist())
    tangent = csr_matrix((data, (rows, cols)), shape=(dofs.ndof, dofs.ndof))
    active_penetrations = [-float(gap) for gap in gaps if gap < 0.0]
    maximum_penetration = max(active_penetrations, default=0.0)
    if penetration_limit is not None and maximum_penetration > penetration_limit:
        raise NumericalConvergenceError(
            "Penalty contact trial exceeded contact_max_penetration.",
            reason=NonlinearFailureReason.CONTACT_PENETRATION_EXCESSIVE,
            diagnostics={
                "maximum_penetration": maximum_penetration,
                "contact_max_penetration": penetration_limit,
                "active_contacts": active,
                "gaps": gaps,
                "search_mode": search_mode,
                "finite_sliding": finite_sliding,
            },
        )
    details: dict[str, object] = {
        "formulation": "frictionless_penalty",
        "search_mode": search_mode,
        "finite_sliding": finite_sliding,
        "penalty": float(penalty),
        "active_contacts": active,
        "gaps": gaps,
        "master_face_indices": [int(operator.master_face_index) for operator in operators],
        "master_face_counts": [int(operator.master_face_count) for operator in operators],
        "normals": [operator.normal.tolist() for operator in operators],
        "slave_surface_mode": "node_patch_to_faceted_surface" if any(
            contact.slave_patch_nodes is not None for contact in model.contacts
        ) else "single_node_to_faceted_surface",
        "slave_node_count": len(operators),
        "projection_clamped": [bool(operator.projection_clamped) for operator in operators],
        "closest_distances": [float(operator.closest_distance) for operator in operators],
        "projection_modes": [operator.projection_mode for operator in operators],
        "active_penetrations": active_penetrations,
        "maximum_penetration": maximum_penetration,
        "minimum_gap": min(gaps, default=0.0),
        "contact_force_norm": float(np.linalg.norm(internal)),
        "tangent_nnz": int(tangent.nnz),
    }
    details.update(normalized_contact_diagnostics(details))
    return internal, tangent, details

class FrictionlessActiveSetSolver:
    """Enforce normal contact exactly and optional regularized Coulomb friction."""

    def solve(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        stiffness: csr_matrix,
        loads: np.ndarray,
        fixed: np.ndarray,
        *,
        telemetry: TelemetryHandle | None = None,
    ) -> ContactSolveState:
        if model.linear_constraints():
            raise InputValidationError("Frictionless contact cannot yet be combined with MPC or RBE links.")
        contacts = _expanded_contacts(model.contacts)
        operators = [_operator(contact, model.nodes, dofs) for contact in contacts]
        if any(operator.has_friction for operator in operators):
            if _search_mode(model) == "updated":
                raise InputValidationError("Updated contact search is not yet available with frictional contact.")
            return self._solve_with_friction(model, dofs, stiffness, loads, fixed, operators, telemetry=telemetry)
        reduction = ConstraintReduction.from_system(dofs, stiffness, loads, [], fixed)
        if _search_mode(model) == "updated":
            return self._solve_updated_frictionless(model, dofs, stiffness, loads, reduction, contacts, telemetry=telemetry)
        return self._solve_frictionless(model, dofs, stiffness, loads, reduction, operators, telemetry=telemetry)

    def _solve_updated_frictionless(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        stiffness: csr_matrix,
        loads: np.ndarray,
        reduction: ConstraintReduction,
        contacts: list[FrictionlessContact],
        *,
        telemetry: TelemetryHandle | None = None,
    ) -> ContactSolveState:
        """Repeat frozen-contact solves while facettes and normals are updated."""
        reference = np.zeros(dofs.ndof, dtype=float)
        prior_faces: tuple[int, ...] | None = None
        search_history: list[dict[str, object]] = []
        maximum = _positive_int(model.analysis.parameters.get("contact_search_max_iterations", 12), "contact_search_max_iterations")
        tolerance = _positive_float(model.analysis.parameters.get("contact_search_tolerance", 1.0e-10), "contact_search_tolerance")
        for iteration in range(1, maximum + 1):
            operators = [_operator(contact, model.nodes, dofs, reference) for contact in contacts]
            state = self._solve_frictionless(model, dofs, stiffness, loads, reduction, operators, telemetry=telemetry)
            faces = tuple(operator.master_face_index for operator in operators)
            change = float(np.linalg.norm(state.displacement - reference))
            search_history.append({"iteration": iteration, "master_face_indices": list(faces), "displacement_change": change})
            if faces == prior_faces and change <= tolerance * max(float(np.linalg.norm(state.displacement)), 1.0):
                state.details["search_mode"] = "updated_initial_geometry_iteration"
                state.details["search_history"] = search_history
                state.details["search_iteration_count"] = len(search_history)
                return state
            prior_faces = faces
            reference = state.displacement
        raise NumericalConvergenceError(
            f"Updated contact search did not converge within {maximum} iterations.",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
        )

    def _solve_frictionless(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        stiffness: csr_matrix,
        loads: np.ndarray,
        reduction: ConstraintReduction,
        operators: list["_ContactOperator"],
        *,
        telemetry: TelemetryHandle | None = None,
    ) -> ContactSolveState:
        active: tuple[int, ...] = ()
        history: list[dict[str, object]] = []
        visited: set[tuple[int, ...]] = {active}
        max_iterations = _positive_int(model.analysis.parameters.get("contact_max_iterations", 25), "contact_max_iterations")
        for iteration in range(1, max_iterations + 1):
            displacement, multipliers = _solve_active_set(reduction, operators, active)
            gaps = np.asarray([operator.gap(displacement) for operator in operators])
            pressures: np.ndarray = np.zeros(len(operators), dtype=float)
            for position, contact_index in enumerate(active):
                pressures[contact_index] = -multipliers[position]
            proposed = tuple(
                index
                for index, gap in enumerate(gaps)
                if gap < -operators[index].tolerance
                or (index in active and gap <= operators[index].tolerance and pressures[index] >= -operators[index].tolerance)
            )
            tensile = tuple(index for index in active if pressures[index] < -operators[index].tolerance)
            if tensile:
                proposed = tuple(index for index in proposed if index not in tensile)
            history.append(
                {
                    "iteration": iteration,
                    "active_contacts": list(active),
                    "proposed_contacts": list(proposed),
                    "min_gap": float(np.min(gaps, initial=0.0)),
                    "min_pressure": float(np.min(pressures, initial=0.0)),
                }
            )
            if telemetry is not None:
                emit_route_event_best_effort(
                    telemetry,
                    EventType.CONTACT_STATE,
                    status=EventStatus.RUNNING,
                    step=1,
                    iteration=iteration,
                    solver_backend="contact_active_set",
                    metrics={
                        "phase": "normal_active_set",
                        "strategy": "frictionless",
                        "active_contacts": list(active),
                        "proposed_contacts": list(proposed),
                        "min_gap": float(np.min(gaps, initial=0.0)),
                        "min_pressure": float(np.min(pressures, initial=0.0)),
                        "convergence_cause": "ACTIVE_SET_STABLE" if proposed == active else "ACTIVE_SET_UPDATE",
                    },
                )
            if proposed == active:
                contact_force = _contact_force(operators, active, multipliers, dofs.ndof)
                details = _details(operators, gaps, pressures, active, history)
                details["convergence"] = _contact_convergence_diagnostics(history, gaps, pressures, active)
                return ContactSolveState(
                    displacement=displacement,
                    internal_force=np.asarray(stiffness @ displacement + contact_force).ravel(),
                    reduced_stiffness=reduction.matrix,
                    details=details,
                    applied_loads=np.asarray(loads, dtype=float).copy(),
                )
            active, transition_cause = _select_active_set_transition(active, proposed, visited)
            history[-1]["transition_cause"] = transition_cause
            visited.add(active)
        raise NumericalConvergenceError(
            f"Contact active set did not converge within {max_iterations} iterations.",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
            diagnostics={
                "strategy": "frictionless",
                "iteration": max_iterations,
                "active_contacts": list(active),
                "cause": "ACTIVE_SET_MAX_ITERATIONS",
                "visited_active_sets": len(visited),
            },
        )

    def _solve_with_friction(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        stiffness: csr_matrix,
        loads: np.ndarray,
        fixed: np.ndarray,
        operators: list["_ContactOperator"],
        *,
        telemetry: TelemetryHandle | None = None,
    ) -> ContactSolveState:
        """Solve a small-displacement Coulomb problem by active-set outer iterations.

        The normal constraint remains an exact Lagrange multiplier.  Tangential
        sticking contributes a regularizing elastic tangent; sliding applies a
        bounded force from the preceding iterate.  This is deliberately
        limited to the direct, small-model contact scope.
        """
        path = _contact_load_path(model, dofs, loads)
        slip_references: np.ndarray = np.zeros((len(operators), 2), dtype=float)
        step_details: list[dict[str, object]] = []
        final: _FrictionIncrementState | None = None
        state_transaction = StateTransaction(np.asarray(slip_references, dtype=float).copy())
        max_iterations = _positive_int(model.analysis.parameters.get("contact_max_iterations", 25), "contact_max_iterations")
        tolerance = _positive_float(
            model.analysis.parameters.get("contact_friction_tolerance", 1.0e-9), "contact_friction_tolerance"
        )
        for step, step_loads in enumerate(path, start=1):
            if telemetry is not None:
                emit_route_event_best_effort(
                    telemetry,
                    EventType.STEP_START,
                    status=EventStatus.STARTED,
                    step=step,
                    solver_backend="contact_active_set",
                    metrics={"phase": "contact_increment", "load_norm": float(np.linalg.norm(step_loads))},
                )
            trial_references = state_transaction.begin_trial()
            try:
                final = self._solve_friction_increment(
                    dofs,
                    stiffness,
                    step_loads,
                    fixed,
                    operators,
                    trial_references,
                    max_iterations,
                    tolerance,
                    telemetry=telemetry,
                    step=step,
                )
            except NumericalConvergenceError as error:
                state_transaction.rollback()
                if telemetry is not None:
                    diagnostics = dict(error.diagnostics or {})
                    emit_route_event_best_effort(
                        telemetry,
                        EventType.STEP_REJECTED,
                        status=EventStatus.REJECTED,
                        step=step,
                        solver_backend="contact_active_set",
                        message=str(error),
                        metrics={
                            "phase": "contact_increment",
                            "accepted": False,
                            "rejected": True,
                            "active_set_iterations": int(diagnostics.get("iteration", 0) or 0),
                            "active_contact_count": len(diagnostics.get("active_contacts", [])),
                            "strategy": str(diagnostics.get("strategy", "unknown")),
                            "convergence_cause": str(diagnostics.get("cause", "CONTACT_UPDATE_FAILURE")),
                            "rollback_performed": True,
                        },
                    )
                raise
            state_transaction.trial = np.asarray(final.slip_references, dtype=float).copy()
            state_transaction.commit()
            slip_references = np.asarray(state_transaction.committed, dtype=float).copy()
            step_details.append(
                {
                    "step": step,
                    "load_norm": float(np.linalg.norm(step_loads)),
                    "iteration_count": len(final.history),
                    "states": list(final.states),
                    "slip_references": final.slip_references.tolist(),
                    "tangential_forces": final.tangential_forces.tolist(),
                    "local_dissipation_increment": final.dissipation_increment,
                }
            )
            if telemetry is not None:
                strategy = str(final.history[-1].get("strategy", "direct")) if final.history else "direct"
                metrics: dict[str, object] = {
                    "phase": "contact_increment",
                    "accepted": True,
                    "rejected": False,
                    "active_set_iterations": len(final.history),
                    "active_contact_count": len(final.active),
                    "strategy": strategy,
                    "convergence_cause": "ACTIVE_SET_STABLE",
                }
                if model.analysis.parameters.get("contact_emit_step_checkpoints", False):
                    metrics["committed_contact_state"] = {
                        "step": step,
                        "displacement": final.displacement.tolist(),
                        "multipliers": final.multipliers.tolist(),
                        "gaps": final.gaps.tolist(),
                        "pressures": final.pressures.tolist(),
                        "active_contacts": list(final.active),
                        "tangential_states": list(final.states),
                        "tangential_forces": final.tangential_forces.tolist(),
                        "slip_references": final.slip_references.tolist(),
                    }
                emit_route_event_best_effort(
                    telemetry,
                    EventType.STEP_ACCEPTED,
                    status=EventStatus.ACCEPTED,
                    step=step,
                    solver_backend="contact_active_set",
                    metrics=metrics,
                )
        if final is None:
            raise NumericalConvergenceError(
                "Frictional contact load path is empty.",
                reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
            )
        details = _details(
            operators, final.gaps, final.pressures, final.active, final.history,
            tangential_states=final.states, tangential_forces=final.tangential_forces,
            tangential_displacements=final.tangential_displacements,
        )
        details["load_steps"] = step_details
        details["slip_references"] = final.slip_references.tolist()
        details["state_transaction"] = {
            "committed": True,
            "committed_digest": state_transaction.committed_digest,
            "rollback_on_failure": True,
        }
        details["convergence"] = _contact_convergence_diagnostics(
            final.history, final.gaps, final.pressures, final.active
        )
        cumulative_dissipation = 0.0
        for item in step_details:
            cumulative_dissipation += float(cast(Any, item["local_dissipation_increment"]))
        details["cumulative_local_dissipation"] = cumulative_dissipation
        normal_force = _contact_force(operators, final.active, final.multipliers, dofs.ndof)
        friction_force = _tangential_contact_force(operators, final.tangential_forces, dofs.ndof)
        return ContactSolveState(
            displacement=final.displacement,
            internal_force=np.asarray(stiffness @ final.displacement + normal_force + friction_force).ravel(),
            reduced_stiffness=final.reduction.matrix,
            details=details,
            applied_loads=path[-1],
        )

    @staticmethod
    def _solve_friction_increment(
        dofs: DofManager, stiffness: csr_matrix, loads: np.ndarray, fixed: np.ndarray,
        operators: list["_ContactOperator"], slip_references: np.ndarray,
        max_iterations: int, tolerance: float,
        *,
        telemetry: TelemetryHandle | None = None,
        step: int = 1,
    ) -> "_FrictionIncrementState":
        """Try the direct fixed point, then solve the active slip equations.

        The direct loop is retained as the primary formulation: it reaches the
        exact regularized Coulomb solution in one or a few iterations for the
        analytical verification cases.  A deformable structure can rotate the
        trial tangential direction enough to make that fixed point alternate.
        In that event the fallback solves the two tangential slip-force
        components with the normal Lagrange multiplier still enforced exactly.
        """
        direct_error: NumericalConvergenceError | None = None
        try:
            return FrictionlessActiveSetSolver._iterate_friction_increment(
                dofs,
                stiffness,
                loads,
                fixed,
                operators,
                slip_references,
                max_iterations,
                tolerance,
                strategy="direct",
                telemetry=telemetry,
                step=step,
            )
        except NumericalConvergenceError as error:
            direct_error = error
            direct_diagnostics = dict(error.diagnostics or {})
            if telemetry is not None:
                emit_route_event_best_effort(
                    telemetry,
                    EventType.CONTACT_STATE,
                    status=EventStatus.RUNNING,
                    step=step,
                    iteration=int((error.diagnostics or {}).get("iteration", 0) or 0),
                    solver_backend="contact_active_set",
                    message=str(error),
                    metrics={
                        "phase": "direct_active_set_failure",
                        "strategy": "direct",
                        "active_contacts": list((error.diagnostics or {}).get("active_contacts", [])),
                        "convergence_cause": str((error.diagnostics or {}).get("cause", "ACTIVE_SET_FAILURE")),
                        "active_set_iteration": int((error.diagnostics or {}).get("iteration", 0) or 0),
                    },
                )
            try:
                root_state = solve_active_slip_root(
                    dofs,
                    stiffness,
                    loads,
                    fixed,
                    operators,
                    slip_references,
                    tolerance,
                    solve_active_set=_solve_active_set,
                    pressures_for=_pressures,
                    proposed_active=_proposed_active,
                    tangential_force=_tangential_contact_force,
                    trace=_contact_trace(telemetry, step=step, strategy="active_slip_root"),
                    observed_tangential_states=tuple(
                        direct_diagnostics.get("tangential_states", [])
                    ) if direct_diagnostics.get("tangential_states") else None,
                )
                return _FrictionIncrementState(
                    root_state.displacement,
                    root_state.multipliers,
                    root_state.reduction,
                    root_state.gaps,
                    root_state.pressures,
                    root_state.active,
                    root_state.states,
                    root_state.forces,
                    root_state.tangential_displacements,
                    root_state.references,
                    root_state.history,
                    _dissipation_increment(slip_references, root_state.references, root_state.forces),
                )
            except NumericalConvergenceError as root_error:
                root_diagnostics = dict(root_error.diagnostics or {})
                if telemetry is not None:
                    emit_route_event_best_effort(
                        telemetry,
                        EventType.CONTACT_STATE,
                        status=EventStatus.RUNNING,
                        step=step,
                        iteration=int(root_diagnostics.get("iteration", 0) or 0),
                        solver_backend="contact_active_set",
                        message=str(root_error),
                        metrics={
                            "phase": "active_slip_root_failure",
                            "strategy": "active_slip_root",
                            "active_contacts": list(root_diagnostics.get("active_contacts", [])),
                            "convergence_cause": str(root_diagnostics.get("cause", "ROOT_SOLVE_FAILURE")),
                            "active_set_iteration": int(root_diagnostics.get("iteration", 0) or 0),
                        },
                    )
                raise NumericalConvergenceError(
                    "Frictional contact active set did not converge with direct or active-slip root iterations.",
                    reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                    diagnostics={
                        "step": step,
                        "strategy": "direct_then_active_slip_root",
                        "cause": "DIRECT_AND_ACTIVE_SLIP_ROOT_FAILED",
                        "direct_error": str(direct_error) if direct_error is not None else "direct_failed",
                        "direct_diagnostics": direct_diagnostics,
                        "active_slip_root_error": str(root_error),
                        "active_slip_root_diagnostics": root_diagnostics,
                    },
                ) from root_error

    @staticmethod
    def _iterate_friction_increment(
        dofs: DofManager,
        stiffness: csr_matrix,
        loads: np.ndarray,
        fixed: np.ndarray,
        operators: list["_ContactOperator"],
        slip_references: np.ndarray,
        max_iterations: int,
        tolerance: float,
        *,
        strategy: str,
        telemetry: TelemetryHandle | None = None,
        step: int = 1,
    ) -> "_FrictionIncrementState":
        """Perform one fixed-point strategy without mutating committed slip data."""
        active: tuple[int, ...] = ()
        states: tuple[str, ...] = tuple("open" for _ in operators)
        tangential_forces: np.ndarray = np.zeros((len(operators), 2), dtype=float)
        history: list[dict[str, object]] = []
        last_next_states = states
        # The reference is the committed state at the beginning of the load
        # increment.  It must remain frozen while equilibrium is iterated;
        # only the converged return mapping can commit a new reference.
        references = np.asarray(slip_references, dtype=float).copy()
        initial_references = references.copy()
        visited: set[tuple[int, ...]] = {active}
        for iteration in range(1, max_iterations + 1):
            effective_stiffness, effective_loads = _friction_system(
                stiffness, loads, operators, active, states, tangential_forces, references
            )
            reduction = ConstraintReduction.from_system(dofs, effective_stiffness, effective_loads, [], fixed)
            displacement, multipliers = _solve_active_set(reduction, operators, active)
            gaps = np.asarray([operator.gap(displacement) for operator in operators])
            pressures = _pressures(active, multipliers, len(operators))
            proposed = _proposed_active(operators, active, gaps, pressures)
            next_states, next_forces, tangential_displacements, next_references = _friction_update(
                operators, active, displacement, pressures, references, states
            )
            next_states = _seed_stick_states(next_states, proposed, operators)
            last_next_states = next_states
            force_delta = float(np.linalg.norm(next_forces - tangential_forces))
            reference_delta = float(np.linalg.norm(next_references - references))
            force_scale = max(float(np.linalg.norm(next_forces)), 1.0)
            history.append(
                {
                    "iteration": iteration,
                    "strategy": strategy,
                    "active_contacts": list(active),
                    "proposed_contacts": list(proposed),
                    "tangential_states": list(next_states),
                    "min_gap": float(np.min(gaps, initial=0.0)),
                    "min_pressure": float(np.min(pressures, initial=0.0)),
                    "tangential_force_change": force_delta,
                    "slip_reference_change": reference_delta,
                }
            )
            transition_cause = "ACTIVE_SET_STABLE" if proposed == active else "ACTIVE_SET_UPDATE"
            if proposed != active:
                next_active, transition_cause = _select_active_set_transition(active, proposed, visited)
                next_states = _reseed_stick_predictor_after_normal_set_change(next_states, next_active, operators)
                history[-1]["tangential_predictor"] = "STICK_RESEEDED_AFTER_NORMAL_SET_CHANGE"
            else:
                next_active = active
            history[-1]["transition_cause"] = transition_cause
            if telemetry is not None:
                emit_route_event_best_effort(
                    telemetry,
                    EventType.CONTACT_STATE,
                    status=EventStatus.RUNNING,
                    step=step,
                    iteration=iteration,
                    solver_backend="contact_active_set",
                    metrics={
                        "phase": "friction_active_set",
                        "strategy": strategy,
                        "active_contacts": list(active),
                        "proposed_contacts": list(proposed),
                        "next_active_contacts": list(next_active),
                        "tangential_states": list(next_states),
                        "min_gap": float(np.min(gaps, initial=0.0)),
                        "min_pressure": float(np.min(pressures, initial=0.0)),
                        "tangential_force_change": force_delta,
                        "slip_reference_change": reference_delta,
                        "convergence_cause": transition_cause,
                    },
                )
            if proposed == active and states == next_states and force_delta <= tolerance * force_scale:
                return _FrictionIncrementState(
                    displacement, multipliers, reduction, gaps, pressures, active, next_states,
                    next_forces, tangential_displacements, next_references, history,
                    _dissipation_increment(initial_references, next_references, next_forces),
                )
            active = next_active
            states = next_states
            tangential_forces = next_forces
            visited.add(active)
        raise NumericalConvergenceError(
            f"Frictional contact {strategy} active set did not converge within {max_iterations} iterations.",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
            diagnostics={
                "step": step,
                "strategy": strategy,
                "iteration": max_iterations,
                "active_contacts": list(active),
                "tangential_states": list(last_next_states),
                "tangential_forces": tangential_forces.tolist(),
                "cause": "ACTIVE_SET_MAX_ITERATIONS",
                "visited_active_sets": len(visited),
            },
        )


def _contact_trace(
    telemetry: TelemetryHandle | None,
    *,
    step: int,
    strategy: str,
) -> ContactTrace | None:
    """Build the optional trace callback used by the active-slip root path."""

    if telemetry is None:
        return None

    def trace(phase: str, values: Mapping[str, object]) -> None:
        iteration_value = values.get("iteration")
        iteration = int(iteration_value) if isinstance(iteration_value, int) else None
        metrics = {"phase": phase, "strategy": strategy, **dict(values)}
        emit_route_event_best_effort(
            telemetry,
            EventType.CONTACT_STATE,
            status=EventStatus.RUNNING,
            step=step,
            iteration=iteration,
            solver_backend="contact_active_set",
            metrics=metrics,
        )

    return trace
