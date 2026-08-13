"""Mesh-level diagnostics for multi-point constraints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np

from solveur.core.constraints import validate_constraint_definitions
from solveur.core.errors import InputValidationError

if TYPE_CHECKING:
    from solveur.core.dofs import DofManager
    from solveur.core.model import FiniteElementModel


def multipoint_constraint_errors(model: "FiniteElementModel", dofs: "DofManager") -> list[str]:
    """Return actionable errors for direct-API MPC models before assembly."""
    constraints = model.linear_constraints()
    if not constraints:
        return []
    if model.analysis.type != "linear_static":
        return ["Multi-point constraints are currently implemented for linear_static analysis only."]
    fixed = np.array(
        [dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs],
        dtype=int,
    )
    try:
        validate_constraint_definitions(dofs, constraints, fixed)
    except (InputValidationError, ValueError) as exc:
        return [f"Multi-point constraints: {exc}"]
    return []
