"""Small nonlinear fallback for strongly coupled regularized Coulomb slip."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from scipy.optimize import least_squares, root
from scipy.sparse import csr_matrix

from solveur.core.constraints import ConstraintReduction
from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError


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


SolveActiveSet = Callable[[ConstraintReduction, list[Any], tuple[int, ...]], tuple[np.ndarray, np.ndarray]]
Pressures = Callable[[tuple[int, ...], np.ndarray, int], np.ndarray]
ProposedActive = Callable[[list[Any], tuple[int, ...], np.ndarray, np.ndarray], tuple[int, ...]]
TangentialForce = Callable[[list[Any], np.ndarray, int], np.ndarray]


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
) -> ActiveSlipSolution:
    """Resolve active-slip forces while retaining exact normal constraints.

    The nonlinear unknown is the two tangential components of each closed
    rough contact.  Each residual evaluation solves the sparse normal-contact
    saddle system, so the pressure-dependent Coulomb limit remains coupled to
    the deformable structure.
    """
    active = _normal_active_set(dofs, stiffness, loads, fixed, operators, solve_active_set, pressures_for, proposed_active)
    rough = tuple(index for index in active if operators[index].has_friction)
    if not rough:
        raise NumericalConvergenceError("Active-slip fallback requires one closed frictional contact.")
    if any(index not in active and operator.has_friction for index, operator in enumerate(operators)):
        raise NumericalConvergenceError("Active-slip fallback cannot resolve opening frictional contacts.")

    def solve_for(vector: np.ndarray) -> tuple[np.ndarray, np.ndarray, ConstraintReduction, np.ndarray, np.ndarray]:
        forces: np.ndarray = np.zeros((len(operators), 2), dtype=float)
        forces[list(rough)] = vector.reshape(len(rough), 2)
        reduction = ConstraintReduction.from_system(dofs, stiffness, loads - tangential_force(operators, forces, dofs.ndof), [], fixed)
        displacement, multipliers = solve_active_set(reduction, operators, active)
        gaps = np.asarray([operator.gap(displacement) for operator in operators])
        pressures = pressures_for(active, multipliers, len(operators))
        return displacement, multipliers, reduction, gaps, pressures

    zero_force: np.ndarray = np.zeros(2 * len(rough), dtype=float)
    displacement, _, _, _, pressures = solve_for(zero_force)
    displacement_sensitivity, pressure_sensitivity = _active_slip_response_sensitivities(
        solve_for,
        zero_force,
        displacement,
        pressures,
    )
    initial_force: list[float] = []
    for index in rough:
        operator = operators[index]
        trial = operator.tangential_stiffness * (operator.tangential_displacement(displacement) - slip_references[index])
        norm = float(np.linalg.norm(trial))
        if norm <= tolerance:
            raise NumericalConvergenceError("Active-slip fallback found an undefined tangential direction.")
        initial_force.extend((operator.friction_coefficient * pressures[index] * trial / norm).tolist())

    def residual(vector: np.ndarray) -> np.ndarray:
        response, _, _, _, response_pressures = solve_for(vector)
        values: list[float] = []
        for position, index in enumerate(rough):
            operator = operators[index]
            trial = operator.tangential_stiffness * (operator.tangential_displacement(response) - slip_references[index])
            norm = float(np.linalg.norm(trial))
            if norm <= tolerance or response_pressures[index] <= 0.0:
                return np.full(2 * len(rough), 1.0e12, dtype=float)
            target = operator.friction_coefficient * response_pressures[index] * trial / norm
            values.extend((vector[2 * position: 2 * position + 2] - target).tolist())
        return np.asarray(values, dtype=float)

    def consistent_jacobian(vector: np.ndarray) -> np.ndarray:
        """Differentiate the frozen active-slip residual exactly by superposition."""
        response, _, _, _, response_pressures = solve_for(vector)
        size = 2 * len(rough)
        jacobian = np.eye(size, dtype=float)
        for position, index in enumerate(rough):
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
    displacement, multipliers, reduction, gaps, pressures = solve_for(solution)
    forces: np.ndarray = np.zeros((len(operators), 2), dtype=float)
    forces[list(rough)] = solution.reshape(len(rough), 2)
    states = tuple("slip" if index in rough else ("frictionless" if index in active else "open") for index in range(len(operators)))
    tangential_displacements = np.asarray([operator.tangential_displacement(displacement) for operator in operators], dtype=float)
    references = np.asarray(slip_references, dtype=float).copy()
    for index in rough:
        references[index] = tangential_displacements[index] - forces[index] / operators[index].tangential_stiffness
    history = [{
        "iteration": evaluations, "strategy": strategy, "active_contacts": list(active),
        "proposed_contacts": list(active), "tangential_states": list(states),
        "min_gap": float(np.min(gaps, initial=0.0)), "min_pressure": float(np.min(pressures, initial=0.0)),
        "tangential_force_change": residual_norm, "slip_reference_change": float(np.linalg.norm(references - slip_references)),
    }]
    return ActiveSlipSolution(
        displacement, multipliers, reduction, gaps, pressures, active, states, forces,
        tangential_displacements, references, history,
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
) -> tuple[int, ...]:
    """Find a stable normal active set before solving the slip unknowns."""
    reduction = ConstraintReduction.from_system(dofs, stiffness, loads, [], fixed)
    active: tuple[int, ...] = ()
    for _ in range(25):
        displacement, multipliers = solve_active_set(reduction, operators, active)
        gaps = np.asarray([operator.gap(displacement) for operator in operators])
        pressures = pressures_for(active, multipliers, len(operators))
        proposed = proposed_active(operators, active, gaps, pressures)
        if proposed == active:
            return active
        active = proposed
    raise NumericalConvergenceError("Normal contact set did not converge before the active-slip fallback.")
