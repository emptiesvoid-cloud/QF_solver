"""Internal contact geometry, active-set and friction helpers."""

from __future__ import annotations

from dataclasses import dataclass
import warnings

import numpy as np
from scipy.sparse import bmat, csr_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from solveur.contact.entities import FrictionlessContact
from solveur.core.constraints import ConstraintReduction
from solveur.core.dofs import DofManager
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear_contracts import NonlinearFailureReason


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
