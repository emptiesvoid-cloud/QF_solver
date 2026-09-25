"""Nonlinear fallbacks for coupled normal contact and regularized Coulomb slip."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

import numpy as np
from scipy.optimize import least_squares, root
from scipy.sparse import csr_matrix

from solveur.core.constraints import ConstraintReduction
from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.contact.support import _select_active_set_transition


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
            observed_tangential_states=observed_tangential_states,
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
            continue

        _validate_post_root_state(
            solution,
            operators,
            active,
            slip_references,
            tolerance=tolerance,
            expected_tangential_states=observed_tangential_states,
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
    frozen-mode active-slip root have failed.  For each deterministic normal
    active-set candidate, the nonlinear unknown includes both tangential force
    components of every active frictional contact.  Projection onto the
    pressure-dependent Coulomb disk selects stick or slip from the current
    trial displacement; mode labels are not inherited from a stale iterate.

    The exhaustive normal-set search is deliberately capped.  Larger contact
    systems keep the existing fail-closed outcome rather than paying an
    exponential search cost or accepting an uncertified set.
    """
    contact_count = len(operators)
    if contact_count > maximum_enumerated_contacts:
        raise NumericalConvergenceError(
            "Coupled frictional contact search exceeds its deterministic contact-count limit.",
            reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
            diagnostics={
                "strategy": "coupled_contact_projection",
                "cause": "COUPLED_SEARCH_CONTACT_LIMIT_EXCEEDED",
                "contact_count": contact_count,
                "maximum_enumerated_contacts": maximum_enumerated_contacts,
            },
        )

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

    candidates = [
        tuple(index for index in range(contact_count) if mask & (1 << index))
        for mask in range(1 << contact_count)
    ]
    seed = set(seed_active)
    candidates.sort(key=lambda candidate: (len(set(candidate) ^ seed), candidate))
    rejected: list[dict[str, object]] = []

    for candidate_index, active in enumerate(candidates, start=1):
        try:
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
            _validate_post_root_state(
                solution,
                operators,
                active,
                slip_references,
                tolerance=tolerance,
                expected_tangential_states=None,
            )
        except NumericalConvergenceError as error:
            rejected.append(
                {
                    "active_contacts": list(active),
                    "error": str(error),
                    "diagnostics": dict(error.diagnostics or {}),
                }
            )
            if trace is not None:
                trace(
                    "coupled_contact_candidate_rejected",
                    {
                        "candidate_index": candidate_index,
                        "candidate_count": len(candidates),
                        "active_contacts": list(active),
                        "cause": str((error.diagnostics or {}).get("cause", "CANDIDATE_INVALID")),
                    },
                )
            continue

        if trace is not None:
            trace(
                "coupled_contact_candidate_accepted",
                {
                    "candidate_index": candidate_index,
                    "candidate_count": len(candidates),
                    "active_contacts": list(active),
                    "states": list(solution.states),
                    "closed_frictional_contacts": list(solution.closed_frictional_contacts),
                    "stick_frictional_contacts": list(solution.stick_frictional_contacts),
                    "slip_frictional_contacts": list(solution.slip_frictional_contacts),
                    "max_complementarity": solution.max_complementarity,
                },
            )
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

    def residual(vector: np.ndarray) -> np.ndarray:
        displacement, _, _, _, pressures, _ = solve_for(vector)
        forces = np.asarray(vector, dtype=float).reshape(len(frictional), 2)
        target = projected_trial(displacement, pressures)[list(frictional)]
        return (forces - target).ravel()

    zero: np.ndarray = np.zeros(vector_size, dtype=float)
    displacement, _, _, _, pressures, _ = solve_for(zero)
    initial = projected_trial(displacement, pressures)[list(frictional)].ravel()
    if vector_size:
        root_result = root(residual, initial, method="hybr", options={"xtol": tolerance})
        vector = np.asarray(root_result.x, dtype=float)
        strategy = "coupled_coulomb_projection_root"
        evaluations = int(root_result.nfev)
        residual_norm = float(np.linalg.norm(residual(vector))) if np.all(np.isfinite(vector)) else float("inf")
        residual_limit = tolerance * max(float(np.linalg.norm(vector)), 1.0)
        if not root_result.success or not np.isfinite(residual_norm) or residual_norm > residual_limit:
            try:
                vector, evaluations, residual_norm = _semismooth_newton_solution(
                    residual, initial, tolerance
                )
                strategy = "coupled_coulomb_projection_semismooth_newton"
            except NumericalConvergenceError:
                vector, evaluations, residual_norm = _globalized_slip_solution(
                    residual, initial, tolerance
                )
                strategy = "coupled_coulomb_projection_least_squares"
        residual_limit = tolerance * max(float(np.linalg.norm(vector)), 1.0)
        if not np.isfinite(residual_norm) or residual_norm > residual_limit:
            raise NumericalConvergenceError(
                "Coupled Coulomb projection residual exceeds its frozen tolerance.",
                reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                diagnostics={
                    "cause": "COUPLED_TANGENTIAL_RESIDUAL_TOO_LARGE",
                    "active_contacts": list(active),
                    "residual_norm": residual_norm,
                    "residual_limit": residual_limit,
                },
            )
    else:
        vector = zero
        strategy = "coupled_coulomb_projection_no_frictional_contacts"
        evaluations = 1
        residual_norm = 0.0

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
        if float(pressures[index]) > operator.tolerance:
            closed.append(index)
        trial = operator.tangential_stiffness * (tangential_displacements[index] - slip_references[index])
        trial_norm = float(np.linalg.norm(trial))
        limit = operator.friction_coefficient * max(float(pressures[index]), 0.0)
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
                "max_complementarity": max_complementarity,
            }
        ],
        tuple(closed),
        tuple(opened),
        tuple(stick),
        tuple(slip),
        max_complementarity,
    )
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
        if operators[index].has_friction and float(probe_pressures[index]) > operators[index].tolerance
    )
    open_frictional = tuple(
        index for index, operator in enumerate(operators) if operator.has_friction and index not in active
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

    def solve_closed_for(
        vector: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, ConstraintReduction, np.ndarray, np.ndarray]:
        forces: np.ndarray = np.zeros((len(operators), 2), dtype=float)
        forces[list(slip_frictional)] = vector.reshape(len(slip_frictional), 2)
        effective_stiffness = stiffness
        effective_loads = np.asarray(loads, dtype=float).copy()
        for index in stick_frictional:
            operator = operators[index]
            for component, direction in enumerate(operator.tangential_vectors):
                effective_stiffness = effective_stiffness + csr_matrix(
                    operator.tangential_stiffness * np.outer(direction, direction)
                )
                effective_loads += operator.tangential_stiffness * slip_references[index, component] * direction
        for index in slip_frictional:
            operator = operators[index]
            for component, direction in enumerate(operator.tangential_vectors):
                effective_loads -= forces[index, component] * direction
        reduction = ConstraintReduction.from_system(
            dofs,
            effective_stiffness,
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
        if norm <= tolerance:
            raise NumericalConvergenceError("Active-slip fallback found an undefined tangential direction.")
        initial_force.extend((operator.friction_coefficient * pressures[index] * trial / norm).tolist())

    def residual(vector: np.ndarray) -> np.ndarray:
        response, _, _, _, response_pressures = solve_closed_for(vector)
        values: list[float] = []
        for position, index in enumerate(slip_frictional):
            operator = operators[index]
            trial = operator.tangential_stiffness * (
                operator.tangential_displacement(response) - slip_references[index]
            )
            norm = float(np.linalg.norm(trial))
            if norm <= tolerance or response_pressures[index] <= 0.0:
                return np.full(2 * len(slip_frictional), 1.0e12, dtype=float)
            target = operator.friction_coefficient * response_pressures[index] * trial / norm
            values.extend((vector[2 * position: 2 * position + 2] - target).tolist())
        return np.asarray(values, dtype=float)

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
            if norm <= tolerance or pressure <= 0.0:
                raise NumericalConvergenceError("Active-slip consistent tangent is undefined at the stick/slip boundary.")
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

    initial = np.asarray(initial_force, dtype=float)
    root_result = root(residual, initial, method="hybr", options={"xtol": tolerance})
    solution = np.asarray(root_result.x, dtype=float)
    strategy = "active_slip_root"
    evaluations = int(root_result.nfev)
    residual_norm = float(np.linalg.norm(residual(solution))) if np.all(np.isfinite(solution)) else float("inf")
    residual_limit = tolerance * max(float(np.linalg.norm(solution)), 1.0)
    if not root_result.success or not np.isfinite(residual_norm) or residual_norm > residual_limit:
        try:
            solution, evaluations, residual_norm = _semismooth_newton_solution(
                residual,
                initial,
                tolerance,
                jacobian=consistent_jacobian,
            )
            strategy = "active_slip_consistent_newton"
        except NumericalConvergenceError:
            solution, evaluations, residual_norm = _globalized_slip_solution(
                residual,
                initial,
                tolerance,
            )
            strategy = "active_slip_least_squares"
    residual_limit = tolerance * max(float(np.linalg.norm(solution)), 1.0)
    if residual_norm > residual_limit:
        raise NumericalConvergenceError(f"Active-slip root residual is too large: {residual_norm:.3e}.")
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
            else ("frictionless" if index in active else "open")
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
        if operator.has_friction and index not in active:
            if solution.states[index] != "open" or not np.array_equal(solution.references[index], slip_references[index]):
                raise NumericalConvergenceError(
                    "Active-slip open frictional contact changed state unexpectedly.",
                    reason=NonlinearFailureReason.CONTACT_UPDATE_FAILURE,
                    diagnostics={"cause": "OPEN_CONTACT_STATE_INVALID", "contact": index},
                )
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
) -> tuple[np.ndarray, int, float]:
    """Apply a safeguarded Newton step to the frozen active-slip equations.

    The contact status and the slip direction branch are fixed by the outer
    active-set loop. On that branch, the caller can provide a consistent
    algorithmic Jacobian. A forward-difference generalized Jacobian remains a
    deterministic fallback. Armijo backtracking rejects a step that would
    increase the residual.
    """
    vector = np.asarray(initial, dtype=float).copy()
    evaluations = 0
    for _ in range(30):
        values = np.asarray(residual(vector), dtype=float)
        evaluations += 1
        norm = float(np.linalg.norm(values)) if np.all(np.isfinite(values)) else float("inf")
        limit = tolerance * max(float(np.linalg.norm(vector)), 1.0)
        if norm <= limit:
            return vector, evaluations, norm
        if not np.isfinite(norm):
            raise NumericalConvergenceError("Active-slip semi-smooth Newton encountered a non-finite residual.")

        if jacobian is None:
            matrix, jacobian_evaluations = _residual_jacobian(residual, vector, values)
        else:
            matrix = np.asarray(jacobian(vector), dtype=float)
            jacobian_evaluations = 1
            if matrix.shape != (len(vector), len(vector)) or not np.all(np.isfinite(matrix)):
                raise NumericalConvergenceError("Active-slip consistent Jacobian is invalid.")
        evaluations += jacobian_evaluations
        try:
            step = np.linalg.solve(matrix, -values)
        except np.linalg.LinAlgError as error:
            raise NumericalConvergenceError("Active-slip semi-smooth Newton Jacobian is singular.") from error
        if not np.all(np.isfinite(step)):
            raise NumericalConvergenceError("Active-slip semi-smooth Newton produced a non-finite step.")

        accepted = False
        scale = 1.0
        for _ in range(12):
            candidate = vector + scale * step
            candidate_values = np.asarray(residual(candidate), dtype=float)
            evaluations += 1
            candidate_norm = (
                float(np.linalg.norm(candidate_values)) if np.all(np.isfinite(candidate_values)) else float("inf")
            )
            if candidate_norm <= (1.0 - 1.0e-4 * scale) * norm:
                vector = candidate
                accepted = True
                break
            scale *= 0.5
        if not accepted:
            raise NumericalConvergenceError("Active-slip semi-smooth Newton line search could not reduce the residual.")
    raise NumericalConvergenceError("Active-slip semi-smooth Newton reached its iteration limit.")


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
) -> tuple[np.ndarray, int, float]:
    """Use a trust-region least-squares step when a raw root iteration fails.

    Coulomb return mapping is non-smooth at the stick/slip boundary.  The
    residual is still the exact active-slip equation, but SciPy's reflective
    trust-region globalization can reduce it even when the local hybrid
    Newton approximation is poorly scaled by structural compliance.
    """
    result = least_squares(
        residual,
        initial,
        method="trf",
        xtol=tolerance,
        ftol=tolerance,
        gtol=tolerance,
        max_nfev=500,
        x_scale="jac",
    )
    solution = np.asarray(result.x, dtype=float)
    residual_norm = float(np.linalg.norm(residual(solution))) if np.all(np.isfinite(solution)) else float("inf")
    limit = tolerance * max(float(np.linalg.norm(solution)), 1.0)
    if not result.success or not np.isfinite(residual_norm) or residual_norm > limit:
        raise NumericalConvergenceError(
            "Active-slip globalized least-squares fallback failed: "
            f"{result.message}; residual={residual_norm:.3e}."
        )
    return solution, int(result.nfev), residual_norm


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
