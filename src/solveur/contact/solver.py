"""Sparse active-set solve for bounded node-to-triangle contact."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
import numpy as np
from scipy.sparse import csr_matrix
from solveur.contact.entities import FrictionlessContact
from solveur.contact.slip_root import solve_active_slip_root
from solveur.core.constraints import ConstraintReduction
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.material_state import StateTransaction
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
    _proposed_active,
    _search_mode,
    _seed_stick_states,
    _solve_active_set,
    _tangential_contact_force,
)

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
    return internal, tangent, {
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

class FrictionlessActiveSetSolver:
    """Enforce normal contact exactly and optional regularized Coulomb friction."""

    def solve(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        stiffness: csr_matrix,
        loads: np.ndarray,
        fixed: np.ndarray,
    ) -> ContactSolveState:
        if model.linear_constraints():
            raise InputValidationError("Frictionless contact cannot yet be combined with MPC or RBE links.")
        contacts = _expanded_contacts(model.contacts)
        operators = [_operator(contact, model.nodes, dofs) for contact in contacts]
        if any(operator.has_friction for operator in operators):
            if _search_mode(model) == "updated":
                raise InputValidationError("Updated contact search is not yet available with frictional contact.")
            return self._solve_with_friction(model, dofs, stiffness, loads, fixed, operators)
        reduction = ConstraintReduction.from_system(dofs, stiffness, loads, [], fixed)
        if _search_mode(model) == "updated":
            return self._solve_updated_frictionless(model, dofs, stiffness, loads, reduction, contacts)
        return self._solve_frictionless(model, dofs, stiffness, loads, reduction, operators)

    def _solve_updated_frictionless(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        stiffness: csr_matrix,
        loads: np.ndarray,
        reduction: ConstraintReduction,
        contacts: list[FrictionlessContact],
    ) -> ContactSolveState:
        """Repeat frozen-contact solves while facettes and normals are updated."""
        reference = np.zeros(dofs.ndof, dtype=float)
        prior_faces: tuple[int, ...] | None = None
        search_history: list[dict[str, object]] = []
        maximum = _positive_int(model.analysis.parameters.get("contact_search_max_iterations", 12), "contact_search_max_iterations")
        tolerance = _positive_float(model.analysis.parameters.get("contact_search_tolerance", 1.0e-10), "contact_search_tolerance")
        for iteration in range(1, maximum + 1):
            operators = [_operator(contact, model.nodes, dofs, reference) for contact in contacts]
            state = self._solve_frictionless(model, dofs, stiffness, loads, reduction, operators)
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
    ) -> ContactSolveState:
        active: tuple[int, ...] = ()
        history: list[dict[str, object]] = []
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
            active = proposed
        raise NumericalConvergenceError(
            f"Contact active set did not converge within {max_iterations} iterations.",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
        )

    def _solve_with_friction(
        self,
        model: FiniteElementModel,
        dofs: DofManager,
        stiffness: csr_matrix,
        loads: np.ndarray,
        fixed: np.ndarray,
        operators: list["_ContactOperator"],
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
                )
            except NumericalConvergenceError:
                state_transaction.rollback()
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
    ) -> "_FrictionIncrementState":
        """Try the direct fixed point, then solve the active slip equations.

        The direct loop is retained as the primary formulation: it reaches the
        exact regularized Coulomb solution in one or a few iterations for the
        analytical verification cases.  A deformable structure can rotate the
        trial tangential direction enough to make that fixed point alternate.
        In that event the fallback solves the two tangential slip-force
        components with the normal Lagrange multiplier still enforced exactly.
        """
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
            )
        except NumericalConvergenceError:
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
                raise NumericalConvergenceError(
                    "Frictional contact active set did not converge with direct or active-slip root iterations.",
                    reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
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
    ) -> "_FrictionIncrementState":
        """Perform one fixed-point strategy without mutating committed slip data."""
        active: tuple[int, ...] = ()
        states: tuple[str, ...] = tuple("open" for _ in operators)
        tangential_forces: np.ndarray = np.zeros((len(operators), 2), dtype=float)
        history: list[dict[str, object]] = []
        # The reference is the committed state at the beginning of the load
        # increment.  It must remain frozen while equilibrium is iterated;
        # only the converged return mapping can commit a new reference.
        references = np.asarray(slip_references, dtype=float).copy()
        initial_references = references.copy()
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
            if proposed == active and states == next_states and force_delta <= tolerance * force_scale:
                return _FrictionIncrementState(
                    displacement, multipliers, reduction, gaps, pressures, active, next_states,
                    next_forces, tangential_displacements, next_references, history,
                    _dissipation_increment(initial_references, next_references, next_forces),
                )
            active = proposed
            states = next_states
            tangential_forces = next_forces
        raise NumericalConvergenceError(
            f"Frictional contact {strategy} active set did not converge within {max_iterations} iterations.",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
        )
