"""Bounded sparse linear-buckling analysis on the geometric tangent path."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import eigs, eigsh

from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.assembly.geometric import build_total_lagrangian_assembly
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.iteration import solve_full_newton
from solveur.core.results import SolveResult
from solveur.mesh.validation import MeshValidator


@dataclass(frozen=True)
class BucklingEigenpair:
    """Smallest constrained tangent eigenpair at one load factor."""

    value: float
    mode: np.ndarray


class LinearBucklingSolver:
    """Estimate the first tangent-instability factor for supported solid families.

    The implementation is deliberately bounded: it follows a converged
    proportional preload, forms the sparse initial-stress decomposition
    ``K(alpha) = K0 + alpha * Kg`` and solves/refines the first loss of
    positive definiteness with sparse generalized paths. It is a research
    path and does not claim post-buckling continuation or physical validation.
    """

    def solve(self, model: FiniteElementModel) -> SolveResult:
        self._validate_scope(model)
        report = MeshValidator().validate(model)
        if report.status == "FAIL":
            raise MeshValidationError("Mesh validation failed: " + "; ".join(report.errors))
        dofs = model.dof_manager()
        fixed = np.unique(
            [dofs.index(condition.node, name) for condition in model.fixed_dofs for name in condition.dofs]
        )
        free = np.setdiff1d(np.arange(dofs.ndof, dtype=int), fixed)
        if free.size < 2:
            raise MeshValidationError("linear_buckling requires at least two free degrees of freedom.")
        assembly = build_total_lagrangian_assembly(model)
        loads = np.zeros(dofs.ndof, dtype=float)
        for load in model.loads:
            loads[dofs.index(load.node, load.dof)] += load.value
        parameters = model.analysis.parameters
        preload_factor = _positive_float(parameters.get("preload_factor", 1.0), "preload_factor")
        increments = _positive_int(parameters.get("load_increments", 8), "load_increments")
        tolerance = _positive_float(parameters.get("tolerance", 1.0e-8), "tolerance")
        max_iterations = _positive_int(parameters.get("max_iterations", 30), "max_iterations")
        displacement, preload_diagnostics = solve_full_newton(
            assembly,
            preload_factor * loads,
            fixed,
            increments=increments,
            tolerance=tolerance,
            max_iterations=max_iterations,
        )
        zero = np.zeros(assembly.ndof, dtype=float)
        _, initial_tangent = assembly.assemble(zero)
        _, preload_tangent = assembly.assemble(displacement)
        if initial_tangent is None or preload_tangent is None:
            raise NumericalConvergenceError(
                "linear_buckling requires sparse tangents from the geometric assembly.",
                reason=NonlinearFailureReason.BUCKLING_FAILURE,
            )
        geometric_tangent_builder = getattr(assembly, "geometric_tangent", None)
        if not callable(geometric_tangent_builder):
            raise NumericalConvergenceError(
                "linear_buckling requires an initial-stress geometric tangent from the assembly.",
                reason=NonlinearFailureReason.BUCKLING_FAILURE,
            )
        geometric_tangent = geometric_tangent_builder(displacement).tocsr()
        reduced_initial = initial_tangent[free, :][:, free].tocsr()
        reduced_geometric = geometric_tangent[free, :][:, free].tocsr()
        critical_factor, mode, bracket = self._critical_factor(
            reduced_initial,
            reduced_geometric,
            free,
            assembly.ndof,
            parameters,
        )
        critical_matrix = (reduced_initial + critical_factor * reduced_geometric).tocsr()
        reduced_mode = np.asarray(mode[free], dtype=float)
        mode_norm = float(np.linalg.norm(reduced_mode))
        if not np.isfinite(mode_norm) or mode_norm <= 0.0:
            raise NumericalConvergenceError(
                "linear_buckling returned an invalid critical mode.",
                reason=NonlinearFailureReason.BUCKLING_FAILURE,
            )
        mode_residual_norm = float(np.linalg.norm(critical_matrix @ reduced_mode))
        mode_reference_norm = float(np.linalg.norm(reduced_initial @ reduced_mode))
        eigen_formulation = str(bracket.get("method", "bracketed_sparse_eigenvalue"))
        eigen_solver = "eigs" if eigen_formulation == "generalized_eigs_shift_invert" else "eigsh"
        solver = {
            "backend": f"scipy.sparse.linalg.{eigen_solver}",
            "eigen_solver": eigen_solver,
            "preload_factor": preload_factor,
            "preload_diagnostics": preload_diagnostics,
            "critical_factor": critical_factor,
            "critical_bracket": bracket,
            "critical_eigenproblem": "(K + lambda * Kg) phi = 0",
            "eigen_formulation": eigen_formulation,
            "geometric_tangent_source": "initial_stress_second_piola",
            "critical_mode_norm": mode_norm,
            "critical_mode_residual_norm": mode_residual_norm,
            "critical_mode_residual_relative": mode_residual_norm / max(mode_reference_norm, 1.0),
            "critical_mode_free_dof_count": int(reduced_mode.size),
            "initial_tangent_nnz": int(initial_tangent.nnz),
            "geometric_tangent_nnz": int(geometric_tangent.nnz),
            "maturity": "research",
            "scope": "bounded-linear-tangent-buckling-tet4-tet10-hex8-hex20",
            "limitations": [
                "First tangent-instability factor only; no post-buckling continuation.",
                "Geometric tangent is the initial-stress contribution from one converged proportional preload.",
                "External correlation and broad solid-family qualification remain open.",
            ],
        }
        return SolveResult(
            status="PASS",
            displacements=mode,
            dofs=dofs,
            mesh_report=report,
            node_count=model.node_count,
            element_count=len(model.elements),
            analysis="linear_buckling",
            method="eigsh",
            message="Bounded sparse tangent-buckling factor computed.",
            solver=solver,
        )

    @staticmethod
    def _critical_factor(
        initial: csr_matrix,
        geometric: csr_matrix,
        free: np.ndarray,
        ndof: int,
        parameters: dict[str, object],
    ) -> tuple[float, np.ndarray, dict[str, object]]:
        eigensolver_tolerance = _positive_float(
            parameters.get("eigensolver_tolerance", 1.0e-8), "eigensolver_tolerance"
        )
        eigensolver_maxiter = _positive_int(
            parameters.get("eigensolver_maxiter", max(1000, 5 * initial.shape[0])), "eigensolver_maxiter"
        )
        bracket_iterations = _positive_int(parameters.get("bracket_iterations", 40), "bracket_iterations")
        initial_factor = _positive_float(parameters.get("initial_factor", 1.0), "initial_factor")
        maximum = _positive_float(parameters.get("maximum_factor", 1.0e6), "maximum_factor")
        if maximum <= initial_factor:
            raise InputValidationError("maximum_factor must be greater than initial_factor.")

        generalized_fallback: str | None = None

        def eigenpair(factor: float) -> BucklingEigenpair:
            matrix = (initial + factor * geometric).tocsr()
            if matrix.shape[0] <= 3:
                values, vectors = np.linalg.eigh(matrix.toarray())
                value = float(values[0])
                reduced_mode = np.asarray(vectors[:, 0], dtype=float)
            else:
                values, vectors = eigsh(
                    matrix,
                    k=1,
                    which="SA",
                    tol=eigensolver_tolerance,
                    maxiter=eigensolver_maxiter,
                )
                value = float(values[0])
                reduced_mode = np.asarray(vectors[:, 0], dtype=float)
            pivot = int(np.argmax(np.abs(reduced_mode)))
            if reduced_mode[pivot] < 0.0:
                reduced_mode = -reduced_mode
            mode = np.zeros(ndof, dtype=float)
            mode[free] = reduced_mode
            return BucklingEigenpair(value, mode)

        generalized = _generalized_critical_factor(
            initial,
            geometric,
            free,
            ndof,
            eigensolver_tolerance=eigensolver_tolerance,
            eigensolver_maxiter=eigensolver_maxiter,
        )
        if generalized is not None:
            factor, mode = generalized
            return factor, mode, {
                "lower": 0.0,
                "upper": float(factor),
                "method": "generalized_eigsh",
                "mass_matrix": "-geometric_tangent",
            }
        generalized_fallback = (
            "generalized eigsh requires a positive-definite -geometric_tangent; "
            "the sparse bracketed tangent-eigenvalue path was retained"
        )

        lower_pair = eigenpair(0.0)
        initial_scale = max(float(abs(initial).sum(axis=1).max()), 1.0)
        definiteness_tolerance = max(np.finfo(float).eps * initial_scale, eigensolver_tolerance * initial_scale)
        if not np.isfinite(lower_pair.value) or lower_pair.value <= definiteness_tolerance:
            raise NumericalConvergenceError(
                "linear_buckling initial constrained tangent is not positive definite.",
                reason=NonlinearFailureReason.BUCKLING_FAILURE,
                diagnostics={
                    "minimum_eigenvalue": lower_pair.value,
                    "positive_definiteness_tolerance": definiteness_tolerance,
                },
            )
        upper = initial_factor
        while upper < maximum:
            candidate = eigenpair(upper)
            if candidate.value <= 0.0:
                break
            upper *= 2.0
        else:
            candidate = eigenpair(upper)
        if candidate.value > 0.0:
            raise NumericalConvergenceError(
                "linear_buckling could not bracket a loss of tangent positive definiteness.",
                reason=NonlinearFailureReason.BUCKLING_FAILURE,
                diagnostics={"maximum_factor": maximum, "eigenvalue": candidate.value},
            )
        target_tolerance = _positive_float(parameters.get("factor_tolerance", 1.0e-4), "factor_tolerance")
        lower_factor = 0.0
        for _ in range(bracket_iterations):
            middle = 0.5 * (lower_factor + upper)
            middle_pair = eigenpair(middle)
            if middle_pair.value > 0.0:
                lower_factor = middle
            else:
                candidate = middle_pair
                upper = middle
            if (upper - lower_factor) / max(abs(upper), 1.0) <= target_tolerance:
                break
        critical = upper
        indefinite_generalized = _indefinite_generalized_critical_factor(
            initial,
            geometric,
            free,
            ndof,
            lower_factor=lower_factor,
            upper_factor=upper,
            eigensolver_tolerance=eigensolver_tolerance,
            eigensolver_maxiter=eigensolver_maxiter,
        )
        if indefinite_generalized is not None:
            factor, mode, shift, attempted_shifts = indefinite_generalized
            return factor, mode, {
                "lower": float(lower_factor),
                "upper": float(upper),
                "method": "generalized_eigs_shift_invert",
                "mass_matrix": "-geometric_tangent",
                "generalized_fallback_reason": generalized_fallback,
                "shift_invert_strategy": "strictly_interior_dyadic_bracket",
                "shift_invert_sigma": shift,
                "shift_invert_attempted_shifts": list(attempted_shifts),
            }
        bracket: dict[str, object] = {
            "lower": float(lower_factor),
            "upper": float(upper),
            "method": "bracketed_sparse_eigenvalue",
        }
        if generalized_fallback is not None:
            bracket["generalized_fallback_reason"] = generalized_fallback
        bracket["indefinite_shift_invert"] = {
            "status": "FALLBACK",
            "strategy": "strictly_interior_dyadic_bracket",
            "attempted_shifts": list(_interior_shift_candidates(lower_factor, upper)),
            "reason": "no real residual-qualified in-bracket eigenpair was recovered",
        }
        return critical, candidate.mode, bracket

    @staticmethod
    def _validate_scope(model: FiniteElementModel) -> None:
        families = {element.type for element in model.elements}
        if not families or not families <= {"TET4", "TET10", "HEX8", "HEX20"}:
            raise InputValidationError("linear_buckling currently supports TET4, TET10, HEX8 and HEX20.")
        if len(families) != 1:
            raise InputValidationError("linear_buckling currently requires one homogeneous element family.")
        if len({element.material for element in model.elements}) != 1:
            raise InputValidationError("linear_buckling currently requires one homogeneous material.")
        material = model.materials[next(iter({element.material for element in model.elements}))]
        if str(material.get("type", "")) != "isotropic_3d":
            raise InputValidationError("linear_buckling requires material type 'isotropic_3d'.")
        if model.distributed_loads:
            raise InputValidationError("linear_buckling currently accepts nodal dead loads only.")


def _positive_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(float(value)) or float(value) <= 0.0:
        raise InputValidationError(f"{name} must be a finite positive number.")
    return float(value)


def _positive_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InputValidationError(f"{name} must be a positive integer.")
    return int(value)


def _generalized_critical_factor(
    initial: csr_matrix,
    geometric: csr_matrix,
    free: np.ndarray,
    ndof: int,
    *,
    eigensolver_tolerance: float,
    eigensolver_maxiter: int,
) -> tuple[float, np.ndarray] | None:
    """Try the sparse generalized buckling problem before the bounded fallback.

    With ``B = -Kg`` positive definite, the singularity condition is the
    generalized sparse eigenproblem ``K phi = lambda B phi``. A geometric
    tangent that is indefinite is handled by the bracketed shift-invert path
    after the positive-definite ``eigsh`` attempt has been rejected.
    """

    mass = (-geometric).tocsr()
    if mass.shape[0] < 3:
        # The existing bounded path owns the tiny dense-safe edge case.
        return None
    try:
        minimum, _ = eigsh(
            mass,
            k=1,
            which="SA",
            tol=eigensolver_tolerance,
            maxiter=eigensolver_maxiter,
        )
        minimum_value = float(minimum[0])
        if not np.isfinite(minimum_value) or minimum_value <= max(1.0e-12, eigensolver_tolerance):
            return None
        values, vectors = eigsh(
            initial,
            M=mass,
            k=1,
            sigma=0.0,
            which="LM",
            tol=eigensolver_tolerance,
            maxiter=eigensolver_maxiter,
        )
    except (TypeError, ValueError, RuntimeError, np.linalg.LinAlgError):
        return None
    factor = float(values[0])
    reduced_mode = np.asarray(vectors[:, 0], dtype=float)
    if not np.isfinite(factor) or factor <= 0.0 or not np.all(np.isfinite(reduced_mode)):
        return None
    mode_norm = float(np.linalg.norm(reduced_mode))
    if mode_norm <= 0.0 or not np.isfinite(mode_norm):
        return None
    reduced_mode /= mode_norm
    pivot = int(np.argmax(np.abs(reduced_mode)))
    if reduced_mode[pivot] < 0.0:
        reduced_mode = -reduced_mode
    mode = np.zeros(ndof, dtype=float)
    mode[free] = reduced_mode
    residual = initial @ reduced_mode + factor * geometric @ reduced_mode
    residual_norm = float(np.linalg.norm(residual))
    reference_norm = max(float(np.linalg.norm(initial @ reduced_mode)), 1.0)
    if not np.isfinite(residual_norm) or residual_norm / reference_norm > max(1.0e-5, 100.0 * eigensolver_tolerance):
        return None
    return factor, mode


def _indefinite_generalized_critical_factor(
    initial: csr_matrix,
    geometric: csr_matrix,
    free: np.ndarray,
    ndof: int,
    *,
    lower_factor: float,
    upper_factor: float,
    eigensolver_tolerance: float,
    eigensolver_maxiter: int,
) -> tuple[float, np.ndarray, float, tuple[float, ...]] | None:
    """Refine a bracket with generalized shift-invert when ``-Kg`` is indefinite.

    ``eigsh`` requires a positive-definite generalized mass matrix. The
    symmetric indefinite problem can use ARPACK's nonsymmetric interface,
    but a complex or out-of-bracket eigenpair is rejected rather than being
    presented as a physical buckling factor.
    """

    if initial.shape[0] <= 3 or not upper_factor > lower_factor:
        return None
    mass = (-geometric).tocsr()
    attempted_shifts = _interior_shift_candidates(lower_factor, upper_factor)
    for shift in attempted_shifts:
        try:
            values, vectors = eigs(
                initial,
                M=mass,
                k=1,
                sigma=shift,
                which="LM",
                tol=eigensolver_tolerance,
                maxiter=eigensolver_maxiter,
            )
        except (TypeError, ValueError, RuntimeError, np.linalg.LinAlgError):
            continue
        value = complex(values[0])
        scale = max(abs(value.real), 1.0)
        if (
            not np.isfinite(value.real)
            or not np.isfinite(value.imag)
            or abs(value.imag) > max(1.0e-8, 100.0 * eigensolver_tolerance) * scale
        ):
            continue
        factor = float(value.real)
        bracket_tolerance = max(1.0e-6, 100.0 * eigensolver_tolerance) * max(abs(upper_factor), 1.0)
        if factor <= 0.0 or factor < lower_factor - bracket_tolerance or factor > upper_factor + bracket_tolerance:
            continue
        reduced_mode = np.real(np.asarray(vectors[:, 0], dtype=complex)).astype(float, copy=False)
        mode_norm = float(np.linalg.norm(reduced_mode))
        if mode_norm <= 0.0 or not np.isfinite(mode_norm):
            continue
        reduced_mode /= mode_norm
        pivot = int(np.argmax(np.abs(reduced_mode)))
        if reduced_mode[pivot] < 0.0:
            reduced_mode = -reduced_mode
        residual = initial @ reduced_mode + factor * geometric @ reduced_mode
        residual_norm = float(np.linalg.norm(residual))
        reference_norm = max(float(np.linalg.norm(initial @ reduced_mode)), 1.0)
        if not np.isfinite(residual_norm) or residual_norm / reference_norm > max(
            1.0e-5, 100.0 * eigensolver_tolerance
        ):
            continue
        mode = np.zeros(ndof, dtype=float)
        mode[free] = reduced_mode
        return factor, mode, shift, attempted_shifts
    return None


def _interior_shift_candidates(lower_factor: float, upper_factor: float) -> tuple[float, ...]:
    """Return deterministic strictly interior shifts from a verified bracket.

    The endpoint can be the exact critical eigenvalue, making the shift-invert
    factorization singular. Midpoint and quarter-point candidates are derived
    solely from the bracket and retain the same physical search interval.
    """

    width = upper_factor - lower_factor
    candidates = tuple(lower_factor + fraction * width for fraction in (0.5, 0.25, 0.75))
    return tuple(
        candidate
        for index, candidate in enumerate(candidates)
        if np.isfinite(candidate)
        and lower_factor < candidate < upper_factor
        and candidate not in candidates[:index]
    )
