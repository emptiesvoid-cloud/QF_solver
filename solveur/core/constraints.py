"""Linear multi-point constraints and an elimination-based reduction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix, hstack, vstack
from scipy.sparse.linalg import lsmr, spsolve

from solveur.core.dofs import DofManager, normalize_dof_name
from solveur.core.errors import InputValidationError, NumericalConvergenceError


@dataclass(frozen=True)
class ConstraintTerm:
    """One coefficient multiplying a named nodal degree of freedom."""

    node: int
    dof: str
    coefficient: float


@dataclass(frozen=True)
class LinearConstraint:
    """One equation ``sum(coefficient * q) = value``.

    The first term is the dependent degree of freedom for sparse substitution.
    Its order is therefore part of the public input convention, while the
    equation itself remains visible in its usual mathematical form.
    """

    terms: tuple[ConstraintTerm, ...]
    value: float = 0.0
    name: str = ""

    @property
    def dependent(self) -> ConstraintTerm:
        return self.terms[0]


@dataclass(frozen=True)
class ConstraintReduction:
    """Affine coordinate transformation enforcing fixed and MPC equations."""

    full_size: int
    independent: np.ndarray
    transform: csr_matrix
    offset: np.ndarray
    matrix: csr_matrix
    rhs: np.ndarray
    diagnostics: dict[str, object]

    @classmethod
    def from_system(
        cls,
        dofs: DofManager,
        stiffness: csr_matrix,
        loads: np.ndarray,
        constraints: list[LinearConstraint],
        fixed: np.ndarray,
    ) -> "ConstraintReduction":
        """Build the sparse affine elimination for one linear static system."""
        equations, relations = validate_constraint_definitions(dofs, constraints, fixed)
        independent = np.array(
            [index for index in range(dofs.ndof) if index not in relations], dtype=int
        )
        if independent.size == 0:
            raise InputValidationError("Constraints leave no independent degree of freedom.")
        column_of = {int(index): column for column, index in enumerate(independent)}
        transform_rows: list[int] = []
        transform_cols: list[int] = []
        transform_values: list[float] = []
        offset = np.zeros(dofs.ndof, dtype=float)
        memo: dict[int, tuple[float, dict[int, float]]] = {}
        for index in range(dofs.ndof):
            constant, coefficients = _resolve(index, relations, column_of, memo, ())
            offset[index] = constant
            for column, value in coefficients.items():
                if value:
                    transform_rows.append(index)
                    transform_cols.append(column)
                    transform_values.append(value)
        transform = csr_matrix(
            (transform_values, (transform_rows, transform_cols)),
            shape=(dofs.ndof, independent.size),
        )
        reduced_stiffness = (transform.T @ stiffness @ transform).tocsr()
        reduced_stiffness = (0.5 * (reduced_stiffness + reduced_stiffness.T)).tocsr()
        rhs = np.asarray(transform.T @ (np.asarray(loads, dtype=float) - stiffness @ offset)).ravel()
        return cls(
            full_size=dofs.ndof,
            independent=independent,
            transform=transform,
            offset=offset,
            matrix=reduced_stiffness,
            rhs=rhs,
            diagnostics={
                "strategy": "sparse_affine_substitution",
                "constraint_count": len(equations),
                "mpc_count": len(constraints),
                "fixed_constraint_count": int(fixed.size),
                "independent_dof_count": int(independent.size),
                "dependent_dof_count": int(dofs.ndof - independent.size),
                "transform_nnz": int(transform.nnz),
            },
        )

    def expand(self, values: np.ndarray) -> np.ndarray:
        """Map independent coordinates to the constrained full displacement."""
        result = self.offset + np.asarray(self.transform @ np.asarray(values, dtype=float)).ravel()
        if not np.all(np.isfinite(result)):
            raise NumericalConvergenceError("MPC reconstruction produced non-finite displacements.")
        return result

    def lagrange_solution(
        self,
        stiffness: csr_matrix,
        loads: np.ndarray,
        dofs: DofManager,
        constraints: list[LinearConstraint],
        fixed: np.ndarray,
    ) -> np.ndarray:
        """Solve the full KKT system as an independent small-model oracle."""
        matrix, values = _constraint_matrix(dofs, constraints, fixed)
        if matrix.shape[0] == 0:
            return np.asarray(spsolve(stiffness.tocsc(), np.asarray(loads, dtype=float))).ravel()
        zero = csr_matrix((matrix.shape[0], matrix.shape[0]), dtype=float)
        saddle = vstack((hstack((stiffness, matrix.T)), hstack((matrix, zero)))).tocsc()
        rhs = np.concatenate((np.asarray(loads, dtype=float), values))
        solution = np.asarray(spsolve(saddle, rhs)).ravel()[: dofs.ndof]
        if not np.all(np.isfinite(solution)):
            raise NumericalConvergenceError("Lagrange MPC verification produced a non-finite solution.")
        return solution


def validate_constraint_definitions(
    dofs: DofManager,
    constraints: list[LinearConstraint],
    fixed: np.ndarray,
) -> tuple[list[tuple[int, float, dict[int, float], str]], dict[int, tuple[float, dict[int, float]]]]:
    """Check ordered MPC equations without assembling an element stiffness matrix."""
    equations = _equations(dofs, constraints, fixed)
    relations = _relations(equations)
    independent_indices = [index for index in range(dofs.ndof) if index not in relations]
    independent = {index: column for column, index in enumerate(independent_indices)}
    memo: dict[int, tuple[float, dict[int, float]]] = {}
    for index in relations:
        _resolve(index, relations, independent, memo, ())
    return equations, relations


def recover_constraint_forces(
    stiffness: csr_matrix,
    loads: np.ndarray,
    displacement: np.ndarray,
    dofs: DofManager,
    constraints: list[LinearConstraint],
    fixed: np.ndarray,
    *,
    residual_override: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    """Recover constraint generalized forces from the full equilibrium residual.

    The returned force vector is ``C.T @ lambda`` with
    ``K u - f + C.T lambda = 0``.  It is the force contribution needed to
    close full-space equilibrium.  Fixed support reactions are also returned
    separately with the historical ``K u - f`` sign convention used by the
    global audit.
    """
    matrix, values = _constraint_matrix(dofs, constraints, fixed)
    residual = (
        np.asarray(residual_override, dtype=float).ravel()
        if residual_override is not None
        else np.asarray(stiffness @ displacement - np.asarray(loads, dtype=float)).ravel()
    )
    if residual.shape != (dofs.ndof,):
        raise InputValidationError("Constraint-force residual has an incompatible size.")
    if matrix.shape[0] == 0:
        return np.zeros_like(residual), np.zeros_like(residual), {
            "equation_count": 0,
            "constraint_violation_norm": 0.0,
            "equilibrium_relative_error": 0.0,
            "sign_convention": "K u - f + C.T lambda = 0",
            "largest_multipliers": [],
        }
    solution = lsmr(matrix.T, -residual, atol=1.0e-12, btol=1.0e-12)
    multipliers = np.asarray(solution[0], dtype=float)
    forces = np.asarray(matrix.T @ multipliers).ravel()
    if not np.all(np.isfinite(multipliers)) or not np.all(np.isfinite(forces)):
        raise NumericalConvergenceError("Constraint-force recovery produced non-finite values.")
    violation = np.asarray(matrix @ displacement - values).ravel()
    residual_norm = float(np.linalg.norm(residual))
    closure_norm = float(np.linalg.norm(residual + forces))
    equilibrium_error = closure_norm / max(residual_norm, 1.0)
    labels = _constraint_labels(constraints, fixed)
    order = np.argsort(np.abs(multipliers))[::-1][: min(20, multipliers.size)]
    largest = [
        {
            "index": int(index),
            "name": labels[index],
            "kind": "fixed" if index >= len(constraints) else "kinematic",
            "multiplier": float(multipliers[index]),
            "violation": float(violation[index]),
        }
        for index in order
    ]
    support_reactions = np.zeros_like(residual)
    fixed_start = len(constraints)
    for offset, index in enumerate(fixed):
        support_reactions[int(index)] = -multipliers[fixed_start + offset]
    return forces, support_reactions, {
        "equation_count": int(matrix.shape[0]),
        "kinematic_equation_count": len(constraints),
        "fixed_equation_count": int(fixed.size),
        "constraint_violation_norm": float(np.linalg.norm(violation)),
        "constraint_violation_max_abs": float(np.max(np.abs(violation), initial=0.0)),
        "equilibrium_relative_error": equilibrium_error,
        "lsmr_stop_code": int(solution[1]),
        "sign_convention": "K u - f + C.T lambda = 0",
        "fixed_support_reaction_norm": float(np.linalg.norm(support_reactions)),
        "largest_multipliers": largest,
    }


def _equations(
    dofs: DofManager,
    constraints: list[LinearConstraint],
    fixed: np.ndarray,
) -> list[tuple[int, float, dict[int, float], str]]:
    equations: list[tuple[int, float, dict[int, float], str]] = []
    for position, constraint in enumerate(constraints):
        if len(constraint.terms) < 2:
            raise InputValidationError(f"MPC {position} must contain at least two terms.")
        dependent = constraint.dependent
        pivot = float(dependent.coefficient)
        if not np.isfinite(pivot) or abs(pivot) <= 1.0e-14:
            raise InputValidationError(f"MPC {position} has a zero dependent coefficient.")
        dependent_index = dofs.index(dependent.node, dependent.dof)
        coefficients: dict[int, float] = {}
        seen: set[tuple[int, str]] = set()
        for term in constraint.terms:
            key = (int(term.node), normalize_dof_name(term.dof))
            if key in seen:
                raise InputValidationError(f"MPC {position} repeats DOF {key[1]} on node {key[0]}.")
            seen.add(key)
            value = float(term.coefficient)
            if not np.isfinite(value):
                raise InputValidationError(f"MPC {position} has a non-finite coefficient.")
            if term is dependent:
                continue
            coefficients[dofs.index(term.node, term.dof)] = -value / pivot
        equations.append((dependent_index, float(constraint.value) / pivot, coefficients, constraint.name or f"mpc_{position}"))
    for index in fixed:
        equations.append((int(index), 0.0, {}, f"fixed_{int(index)}"))
    return equations


def _relations(equations: list[tuple[int, float, dict[int, float], str]]) -> dict[int, tuple[float, dict[int, float]]]:
    relations: dict[int, tuple[float, dict[int, float]]] = {}
    for dependent, constant, coefficients, name in equations:
        if dependent in relations:
            old_constant, old_coefficients = relations[dependent]
            same = abs(old_constant - constant) <= 1.0e-12 and old_coefficients == coefficients
            if same:
                raise InputValidationError(f"Constraint {name!r} is redundant.")
            raise InputValidationError(f"Constraint {name!r} conflicts with another equation on the same dependent DOF.")
        relations[dependent] = (constant, coefficients)
    return relations


def _resolve(
    index: int,
    relations: dict[int, tuple[float, dict[int, float]]],
    column_of: dict[int, int],
    memo: dict[int, tuple[float, dict[int, float]]],
    path: tuple[int, ...],
) -> tuple[float, dict[int, float]]:
    if index in memo:
        return memo[index]
    if index not in relations:
        return 0.0, {column_of[index]: 1.0}
    if index in path:
        raise InputValidationError("MPC dependency cycle detected.")
    constant, coefficients = relations[index]
    resolved = float(constant)
    mapped: dict[int, float] = {}
    for child, factor in coefficients.items():
        child_constant, child_mapping = _resolve(child, relations, column_of, memo, (*path, index))
        resolved += factor * child_constant
        for column, value in child_mapping.items():
            mapped[column] = mapped.get(column, 0.0) + factor * value
    result = (resolved, {column: value for column, value in mapped.items() if abs(value) > 1.0e-15})
    memo[index] = result
    return result


def _constraint_matrix(
    dofs: DofManager,
    constraints: list[LinearConstraint],
    fixed: np.ndarray,
) -> tuple[csr_matrix, np.ndarray]:
    rows: list[int] = []
    columns: list[int] = []
    values: list[float] = []
    rhs: list[float] = []
    for row, constraint in enumerate(constraints):
        rhs.append(float(constraint.value))
        for term in constraint.terms:
            rows.append(row)
            columns.append(dofs.index(term.node, term.dof))
            values.append(float(term.coefficient))
    start = len(constraints)
    for offset, index in enumerate(fixed):
        rows.append(start + offset)
        columns.append(int(index))
        values.append(1.0)
        rhs.append(0.0)
    return csr_matrix((values, (rows, columns)), shape=(len(rhs), dofs.ndof)), np.asarray(rhs, dtype=float)


def _constraint_labels(constraints: list[LinearConstraint], fixed: np.ndarray) -> list[str]:
    labels = [constraint.name or f"mpc_{index}" for index, constraint in enumerate(constraints)]
    labels.extend(f"fixed_{int(index)}" for index in fixed)
    return labels
