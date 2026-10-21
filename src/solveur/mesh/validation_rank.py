"""Mechanical-rank validation helper."""

from __future__ import annotations

from typing import Any

import numpy as np

from solveur.core.constraints import ConstraintReduction


def check_mechanical_rank(
    model: object,
    dofs: object,
    details: dict[str, Any],
    warnings: list[str],
) -> None:
    if dofs.ndof > 180:
        details["mechanical_rank"] = {"checked": False, "reason": "model too large", "ndof": dofs.ndof}
        return
    try:
        from solveur.core.assembly.assembler import GlobalAssembler

        assembler = GlobalAssembler()
        stiffness = assembler.assemble_stiffness(model, dofs)
        fixed = assembler.fixed_indices(model, dofs)
        constraints = model.linear_constraints()
        if constraints:
            reduction = ConstraintReduction.from_system(
                dofs,
                stiffness,
                np.zeros(dofs.ndof, dtype=np.float64),
                constraints,
                fixed,
            )
            reduced = reduction.matrix
            rank_basis = "fixed_and_mpc_reduced"
        else:
            free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
            reduced = stiffness[free, :][:, free]
            rank_basis = "fixed_dof_reduced"
        dense = 0.5 * (reduced.toarray() + reduced.toarray().T)
        if dense.size == 0:
            details["mechanical_rank"] = {
                "checked": True,
                "rank_basis": rank_basis,
                "free_dof_count": int(reduced.shape[0]),
                "rank": 0,
                "zero_mode_count": 0,
            }
            return
        eigenvalues = np.linalg.eigvalsh(dense)
        scale = max(float(np.max(np.abs(eigenvalues))), 1.0)
        tolerance = max(scale * 1.0e-10, 1.0e-12)
        zero_modes = int(np.count_nonzero(eigenvalues <= tolerance))
        details["mechanical_rank"] = {
            "checked": True,
            "rank_basis": rank_basis,
            "free_dof_count": int(reduced.shape[0]),
            "rank": int(np.linalg.matrix_rank(dense, tol=tolerance)),
            "zero_mode_count": zero_modes,
            "eigenvalue_min": float(np.min(eigenvalues)),
            "eigenvalue_max": float(np.max(eigenvalues)),
            "tolerance": float(tolerance),
        }
        if zero_modes > 0:
            warnings.append(f"Reduced stiffness has {zero_modes} near-zero modes; constraints may be insufficient.")
    except (ValueError, RuntimeError, np.linalg.LinAlgError) as exc:
        details["mechanical_rank"] = {"checked": False, "reason": str(exc), "ndof": dofs.ndof}
