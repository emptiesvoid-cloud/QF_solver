"""Nonlinear fallbacks for coupled normal contact and regularized Coulomb slip."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, cast

import numpy as np
from scipy.optimize import least_squares, root
from scipy.sparse import csr_matrix

from solveur.core.constraints import ConstraintReduction
from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.contact.support import _select_active_set_transition, _sparse_rank_one


@dataclass(frozen=True)
class ActiveSlipSolution:
    """Converged active-slip state returned to the contact active-set solver."""

    displacement: np.ndarray
    multipliers: np.ndarray
    reduction: ConstraintReduction
    gaps: np.ndarray
    pressures: np.ndarray
    active: tuple[int, ...]
    states: tuple[str, ...]
    forces: np.ndarray
    tangential_displacements: np.ndarray
    references: np.ndarray
    history: list[dict[str, object]]
    closed_frictional_contacts: tuple[int, ...]
    open_frictional_contacts: tuple[int, ...]
    stick_frictional_contacts: tuple[int, ...]
    slip_frictional_contacts: tuple[int, ...]
    max_complementarity: float


SolveActiveSet = Callable[[ConstraintReduction, list[Any], tuple[int, ...]], tuple[np.ndarray, np.ndarray]]
Pressures = Callable[[tuple[int, ...], np.ndarray, int], np.ndarray]
ProposedActive = Callable[[list[Any], tuple[int, ...], np.ndarray, np.ndarray], tuple[int, ...]]
TangentialForce = Callable[[list[Any], np.ndarray, int], np.ndarray]
ContactTrace = Callable[[str, Mapping[str, object]], None]
_ACTIVE_SET_ITERATION_LIMIT = 25


def _l2_residual_merit(_vector: np.ndarray, values: np.ndarray) -> float:
    """Return the Euclidean merit of the residual used by a Newton direction."""
    return float(np.linalg.norm(np.asarray(values, dtype=float)))


def _scale_contact_residual_jacobian(
    physical_jacobian: np.ndarray,
    physical_residual: np.ndarray,
    contacts: tuple[int, ...],
    operators: list[Any],
    pressures: np.ndarray,
    pressure_sensitivity: np.ndarray,
) -> np.ndarray:
    """Differentiate the per-contact scaled residual, including its pressure scale."""
    jacobian = np.asarray(physical_jacobian, dtype=float)
    residual = np.asarray(physical_residual, dtype=float).reshape((-1, 2))
    pressure_values = np.asarray(pressures, dtype=float)
    sensitivities = np.asarray(pressure_sensitivity, dtype=float)
    if jacobian.shape != (2 * len(contacts), 2 * len(contacts)):
        raise NumericalConvergenceError("Contact residual Jacobian has an inconsistent shape.")
    if residual.shape != (len(contacts), 2) or sensitivities.shape != (len(operators), 2 * len(contacts)):
        raise NumericalConvergenceError("Contact residual scaling data has an inconsistent shape.")

    scaled = jacobian.copy()
    for position, index in enumerate(contacts):
        operator = operators[index]
        pressure = max(float(pressure_values[index]), 0.0)
        friction_limit = float(operator.friction_coefficient) * pressure
        force_scale = max(friction_limit, 1.0)
        scale_sensitivity: np.ndarray = np.zeros(2 * len(contacts), dtype=float)
        if pressure_values[index] > 0.0 and friction_limit > 1.0:
            scale_sensitivity = float(operator.friction_coefficient) * sensitivities[index]
        rows = slice(2 * position, 2 * position + 2)
        scaled[rows, :] = (
            jacobian[rows, :] / force_scale
            - np.outer(residual[position], scale_sensitivity) / force_scale**2
        )
    return scaled


def _best_residual_seed(
    primary: np.ndarray,
    diagnostics: Mapping[str, object],
    residual: Callable[[np.ndarray], np.ndarray],
    convergence_measure: Callable[[np.ndarray, np.ndarray], float],
) -> np.ndarray:
    """Keep the best finite root/Newton iterate without weakening its gate."""
    best = np.asarray(primary, dtype=float).copy()

    def measure(vector: np.ndarray) -> float:
        values = np.asarray(residual(vector), dtype=float)
        if not np.all(np.isfinite(values)):
            return float("inf")
        value = float(convergence_measure(vector, values))
        return value if np.isfinite(value) else float("inf")

    best_measure = measure(best)
    candidate_value = diagnostics.get("last_candidate")
    if candidate_value is not None:
        candidate = np.asarray(candidate_value, dtype=float)
        if candidate.shape == best.shape and np.all(np.isfinite(candidate)):
            candidate_measure = measure(candidate)
            if candidate_measure < best_measure:
                best = candidate.copy()
    return best


def _post_root_tangential_modes(
    solution: ActiveSlipSolution,
    operators: list[Any],
    slip_references: np.ndarray,
) -> tuple[str, ...]:
    """Classify the tangential modes implied by the converged normal state."""
    modes: list[str] = []
    active = set(solution.active)
    for index, operator in enumerate(operators):
        if not operator.has_friction:
            modes.append("frictionless")
            continue
        pressure = float(solution.pressures[index])
        if index not in active or pressure <= operator.tolerance:
            modes.append("open")
            continue
        trial = operator.tangential_stiffness * (
            solution.tangential_displacements[index] - slip_references[index]
        )
        trial_norm = float(np.linalg.norm(trial))
        friction_limit = operator.friction_coefficient * max(pressure, 0.0)
        current = solution.states[index]
        if current == "stick":
            mode = "stick" if trial_norm <= friction_limit + operator.tolerance else "slip"
        elif current == "slip":
            mode = "stick" if trial_norm < friction_limit - operator.tolerance else "slip"
        else:
            mode = "stick" if trial_norm <= friction_limit + operator.tolerance else "slip"
        modes.append(mode)
    return tuple(modes)


def solve_active_slip_root(
    dofs: DofManager,
    stiffness: csr_matrix,
    loads: np.ndarray,
    fixed: np.ndarray,
    operators: list[Any],
    slip_references: np.ndarray,
    tolerance: float,
    *,
    solve_active_set: SolveActiveSet,
    pressures_for: Pressures,
    proposed_active: ProposedActive,
    tangential_force: TangentialForce,
    trace: ContactTrace | None = None,
    observed_tangential_states: tuple[str, ...] | None = None,
) -> ActiveSlipSolution:
    """Resolve active-slip forces while retaining exact normal constraints.

    The nonlinear unknown is the two tangential components of each closed
    rough contact.  Each residual evaluation solves the sparse normal-contact
    saddle system, so the pressure-dependent Coulomb limit remains coupled to
    the deformable structure.
    """
    active = _normal_active_set(
        dofs,
        stiffness,
        loads,
        fixed,
        operators,
        solve_active_set,
        pressures_for,
        proposed_active,
        trace=trace,
    )
    visited_active: set[tuple[int, ...]] = {active}
    mode_hints = observed_tangential_states
    forced_closed_frictional: set[int] = set()
    initial_solution: ActiveSlipSolution | None = None
    visited_tangential_states: set[tuple[tuple[int, ...], tuple[str, ...]]] = set()
    for consistency_iteration in range(1, _ACTIVE_SET_ITERATION_LIMIT + 1):
        solution = _solve_active_slip_on_active_set(
            dofs,
            stiffness,
            loads,
            fixed,
            operators,
            active,
            slip_references,
            tolerance,
            solve_active_set=solve_active_set,
            pressures_for=pressures_for,
            tangential_force=tangential_force,
            trace=trace,
            consistency_iteration=consistency_iteration,
            observed_tangential_states=mode_hints,
            forced_closed_frictional=frozenset(forced_closed_frictional),
            initial_solution=initial_solution,
        )
        post_root_active = proposed_active(operators, active, solution.gaps, solution.pressures)
        history_entry = solution.history[-1]
        history_entry.update(
            {
                "post_root_normal_active_contacts": list(post_root_active),
                "post_root_normal_set_unchanged": post_root_active == active,
                "post_root_consistency_iteration": consistency_iteration,
            }
        )
        if post_root_active != active:
            next_active, transition_cause = _select_active_set_transition(
                active,
                post_root_active,
                visited_active,
            )
            if trace is not None:
                trace(
                    "post_root_normal_set_changed",
                    {
                        "iteration": consistency_iteration,
                        "active_contacts_before_root": list(active),
                        "post_root_normal_active_contacts": list(post_root_active),
                        "next_active_contacts": list(next_active),
                        "convergence_cause": "POST_ROOT_NORMAL_SET_CHANGED",
                        "transition_cause": transition_cause,
                        "closed_frictional_contacts": list(solution.closed_frictional_contacts),
                        "open_frictional_contacts": list(solution.open_frictional_contacts),
                        "tangential_unknown_dimension": 2 * len(solution.slip_frictional_contacts),
                    },
                )
            if next_active in visited_active:
                raise NumericalConvergenceError(
                    "Active-slip post-root normal active set repeated.",
                    reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                    diagnostics={
                        "strategy": "active_slip_root",
                        "iteration": consistency_iteration,
                        "active_contacts": list(active),
                        "post_root_active_contacts": list(post_root_active),
                        "cause": "POST_ROOT_NORMAL_SET_CHANGED",
                        "transition_cause": transition_cause,
                    },
                )
            visited_active.add(next_active)
            active = next_active
            forced_closed_frictional = {
                index
                for index in post_root_active
                if operators[index].has_friction
                and float(solution.pressures[index]) > operators[index].tolerance
            }
            initial_solution = solution
            continue

        post_root_modes = _post_root_tangential_modes(solution, operators, slip_references)
        if post_root_modes != solution.states:
            current_signature = (active, solution.states)
            next_signature = (active, post_root_modes)
            changed_contacts = [
                {
                    "contact": index,
                    "root_state": solution.states[index],
                    "post_root_state": post_root_modes[index],
                    "normal_pressure": float(solution.pressures[index]),
                    "gap": float(solution.gaps[index]),
                    "tangential_force": solution.forces[index].tolist(),
                    "reference": solution.references[index].tolist(),
                }
                for index in range(len(operators))
                if solution.states[index] != post_root_modes[index]
            ]
            if next_signature in visited_tangential_states:
                if trace is not None:
                    trace(
                        "post_root_tangential_state_cycle",
                        {
                            "iteration": consistency_iteration,
                            "active_contacts": list(active),
                            "changed_contacts": changed_contacts,
                            "convergence_cause": "POST_ROOT_TANGENTIAL_STATE_CYCLE",
                        },
                    )
                raise NumericalConvergenceError(
                    "Active-slip post-root tangential state repeated.",
                    reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                    diagnostics={
                        "strategy": "active_slip_root",
                        "iteration": consistency_iteration,
                        "active_contacts": list(active),
                        "changed_contacts": changed_contacts,
                        "cause": "POST_ROOT_TANGENTIAL_STATE_CYCLE",
                    },
                )
            visited_tangential_states.add(current_signature)
            if trace is not None:
                trace(
                    "post_root_tangential_state_changed",
                    {
                        "iteration": consistency_iteration,
                        "active_contacts": list(active),
                        "changed_contacts": changed_contacts,
                        "post_root_closed_frictional_contacts": [
                            index
                            for index in active
                            if operators[index].has_friction
                            and float(solution.pressures[index]) > operators[index].tolerance
                        ],
                        "convergence_cause": "POST_ROOT_TANGENTIAL_STATE_CHANGED",
                    },
                )
            mode_hints = post_root_modes
            forced_closed_frictional = {
                index
                for index in active
                if operators[index].has_friction
                and float(solution.pressures[index]) > operators[index].tolerance
            }
            initial_solution = solution
            continue

        _validate_post_root_state(
            solution,
            operators,
            active,
            slip_references,
            tolerance=tolerance,
            expected_tangential_states=mode_hints,
        )
        if trace is not None:
            trace(
                "post_root_normal_set_stable",
                {
                    "iteration": consistency_iteration,
                    "active_contacts": list(active),
                    "post_root_normal_active_contacts": list(post_root_active),
                    "convergence_cause": "POST_ROOT_NORMAL_SET_STABLE",
                    "closed_frictional_contacts": list(solution.closed_frictional_contacts),
                    "open_frictional_contacts": list(solution.open_frictional_contacts),
                    "tangential_unknown_dimension": 2 * len(solution.slip_frictional_contacts),
                    "max_complementarity": solution.max_complementarity,
                },
            )
        return solution

    raise NumericalConvergenceError(
        "Active-slip post-root normal active-set consistency did not converge "
        f"within {_ACTIVE_SET_ITERATION_LIMIT} iterations.",
        reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
        diagnostics={
            "strategy": "active_slip_root",
            "iteration": _ACTIVE_SET_ITERATION_LIMIT,
            "active_contacts": list(active),
            "cause": "POST_ROOT_NORMAL_SET_CHANGED",
            "visited_active_sets": len(visited_active),
        },
    )


def solve_coupled_contact_projection(
    dofs: DofManager,
    stiffness: csr_matrix,
    loads: np.ndarray,
    fixed: np.ndarray,
    operators: list[Any],
    slip_references: np.ndarray,
    tolerance: float,
    *,
    solve_active_set: SolveActiveSet,
    pressures_for: Pressures,
    proposed_active: ProposedActive,
    tangential_force: TangentialForce,
    trace: ContactTrace | None = None,
    maximum_enumerated_contacts: int = 8,
) -> ActiveSlipSolution:
    """Solve normal complementarity and the full Coulomb projection together.

    This bounded recovery route is used only after the direct iteration and
    frozen-mode active-slip root have failed. For each deterministic normal
    seed, the nonlinear unknown includes both tangential force components of
    every active frictional contact. Projection onto the pressure-dependent
    Coulomb disk selects stick or slip from the current trial displacement;
    mode labels are not inherited from a stale iterate. Once a coupled solve
    changes the normal complementarity proposal, a bounded deterministic
    normal-set correction resolves that set before the candidate can be
    accepted.

    The exhaustive normal-set search is deliberately capped. A larger
    contact system may correct its deterministic seed through the existing
    active-set iteration limit, but it fails closed after a rejected seed
    rather than paying an exponential search cost.
    """
    contact_count = len(operators)
    try:
        seed_active = _normal_active_set(
            dofs,
            stiffness,
            loads,
            fixed,
            operators,
            solve_active_set,
            pressures_for,
            proposed_active,
            trace=trace,
        )
    except NumericalConvergenceError:
        # Candidate enumeration is complete for the declared bounded set, so
        # a seed is only an ordering hint and is not a convergence authority.
        seed_active = ()

    seed_frictional = tuple(index for index in seed_active if operators[index].has_friction)
    rejected: list[dict[str, object]] = []
    candidate_count = 1 << contact_count

    def try_candidate(seed: tuple[int, ...], candidate_index: int) -> ActiveSlipSolution | None:
        active = tuple(seed)
        visited_active_sets = {active}
        active_set_history: list[dict[str, object]] = []
        try:
            for iteration in range(1, _ACTIVE_SET_ITERATION_LIMIT + 1):
                solution = _solve_coupled_projection_on_active_set(
                    dofs,
                    stiffness,
                    loads,
                    fixed,
                    operators,
                    active,
                    slip_references,
                    tolerance,
                    solve_active_set=solve_active_set,
                    pressures_for=pressures_for,
                    tangential_force=tangential_force,
                )
                if solution.active != active:
                    raise NumericalConvergenceError(
                        "Coupled projection returned a state for a different normal active set.",
                        reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                        diagnostics={
                            "cause": "COUPLED_NORMAL_ACTIVE_SET_IDENTITY_MISMATCH",
                            "requested_active_contacts": list(active),
                            "returned_active_contacts": list(solution.active),
                        },
                    )

                proposed = tuple(proposed_active(operators, active, solution.gaps, solution.pressures))
                if proposed != active:
                    next_active, transition_cause = _select_active_set_transition(
                        active, proposed, visited_active_sets
                    )
                    transition = {
                        "iteration": iteration,
                        "active_contacts": list(active),
                        "proposed_active_contacts": list(proposed),
                        "next_active_contacts": list(next_active),
                        "added_contacts": sorted(set(next_active).difference(active)),
                        "removed_contacts": sorted(set(active).difference(next_active)),
                        "minimum_gap": float(np.min(solution.gaps, initial=0.0)),
                        "minimum_pressure": float(np.min(solution.pressures, initial=0.0)),
                        "transition_cause": transition_cause,
                    }
                    active_set_history.append(transition)
                    if trace is not None:
                        trace("coupled_normal_active_set_transition", transition)
                    if next_active in visited_active_sets:
                        raise NumericalConvergenceError(
                            "Coupled normal active-set correction repeated a previously visited set.",
                            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                            diagnostics={
                                "cause": "COUPLED_NORMAL_ACTIVE_SET_CYCLE",
                                "active_contacts": list(active),
                                "proposed_active_contacts": list(proposed),
                                "next_active_contacts": list(next_active),
                                "transition_cause": transition_cause,
                            },
                        )
                    active = next_active
                    visited_active_sets.add(active)
                    continue

                _validate_post_root_state(
                    solution,
                    operators,
                    active,
                    slip_references,
                    tolerance=tolerance,
                    expected_tangential_states=None,
                )
                if trace is not None:
                    trace(
                        "coupled_contact_candidate_accepted",
                        {
                            "candidate_index": candidate_index,
                            "candidate_count": candidate_count,
                            "active_contacts": list(active),
                            "normal_active_set_iterations": iteration,
                            "normal_active_set_history": active_set_history,
                            "states": list(solution.states),
                            "closed_frictional_contacts": list(solution.closed_frictional_contacts),
                            "stick_frictional_contacts": list(solution.stick_frictional_contacts),
                            "slip_frictional_contacts": list(solution.slip_frictional_contacts),
                            "max_complementarity": solution.max_complementarity,
                        },
                    )
                return solution

            raise NumericalConvergenceError(
                "Coupled normal active set did not stabilize within the existing iteration limit.",
                reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                diagnostics={
                    "cause": "COUPLED_NORMAL_ACTIVE_SET_MAX_ITERATIONS",
                    "iteration_limit": _ACTIVE_SET_ITERATION_LIMIT,
                    "active_contacts": list(active),
                    "visited_active_sets": len(visited_active_sets),
                },
            )
        except NumericalConvergenceError as error:
            diagnostics = dict(error.diagnostics or {})
            rejected.append(
                {
                    "active_contacts": list(seed),
                    "last_active_contacts": list(active),
                    "normal_active_set_history": active_set_history,
                    "error": str(error),
                    "diagnostics": diagnostics,
                }
            )
            if trace is not None:
                trace(
                    "coupled_contact_candidate_rejected",
                    {
                        "candidate_index": candidate_index,
                        "candidate_count": candidate_count,
                        "active_contacts": list(seed),
                        "last_active_contacts": list(active),
                        "normal_active_set_iterations": len(active_set_history) + 1,
                        "cause": str(diagnostics.get("cause", "CANDIDATE_INVALID")),
                    },
                )
            return None

    seed_solution = try_candidate(seed_active, candidate_index=1)
    if seed_solution is not None:
        return seed_solution

    # The count cap bounds only exhaustive normal-set enumeration. Trying the
    # deterministic normal seed once is a single coupled solve, even when that
    # seed contains more frictional contacts than the enumeration cap.
    if contact_count > maximum_enumerated_contacts:
        raise NumericalConvergenceError(
            "Coupled frictional contact exhaustive search exceeds its deterministic contact-count limit after the seed set was rejected.",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
            diagnostics={
                "strategy": "coupled_contact_projection",
                "cause": "COUPLED_SEARCH_CONTACT_LIMIT_EXCEEDED",
                "contact_count": contact_count,
                "maximum_enumerated_contacts": maximum_enumerated_contacts,
                "seed_active_contacts": list(seed_active),
                "seed_frictional_contact_count": len(seed_frictional),
                "seed_candidate_rejection": rejected[0] if rejected else None,
                "attempted_candidate_count": 1,
            },
        )

    candidates = [
        tuple(index for index in range(contact_count) if mask & (1 << index))
        for mask in range(candidate_count)
    ]
    seed = set(seed_active)
    candidates.sort(key=lambda candidate: (len(set(candidate) ^ seed), candidate))

    for candidate_index, active in enumerate(candidates, start=1):
        if active == seed_active:
            continue
        solution = try_candidate(active, candidate_index)
        if solution is not None:
            return solution

    raise NumericalConvergenceError(
        "No admissible normal active set satisfies the coupled friction projection.",
        reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
        diagnostics={
            "strategy": "coupled_contact_projection",
            "cause": "COUPLED_ACTIVE_SET_SEARCH_EXHAUSTED",
            "candidate_count": len(candidates),
            "rejected_candidate_count": len(rejected),
            "rejected_candidates": rejected,
        },
    )


def _solve_coupled_projection_on_active_set(
    dofs: DofManager,
    stiffness: csr_matrix,
    loads: np.ndarray,
    fixed: np.ndarray,
    operators: list[Any],
    active: tuple[int, ...],
    slip_references: np.ndarray,
    tolerance: float,
    *,
    solve_active_set: SolveActiveSet,
    pressures_for: Pressures,
    tangential_force: TangentialForce,
) -> ActiveSlipSolution:
    """Solve all active tangential-force components on one normal set."""
    frictional = tuple(index for index in active if operators[index].has_friction)
    vector_size = 2 * len(frictional)

    def solve_for(vector: np.ndarray) -> tuple[np.ndarray, np.ndarray, ConstraintReduction, np.ndarray, np.ndarray, np.ndarray]:
        forces: np.ndarray = np.zeros((len(operators), 2), dtype=float)
        if frictional:
            forces[list(frictional)] = np.asarray(vector, dtype=float).reshape(len(frictional), 2)
        effective_loads = np.asarray(loads, dtype=float) - tangential_force(operators, forces, dofs.ndof)
        reduction = ConstraintReduction.from_system(dofs, stiffness, effective_loads, [], fixed)
        displacement, multipliers = solve_active_set(reduction, operators, active)
        gaps = np.asarray([operator.gap(displacement) for operator in operators], dtype=float)
        pressures = np.asarray(pressures_for(active, multipliers, len(operators)), dtype=float)
        return displacement, multipliers, reduction, gaps, pressures, forces

    def projected_trial(displacement: np.ndarray, pressures: np.ndarray) -> np.ndarray:
        projected: np.ndarray = np.zeros((len(operators), 2), dtype=float)
        for index in frictional:
            operator = operators[index]
            trial = operator.tangential_stiffness * (
                operator.tangential_displacement(displacement) - slip_references[index]
            )
            trial_norm = float(np.linalg.norm(trial))
            limit = operator.friction_coefficient * max(float(pressures[index]), 0.0)
            if trial_norm <= limit or trial_norm == 0.0:
                projected[index] = trial
            else:
                projected[index] = limit * trial / trial_norm
        return projected

    def contact_residual_data(
        vector: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, list[dict[str, object]]]:
        """Return physical and per-contact-scaled projection residuals."""
        displacement, _, _, _, pressures, _ = solve_for(vector)
        forces = np.asarray(vector, dtype=float).reshape(len(frictional), 2)
        target = projected_trial(displacement, pressures)[list(frictional)]
        physical = forces - target
        scales = np.asarray(
            [
                max(
                    operators[index].friction_coefficient
                    * max(float(pressures[index]), 0.0),
                    1.0,
                )
                for index in frictional
            ],
            dtype=float,
        )
        scaled = physical / scales[:, None]
        details = [
            {
                "contact": index,
                "normal_pressure": float(pressures[index]),
                "friction_limit": float(
                    operators[index].friction_coefficient * max(float(pressures[index]), 0.0)
                ),
                "force_scale": float(scales[position]),
                "residual_vector": physical[position].tolist(),
                "residual_norm": float(np.linalg.norm(physical[position])),
                "scaled_residual_norm": float(np.linalg.norm(scaled[position])),
            }
            for position, index in enumerate(frictional)
        ]
        return physical.ravel(), scaled.ravel(), details

    def residual(vector: np.ndarray) -> np.ndarray:
        return contact_residual_data(vector)[1]

    def maximum_contact_residual(_vector: np.ndarray, scaled_values: np.ndarray) -> float:
        pairs = np.asarray(scaled_values, dtype=float).reshape((-1, 2))
        return float(np.max(np.linalg.norm(pairs, axis=1), initial=0.0))

    def refinement_failure_context(vector: np.ndarray) -> Mapping[str, object]:
        physical, scaled, details = contact_residual_data(vector)
        return {
            "physical_residual_norm": float(np.linalg.norm(physical)),
            "maximum_scaled_contact_residual": maximum_contact_residual(vector, scaled),
            "contact_residuals": details,
        }

    zero: np.ndarray = np.zeros(vector_size, dtype=float)
    displacement, _, _, _, pressures, _ = solve_for(zero)
    displacement_sensitivity: np.ndarray = np.empty((len(displacement), vector_size), dtype=float)
    pressure_sensitivity: np.ndarray = np.empty((len(operators), vector_size), dtype=float)
    for column in range(vector_size):
        unit_force = zero.copy()
        unit_force[column] = 1.0
        response, _, _, _, response_pressures, _ = solve_for(unit_force)
        displacement_sensitivity[:, column] = response - displacement
        pressure_sensitivity[:, column] = response_pressures - pressures

    def projection_jacobian(vector: np.ndarray) -> np.ndarray:
        """Return the piecewise-consistent Jacobian of the coupled projection."""
        response, _, _, _, response_pressures, _ = solve_for(vector)
        forces = np.asarray(vector, dtype=float).reshape((len(frictional), 2))
        physical = forces - projected_trial(response, response_pressures)[list(frictional)]
        jacobian = np.eye(vector_size, dtype=float)
        for position, index in enumerate(frictional):
            operator = operators[index]
            pressure = max(float(response_pressures[index]), 0.0)
            trial = operator.tangential_stiffness * (
                operator.tangential_displacement(response) - slip_references[index]
            )
            trial_norm = float(np.linalg.norm(trial))
            trial_sensitivity = operator.tangential_stiffness * np.vstack(
                tuple(direction @ displacement_sensitivity for direction in operator.tangential_vectors)
            )
            target_sensitivity: np.ndarray
            if pressure <= operator.tolerance:
                target_sensitivity = np.zeros((2, vector_size), dtype=float)
            elif trial_norm <= operator.friction_coefficient * pressure:
                target_sensitivity = trial_sensitivity
            elif trial_norm > 0.0:
                direction = trial / trial_norm
                projector = (np.eye(2, dtype=float) - np.outer(direction, direction)) / trial_norm
                target_sensitivity = operator.friction_coefficient * (
                    np.outer(direction, pressure_sensitivity[index])
                    + pressure * projector @ trial_sensitivity
                )
            else:
                target_sensitivity = np.zeros((2, vector_size), dtype=float)
            rows = slice(2 * position, 2 * position + 2)
            jacobian[rows, :] -= target_sensitivity
        return _scale_contact_residual_jacobian(
            jacobian,
            physical.ravel(),
            frictional,
            operators,
            response_pressures,
            pressure_sensitivity,
        )

    initial = projected_trial(displacement, pressures)[list(frictional)].ravel()
    if vector_size:
        root_result = root(
            residual,
            initial,
            jac=projection_jacobian,
            method="hybr",
            options={"xtol": tolerance},
        )
        vector = np.asarray(root_result.x, dtype=float)
        strategy = "coupled_coulomb_projection_root"
        evaluations = int(root_result.nfev)
        if np.all(np.isfinite(vector)):
            _, scaled_values, _ = contact_residual_data(vector)
            maximum_scaled_residual = maximum_contact_residual(vector, scaled_values)
        else:
            maximum_scaled_residual = float("inf")
        if not root_result.success or maximum_scaled_residual > tolerance:
            try:
                vector, evaluations, residual_norm = _semismooth_newton_solution(
                    residual,
                    vector,
                    tolerance,
                    jacobian=projection_jacobian,
                    convergence_measure=maximum_contact_residual,
                    line_search_merit=_l2_residual_merit,
                )
                strategy = "coupled_coulomb_projection_semismooth_newton"
            except NumericalConvergenceError as semismooth_error:
                vector = _best_residual_seed(
                    vector,
                    semismooth_error.diagnostics or {},
                    residual,
                    maximum_contact_residual,
                )
                remaining_refinement_iterations = max(
                    0,
                    30 - int((semismooth_error.diagnostics or {}).get("iterations", 0)),
                )
                vector, evaluations, residual_norm = _globalized_slip_solution(
                    residual,
                    vector,
                    tolerance,
                    objective_residual=residual,
                    objective_jacobian=projection_jacobian,
                    refinement_residual=residual,
                    refinement_jacobian=projection_jacobian,
                    refinement_iteration_limit=remaining_refinement_iterations,
                    convergence_measure=maximum_contact_residual,
                    refinement_convergence_measure=maximum_contact_residual,
                    refinement_line_search_merit=_l2_residual_merit,
                    diagnostic_context=refinement_failure_context,
                )
                strategy = "coupled_coulomb_projection_least_squares"
        physical_residual, scaled_values, contact_residuals = contact_residual_data(vector)
        residual_norm = float(np.linalg.norm(physical_residual))
        maximum_scaled_residual = maximum_contact_residual(vector, scaled_values)
        if not np.isfinite(residual_norm) or maximum_scaled_residual > tolerance:
            worst_contact = max(
                contact_residuals,
                key=lambda row: float(cast(float, row["scaled_residual_norm"])),
                default=None,
            )
            raise NumericalConvergenceError(
                "Coupled Coulomb projection per-contact residual exceeds its frozen tolerance.",
                reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                diagnostics={
                    "cause": "COUPLED_TANGENTIAL_RESIDUAL_TOO_LARGE",
                    "active_contacts": list(active),
                    "residual_norm": residual_norm,
                    "maximum_scaled_contact_residual": maximum_scaled_residual,
                    "tolerance": tolerance,
                    "worst_contact": worst_contact,
                    "contact_residuals": contact_residuals,
                    "root_success": bool(root_result.success),
                    "root_message": str(root_result.message),
                },
            )
    else:
        vector = zero
        strategy = "coupled_coulomb_projection_no_frictional_contacts"
        evaluations = 1
        residual_norm = 0.0
        maximum_scaled_residual = 0.0
        contact_residuals = []

    displacement, multipliers, reduction, gaps, pressures, forces = solve_for(vector)
    tangential_displacements = np.asarray(
        [operator.tangential_displacement(displacement) for operator in operators], dtype=float
    )
    references = np.asarray(slip_references, dtype=float).copy()
    states: list[str] = []
    stick: list[int] = []
    slip: list[int] = []
    closed: list[int] = []
    opened: list[int] = []
    for index, operator in enumerate(operators):
        if index not in active:
            states.append("open")
            if operator.has_friction:
                opened.append(index)
            continue
        if not operator.has_friction:
            states.append("frictionless")
            continue
        pressure = float(pressures[index])
        if pressure <= operator.tolerance:
            # A normal constraint can remain weakly active with no compressive
            # multiplier. Such a contact has no Coulomb capacity and must not
            # inherit a stick/slip label from the active normal set.
            force_norm = float(np.linalg.norm(forces[index]))
            state_tolerance = max(operator.tolerance, tolerance)
            if force_norm > state_tolerance:
                raise NumericalConvergenceError(
                    "Coupled projection retained tangential force at zero pressure.",
                    reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                    diagnostics={
                        "cause": "ZERO_PRESSURE_TANGENTIAL_FORCE",
                        "contact": index,
                        "normal_pressure": pressure,
                        "tangential_force_norm": force_norm,
                        "state_tolerance": state_tolerance,
                    },
                )
            states.append("open")
            opened.append(index)
            continue
        closed.append(index)
        trial = operator.tangential_stiffness * (tangential_displacements[index] - slip_references[index])
        trial_norm = float(np.linalg.norm(trial))
        limit = operator.friction_coefficient * pressure
        if trial_norm <= limit + operator.tolerance:
            states.append("stick")
            stick.append(index)
        else:
            states.append("slip")
            slip.append(index)
            references[index] = tangential_displacements[index] - forces[index] / operator.tangential_stiffness

    max_complementarity = float(np.max(np.abs(gaps * pressures), initial=0.0))
    return ActiveSlipSolution(
        displacement,
        multipliers,
        reduction,
        gaps,
        pressures,
        active,
        tuple(states),
        forces,
        tangential_displacements,
        references,
        [
            {
                "iteration": evaluations,
                "strategy": strategy,
                "active_contacts": list(active),
                "proposed_contacts": list(active),
                "tangential_states": list(states),
                "closed_frictional_contacts": closed,
                "stick_frictional_contacts": stick,
                "slip_frictional_contacts": slip,
                "open_frictional_contacts": opened,
                "tangential_unknown_dimension": vector_size,
                "tangential_force_residual": residual_norm,
                "maximum_scaled_contact_residual": maximum_scaled_residual,
                "contact_residuals": contact_residuals,
                "max_complementarity": max_complementarity,
            }
        ],
        tuple(closed),
        tuple(opened),
        tuple(stick),
        tuple(slip),
        max_complementarity,
    )
def _scale_contact_residuals(
    residual_values: np.ndarray,
    slip_contacts: tuple[int, ...],
    operators: list[Any],
    pressures: np.ndarray,
) -> tuple[np.ndarray, list[dict[str, object]], float]:
    """Scale each slip equation by the local force scale used by admissibility.

    A single Euclidean norm across all contacts can hide a locally inadmissible
    contact as the contact count grows. Acceptance therefore uses the maximum
    per-contact normalized residual, matching the post-root Coulomb check.
    """
    values = np.asarray(residual_values, dtype=float).reshape((-1, 2))
    if len(values) != len(slip_contacts):
        raise ValueError("Active-slip residual dimension does not match its contact set.")
    scales: np.ndarray = np.empty(len(slip_contacts), dtype=float)
    details: list[dict[str, object]] = []
    maximum_scaled_norm = 0.0
    for position, index in enumerate(slip_contacts):
        pressure = float(pressures[index])
        friction_limit = float(operators[index].friction_coefficient) * max(pressure, 0.0)
        scale = max(friction_limit, 1.0)
        vector = values[position]
        residual_norm = float(np.linalg.norm(vector))
        scaled_norm = residual_norm / scale
        scales[position] = scale
        maximum_scaled_norm = max(maximum_scaled_norm, scaled_norm)
        details.append(
            {
                "contact": index,
                "normal_pressure": pressure,
                "friction_limit": friction_limit,
                "force_scale": scale,
                "residual_vector": vector.tolist(),
                "residual_norm": residual_norm,
                "scaled_residual_norm": scaled_norm,
            }
        )
    return values / scales[:, None], details, maximum_scaled_norm


def _solve_active_slip_on_active_set(
    dofs: DofManager,
    stiffness: csr_matrix,
    loads: np.ndarray,
    fixed: np.ndarray,
    operators: list[Any],
    active: tuple[int, ...],
    slip_references: np.ndarray,
    tolerance: float,
    *,
    solve_active_set: SolveActiveSet,
    pressures_for: Pressures,
    tangential_force: TangentialForce,
    trace: ContactTrace | None,
    consistency_iteration: int,
    observed_tangential_states: tuple[str, ...] | None,
    forced_closed_frictional: frozenset[int] = frozenset(),
    initial_solution: ActiveSlipSolution | None = None,
) -> ActiveSlipSolution:
    """Solve only the closed, frictional tangential unknowns for one normal set."""
    zero_force_probe: np.ndarray = np.zeros((len(operators), 2), dtype=float)
    probe_reduction = ConstraintReduction.from_system(
        dofs,
        stiffness,
        loads - tangential_force(operators, zero_force_probe, dofs.ndof),
        [],
        fixed,
    )
    probe_displacement, probe_multipliers = solve_active_set(probe_reduction, operators, active)
    probe_pressures = pressures_for(active, probe_multipliers, len(operators))
    closed_frictional = tuple(
        index
        for index in active
        if operators[index].has_friction
        and (
            float(probe_pressures[index]) > operators[index].tolerance
            or index in forced_closed_frictional
        )
    )
    closed_frictional_set = set(closed_frictional)
    open_frictional = tuple(
        index
        for index, operator in enumerate(operators)
        if operator.has_friction and index not in closed_frictional_set
    )
    if not closed_frictional:
        raise NumericalConvergenceError(
            "Active-slip fallback requires one closed frictional contact with valid compression.",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
            diagnostics={
                "strategy": "active_slip_root",
                "active_contacts": list(active),
                "open_frictional_contacts": list(open_frictional),
                "cause": "NO_COMPRESSED_FRICTIONAL_CONTACT",
            },
        )
    if observed_tangential_states is None:
        # Preserve the historical direct-root API for existing unit fixtures.
        # The production solver always supplies the direct iteration's state
        # classification, which is required for the hybrid route below.
        slip_frictional = closed_frictional
        stick_frictional: tuple[int, ...] = ()
    else:
        if len(observed_tangential_states) != len(operators):
            raise NumericalConvergenceError(
                "Active-slip root received an incomplete direct tangential-state classification.",
                reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                diagnostics={
                    "strategy": "active_slip_hybrid_root",
                    "active_contacts": list(active),
                    "cause": "MISSING_DIRECT_STATE_CLASSIFICATION",
                },
            )
        active_frictional = set(closed_frictional)
        invalid = [
            index
            for index in active_frictional
            if observed_tangential_states[index] not in {"stick", "slip"}
        ]
        if invalid:
            raise NumericalConvergenceError(
                "Active-slip root received an invalid direct tangential-state classification.",
                reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                diagnostics={
                    "strategy": "active_slip_hybrid_root",
                    "active_contacts": list(active),
                    "invalid_contacts": invalid,
                    "observed_tangential_states": list(observed_tangential_states),
                    "cause": "INVALID_DIRECT_STATE_CLASSIFICATION",
                },
            )
        slip_frictional = tuple(
            index for index in closed_frictional if observed_tangential_states[index] == "slip"
        )
        stick_frictional = tuple(
            index for index in closed_frictional if observed_tangential_states[index] == "stick"
        )
        if not slip_frictional:
            raise NumericalConvergenceError(
                "Active-slip hybrid root requires at least one observed slip contact.",
                reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                diagnostics={
                    "strategy": "active_slip_hybrid_root",
                    "active_contacts": list(active),
                    "closed_frictional_contacts": list(closed_frictional),
                    "stick_frictional_contacts": list(stick_frictional),
                    "cause": "NO_OBSERVED_SLIP_CONTACT",
                },
            )
    if trace is not None:
        trace(
            "active_slip_hybrid_subset" if observed_tangential_states is not None else "active_slip_mixed_subset",
            {
                "iteration": consistency_iteration,
                "active_contacts": list(active),
                "closed_frictional_contacts": list(closed_frictional),
                "stick_frictional_contacts": list(stick_frictional),
                "slip_frictional_contacts": list(slip_frictional),
                "open_frictional_contacts": list(open_frictional),
                "tangential_unknown_dimension": 2 * len(slip_frictional),
                "compression_valid": {
                    str(index): float(probe_pressures[index]) > operators[index].tolerance for index in active
                },
                "observed_tangential_states": (
                    list(observed_tangential_states) if observed_tangential_states is not None else None
                ),
                "convergence_cause": (
                    "HYBRID_STICK_SLIP_SUBSET" if observed_tangential_states is not None
                    else "MIXED_OPEN_ACTIVE_SUBSET"
                ),
            },
        )

    stick_stiffness = stiffness
    stick_loads = np.asarray(loads, dtype=float).copy()
    for index in stick_frictional:
        operator = operators[index]
        for component, direction in enumerate(operator.tangential_vectors):
            stick_stiffness = stick_stiffness + _sparse_rank_one(
                direction, operator.tangential_stiffness
            )
            stick_loads += (
                operator.tangential_stiffness * slip_references[index, component] * direction
            )

    def solve_closed_for(
        vector: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, ConstraintReduction, np.ndarray, np.ndarray]:
        forces: np.ndarray = np.zeros((len(operators), 2), dtype=float)
        forces[list(slip_frictional)] = vector.reshape(len(slip_frictional), 2)
        effective_loads = stick_loads.copy()
        for index in slip_frictional:
            operator = operators[index]
            for component, direction in enumerate(operator.tangential_vectors):
                effective_loads -= forces[index, component] * direction
        reduction = ConstraintReduction.from_system(
            dofs,
            stick_stiffness,
            effective_loads,
            [],
            fixed,
        )
        displacement, multipliers = solve_active_set(reduction, operators, active)
        gaps = np.asarray([operator.gap(displacement) for operator in operators])
        pressures = pressures_for(active, multipliers, len(operators))
        return displacement, multipliers, reduction, gaps, pressures

    zero_force: np.ndarray = np.zeros(2 * len(slip_frictional), dtype=float)
    displacement, _, _, _, pressures = solve_closed_for(zero_force)
    displacement_sensitivity, pressure_sensitivity = _active_slip_response_sensitivities(
        solve_closed_for,
        zero_force,
        displacement,
        pressures,
    )
    initial_force: list[float] = []
    for index in slip_frictional:
        operator = operators[index]
        trial = operator.tangential_stiffness * (
            operator.tangential_displacement(displacement) - slip_references[index]
        )
        norm = float(np.linalg.norm(trial))
        if initial_solution is not None:
            previous_pressure = float(initial_solution.pressures[index])
            previous_trial = operator.tangential_stiffness * (
                initial_solution.tangential_displacements[index] - slip_references[index]
            )
            previous_norm = float(np.linalg.norm(previous_trial))
            if previous_norm > tolerance and previous_pressure > operator.tolerance:
                initial_force.extend(
                    (
                        operator.friction_coefficient
                        * previous_pressure
                        * previous_trial
                        / previous_norm
                    ).tolist()
                )
                continue
            previous_force = np.asarray(initial_solution.forces[index], dtype=float)
            if np.all(np.isfinite(previous_force)) and float(np.linalg.norm(previous_force)) > tolerance:
                initial_force.extend(previous_force.tolist())
                continue
        if norm <= tolerance or pressures[index] <= operator.tolerance:
            initial_force.extend((0.0, 0.0))
        else:
            initial_force.extend((operator.friction_coefficient * pressures[index] * trial / norm).tolist())

    residual_cache: dict[str, np.ndarray] = {}

    def residual(vector: np.ndarray) -> np.ndarray:
        response, _, _, _, response_pressures = solve_closed_for(vector)
        values: list[float] = []
        for position, index in enumerate(slip_frictional):
            operator = operators[index]
            trial = operator.tangential_stiffness * (
                operator.tangential_displacement(response) - slip_references[index]
            )
            norm = float(np.linalg.norm(trial))
            if norm <= tolerance or response_pressures[index] <= operator.tolerance:
                target: np.ndarray = np.zeros(2, dtype=float)
            else:
                target = operator.friction_coefficient * response_pressures[index] * trial / norm
            values.extend((vector[2 * position: 2 * position + 2] - target).tolist())
        result = np.asarray(values, dtype=float)
        residual_cache["vector"] = np.asarray(vector, dtype=float).copy()
        residual_cache["values"] = result.copy()
        residual_cache["pressures"] = np.asarray(response_pressures, dtype=float).copy()
        return result

    def pressures_for_residual(vector: np.ndarray, values: np.ndarray) -> np.ndarray:
        if (
            "vector" in residual_cache
            and np.array_equal(residual_cache["vector"], vector)
            and np.array_equal(residual_cache["values"], values)
        ):
            return residual_cache["pressures"]
        return np.asarray(solve_closed_for(vector)[4], dtype=float)

    def contact_residual_data(
        vector: np.ndarray, values: np.ndarray
    ) -> tuple[np.ndarray, list[dict[str, object]], float]:
        pressures = pressures_for_residual(vector, values)
        scaled, details, maximum = _scale_contact_residuals(
            values,
            slip_frictional,
            operators,
            pressures,
        )
        forces = np.asarray(vector, dtype=float).reshape((-1, 2))
        residual_pairs = np.asarray(values, dtype=float).reshape((-1, 2))
        for position, (index, detail) in enumerate(zip(slip_frictional, details, strict=True)):
            detail["tangential_force_vector"] = forces[position].tolist()
            detail["target_tangential_force"] = (forces[position] - residual_pairs[position]).tolist()
            detail["tangential_basis"] = [
                np.asarray(direction, dtype=float).tolist()
                for direction in operators[index].tangential_vectors
            ]
        return scaled, details, maximum

    def scaled_residual(vector: np.ndarray) -> np.ndarray:
        values = residual(vector)
        scaled, _, _ = contact_residual_data(vector, values)
        return scaled.ravel()

    def maximum_contact_residual(vector: np.ndarray, values: np.ndarray) -> float:
        return contact_residual_data(vector, values)[2]

    def scaled_maximum_contact_residual(_vector: np.ndarray, values: np.ndarray) -> float:
        pairs = np.asarray(values, dtype=float).reshape((-1, 2))
        return float(np.max(np.linalg.norm(pairs, axis=1), initial=0.0))

    def refinement_failure_context(vector: np.ndarray) -> Mapping[str, object]:
        values = residual(vector)
        _, details, maximum = contact_residual_data(vector, values)
        return {
            "physical_residual_norm": float(np.linalg.norm(values)),
            "maximum_scaled_contact_residual": maximum,
            "contact_residuals": details,
        }

    def consistent_jacobian(vector: np.ndarray) -> np.ndarray:
        """Differentiate the frozen active-slip residual exactly by superposition."""
        response, _, _, _, response_pressures = solve_closed_for(vector)
        size = 2 * len(slip_frictional)
        jacobian = np.eye(size, dtype=float)
        for position, index in enumerate(slip_frictional):
            operator = operators[index]
            pressure = float(response_pressures[index])
            trial = operator.tangential_stiffness * (
                operator.tangential_displacement(response) - slip_references[index]
            )
            norm = float(np.linalg.norm(trial))
            if norm <= tolerance or pressure <= operator.tolerance:
                continue
            direction = trial / norm
            projector = (np.eye(2, dtype=float) - np.outer(direction, direction)) / norm
            trial_sensitivity = operator.tangential_stiffness * np.vstack(
                tuple(vector_row @ displacement_sensitivity for vector_row in operator.tangential_vectors)
            )
            target_sensitivity = operator.friction_coefficient * (
                np.outer(direction, pressure_sensitivity[index]) + pressure * projector @ trial_sensitivity
            )
            rows = slice(2 * position, 2 * position + 2)
            jacobian[rows, :] -= target_sensitivity
        return jacobian

    def scaled_jacobian(vector: np.ndarray) -> np.ndarray:
        """Differentiate the scaled residual used by the trust-region objective."""
        values = residual(vector)
        physical_jacobian = consistent_jacobian(vector)
        pressures = pressures_for_residual(vector, values)
        return _scale_contact_residual_jacobian(
            physical_jacobian,
            values,
            slip_frictional,
            operators,
            pressures,
            pressure_sensitivity,
        )

    initial = np.asarray(initial_force, dtype=float)
    root_result = root(
        residual,
        initial,
        jac=consistent_jacobian,
        method="hybr",
        options={"xtol": tolerance},
    )
    solution = np.asarray(root_result.x, dtype=float)
    strategy = "active_slip_root"
    evaluations = int(root_result.nfev)
    root_values = residual(solution) if np.all(np.isfinite(solution)) else np.full_like(initial, np.inf)
    residual_norm = float(np.linalg.norm(root_values))
    root_scaled_norm = maximum_contact_residual(solution, root_values) if np.isfinite(residual_norm) else float("inf")
    if not root_result.success or not np.isfinite(residual_norm) or root_scaled_norm > tolerance:
        semismooth_seed = solution if np.all(np.isfinite(solution)) else initial
        try:
            solution, evaluations, residual_norm = _semismooth_newton_solution(
                scaled_residual,
                semismooth_seed,
                tolerance,
                jacobian=scaled_jacobian,
                convergence_measure=scaled_maximum_contact_residual,
                line_search_merit=_l2_residual_merit,
            )
            strategy = "active_slip_consistent_newton"
        except NumericalConvergenceError as semismooth_error:
            solution = _best_residual_seed(
                semismooth_seed,
                semismooth_error.diagnostics or {},
                residual,
                maximum_contact_residual,
            )
            remaining_refinement_iterations = max(
                0,
                30 - int((semismooth_error.diagnostics or {}).get("iterations", 0)),
            )
            solution, evaluations, residual_norm = _globalized_slip_solution(
                residual,
                solution,
                tolerance,
                objective_residual=scaled_residual,
                objective_jacobian=scaled_jacobian,
                refinement_residual=scaled_residual,
                refinement_jacobian=scaled_jacobian,
                refinement_iteration_limit=remaining_refinement_iterations,
                convergence_measure=maximum_contact_residual,
                refinement_convergence_measure=scaled_maximum_contact_residual,
                refinement_line_search_merit=_l2_residual_merit,
                diagnostic_context=refinement_failure_context,
            )
            strategy = "active_slip_least_squares"
    final_values = residual(solution)
    residual_norm = float(np.linalg.norm(final_values))
    _, contact_residuals, max_scaled_contact_residual = contact_residual_data(
        solution, final_values
    )
    if not np.isfinite(residual_norm) or max_scaled_contact_residual > tolerance:
        worst_contact = max(
            contact_residuals,
            key=lambda row: float(cast(float, row["scaled_residual_norm"])),
        )
        raise NumericalConvergenceError(
            "Active-slip root failed the per-contact Coulomb residual gate.",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
            diagnostics={
                "cause": "ACTIVE_SLIP_CONTACT_RESIDUAL_EXCEEDED",
                "active_contacts": list(active),
                "slip_contacts": list(slip_frictional),
                "strategy": strategy,
                "root_success": bool(root_result.success),
                "residual_norm": residual_norm,
                "max_scaled_contact_residual": max_scaled_contact_residual,
                "tolerance": tolerance,
                "worst_contact": worst_contact,
                "contact_residuals": contact_residuals,
            },
        )
    displacement, multipliers, reduction, gaps, pressures = solve_closed_for(solution)
    forces: np.ndarray = np.zeros((len(operators), 2), dtype=float)
    forces[list(slip_frictional)] = solution.reshape(len(slip_frictional), 2)
    for index in stick_frictional:
        forces[index] = operators[index].tangential_stiffness * (
            operators[index].tangential_displacement(displacement) - slip_references[index]
        )
    states = tuple(
        "slip"
        if index in slip_frictional
        else (
            "stick"
            if index in stick_frictional
            else ("frictionless" if not operators[index].has_friction else "open")
        )
        for index in range(len(operators))
    )
    tangential_displacements = np.asarray(
        [operator.tangential_displacement(displacement) for operator in operators], dtype=float
    )
    references = np.asarray(slip_references, dtype=float).copy()
    for index in slip_frictional:
        references[index] = tangential_displacements[index] - forces[index] / operators[index].tangential_stiffness
    max_complementarity = float(np.max(np.abs(gaps * pressures), initial=0.0))
    history = [
        {
            "iteration": evaluations,
            "strategy": strategy,
            "active_contacts": list(active),
            "proposed_contacts": list(active),
            "tangential_states": list(states),
            "closed_frictional_contacts": list(closed_frictional),
            "stick_frictional_contacts": list(stick_frictional),
            "slip_frictional_contacts": list(slip_frictional),
            "open_frictional_contacts": list(open_frictional),
            "tangential_unknown_dimension": 2 * len(slip_frictional),
            "observed_tangential_states": (
                list(observed_tangential_states) if observed_tangential_states is not None else None
            ),
            "min_gap": float(np.min(gaps, initial=0.0)),
            "min_pressure": float(np.min(pressures, initial=0.0)),
            "tangential_force_change": residual_norm,
            "max_scaled_contact_residual": max_scaled_contact_residual,
            "slip_reference_change": float(np.linalg.norm(references - slip_references)),
            "max_complementarity": max_complementarity,
        }
    ]
    return ActiveSlipSolution(
        displacement,
        multipliers,
        reduction,
        gaps,
        pressures,
        active,
        states,
        forces,
        tangential_displacements,
        references,
        history,
        closed_frictional,
        open_frictional,
        stick_frictional,
        slip_frictional,
        max_complementarity,
    )


def _validate_post_root_state(
    solution: ActiveSlipSolution,
    operators: list[Any],
    active: tuple[int, ...],
    slip_references: np.ndarray,
    *,
    tolerance: float,
    expected_tangential_states: tuple[str, ...] | None,
) -> None:
    """Fail closed unless the root result is a finite, complementary mixed state."""
    if not (
        np.all(np.isfinite(solution.displacement))
        and np.all(np.isfinite(solution.gaps))
        and np.all(np.isfinite(solution.pressures))
        and np.all(np.isfinite(solution.forces))
        and np.all(np.isfinite(solution.references))
    ):
        raise NumericalConvergenceError(
            "Active-slip post-root state is non-finite.",
            reason=NonlinearFailureReason.NAN_DETECTED,
            diagnostics={"cause": "POST_ROOT_STATE_NONFINITE", "active_contacts": list(active)},
        )
    max_scaled_complementarity = 0.0
    for index, operator in enumerate(operators):
        gap = float(solution.gaps[index])
        pressure = float(solution.pressures[index])
        max_scaled_complementarity = max(
            max_scaled_complementarity,
            abs(gap * pressure) / max(abs(pressure), 1.0),
        )
        if index in active:
            if abs(gap) > operator.tolerance or pressure < -operator.tolerance:
                raise NumericalConvergenceError(
                    "Active-slip post-root normal complementarity check failed.",
                    reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                    diagnostics={
                        "cause": "POST_ROOT_COMPLEMENTARITY_FAILURE",
                        "active_contacts": list(active),
                        "contact": index,
                        "gap": gap,
                        "pressure": pressure,
                    },
                )
        elif gap < -operator.tolerance or abs(float(np.linalg.norm(solution.forces[index]))) > operator.tolerance:
            raise NumericalConvergenceError(
                "Active-slip open-contact state is not admissible.",
                reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                diagnostics={
                    "cause": "OPEN_CONTACT_STATE_INVALID",
                    "active_contacts": list(active),
                    "contact": index,
                    "gap": gap,
                    "tangential_force": solution.forces[index].tolist(),
                },
            )
        if operator.has_friction and (index not in active or pressure <= operator.tolerance):
            force_norm = float(np.linalg.norm(solution.forces[index]))
            state_tolerance = max(operator.tolerance, tolerance)
            if (
                solution.states[index] != "open"
                or force_norm > state_tolerance
                or not np.array_equal(solution.references[index], slip_references[index])
            ):
                raise NumericalConvergenceError(
                    "Tangentially open frictional contact changed state unexpectedly.",
                    reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                    diagnostics={
                        "cause": "OPEN_CONTACT_STATE_INVALID",
                        "contact": index,
                        "active_normal_constraint": index in active,
                        "normal_pressure": pressure,
                        "tangential_force_norm": force_norm,
                    },
                )
            continue
        if operator.has_friction and index in active:
            state = solution.states[index]
            pressure_limit = operator.friction_coefficient * max(pressure, 0.0)
            tangential_force = np.asarray(solution.forces[index], dtype=float)
            trial = operator.tangential_stiffness * (
                operator.tangential_displacement(solution.displacement) - slip_references[index]
            )
            trial_norm = float(np.linalg.norm(trial))
            force_norm = float(np.linalg.norm(tangential_force))
            if expected_tangential_states is not None and state != expected_tangential_states[index]:
                raise NumericalConvergenceError(
                    "Active-slip hybrid root changed the observed tangential state.",
                    reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                    diagnostics={
                        "cause": "TANGENTIAL_STATE_CHANGED",
                        "contact": index,
                        "observed_state": expected_tangential_states[index],
                        "root_state": state,
                        "normal_pressure": pressure,
                        "active_normal_constraint": index in active,
                        "tangential_force_norm": force_norm,
                        "friction_limit": pressure_limit,
                        "trial_norm": trial_norm,
                        "gap": gap,
                    },
                )
            if state == "stick":
                if force_norm > pressure_limit + max(operator.tolerance, tolerance):
                    raise NumericalConvergenceError(
                        "Active-slip hybrid stick contact left the Coulomb cone.",
                        reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                        diagnostics={
                            "cause": "STICK_CONE_ADMISSIBILITY_FAILURE",
                            "contact": index,
                            "tangential_force_norm": force_norm,
                            "friction_limit": pressure_limit,
                        },
                    )
            elif state == "slip":
                if trial_norm <= max(operator.tolerance, tolerance):
                    raise NumericalConvergenceError(
                        "Active-slip hybrid slip direction is undefined.",
                        reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                        diagnostics={"cause": "SLIP_DIRECTION_INVALID", "contact": index},
                    )
                if pressure <= 0.0:
                    # At zero compression the Coulomb disk collapses to the
                    # origin. Sliding can still update its reference, but has
                    # no nonzero direction/traction to align with.
                    admissibility_error = force_norm
                    target: np.ndarray = np.zeros(2, dtype=float)
                else:
                    target = pressure_limit * trial / trial_norm
                    admissibility_error = float(np.linalg.norm(tangential_force - target))
                if admissibility_error > tolerance * max(pressure_limit, 1.0):
                    raise NumericalConvergenceError(
                        "Active-slip hybrid slip cone/alignment check failed.",
                        reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                        diagnostics={
                            "cause": "SLIP_CONE_ALIGNMENT_FAILURE",
                            "contact": index,
                            "admissibility_error": admissibility_error,
                            "friction_limit": pressure_limit,
                            "normal_pressure": pressure,
                            "tolerance": tolerance,
                            "admissibility_limit": tolerance * max(pressure_limit, 1.0),
                            "trial_vector": trial.tolist(),
                            "trial_norm": trial_norm,
                            "tangential_force_vector": tangential_force.tolist(),
                            "target_tangential_force": target.tolist(),
                            "tangential_basis": [
                                np.asarray(direction, dtype=float).tolist()
                                for direction in operator.tangential_vectors
                            ],
                            "active_contacts": list(active),
                            "active_set_iteration": (
                                int(cast(int, solution.history[-1].get("iteration", 0)))
                                if solution.history
                                else 0
                            ),
                        },
                    )
    tolerance = max((float(operator.tolerance) for operator in operators), default=0.0)
    if max_scaled_complementarity > tolerance:
        raise NumericalConvergenceError(
            "Active-slip post-root complementarity scaling check failed.",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
            diagnostics={
                "cause": "POST_ROOT_COMPLEMENTARITY_FAILURE",
                "active_contacts": list(active),
                "max_scaled_complementarity": max_scaled_complementarity,
            },
        )


def _semismooth_newton_solution(
    residual: Callable[[np.ndarray], np.ndarray],
    initial: np.ndarray,
    tolerance: float,
    *,
    jacobian: Callable[[np.ndarray], np.ndarray] | None = None,
    convergence_measure: Callable[[np.ndarray, np.ndarray], float] | None = None,
    line_search_merit: Callable[[np.ndarray, np.ndarray], float] | None = None,
    max_iterations: int = 30,
) -> tuple[np.ndarray, int, float]:
    """Apply a safeguarded Newton step to the frozen active-slip equations.

    The contact status and the slip direction branch are fixed by the outer
    active-set loop. On that branch, the caller can provide a consistent
    algorithmic Jacobian. A forward-difference generalized Jacobian remains a
    deterministic fallback. The convergence gate can remain a strict
    per-contact maximum while Armijo uses a smooth merit matching the residual
    and Jacobian used to compute the Newton direction.
    """
    vector = np.asarray(initial, dtype=float).copy()
    evaluations = 0
    for iteration in range(max_iterations):
        values = np.asarray(residual(vector), dtype=float)
        evaluations += 1
        norm = float(np.linalg.norm(values)) if np.all(np.isfinite(values)) else float("inf")
        measure = (
            float(convergence_measure(vector, values))
            if convergence_measure is not None and np.isfinite(norm)
            else norm
        )
        merit = (
            float(line_search_merit(vector, values))
            if line_search_merit is not None and np.isfinite(norm)
            else measure
        )
        limit = tolerance if convergence_measure is not None else tolerance * max(float(np.linalg.norm(vector)), 1.0)
        if measure <= limit:
            return vector, evaluations, norm
        if not np.isfinite(norm) or not np.isfinite(measure) or not np.isfinite(merit):
            raise NumericalConvergenceError(
                "Active-slip semi-smooth Newton encountered a non-finite residual.",
                diagnostics={
                    "cause": "SEMISMOOTH_NONFINITE_RESIDUAL",
                    "iterations": iteration + 1,
                    "last_candidate": vector.tolist(),
                },
            )

        if jacobian is None:
            matrix, jacobian_evaluations = _residual_jacobian(residual, vector, values)
        else:
            matrix = np.asarray(jacobian(vector), dtype=float)
            jacobian_evaluations = 1
            if matrix.shape != (len(vector), len(vector)) or not np.all(np.isfinite(matrix)):
                raise NumericalConvergenceError(
                    "Active-slip consistent Jacobian is invalid.",
                    diagnostics={
                        "cause": "SEMISMOOTH_INVALID_JACOBIAN",
                        "iterations": iteration + 1,
                        "last_candidate": vector.tolist(),
                    },
                )
        evaluations += jacobian_evaluations
        try:
            step = np.linalg.solve(matrix, -values)
        except np.linalg.LinAlgError as error:
            raise NumericalConvergenceError(
                "Active-slip semi-smooth Newton Jacobian is singular.",
                diagnostics={
                    "cause": "SEMISMOOTH_SINGULAR_JACOBIAN",
                    "iterations": iteration + 1,
                    "last_candidate": vector.tolist(),
                },
            ) from error
        if not np.all(np.isfinite(step)):
            raise NumericalConvergenceError(
                "Active-slip semi-smooth Newton produced a non-finite step.",
                diagnostics={
                    "cause": "SEMISMOOTH_NONFINITE_STEP",
                    "iterations": iteration + 1,
                    "last_candidate": vector.tolist(),
                },
            )

        accepted = False
        scale = 1.0
        for _ in range(12):
            candidate = vector + scale * step
            candidate_values = np.asarray(residual(candidate), dtype=float)
            evaluations += 1
            candidate_norm = (
                float(np.linalg.norm(candidate_values)) if np.all(np.isfinite(candidate_values)) else float("inf")
            )
            candidate_measure = (
                float(convergence_measure(candidate, candidate_values))
                if convergence_measure is not None and np.isfinite(candidate_norm)
                else candidate_norm
            )
            candidate_merit = (
                float(line_search_merit(candidate, candidate_values))
                if line_search_merit is not None and np.isfinite(candidate_norm)
                else candidate_measure
            )
            if np.isfinite(candidate_merit) and candidate_merit <= (1.0 - 1.0e-4 * scale) * merit:
                vector = candidate
                accepted = True
                break
            scale *= 0.5
        if not accepted:
            raise NumericalConvergenceError(
                "Active-slip semi-smooth Newton line search could not reduce the residual.",
                diagnostics={
                    "cause": "SEMISMOOTH_LINE_SEARCH_FAILED",
                    "iterations": iteration + 1,
                    "last_candidate": vector.tolist(),
                    "last_convergence_measure": measure,
                    "last_line_search_merit": merit,
                    "evaluations": evaluations,
                },
            )
    raise NumericalConvergenceError(
        "Active-slip semi-smooth Newton reached its iteration limit.",
        diagnostics={
            "cause": "SEMISMOOTH_ITERATION_LIMIT",
            "iterations": max_iterations,
            "last_candidate": vector.tolist(),
        },
    )


def _residual_jacobian(
    residual: Callable[[np.ndarray], np.ndarray],
    vector: np.ndarray,
    values: np.ndarray,
) -> tuple[np.ndarray, int]:
    """Build a deterministic forward-difference generalized Jacobian."""
    size = len(vector)
    jacobian: np.ndarray = np.empty((size, size), dtype=float)
    step_scale = float(np.sqrt(np.finfo(float).eps))
    for column in range(size):
        step = step_scale * max(abs(float(vector[column])), 1.0)
        perturbed = vector.copy()
        perturbed[column] += step
        delta = np.asarray(residual(perturbed), dtype=float) - values
        if not np.all(np.isfinite(delta)):
            raise NumericalConvergenceError("Active-slip semi-smooth Newton Jacobian is non-finite.")
        jacobian[:, column] = delta / step
    return jacobian, size


def _active_slip_response_sensitivities(
    solve_for: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray, ConstraintReduction, np.ndarray, np.ndarray]],
    zero_force: np.ndarray,
    displacement: np.ndarray,
    pressures: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Return exact unit-force responses of the frozen linear contact system.

    With fixed active normal constraints the saddle system is linear in the
    tangential contact forces. Solving once per unit component is therefore a
    superposition derivative, not a finite-difference approximation.
    """
    columns = len(zero_force)
    displacement_sensitivity: np.ndarray = np.empty((len(displacement), columns), dtype=float)
    pressure_sensitivity: np.ndarray = np.empty((len(pressures), columns), dtype=float)
    for column in range(columns):
        unit_force = zero_force.copy()
        unit_force[column] = 1.0
        response, _, _, _, response_pressures = solve_for(unit_force)
        displacement_sensitivity[:, column] = response - displacement
        pressure_sensitivity[:, column] = response_pressures - pressures
    return displacement_sensitivity, pressure_sensitivity


def _globalized_slip_solution(
    residual: Callable[[np.ndarray], np.ndarray],
    initial: np.ndarray,
    tolerance: float,
    *,
    objective_residual: Callable[[np.ndarray], np.ndarray] | None = None,
    objective_jacobian: Callable[[np.ndarray], np.ndarray] | None = None,
    refinement_residual: Callable[[np.ndarray], np.ndarray] | None = None,
    refinement_jacobian: Callable[[np.ndarray], np.ndarray] | None = None,
    refinement_iteration_limit: int = 30,
    convergence_measure: Callable[[np.ndarray, np.ndarray], float] | None = None,
    refinement_convergence_measure: Callable[[np.ndarray, np.ndarray], float] | None = None,
    refinement_line_search_merit: Callable[[np.ndarray, np.ndarray], float] | None = None,
    diagnostic_context: Callable[[np.ndarray], Mapping[str, object]] | None = None,
) -> tuple[np.ndarray, int, float]:
    """Use a trust-region least-squares step when a raw root iteration fails.

    Coulomb return mapping is non-smooth at the stick/slip boundary.  The
    residual is still the exact active-slip equation, but SciPy's reflective
    trust-region globalization can reduce it even when the local hybrid
    Newton approximation is poorly scaled by structural compliance.
    """
    # Optimizer termination is not the physical contact-equation acceptance
    # gate checked below. In particular, an ``xtol`` stop at the physical
    # tolerance can happen while individual contact equations remain outside
    # that gate. Ask the optimizer to continue beyond the physical tolerance,
    # down to a conservative floating-point floor, without changing acceptance.
    optimizer_tolerance = max(
        32.0 * np.finfo(float).eps,
        min(float(tolerance) * 1.0e-3, 1.0e-12),
    )
    result = least_squares(
        objective_residual or residual,
        initial,
        method="trf",
        jac=objective_jacobian or "2-point",
        xtol=optimizer_tolerance,
        ftol=optimizer_tolerance,
        gtol=optimizer_tolerance,
        max_nfev=500,
        x_scale="jac",
    )
    solution = np.asarray(result.x, dtype=float)
    finite_solution = bool(np.all(np.isfinite(solution)))
    residual_values = np.asarray(residual(solution), dtype=float) if finite_solution else np.asarray([float("inf")])
    residual_norm = float(np.linalg.norm(residual_values))
    if convergence_measure is None:
        converged = residual_norm <= tolerance * max(float(np.linalg.norm(solution)), 1.0)
        scaled_measure: float | None = None
    else:
        scaled_measure = (
            float(convergence_measure(solution, residual_values)) if finite_solution else float("inf")
        )
        converged = np.isfinite(scaled_measure) and scaled_measure <= tolerance
    refinement_error: str | None = None
    refinement_evaluations = 0
    if (
        finite_solution
        and np.isfinite(residual_norm)
        and not converged
        and refinement_iteration_limit > 0
    ):
        try:
            solution, refinement_evaluations, _ = _semismooth_newton_solution(
                refinement_residual or residual,
                solution,
                tolerance,
                jacobian=refinement_jacobian,
                convergence_measure=refinement_convergence_measure or convergence_measure,
                line_search_merit=refinement_line_search_merit,
                max_iterations=refinement_iteration_limit,
            )
            residual_values = np.asarray(residual(solution), dtype=float)
            residual_norm = float(np.linalg.norm(residual_values))
            if convergence_measure is None:
                scaled_measure = None
                converged = residual_norm <= tolerance * max(float(np.linalg.norm(solution)), 1.0)
            else:
                scaled_measure = float(convergence_measure(solution, residual_values))
                converged = np.isfinite(scaled_measure) and scaled_measure <= tolerance
        except NumericalConvergenceError as error:
            refinement_error = str(error)
            refinement_evaluations = int((error.diagnostics or {}).get("evaluations", 0))

    if not result.success or not np.isfinite(residual_norm) or not converged:
        context = dict(diagnostic_context(solution)) if diagnostic_context is not None and finite_solution else {}
        optimizer_gradient = getattr(result, "grad", None)
        optimizer_gradient_array = (
            np.asarray(optimizer_gradient, dtype=float)
            if optimizer_gradient is not None
            else np.asarray([], dtype=float)
        )
        optimizer_gradient_inf_norm = (
            float(np.linalg.norm(optimizer_gradient_array, ord=np.inf))
            if optimizer_gradient_array.size and np.all(np.isfinite(optimizer_gradient_array))
            else None
        )
        optimizer_cost_raw = getattr(result, "cost", None)
        optimizer_cost = (
            float(optimizer_cost_raw)
            if optimizer_cost_raw is not None and np.isfinite(optimizer_cost_raw)
            else None
        )
        optimizer_optimality_raw = getattr(result, "optimality", None)
        optimizer_optimality = (
            float(optimizer_optimality_raw)
            if optimizer_optimality_raw is not None and np.isfinite(optimizer_optimality_raw)
            else None
        )
        raise NumericalConvergenceError(
            "Active-slip globalized least-squares fallback failed: "
            f"{result.message}; residual={residual_norm:.3e}.",
            diagnostics={
                "cause": "GLOBALIZED_SLIP_RESIDUAL_NOT_CONVERGED",
                "residual_norm": residual_norm,
                "scaled_contact_residual": scaled_measure,
                "tolerance": tolerance,
                "optimizer_status": int(result.status),
                "optimizer_message": str(result.message),
                "optimizer_nfev": int(result.nfev),
                "optimizer_success": bool(result.success),
                "optimizer_xtol": optimizer_tolerance,
                "optimizer_ftol": optimizer_tolerance,
                "optimizer_gtol": optimizer_tolerance,
                "optimizer_cost": optimizer_cost,
                "optimizer_optimality": optimizer_optimality,
                "optimizer_gradient_inf_norm": optimizer_gradient_inf_norm,
                "refinement_evaluations": refinement_evaluations,
                "refinement_error": refinement_error,
                "refinement_iteration_limit": refinement_iteration_limit,
                **context,
            },
        )
    return solution, int(result.nfev) + refinement_evaluations, residual_norm


def _normal_active_set(
    dofs: DofManager,
    stiffness: csr_matrix,
    loads: np.ndarray,
    fixed: np.ndarray,
    operators: list[Any],
    solve_active_set: SolveActiveSet,
    pressures_for: Pressures,
    proposed_active: ProposedActive,
    *,
    trace: ContactTrace | None = None,
) -> tuple[int, ...]:
    """Find a stable normal active set before solving the slip unknowns."""
    reduction = ConstraintReduction.from_system(dofs, stiffness, loads, [], fixed)
    active: tuple[int, ...] = ()
    visited: set[tuple[int, ...]] = {active}
    for iteration in range(1, _ACTIVE_SET_ITERATION_LIMIT + 1):
        displacement, multipliers = solve_active_set(reduction, operators, active)
        gaps = np.asarray([operator.gap(displacement) for operator in operators])
        pressures = pressures_for(active, multipliers, len(operators))
        proposed = proposed_active(operators, active, gaps, pressures)
        transition_cause = "ACTIVE_SET_STABLE" if proposed == active else "ACTIVE_SET_UPDATE"
        if proposed != active:
            next_active, transition_cause = _select_active_set_transition(active, proposed, visited)
        else:
            next_active = active
        if trace is not None:
            trace(
                "normal_active_set",
                {
                    "iteration": iteration,
                    "active_contacts": list(active),
                    "proposed_contacts": list(proposed),
                    "next_active_contacts": list(next_active),
                    "min_gap": float(np.min(gaps, initial=0.0)),
                    "min_pressure": float(np.min(pressures, initial=0.0)),
                    "convergence_cause": transition_cause,
                },
            )
        if proposed == active:
            return active
        active = next_active
        visited.add(active)
    raise NumericalConvergenceError(
        "Normal contact set did not converge before the active-slip fallback.",
        diagnostics={
            "strategy": "active_slip_root_normal_active_set",
        "iteration": _ACTIVE_SET_ITERATION_LIMIT,
            "active_contacts": list(active),
            "cause": "ACTIVE_SET_MAX_ITERATIONS",
            "visited_active_sets": len(visited),
        },
    )
