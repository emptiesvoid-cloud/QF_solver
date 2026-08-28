"""Optional numerical backends used by the common solver layer.

SciPy remains the zero-configuration backend.  PETSc is imported lazily so
that the standard wheel never acquires an MPI or PETSc runtime dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from solveur.core.errors import InputValidationError, NumericalConvergenceError


@dataclass(frozen=True)
class BackendSelection:
    """Auditable backend choice for one numerical operation."""

    requested: str
    selected: str
    fallback_used: bool
    petsc_available: bool
    slepc_available: bool
    reason: str

    def to_dict(self) -> dict[str, object]:
        return {
            "requested": self.requested,
            "selected": self.selected,
            "fallback_used": self.fallback_used,
            "petsc_available": self.petsc_available,
            "slepc_available": self.slepc_available,
            "reason": self.reason,
        }


def optional_backend_status() -> dict[str, bool]:
    """Report optional backend availability without importing it eagerly."""

    return {"petsc": _petsc_module() is not None, "slepc": _slepc_module() is not None}


def select_backend(
    requested: str | None,
    *,
    problem_size: int,
    parameters: dict[str, Any] | None = None,
) -> BackendSelection:
    """Select ``scipy`` or optional ``petsc`` for a numerical operation.

    ``auto`` is deliberately conservative: SciPy remains the default, while
    PETSc can be selected for large systems when explicitly preferred or when
    ``petsc_min_dofs`` is reached.  An explicit ``petsc`` request never falls
    back silently.
    """

    params = parameters or {}
    normalized = str(requested or "auto").strip().lower()
    if normalized not in {"auto", "scipy", "petsc"}:
        raise InputValidationError("backend must be 'auto', 'scipy' or 'petsc'.")
    status = optional_backend_status()
    if normalized == "scipy":
        return BackendSelection(normalized, "scipy", False, status["petsc"], status["slepc"], "explicit SciPy backend")
    if normalized == "petsc":
        if not status["petsc"]:
            raise InputValidationError(
                "PETSc backend requested but petsc4py is not installed; use backend='scipy' or install the HPC extra."
            )
        return BackendSelection(normalized, "petsc", False, status["petsc"], status["slepc"], "explicit PETSc backend")
    threshold = int(params.get("petsc_min_dofs", 250_000))
    prefer = bool(params.get("prefer_petsc", False))
    policy_requests_petsc = prefer or problem_size >= threshold
    if status["petsc"] and policy_requests_petsc:
        return BackendSelection(
            normalized,
            "petsc",
            False,
            status["petsc"],
            status["slepc"],
            "PETSc is available and the configured size/preference policy selected it",
        )
    if policy_requests_petsc and not status["petsc"]:
        return BackendSelection(
            normalized,
            "scipy",
            True,
            status["petsc"],
            status["slepc"],
            "PETSc is unavailable; SciPy fallback selected by the automatic policy",
        )
    return BackendSelection(
        normalized,
        "scipy",
        False,
        status["petsc"],
        status["slepc"],
        "SciPy selected as the standard backend",
    )


def solve_with_petsc(
    matrix: Any,
    rhs: np.ndarray,
    method: str,
    parameters: dict[str, Any],
) -> tuple[np.ndarray, int, float]:
    """Solve one real sparse system through PETSc when the optional extra exists."""

    petsc = _petsc_module()
    if petsc is None:
        raise InputValidationError("petsc4py is required for backend='petsc'.")
    from petsc4py import PETSc  # type: ignore[import-not-found]

    sparse = matrix.tocsr()
    mat = PETSc.Mat().createAIJ(
        size=sparse.shape,
        csr=(sparse.indptr, sparse.indices, sparse.data),
    )
    mat.assemble()
    b, x = mat.createVecs()
    b.setArray(np.asarray(rhs, dtype=float))
    ksp = PETSc.KSP().create()
    normalized = str(method).lower()
    if normalized in {"direct", "spsolve", "splu", "direct_frequency"}:
        ksp.setType("preonly")
        ksp.getPC().setType("lu")
    else:
        ksp.setType({"cg": "cg", "minres": "minres", "gmres": "gmres", "bicgstab": "bcgs"}.get(normalized, "gmres"))
        ksp.getPC().setType(_petsc_preconditioner_type(parameters.get("preconditioner", "none")))
    ksp.setOperators(mat)
    ksp.setTolerances(
        rtol=float(parameters.get("rtol", 1.0e-10)),
        atol=float(parameters.get("atol", 0.0)),
        max_it=int(parameters.get("maxiter", 10_000) or 10_000),
    )
    ksp.setFromOptions()
    try:
        ksp.solve(b, x)
        reason = int(ksp.getConvergedReason())
        if reason <= 0:
            raise NumericalConvergenceError(f"PETSc {normalized} did not converge (reason={reason}).")
        result = np.asarray(x.getArray(), dtype=float).copy()
        iterations = int(ksp.getIterationNumber())
        residual_norm = float(ksp.getResidualNorm())
    finally:
        ksp.destroy()
        b.destroy()
        x.destroy()
        mat.destroy()
    return result, iterations, residual_norm


def solve_with_slepc(
    stiffness: Any,
    mass: Any,
    mode_count: int,
    parameters: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    """Solve a real generalized eigenproblem with optional SLEPc."""

    if _petsc_module() is None or _slepc_module() is None:
        raise InputValidationError("petsc4py and slepc4py are required for the SLEPc modal backend.")
    from petsc4py import PETSc  # type: ignore[import-not-found]
    from slepc4py import SLEPc  # type: ignore[import-not-found]

    stiffness_csr = stiffness.tocsr()
    mass_csr = mass.tocsr()
    matrices = []
    for sparse in (stiffness_csr, mass_csr):
        matrix = PETSc.Mat().createAIJ(size=sparse.shape, csr=(sparse.indptr, sparse.indices, sparse.data))
        matrix.assemble()
        matrices.append(matrix)
    operator, mass_operator = matrices
    eps = SLEPc.EPS().create()
    try:
        eps.setOperators(operator, mass_operator)
        eps.setProblemType(SLEPc.EPS.ProblemType.GHEP)
        eps.setDimensions(nev=mode_count)
        eps.setWhichEigenpairs(SLEPc.EPS.Which.SMALLEST_REAL)
        eps.setTolerances(
            tol=float(parameters.get("arpack_tolerance", parameters.get("modal_residual_failure_tolerance", 1.0e-8))),
            max_it=int(parameters.get("arpack_maxiter", 10_000)),
        )
        eps.setFromOptions()
        eps.solve()
        count = min(int(eps.getConverged()), mode_count)
        if count < mode_count:
            raise NumericalConvergenceError(f"SLEPc converged only {count} of {mode_count} requested modes.")
        real, imaginary = operator.createVecs()
        values = np.empty(mode_count, dtype=float)
        vectors = np.empty((stiffness_csr.shape[0], mode_count), dtype=float)
        for index in range(mode_count):
            eigenvalue = eps.getEigenpair(index, real, imaginary)
            # SLEPc versions return either the real scalar or a (real, imag)
            # pair here.  Keep the adapter tolerant without changing the
            # generalized-eigenproblem contract exposed by QF Solver.
            if isinstance(eigenvalue, tuple):
                eigenvalue = eigenvalue[0]
            values[index] = float(np.real(eigenvalue))
            vectors[:, index] = np.asarray(real.getArray(), dtype=float)
        real.destroy()
        imaginary.destroy()
    finally:
        eps.destroy()
        operator.destroy()
        mass_operator.destroy()
    return values, vectors


def _petsc_module() -> Any | None:
    try:
        import petsc4py  # type: ignore[import-not-found]
    except Exception:
        return None
    return petsc4py


def _slepc_module() -> Any | None:
    try:
        import slepc4py  # type: ignore[import-not-found]
    except Exception:
        return None
    return slepc4py


def _petsc_preconditioner_type(value: object) -> str:
    """Map the public preconditioner names to PETSc PC types.

    The mapping is intentionally small and explicit.  An unknown value must
    fail before KSP execution rather than silently degrading to an
    unpreconditioned solve, which would make a large-model campaign
    irreproducible.
    """

    normalized = str(value or "none").strip().lower()
    aliases = {
        "none": "none",
        "identity": "none",
        "jacobi": "jacobi",
        "ilu": "ilu",
        "spilu": "ilu",
        "gamg": "gamg",
        "amg": "gamg",
        "hypre": "hypre",
        "sor": "sor",
        "asm": "asm",
        "bjacobi": "bjacobi",
        "block_jacobi": "bjacobi",
    }
    try:
        return aliases[normalized]
    except KeyError as exc:
        supported = ", ".join(sorted(aliases))
        raise InputValidationError(
            f"Unsupported PETSc preconditioner {value!r}; supported values: {supported}."
        ) from exc
