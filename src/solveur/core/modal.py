"""Modal analysis solver."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.linalg import eigh
from scipy.sparse import tril, triu
from scipy.sparse.linalg import ArpackNoConvergence, LinearOperator, eigsh, lobpcg, spsolve_triangular, spilu

from solveur.core.assembler import GlobalAssembler
from solveur.core.audit import SolverAudit
from solveur.core.dynamic_reduction import DynamicDofReducer
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.results import ModalResult
from solveur.mesh.validation import MeshValidator


class ModalAnalysisSolver:
    """Solve constrained generalized eigenproblems K phi = lambda M phi."""

    def __init__(self) -> None:
        self.validator = MeshValidator()
        self.assembler = GlobalAssembler()

    def solve(self, model: FiniteElementModel) -> ModalResult:
        report = self.validator.validate(model)
        if report.status == "FAIL":
            raise MeshValidationError("Mesh validation failed: " + "; ".join(report.errors))
        dofs = model.dof_manager()
        stiffness = self.assembler.assemble_stiffness(model, dofs)
        stiffness_assembly = dict(self.assembler.last_diagnostics)
        mass = self.assembler.assemble_mass(model, dofs)
        mass_assembly = dict(self.assembler.last_diagnostics)
        fixed = self.assembler.fixed_indices(model, dofs)
        reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)
        free = reducer.free

        try:
            requested = int(model.analysis.parameters.get("modes", 6))
            dense_limit = int(model.analysis.parameters.get("dense_modal_max_dofs", 2000))
        except (TypeError, ValueError) as exc:
            raise InputValidationError("modes and dense_modal_max_dofs must be integers.") from exc
        if requested <= 0:
            raise InputValidationError("modes must be a positive integer.")
        mode_count = max(1, min(requested, reducer.reduced_size))
        kff = reducer.stiffness
        mff = reducer.mass
        if dense_limit <= 0:
            raise InputValidationError("dense_modal_max_dofs must be a positive integer.")
        options = ModalSolverOptions.from_parameters(
            model.analysis.parameters,
            method=model.analysis.method,
            mode_count=mode_count,
            system_size=reducer.reduced_size,
        )
        try:
            values, vectors, used_method = self._solve_eigenproblem(
                kff,
                mff,
                mode_count,
                model.analysis.method,
                dense_limit=dense_limit,
                shift=options.shift_eigenvalue,
                which=options.which,
                tolerance=options.tolerance,
                maxiter=options.maxiter,
                ncv=options.ncv,
                lobpcg_preconditioner=str(model.analysis.parameters.get("lobpcg_preconditioner", "diagonal")),
            )
        except InputValidationError:
            raise
        except (np.linalg.LinAlgError, ArpackNoConvergence, ValueError, RuntimeError) as exc:
            raise NumericalConvergenceError(f"Modal eigensolve failed: {exc}") from exc
        if not np.all(np.isfinite(values)) or not np.all(np.isfinite(vectors)):
            raise NumericalConvergenceError("Modal eigensolve produced non-finite eigenpairs.")
        lazy_condensation = bool(reducer.diagnostics.get("lazy_condensation", False))
        audit_matrices: dict[str, object] = {"stiffness": stiffness, "mass": mass}
        if not lazy_condensation:
            audit_matrices["reduced_stiffness"] = kff
            audit_matrices["reduced_mass"] = mff
        audit_notes = []
        if lazy_condensation:
            audit_notes.append(
                "Large modal run uses exact lazy drilling condensation; the reduced Schur complement is applied as a sparse operator."
            )
        audit = SolverAudit.from_state(
            model=model,
            dofs=dofs,
            report=report,
            fixed=fixed,
            free=free,
            method=used_method,
            matrices=audit_matrices,
            include_element_audits=not lazy_condensation,
            notes=audit_notes,
        )
        positive = values > 1.0e-12
        values = values[positive]
        vectors = vectors[:, positive]
        order = np.argsort(values)
        values = values[order]
        vectors = vectors[:, order]
        if values.size == 0:
            raise NumericalConvergenceError("Modal eigensolve found no positive physical eigenvalue.")
        influences = {
            direction: reducer.reduce_state(_direction_vector(dofs, direction))
            for direction in ("UX", "UY", "UZ")
        }
        diagnostics = _modal_diagnostics(kff, mff, values, vectors, influences)
        diagnostics["dense_modal_max_dofs"] = dense_limit
        diagnostics["dense_conversion_used"] = used_method == "eigh"
        diagnostics["arpack"] = options.to_dict()
        diagnostics["assembly"] = {"stiffness": stiffness_assembly, "mass": mass_assembly}
        diagnostics["dynamic_reduction"] = dict(reducer.diagnostics)
        residual_limit = float(model.analysis.parameters.get("modal_residual_failure_tolerance", 1.0e-7))
        if diagnostics["max_relative_residual"] > residual_limit:
            raise NumericalConvergenceError(
                "Modal eigenpair residual is abnormal: "
                f"relative={diagnostics['max_relative_residual']:.6e}, allowed={residual_limit:.6e}."
            )
        frequencies = np.sqrt(values) / (2.0 * math.pi)
        full_modes = np.column_stack([reducer.expand_state(vectors[:, index]) for index in range(values.size)])
        return ModalResult(
            status="PASS",
            eigenvalues=values,
            frequencies_hz=frequencies,
            modes=full_modes,
            dofs=dofs,
            mesh_report=report,
            node_count=model.node_count,
            element_count=len(model.elements),
            method=used_method,
            solver=diagnostics,
            audit=audit,
        )

    @staticmethod
    def _solve_eigenproblem(
        kff: object,
        mff: object,
        mode_count: int,
        method: str,
        *,
        dense_limit: int = 2000,
        shift: float = 0.0,
        which: str = "LM",
        tolerance: float = 0.0,
        maxiter: int | None = None,
        ncv: int | None = None,
        lobpcg_preconditioner: str = "diagonal",
    ) -> tuple[np.ndarray, np.ndarray, str]:
        if method == "lobpcg" and mode_count < kff.shape[0] - 1:
            preconditioner = _lobpcg_preconditioner(kff, lobpcg_preconditioner)
            rng = np.random.default_rng(20260809)
            initial = rng.standard_normal((kff.shape[0], mode_count))
            values, vectors = lobpcg(
                kff,
                initial,
                B=mff,
                M=preconditioner,
                largest=False,
                tol=tolerance or 1.0e-8,
                maxiter=maxiter or 1000,
                retLambdaHistory=False,
                verbosityLevel=0,
            )
            return values, vectors, "lobpcg"
        if method in {"eigsh", "lanczos"} and mode_count < kff.shape[0] - 1:
            # For the smallest modes, avoid an implicit sparse LU when the
            # caller explicitly selects SM without a physical shift.
            sigma = shift if shift != 0.0 or which != "SM" else None
            values, vectors = eigsh(
                kff,
                k=mode_count,
                M=mff,
                sigma=sigma,
                which=which,
                tol=tolerance,
                maxiter=maxiter,
                ncv=ncv,
            )
            return values, vectors, "eigsh"
        if kff.shape[0] > dense_limit:
            raise InputValidationError(
                f"Dense modal solve refused for {kff.shape[0]} free dofs; limit={dense_limit}. "
                "Use method='eigsh' and request fewer modes, or raise dense_modal_max_dofs explicitly."
            )
        dense_k = kff.toarray()
        dense_m = mff.toarray()
        values, vectors = eigh(dense_k, dense_m)
        return values[:mode_count], vectors[:, :mode_count], "eigh"


def _preconditioner_diagonal(matrix: object) -> np.ndarray:
    diagonal_method = getattr(matrix, "diagonal", None)
    if callable(diagonal_method):
        diagonal = np.asarray(diagonal_method(), dtype=float)
    else:
        physical = getattr(matrix, "physical_stiffness", None)
        if physical is None:
            raise InputValidationError("LOBPCG requires a matrix diagonal or physical stiffness block.")
        diagonal = np.asarray(physical.diagonal(), dtype=float)
    scale = max(float(np.max(np.abs(diagonal), initial=0.0)), 1.0)
    return np.maximum(np.abs(diagonal), 1.0e-12 * scale)


def _lobpcg_preconditioner(matrix: object, name: str) -> LinearOperator:
    normalized = str(name).strip().lower()
    if normalized not in {"diagonal", "ssor", "spilu"}:
        raise InputValidationError("lobpcg_preconditioner must be 'diagonal', 'ssor' or 'spilu'.")
    if normalized == "ssor":
        physical = getattr(matrix, "physical_stiffness", None)
        if physical is None:
            raise InputValidationError("SSOR LOBPCG preconditioning requires a physical stiffness block.")
        diagonal = np.asarray(physical.diagonal(), dtype=float)
        lower = tril(physical, format="csr")
        upper = triu(physical, format="csr")

        def apply_ssor(vector: np.ndarray) -> np.ndarray:
            values = np.asarray(vector, dtype=float)
            forward = spsolve_triangular(lower, values, lower=True)
            scaled = forward * diagonal if forward.ndim == 1 else forward * diagonal[:, None]
            return np.asarray(spsolve_triangular(upper, scaled, lower=False))

        return LinearOperator(shape=matrix.shape, dtype=float, matvec=apply_ssor, matmat=apply_ssor)
    if normalized == "spilu":
        physical = getattr(matrix, "physical_stiffness", None)
        if physical is None:
            raise InputValidationError("spilu LOBPCG preconditioning requires a physical stiffness block.")
        factor = spilu(physical.tocsc(), drop_tol=1.0e-4, fill_factor=10.0)

        def apply_factor(vector: np.ndarray) -> np.ndarray:
            values = np.asarray(vector, dtype=float)
            return factor.solve(values)

        return LinearOperator(shape=matrix.shape, dtype=float, matvec=apply_factor, matmat=apply_factor)

    diagonal = _preconditioner_diagonal(matrix)

    def apply_diagonal(vector: np.ndarray) -> np.ndarray:
        values = np.asarray(vector, dtype=float)
        if values.ndim == 1:
            return values / diagonal
        return values / diagonal[:, None]

    return LinearOperator(shape=matrix.shape, dtype=float, matvec=apply_diagonal, matmat=apply_diagonal)


@dataclass(frozen=True)
class ModalSolverOptions:
    """Validated sparse eigensolver controls and physical shift metadata."""

    shift_eigenvalue: float = 0.0
    shift_hz: float | None = None
    which: str = "LM"
    tolerance: float = 0.0
    maxiter: int | None = None
    ncv: int | None = None

    @classmethod
    def from_parameters(
        cls,
        parameters: dict[str, Any],
        *,
        method: str,
        mode_count: int,
        system_size: int,
    ) -> "ModalSolverOptions":
        if "modal_shift_hz" in parameters and "modal_shift_eigenvalue" in parameters:
            raise InputValidationError("Define only one of modal_shift_hz and modal_shift_eigenvalue.")
        shift_hz = _optional_nonnegative_float(parameters.get("modal_shift_hz"), "modal_shift_hz")
        if shift_hz is not None:
            shift = (2.0 * math.pi * shift_hz) ** 2
        else:
            shift = _optional_nonnegative_float(
                parameters.get("modal_shift_eigenvalue"), "modal_shift_eigenvalue"
            ) or 0.0
        which = str(parameters.get("arpack_which", "LM")).upper()
        if which not in {"LM", "SM", "LA", "SA", "BE"}:
            raise InputValidationError("arpack_which must be one of LM, SM, LA, SA or BE.")
        tolerance = _optional_nonnegative_float(parameters.get("arpack_tolerance"), "arpack_tolerance") or 0.0
        maxiter = _optional_positive_int(parameters.get("arpack_maxiter"), "arpack_maxiter")
        ncv = _optional_positive_int(parameters.get("arpack_ncv"), "arpack_ncv")
        if ncv is not None and not mode_count < ncv <= system_size:
            raise InputValidationError(
                f"arpack_ncv must satisfy modes < arpack_ncv <= free dofs; "
                f"got modes={mode_count}, arpack_ncv={ncv}, free dofs={system_size}."
            )
        if shift != 0.0 and method not in {"eigsh", "lanczos"}:
            raise InputValidationError("A modal shift requires method='eigsh' or method='lanczos'.")
        return cls(shift, shift_hz, which, tolerance, maxiter, ncv)

    def to_dict(self) -> dict[str, object]:
        return {
            "shift_eigenvalue": self.shift_eigenvalue,
            "shift_hz": self.shift_hz,
            "which": self.which,
            "tolerance": self.tolerance,
            "maxiter": self.maxiter,
            "ncv": self.ncv,
        }


def _optional_nonnegative_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be a finite non-negative number.") from exc
    if not np.isfinite(result) or result < 0.0:
        raise InputValidationError(f"{name} must be a finite non-negative number.")
    return result


def _optional_positive_int(value: object, name: str) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise InputValidationError(f"{name} must be a positive integer.")
    return int(value)


def _modal_diagnostics(
    stiffness: object,
    mass: object,
    values: np.ndarray,
    vectors: np.ndarray,
    influences: dict[str, np.ndarray],
) -> dict[str, object]:
    """Return white-box modal quality indicators on the reduced problem."""
    if values.size == 0:
        return {"mode_count": 0, "max_relative_residual": 0.0}
    modal_mass = vectors.T @ (mass @ vectors)
    modal_stiffness = vectors.T @ (stiffness @ vectors)
    mass_diag = np.diag(modal_mass)
    stiffness_diag = np.diag(modal_stiffness)
    mass_off = modal_mass - np.diag(mass_diag)
    stiffness_target = np.diag(values * mass_diag)
    stiffness_error = modal_stiffness - stiffness_target
    residuals = [
        _relative_modal_residual(stiffness, mass, values[index], vectors[:, index])
        for index in range(values.size)
    ]
    return {
        "mode_count": int(values.size),
        "max_relative_residual": float(max(residuals)),
        "relative_residuals": [float(value) for value in residuals],
        "mass_orthogonality_error": _relative_norm(mass_off, modal_mass),
        "stiffness_diagonal_error": _relative_norm(stiffness_error, modal_stiffness),
        "modal_masses": [float(value) for value in mass_diag],
        "modal_stiffnesses": [float(value) for value in stiffness_diag],
        "effective_modal_mass": _effective_modal_mass(mass, vectors, influences),
    }


def _relative_modal_residual(stiffness: object, mass: object, value: float, vector: np.ndarray) -> float:
    residual = stiffness @ vector - value * (mass @ vector)
    reference = max(float(np.linalg.norm(stiffness @ vector)), abs(float(value)) * float(np.linalg.norm(mass @ vector)), 1.0)
    return float(np.linalg.norm(residual) / reference)


def _relative_norm(error: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(error) / max(float(np.linalg.norm(reference)), 1.0))


def _effective_modal_mass(
    mass: object, vectors: np.ndarray, influences: dict[str, np.ndarray]
) -> dict[str, object]:
    by_direction: dict[str, list[float]] = {}
    totals: dict[str, float] = {}
    for direction in ("UX", "UY", "UZ"):
        influence = influences[direction]
        total_mass = float(influence @ (mass @ influence))
        masses = []
        for mode in range(vectors.shape[1]):
            phi = vectors[:, mode]
            denominator = max(float(phi @ (mass @ phi)), 1.0e-30)
            masses.append(float((phi @ (mass @ influence)) ** 2 / denominator))
        by_direction[direction] = masses
        totals[direction] = total_mass
    return {"by_direction": by_direction, "total_direction_mass": totals}


def _direction_vector(dofs: object, direction: str) -> np.ndarray:
    vector = np.zeros(dofs.ndof, dtype=float)
    for node, names in dofs.node_dofs.items():
        if direction in names:
            vector[dofs.index(node, direction)] = 1.0
    return vector
