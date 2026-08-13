"""Explainable selection policy for standard sparse linear solvers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix

from solveur.core.errors import InputValidationError


@dataclass(frozen=True)
class LinearSolverSelection:
    """Auditable recommendation without silently replacing the requested method."""

    requested_method: str
    recommended_method: str
    rationale: str
    warnings: tuple[str, ...]
    matrix_symmetric: bool
    matrix_real: bool
    positive_diagonal: bool
    positive_definite_evidence: str
    nnz: int
    sparse_memory_bytes: int
    direct_memory_estimate_bytes: int
    direct_memory_budget_bytes: int | None
    direct_budget_exceeded: bool

    def to_dict(self, *, used_method: str) -> dict[str, object]:
        return {
            "requested_method": self.requested_method,
            "used_method": used_method,
            "recommended_method": self.recommended_method,
            "rationale": self.rationale,
            "warnings": list(self.warnings),
            "matrix_contract": {
                "symmetric": self.matrix_symmetric,
                "real": self.matrix_real,
                "positive_diagonal": self.positive_diagonal,
                "positive_definite_evidence": self.positive_definite_evidence,
                "positive_definite_verified": self.positive_definite_evidence == "dense_cholesky",
                "positive_definite_assumed": self.positive_definite_evidence == "user_declared",
            },
            "resource_estimate": {
                "nnz": self.nnz,
                "sparse_memory_bytes": self.sparse_memory_bytes,
                "direct_memory_estimate_bytes": self.direct_memory_estimate_bytes,
                "direct_memory_budget_bytes": self.direct_memory_budget_bytes,
                "direct_budget_exceeded": self.direct_budget_exceeded,
            },
        }


class LinearSolverPolicy:
    """Classify one reduced matrix and enforce an opt-in direct-memory gate."""

    _DIRECT = {"direct", "spsolve", "direct_frequency", "harmonic_direct"}
    _CG = {"cg", "conjugate_gradient"}

    @classmethod
    def assess(cls, matrix: csr_matrix, method: str, parameters: dict[str, Any]) -> LinearSolverSelection:
        """Return a conservative solver recommendation for a sparse matrix."""
        reduced = matrix.tocsr()
        requested = str(method).lower()
        symmetry = _is_symmetric(reduced)
        matrix_real = _is_real(reduced)
        diagonal = reduced.diagonal()
        positive_diagonal = bool(
            matrix_real and diagonal.size and np.all(np.isfinite(diagonal)) and np.all(np.real(diagonal) > 0.0)
        )
        positive_definite_evidence = _positive_definite_evidence(reduced, parameters, matrix_real and symmetry)
        sparse_bytes = _sparse_storage_bytes(reduced)
        direct_bytes = int(sparse_bytes * _positive_float(parameters, "direct_fill_factor_estimate", 10.0))
        budget_mb = parameters.get("direct_memory_budget_mb")
        budget_bytes = None if budget_mb is None else int(_positive_float(parameters, "direct_memory_budget_mb", 1.0) * 1024**2)
        direct_over_budget = budget_bytes is not None and direct_bytes > budget_bytes
        warnings: list[str] = []

        if not matrix_real:
            recommended, rationale = "direct", "reduced matrix is complex; the standard direct complex route is required"
        elif positive_definite_evidence == "dense_cholesky":
            recommended, rationale = "cg", "reduced matrix is real symmetric positive definite (dense Cholesky verified)"
        elif positive_definite_evidence == "user_declared":
            recommended, rationale = "cg", "reduced matrix is assumed SPD by the explicit user declaration"
        elif symmetry:
            recommended, rationale = "minres", "reduced matrix is symmetric but positive definiteness is not established"
        else:
            recommended, rationale = "gmres", "reduced matrix is not symmetric; a nonsymmetric Krylov method is eligible"

        if requested in cls._DIRECT and direct_over_budget:
            warnings.append("direct sparse factorization estimate exceeds direct_memory_budget_mb")
            if bool(parameters.get("enforce_direct_memory_budget", False)):
                assert budget_bytes is not None
                raise InputValidationError(
                    "Direct solver refused by configured memory budget: "
                    f"estimated={direct_bytes / 1024**2:.1f} MiB, budget={budget_bytes / 1024**2:.1f} MiB."
                )
        if requested in cls._CG and positive_definite_evidence == "not_proven":
            warnings.append("CG requested without a positive-definite matrix proof or explicit user declaration")
        if requested == "minres" and not (matrix_real and symmetry):
            warnings.append("MINRES requested for a nonsymmetric matrix")
        if requested in {"gmres", "bicgstab"} and symmetry:
            warnings.append("nonsymmetric Krylov method requested although the matrix appears symmetric")

        return LinearSolverSelection(
            requested_method=requested,
            recommended_method=recommended,
            rationale=rationale,
            warnings=tuple(warnings),
            matrix_symmetric=symmetry,
            matrix_real=matrix_real,
            positive_diagonal=positive_diagonal,
            positive_definite_evidence=positive_definite_evidence,
            nnz=int(reduced.nnz),
            sparse_memory_bytes=sparse_bytes,
            direct_memory_estimate_bytes=direct_bytes,
            direct_memory_budget_bytes=budget_bytes,
            direct_budget_exceeded=direct_over_budget,
        )

    @classmethod
    def enforce_method_contract(cls, selection: LinearSolverSelection, parameters: dict[str, Any]) -> None:
        """Reject standard Krylov requests that contradict their declared contract."""
        requested = selection.requested_method
        preconditioner = str(parameters.get("preconditioner", "none")).lower()
        if requested in cls._CG and selection.positive_definite_evidence == "not_proven":
            raise InputValidationError(
                "CG requires a verified real SPD reduced matrix. For matrices larger than "
                "spd_dense_check_max_dofs, set assume_spd=true only when the model derivation "
                "establishes positive definiteness. Use MINRES for symmetric indefinite systems "
                "or GMRES/BiCGSTAB for nonsymmetric systems."
            )
        if requested == "minres" and not (selection.matrix_real and selection.matrix_symmetric):
            raise InputValidationError("MINRES requires a real symmetric reduced matrix.")
        if requested in {*cls._CG, "minres"} and preconditioner not in {"", "none", "jacobi"}:
            raise InputValidationError(
                f"{requested.upper()} accepts only 'none' or 'jacobi' preconditioning in the standard solver route."
            )


def linear_execution_settings(method: str, parameters: dict[str, Any]) -> dict[str, object]:
    """Return the effective public settings recorded for one standard solve.

    The dictionary deliberately records only scalar options consumed by the
    SciPy linear route.  It avoids serializing arbitrary user analysis
    parameters into results while keeping a run reproducible enough to explain
    the choice and stopping behavior.
    """
    normalized = str(method).lower()
    iterative = normalized not in LinearSolverPolicy._DIRECT
    return {
        "requested_method": normalized,
        "preconditioner": str(parameters.get("preconditioner", "none")).lower(),
        "rtol": float(parameters.get("rtol", 1.0e-10)) if iterative else None,
        "atol": float(parameters.get("atol", 0.0)) if iterative else None,
        "maxiter": parameters.get("maxiter") if iterative else None,
        "residual_failure_tolerance": float(parameters.get("residual_failure_tolerance", 1.0e-7)),
        "fallback_used": False,
    }


def _is_symmetric(matrix: csr_matrix) -> bool:
    if matrix.shape[0] != matrix.shape[1]:
        return False
    scale = max(float(np.linalg.norm(matrix.data)), 1.0)
    return float(np.linalg.norm((matrix - matrix.T).data)) / scale <= 1.0e-9


def _is_real(matrix: csr_matrix) -> bool:
    """Return true when complex storage contains no meaningful imaginary part."""
    if not np.iscomplexobj(matrix.data):
        return True
    scale = max(float(np.linalg.norm(matrix.data)), 1.0)
    return float(np.linalg.norm(np.imag(matrix.data))) / scale <= 1.0e-12


def _positive_definite_evidence(matrix: csr_matrix, parameters: dict[str, Any], eligible: bool) -> str:
    """Return auditable SPD evidence without an implicit dense conversion.

    A Cholesky proof is intentionally restricted to small matrices.  Large
    sparse systems may use CG only after the caller explicitly records the
    modelling argument through ``assume_spd``; a positive diagonal is never a
    proof by itself.
    """
    if not eligible:
        return "not_proven"
    if bool(parameters.get("assume_spd", False)):
        return "user_declared"
    maximum = int(parameters.get("spd_dense_check_max_dofs", 256))
    if maximum < 1:
        raise InputValidationError("spd_dense_check_max_dofs must be a positive integer.")
    if matrix.shape[0] > maximum:
        return "not_proven"
    try:
        np.linalg.cholesky(matrix.toarray())
    except np.linalg.LinAlgError:
        return "not_proven"
    return "dense_cholesky"


def _sparse_storage_bytes(matrix: csr_matrix) -> int:
    return int(matrix.data.nbytes + matrix.indices.nbytes + matrix.indptr.nbytes)


def _positive_float(parameters: dict[str, Any], name: str, default: float) -> float:
    value = float(parameters.get(name, default))
    if not np.isfinite(value) or value <= 0.0:
        raise InputValidationError(f"{name} must be a finite positive number.")
    return value
