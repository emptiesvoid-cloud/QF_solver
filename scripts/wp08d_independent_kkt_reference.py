"""Independent small-system KKT and regularized Coulomb reference.

Only NumPy is used here.  The reference intentionally accepts an already
assembled reduced elastic matrix and explicit contact operators; it does not
import the solver package or any production contact implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass(frozen=True)
class ReferenceContact:
    """One fixed-normal contact operator in a reference reduced system."""

    normal: np.ndarray
    tangent_basis: np.ndarray
    friction_coefficient: float
    tangential_stiffness: float
    normal_target: float = 0.0
    tangential_target: np.ndarray | None = None

    def validate(self, size: int) -> None:
        normal = np.asarray(self.normal, dtype=float)
        basis = np.asarray(self.tangent_basis, dtype=float)
        if normal.shape != (size,) or basis.shape != (2, size):
            raise ValueError("Reference contact operators have incompatible shapes.")
        if not np.all(np.isfinite(normal)) or not np.all(np.isfinite(basis)):
            raise ValueError("Reference contact operators must be finite.")
        if not np.isfinite(self.friction_coefficient) or self.friction_coefficient < 0.0:
            raise ValueError("Reference friction coefficient must be finite and non-negative.")
        if not np.isfinite(self.tangential_stiffness) or self.tangential_stiffness <= 0.0:
            raise ValueError("Reference tangential stiffness must be finite and positive.")
        if self.tangential_target is not None and np.asarray(self.tangential_target, dtype=float).shape != (2,):
            raise ValueError("Reference tangential target must have two components.")


@dataclass(frozen=True)
class KktReferenceProblem:
    """Minimal independent KKT problem definition."""

    stiffness: np.ndarray
    force: np.ndarray
    constraints: np.ndarray
    constraint_values: np.ndarray
    contacts: tuple[ReferenceContact, ...]

    def validate(self) -> None:
        stiffness = np.asarray(self.stiffness, dtype=float)
        force = np.asarray(self.force, dtype=float)
        constraints = np.asarray(self.constraints, dtype=float)
        values = np.asarray(self.constraint_values, dtype=float)
        if stiffness.ndim != 2 or stiffness.shape[0] != stiffness.shape[1]:
            raise ValueError("Reference stiffness must be square.")
        size = stiffness.shape[0]
        if force.shape != (size,) or constraints.ndim != 2 or constraints.shape[1] != size:
            raise ValueError("Reference KKT vectors/matrices have incompatible shapes.")
        if values.shape != (constraints.shape[0],):
            raise ValueError("Reference constraint values have an incompatible shape.")
        if not all(np.all(np.isfinite(np.asarray(value, dtype=float))) for value in (stiffness, force, constraints, values)):
            raise ValueError("Reference KKT data must be finite.")
        if not np.allclose(stiffness, stiffness.T, rtol=0.0, atol=1.0e-12):
            raise ValueError("Reference stiffness must be symmetric.")
        for contact in self.contacts:
            contact.validate(size)


@dataclass(frozen=True)
class ReferenceResult:
    """Independent reference result and contact diagnostics."""

    displacement: np.ndarray
    multipliers: np.ndarray
    contact_states: tuple[str, ...]
    tangential_forces: np.ndarray
    slip_references: np.ndarray
    cumulative_dissipation: float
    iterations: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "PASS",
            "displacement": self.displacement.tolist(),
            "multipliers": self.multipliers.tolist(),
            "contact_states": list(self.contact_states),
            "tangential_forces": self.tangential_forces.tolist(),
            "slip_references": self.slip_references.tolist(),
            "cumulative_local_dissipation": float(self.cumulative_dissipation),
            "iterations": int(self.iterations),
            "reference_implementation": "independent_numpy_kkt_return_map",
        }


def assemble_kkt(
    stiffness: np.ndarray,
    force: np.ndarray,
    constraints: np.ndarray,
    constraint_values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Assemble the saddle system without using a production constraint helper."""

    matrix = np.asarray(stiffness, dtype=float)
    rhs_force = np.asarray(force, dtype=float)
    rows = np.asarray(constraints, dtype=float)
    values = np.asarray(constraint_values, dtype=float)
    if rows.shape[0] == 0:
        return matrix.copy(), rhs_force.copy()
    zeros = np.zeros((rows.shape[0], rows.shape[0]), dtype=float)
    saddle = np.block([[matrix, rows.T], [rows, zeros]])
    return saddle, np.concatenate((rhs_force, values))


def _solve_kkt(
    stiffness: np.ndarray,
    force: np.ndarray,
    constraints: np.ndarray,
    constraint_values: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    saddle, rhs = assemble_kkt(stiffness, force, constraints, constraint_values)
    solution = np.linalg.solve(saddle, rhs)
    if not np.all(np.isfinite(solution)):
        raise FloatingPointError("Independent KKT solve produced a non-finite state.")
    return solution[: stiffness.shape[0]], solution[stiffness.shape[0] :]


def solve_kkt_return_map(
    problem: KktReferenceProblem,
    *,
    max_iterations: int = 64,
    tolerance: float = 1.0e-12,
) -> ReferenceResult:
    """Solve the frozen-normal KKT problem with a local Coulomb return map."""

    problem.validate()
    if max_iterations <= 0 or tolerance <= 0.0:
        raise ValueError("Reference iteration controls must be positive.")
    stiffness = np.asarray(problem.stiffness, dtype=float)
    force = np.asarray(problem.force, dtype=float)
    base_constraints = np.asarray(problem.constraints, dtype=float)
    base_values = np.asarray(problem.constraint_values, dtype=float)
    size = stiffness.shape[0]
    contact_rows = np.vstack([np.asarray(contact.normal, dtype=float) for contact in problem.contacts]) if problem.contacts else np.zeros((0, size))
    contact_values = np.asarray([contact.normal_target for contact in problem.contacts], dtype=float)
    references: np.ndarray = np.zeros((len(problem.contacts), 2), dtype=float)
    for index, contact in enumerate(problem.contacts):
        if contact.tangential_target is not None:
            references[index] = np.asarray(contact.tangential_target, dtype=float)
    forces: np.ndarray = np.zeros((len(problem.contacts), 2), dtype=float)
    states = ["open" for _ in problem.contacts]
    previous_displacement = np.zeros(size, dtype=float)
    multipliers = np.zeros(base_constraints.shape[0] + len(problem.contacts), dtype=float)
    cumulative_dissipation = 0.0

    for iteration in range(1, max_iterations + 1):
        contact_force = np.zeros(size, dtype=float)
        for contact, local_force in zip(problem.contacts, forces):
            contact_force += np.asarray(contact.tangent_basis, dtype=float).T @ local_force
        rows = np.vstack((base_constraints, contact_rows))
        values = np.concatenate((base_values, contact_values))
        displacement, next_multipliers = _solve_kkt(stiffness, force - contact_force, rows, values)
        normal_multipliers = next_multipliers[-len(problem.contacts) :] if problem.contacts else np.zeros(0)
        next_forces = np.zeros_like(forces)
        next_references = references.copy()
        next_states: list[str] = []
        for index, contact in enumerate(problem.contacts):
            basis = np.asarray(contact.tangent_basis, dtype=float)
            relative = basis @ displacement
            trial = contact.tangential_stiffness * (relative - references[index])
            trial_norm = float(np.linalg.norm(trial))
            pressure = max(-float(normal_multipliers[index]), 0.0)
            limit = contact.friction_coefficient * pressure
            remains_sliding = states[index] == "slip" and trial_norm >= limit - tolerance
            if trial_norm <= limit + tolerance and not remains_sliding:
                state = "stick"
                local_force = trial
            else:
                state = "slip"
                local_force = np.zeros(2, dtype=float) if trial_norm == 0.0 else limit * trial / trial_norm
                next_references[index] = relative - local_force / contact.tangential_stiffness
            if not np.all(np.isfinite(local_force)) or not np.all(np.isfinite(next_references[index])):
                raise FloatingPointError("Independent Coulomb return map produced a non-finite state.")
            next_forces[index] = local_force
            next_states.append(state)
        if np.linalg.norm(next_references - references) > 0.0:
            increment = float(np.sum(next_forces * (next_references - references)))
            cumulative_dissipation += increment
        displacement_norm = float(np.linalg.norm(displacement))
        displacement_delta = float(np.linalg.norm(displacement - previous_displacement))
        force_norm = float(np.linalg.norm(next_forces))
        force_delta = float(np.linalg.norm(next_forces - forces))
        reference_norm = float(np.linalg.norm(next_references))
        reference_delta = float(np.linalg.norm(next_references - references))
        converged = (
            displacement_delta <= tolerance * max(displacement_norm, 1.0)
            and force_delta <= tolerance * max(force_norm, 1.0)
            and reference_delta <= tolerance * max(reference_norm, 1.0)
            and next_states == states
        )
        previous_displacement = displacement
        multipliers = next_multipliers
        references = next_references
        forces = next_forces
        states = next_states
        if converged:
            return ReferenceResult(
                displacement=displacement,
                multipliers=multipliers,
                contact_states=tuple(states),
                tangential_forces=forces,
                slip_references=references,
                cumulative_dissipation=max(float(cumulative_dissipation), 0.0),
                iterations=iteration,
            )
    raise RuntimeError("Independent Coulomb return map did not converge.")
