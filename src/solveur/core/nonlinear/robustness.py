"""Opt-in numerical robustness controls for nonlinear R&D experiments."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any
import warnings

import numpy as np
from scipy.sparse import csr_matrix, diags
from scipy.sparse.linalg import MatrixRankWarning, splu, spsolve


_PARAMETER_KEYS = {
    "experimental_linear_solver",
    "experimental_linear_permutation",
    "experimental_system_scaling",
    "experimental_residual_scaling",
    "experimental_line_search",
    "experimental_line_search_min_alpha",
    "experimental_line_search_max_reductions",
    "experimental_line_search_c",
}
_PERMUTATIONS = {"NATURAL", "MMD_ATA", "MMD_AT_PLUS_A", "COLAMD"}


@dataclass(frozen=True)
class NonlinearRobustnessOptions:
    """Validated, opt-in controls used only by robustness experiments."""

    linear_solver: str = "spsolve"
    linear_permutation: str = "COLAMD"
    system_scaling: str = "none"
    residual_scaling: str = "none"
    line_search: str = "existing"
    line_search_min_alpha: float = 1.0e-4
    line_search_max_reductions: int = 14
    line_search_c: float = 1.0e-4

    @classmethod
    def from_parameters(cls, parameters: dict[str, object]) -> "NonlinearRobustnessOptions | None":
        """Return controls only when an explicit experimental parameter is present."""
        if not _PARAMETER_KEYS.intersection(parameters):
            return None
        options = cls(
            linear_solver=str(parameters.get("experimental_linear_solver", "spsolve")).lower(),
            linear_permutation=str(parameters.get("experimental_linear_permutation", "COLAMD")).upper(),
            system_scaling=str(parameters.get("experimental_system_scaling", "none")).lower(),
            residual_scaling=str(parameters.get("experimental_residual_scaling", "none")).lower(),
            line_search=str(parameters.get("experimental_line_search", "existing")).lower(),
            line_search_min_alpha=float(parameters.get("experimental_line_search_min_alpha", 1.0e-4)),
            line_search_max_reductions=int(parameters.get("experimental_line_search_max_reductions", 14)),
            line_search_c=float(parameters.get("experimental_line_search_c", 1.0e-4)),
        )
        options.validate()
        return options

    def validate(self) -> None:
        if self.linear_solver not in {"spsolve", "splu"}:
            raise ValueError("experimental_linear_solver must be 'spsolve' or 'splu'.")
        if self.linear_permutation not in _PERMUTATIONS:
            raise ValueError("experimental_linear_permutation is not a supported SciPy permutation.")
        if self.system_scaling not in {"none", "symmetric_diagonal"}:
            raise ValueError("experimental_system_scaling must be 'none' or 'symmetric_diagonal'.")
        if self.residual_scaling not in {"none", "row_max"}:
            raise ValueError("experimental_residual_scaling must be 'none' or 'row_max'.")
        if self.system_scaling != "none" and self.residual_scaling != "none":
            raise ValueError("Use one experimental linear scaling mechanism at a time.")
        if self.line_search not in {"existing", "off", "armijo"}:
            raise ValueError("experimental_line_search must be 'existing', 'off' or 'armijo'.")
        if not isfinite(self.line_search_min_alpha) or not 0.0 < self.line_search_min_alpha <= 1.0:
            raise ValueError("experimental_line_search_min_alpha must be in (0, 1].")
        if self.line_search_max_reductions < 0:
            raise ValueError("experimental_line_search_max_reductions must be non-negative.")
        if not isfinite(self.line_search_c) or not 0.0 <= self.line_search_c < 1.0:
            raise ValueError("experimental_line_search_c must be in [0, 1).")

    def to_dict(self) -> dict[str, Any]:
        return {
            "linear_solver": self.linear_solver,
            "linear_permutation": self.linear_permutation,
            "system_scaling": self.system_scaling,
            "residual_scaling": self.residual_scaling,
            "line_search": self.line_search,
            "line_search_min_alpha": self.line_search_min_alpha,
            "line_search_max_reductions": self.line_search_max_reductions,
            "line_search_c": self.line_search_c,
        }


def solve_scaled_system(
    matrix: csr_matrix,
    rhs: np.ndarray,
    options: NonlinearRobustnessOptions,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Solve one reduced Newton system with an explicitly selected experiment."""
    options.validate()
    values = csr_matrix(matrix)
    vector = np.asarray(rhs, dtype=float)
    if values.shape[0] != values.shape[1] or vector.shape != (values.shape[0],):
        raise ValueError("Experimental nonlinear linear system has incompatible dimensions.")
    if not np.all(np.isfinite(values.data)) or not np.all(np.isfinite(vector)):
        raise ValueError("Experimental nonlinear linear system must be finite.")

    factors = np.ones(values.shape[0], dtype=float)
    scaling = "none"
    if options.system_scaling == "symmetric_diagonal":
        diagonal = np.abs(values.diagonal())
        active = diagonal > 0.0
        factors[active] = 1.0 / np.sqrt(diagonal[active])
        effective = diags(factors) @ values @ diags(factors)
        effective_rhs = factors * vector
        scaling = options.system_scaling
    elif options.residual_scaling == "row_max":
        row_max = np.asarray(np.abs(values).sum(axis=1)).ravel()
        active = row_max > 0.0
        factors[active] = 1.0 / row_max[active]
        effective = diags(factors) @ values
        effective_rhs = factors * vector
        scaling = options.residual_scaling
    else:
        effective = values
        effective_rhs = vector

    if options.linear_solver == "splu":
        solution = splu(effective.tocsc(), permc_spec=options.linear_permutation).solve(effective_rhs)
        backend = "scipy.sparse.linalg.splu"
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            solution = spsolve(effective.tocsc(), effective_rhs, permc_spec=options.linear_permutation)
        backend = "scipy.sparse.linalg.spsolve"

    if options.system_scaling == "symmetric_diagonal":
        solution = factors * solution
    solution = np.asarray(solution, dtype=float)
    if not np.all(np.isfinite(solution)):
        raise ValueError("Experimental nonlinear linear solve returned a non-finite correction.")
    return solution, {
        "backend": backend,
        "permutation": options.linear_permutation,
        "scaling": scaling,
        "factor_min": float(np.min(factors)) if factors.size else 1.0,
        "factor_max": float(np.max(factors)) if factors.size else 1.0,
    }
