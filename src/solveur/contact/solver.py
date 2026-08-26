"""Sparse active-set solve for bounded node-to-triangle contact."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast
import numpy as np
from scipy.sparse import bmat, csr_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve
import warnings
from solveur.contact.entities import FrictionlessContact
from solveur.contact.slip_root import solve_active_slip_root
from solveur.core.constraints import ConstraintReduction
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.material_state import StateTransaction

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

    The contribution is deliberately small in scope: initial-configuration
    node-to-triangle contact, no friction and no topology search. It is meant
    to be composed with material and geometric residuals by the common Newton
    driver; the established exact active-set solver remains available through
    its existing API.
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
    operators = [
        _operator(contact, model.nodes, dofs, reference, finite_sliding=finite_sliding)
        for contact in model.contacts
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
        contacts = list(model.contacts)
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

@dataclass(frozen=True)
class _ContactOperator:
    name: str
    vector: np.ndarray
    initial_gap: float
    tolerance: float
    normal: np.ndarray
    master_nodes: tuple[int, int, int]
    master_face_index: int
    master_face_count: int
    slave_node: int
    tangents: tuple[np.ndarray, np.ndarray]
    tangential_vectors: tuple[np.ndarray, np.ndarray]
    friction_coefficient: float
    tangential_stiffness: float
    projection_clamped: bool
    closest_distance: float
    projection_mode: str

    @property
    def has_friction(self) -> bool:
        return self.friction_coefficient > 0.0

    def gap(self, displacement: np.ndarray) -> float:
        return float(self.initial_gap + self.vector @ displacement)

    def tangential_displacement(self, displacement: np.ndarray) -> np.ndarray:
        return np.array([vector @ displacement for vector in self.tangential_vectors], dtype=float)


@dataclass(frozen=True)
class _FrictionIncrementState:
    displacement: np.ndarray
    multipliers: np.ndarray
    reduction: ConstraintReduction
    gaps: np.ndarray
    pressures: np.ndarray
    active: tuple[int, ...]
    states: tuple[str, ...]
    tangential_forces: np.ndarray
    tangential_displacements: np.ndarray
    slip_references: np.ndarray
    history: list[dict[str, object]]
    dissipation_increment: float


def _operator(
    contact: FrictionlessContact,
    nodes: np.ndarray,
    dofs: DofManager,
    reference_displacement: np.ndarray | None = None,
    *,
    finite_sliding: bool = False,
) -> _ContactOperator:
    geometry_nodes = nodes if reference_displacement is None else _deformed_nodes(nodes, dofs, reference_displacement)
    geometry = contact.face_geometry(
        geometry_nodes,
        allow_clamped_projection=finite_sliding,
    )
    normal, barycentric, initial_gap = geometry.normal, geometry.barycentric, geometry.gap
    vector = _relative_vector(contact.slave_node, geometry.master_nodes, dofs, normal, barycentric)
    if reference_displacement is not None:
        initial_gap -= float(vector @ reference_displacement)
    master = np.asarray(geometry_nodes[list(geometry.master_nodes)], dtype=float)
    tangent_one_raw = master[1] - master[0]
    tangent_one_raw -= normal * float(normal @ tangent_one_raw)
    tangent_one_norm = float(np.linalg.norm(tangent_one_raw))
    if tangent_one_norm <= 1.0e-14:
        raise InputValidationError("Contact master triangle cannot define a stable tangential basis.")
    tangent_one = tangent_one_raw / tangent_one_norm
    tangent_two = np.cross(normal, tangent_one)
    tangential_vectors = (
        _relative_vector(contact.slave_node, geometry.master_nodes, dofs, tangent_one, barycentric),
        _relative_vector(contact.slave_node, geometry.master_nodes, dofs, tangent_two, barycentric),
    )
    stiffness = contact.tangential_stiffness
    if contact.friction_coefficient > 0.0 and (stiffness is None or stiffness <= 0.0):
        raise InputValidationError("Frictional contact requires a positive tangential_stiffness.")
    return _ContactOperator(
        name=contact.name or f"contact_slave_{contact.slave_node}",
        vector=vector,
        initial_gap=initial_gap,
        tolerance=contact.gap_tolerance,
        normal=normal,
        master_nodes=geometry.master_nodes,
        master_face_index=geometry.face_index,
        master_face_count=len(contact.faces),
        slave_node=contact.slave_node,
        tangents=(tangent_one, tangent_two),
        tangential_vectors=tangential_vectors,
        friction_coefficient=contact.friction_coefficient,
        tangential_stiffness=float(stiffness or 0.0),
        projection_clamped=geometry.projection_clamped,
        closest_distance=float(geometry.closest_distance),
        projection_mode=geometry.projection_mode,
    )


def _deformed_nodes(nodes: np.ndarray, dofs: DofManager, displacement: np.ndarray) -> np.ndarray:
    """Return nodal translations represented by the current global solution."""
    result = np.asarray(nodes, dtype=float).copy()
    for node in range(len(result)):
        for component, name in enumerate(("UX", "UY", "UZ")):
            if dofs.has(node, name):
                result[node, component] += displacement[dofs.index(node, name)]
    return result


def _search_mode(model: FiniteElementModel) -> str:
    """Read the explicitly bounded contact-search strategy."""
    value = str(model.analysis.parameters.get("contact_search_mode", "initial")).lower()
    if value not in {"initial", "updated"}:
        raise InputValidationError("contact_search_mode must be 'initial' or 'updated'.")
    return value


def _finite_sliding(model: FiniteElementModel) -> bool:
    """Read the opt-in bounded finite-sliding contact mode."""

    value = model.analysis.parameters.get("contact_finite_sliding", False)
    if not isinstance(value, bool):
        raise InputValidationError("contact_finite_sliding must be a boolean.")
    if value and any(contact.friction_coefficient > 0.0 for contact in model.contacts):
        raise InputValidationError(
            "contact_finite_sliding is currently available for frictionless contact only."
        )
    return value


def _relative_vector(
    slave_node: int,
    master_nodes: tuple[int, int, int],
    dofs: DofManager,
    direction: np.ndarray,
    barycentric: np.ndarray,
) -> np.ndarray:
    """Return the global row mapping nodal motion to one relative direction."""
    vector = np.zeros(dofs.ndof, dtype=float)
    for component, name in enumerate(("UX", "UY", "UZ")):
        vector[dofs.index(slave_node, name)] += direction[component]
        for node, weight in zip(master_nodes, barycentric):
            vector[dofs.index(node, name)] -= weight * direction[component]
    return vector


def _solve_active_set(
    reduction: ConstraintReduction,
    operators: list[_ContactOperator],
    active: tuple[int, ...],
) -> tuple[np.ndarray, np.ndarray]:
    if not active:
        solution = _sparse_solve(reduction.matrix, reduction.rhs, "contact base system")
        return reduction.expand(solution), np.zeros(0, dtype=float)
    contact_rows = np.vstack([operators[index].vector @ reduction.transform for index in active])
    constraint_matrix = csr_matrix(contact_rows)
    constraint_rhs = np.array(
        [-operators[index].initial_gap - operators[index].vector @ reduction.offset for index in active], dtype=float
    )
    zero = csr_matrix((len(active), len(active)), dtype=float)
    saddle = bmat(((reduction.matrix, constraint_matrix.T), (constraint_matrix, zero)), format="csr")
    rhs = np.concatenate((reduction.rhs, constraint_rhs))
    solution = _sparse_solve(saddle, rhs, "contact saddle system")
    return reduction.expand(solution[: reduction.independent.size]), solution[reduction.independent.size :]


def _pressures(active: tuple[int, ...], multipliers: np.ndarray, count: int) -> np.ndarray:
    """Map normal Lagrange multipliers to the positive compression convention."""
    pressures: np.ndarray = np.zeros(count, dtype=float)
    for position, contact_index in enumerate(active):
        pressures[contact_index] = -multipliers[position]
    return pressures


def _proposed_active(
    operators: list[_ContactOperator], active: tuple[int, ...], gaps: np.ndarray, pressures: np.ndarray
) -> tuple[int, ...]:
    """Apply the normal Kuhn-Tucker active-set update."""
    proposed = tuple(
        index
        for index, gap in enumerate(gaps)
        if gap < -operators[index].tolerance
        or (index in active and gap <= operators[index].tolerance and pressures[index] >= -operators[index].tolerance)
    )
    tensile = tuple(index for index in active if pressures[index] < -operators[index].tolerance)
    return tuple(index for index in proposed if index not in tensile)


def _friction_system(
    stiffness: csr_matrix,
    loads: np.ndarray,
    operators: list[_ContactOperator],
    active: tuple[int, ...],
    states: tuple[str, ...],
    tangential_forces: np.ndarray,
    slip_references: np.ndarray,
) -> tuple[csr_matrix, np.ndarray]:
    """Build the current stick/slip linearization in full displacement space."""
    effective_stiffness = stiffness
    effective_loads = np.asarray(loads, dtype=float).copy()
    for index in active:
        operator = operators[index]
        if not operator.has_friction:
            continue
        if states[index] == "stick":
            for vector, reference in zip(operator.tangential_vectors, slip_references[index]):
                effective_stiffness = effective_stiffness + csr_matrix(
                    operator.tangential_stiffness * np.outer(vector, vector)
                )
                effective_loads += operator.tangential_stiffness * reference * vector
        elif states[index] == "slip":
            for vector, force in zip(operator.tangential_vectors, tangential_forces[index]):
                effective_loads -= force * vector
    return effective_stiffness.tocsr(), effective_loads


def _friction_update(
    operators: list[_ContactOperator],
    active: tuple[int, ...],
    displacement: np.ndarray,
    pressures: np.ndarray,
    slip_references: np.ndarray,
    prior_states: tuple[str, ...],
) -> tuple[tuple[str, ...], np.ndarray, np.ndarray, np.ndarray]:
    """Classify tangential states and evaluate the regularized Coulomb force."""
    states: list[str] = []
    forces: np.ndarray = np.zeros((len(operators), 2), dtype=float)
    relative_displacements: np.ndarray = np.zeros((len(operators), 2), dtype=float)
    next_references = np.asarray(slip_references, dtype=float).copy()
    for index, operator in enumerate(operators):
        relative = operator.tangential_displacement(displacement)
        relative_displacements[index] = relative
        if index not in active:
            states.append("open")
            continue
        if not operator.has_friction:
            states.append("frictionless")
            continue
        trial = operator.tangential_stiffness * (relative - slip_references[index])
        trial_norm = float(np.linalg.norm(trial))
        limit = operator.friction_coefficient * max(float(pressures[index]), 0.0)
        remains_sliding = prior_states[index] == "slip" and trial_norm >= limit - operator.tolerance
        if trial_norm <= limit + operator.tolerance and not remains_sliding:
            states.append("stick")
            forces[index] = trial
        else:
            states.append("slip")
            forces[index] = limit * trial / trial_norm
            next_references[index] = relative - forces[index] / operator.tangential_stiffness
    return tuple(states), forces, relative_displacements, next_references


def _dissipation_increment(previous: np.ndarray, current: np.ndarray, forces: np.ndarray) -> float:
    """Return non-recoverable local work accumulated by a slip-reference update."""
    return float(np.sum(forces * (current - previous)))


def _contact_load_path(model: FiniteElementModel, dofs: DofManager, loads: np.ndarray) -> list[np.ndarray]:
    """Build monotonic or explicitly tabulated nodal contact load increments."""
    parameters = model.analysis.parameters
    history = parameters.get("contact_load_history")
    if history is None:
        steps = _positive_int(parameters.get("contact_load_steps", 1), "contact_load_steps")
        return [float(step) / steps * np.asarray(loads, dtype=float) for step in range(1, steps + 1)]
    if model.distributed_loads:
        raise InputValidationError("contact_load_history supports nodal loads only in the current contact scope.")
    if not isinstance(history, list) or not history:
        raise InputValidationError("contact_load_history must be a non-empty list of nodal-load factor rows.")
    if len(model.loads) == 0:
        raise InputValidationError("contact_load_history requires at least one nodal load.")
    result: list[np.ndarray] = []
    for index, row in enumerate(history):
        if not isinstance(row, list) or len(row) != len(model.loads):
            raise InputValidationError(
                f"contact_load_history[{index}] must contain {len(model.loads)} finite factors."
            )
        vector = np.zeros(dofs.ndof, dtype=float)
        for factor, load in zip(row, model.loads):
            if not isinstance(factor, (int, float)) or not np.isfinite(float(factor)):
                raise InputValidationError(f"contact_load_history[{index}] has a non-finite factor.")
            vector[dofs.index(load.node, load.dof)] += float(factor) * load.value
        result.append(vector)
    return result


def _seed_stick_states(
    states: tuple[str, ...], proposed: tuple[int, ...], operators: list[_ContactOperator]
) -> tuple[str, ...]:
    """Try the elastic stick tangent when a frictional contact first closes.

    Without this predictor, classifying a newly closed pair from the bare
    system can falsely select sliding, even when the solution including the
    stick tangent is strictly inside the Coulomb cone.
    """
    updated = list(states)
    for index in proposed:
        if updated[index] == "open" and operators[index].has_friction:
            updated[index] = "stick"
    return tuple(updated)


def _tangential_contact_force(operators: list[_ContactOperator], forces: np.ndarray, size: int) -> np.ndarray:
    """Map local tangential contact forces to full nodal force space."""
    result: np.ndarray = np.zeros(size, dtype=float)
    for operator, local_force in zip(operators, forces):
        for vector, force in zip(operator.tangential_vectors, local_force):
            result += force * vector
    return result


def _sparse_solve(matrix: csr_matrix, rhs: np.ndarray, label: str) -> np.ndarray:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            solution = np.asarray(spsolve(matrix.tocsc(), rhs), dtype=float)
    except (MatrixRankWarning, RuntimeError, ValueError) as exc:
        raise NumericalConvergenceError(
            f"{label} is singular or failed: {exc}",
            reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
        ) from exc
    if not np.all(np.isfinite(solution)):
        raise NumericalConvergenceError(
            f"{label} produced non-finite values.",
            reason=NonlinearFailureReason.NAN_DETECTED,
        )
    return solution


def _contact_force(
    operators: list[_ContactOperator], active: tuple[int, ...], multipliers: np.ndarray, size: int
) -> np.ndarray:
    force: np.ndarray = np.zeros(size, dtype=float)
    for index, multiplier in zip(active, multipliers):
        force += multiplier * operators[index].vector
    return force


def _details(
    operators: list[_ContactOperator],
    gaps: np.ndarray,
    pressures: np.ndarray,
    active: tuple[int, ...],
    history: list[dict[str, object]],
    *,
    tangential_states: tuple[str, ...] | None = None,
    tangential_forces: np.ndarray | None = None,
    tangential_displacements: np.ndarray | None = None,
) -> dict[str, object]:
    rows = []
    for index, operator in enumerate(operators):
        row: dict[str, object] = {
            "index": index,
            "name": operator.name,
            "slave_node": operator.slave_node,
            "master_nodes": list(operator.master_nodes),
            "master_face_index": operator.master_face_index,
            "master_face_count": operator.master_face_count,
            "projection_clamped": operator.projection_clamped,
            "closest_distance": operator.closest_distance,
            "projection_mode": operator.projection_mode,
            "normal": operator.normal.tolist(),
            "initial_gap": operator.initial_gap,
            "gap": float(gaps[index]),
            "pressure": float(pressures[index]),
            "active": index in active,
            "complementarity": float(abs(gaps[index] * pressures[index])),
        }
        if tangential_states is not None and tangential_forces is not None and tangential_displacements is not None:
            friction_limit = operator.friction_coefficient * max(float(pressures[index]), 0.0)
            row.update(
                {
                    "tangential_state": tangential_states[index],
                    "tangent_one": operator.tangents[0].tolist(),
                    "tangent_two": operator.tangents[1].tolist(),
                    "tangential_displacement": tangential_displacements[index].tolist(),
                    "tangential_force": tangential_forces[index].tolist(),
                    "tangential_force_norm": float(np.linalg.norm(tangential_forces[index])),
                    "friction_limit": friction_limit,
                    "friction_coefficient": operator.friction_coefficient,
                    "tangential_stiffness": operator.tangential_stiffness,
                }
            )
        rows.append(row)
    return {
        "method": "lagrange_active_set_coulomb_regularized" if tangential_states is not None else "lagrange_active_set",
        "converged": True,
        "iteration_count": len(history),
        "active_contact_count": len(active),
        "contacts": rows,
        "history": history,
    }


def _contact_convergence_diagnostics(
    history: list[dict[str, object]],
    gaps: np.ndarray,
    pressures: np.ndarray,
    active: tuple[int, ...],
) -> dict[str, object]:
    """Return a stable convergence record for normal and frictional contact."""
    active_gaps = [abs(float(gaps[index])) for index in active]
    complementarity = [abs(float(gaps[index] * pressures[index])) for index in range(len(gaps))]
    final_residual = max(active_gaps or [0.0])
    return {
        "converged": True,
        "iterations": len(history),
        "residual_initial": float(history[0].get("min_gap", 0.0)) if history else 0.0,
        "residual_final": final_residual,
        "relative_residual": final_residual,
        "solver": "contact_active_set",
        "backend": "scipy.sparse.linalg.spsolve",
        "reason": "ACTIVE_SET_STABLE",
        "complementarity_max": max(complementarity or [0.0]),
    }


def _positive_int(value: object, name: str) -> int:
    try:
        numeric = float(value if isinstance(value, (str, bytes, bytearray, int, float)) else str(value))
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be a positive integer.") from exc
    if not np.isfinite(numeric) or numeric <= 0.0 or not numeric.is_integer():
        raise InputValidationError(f"{name} must be a positive integer.")
    return int(numeric)


def _positive_float(value: object, name: str) -> float:
    """Read a finite, strictly positive numerical contact tolerance."""
    try:
        result = float(value if isinstance(value, (str, bytes, bytearray, int, float)) else str(value))
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be a positive finite number.") from exc
    if not np.isfinite(result) or result <= 0.0:
        raise InputValidationError(f"{name} must be a positive finite number.")
    return result
