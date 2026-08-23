"""Modal analysis solver."""

from __future__ import annotations

import math

import numpy as np
from scipy.sparse import csr_matrix, diags, tril, triu
from scipy.sparse.linalg import (
    ArpackNoConvergence,
    LinearOperator,
    eigsh,
    gmres,
    lobpcg,
    spsolve_triangular,
    spsolve,
    spilu,
    splu,
)

from solveur.core.assembler import GlobalAssembler
from solveur.core.audit import SolverAudit
from solveur.core.dynamic_reduction import DynamicDofReducer
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.modal_dense import dense_generalized_eigh as _dense_generalized_eigh
from solveur.core.modal_options import (
    ModalSolverOptions,
    _boolean_parameter,
    _nonnegative_int_parameter,
    _positive_int_parameter,
    _positive_parameter,
    validate_slepc_modal_scale,
)
from solveur.core.results import ModalResult
from solveur.core.solver_backend import select_backend, solve_with_slepc
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
        parameters = model.analysis.parameters
        requested_backend = str(parameters.get("backend", "auto")).strip().lower()
        use_slepc_modal = _boolean_parameter(
            parameters.get("use_slepc_modal", False), "use_slepc_modal"
        )
        slepc_requested = use_slepc_modal or requested_backend == "petsc"
        # This is deliberately before K/M assembly.  A SLEPc shift-invert
        # attempt can allocate a factorization much larger than K and M.
        validate_slepc_modal_scale(dofs.ndof, requested=slepc_requested)
        stiffness, mass, stiffness_assembly, mass_assembly = self.assembler.assemble_stiffness_and_mass(model, dofs)
        fixed = self.assembler.fixed_indices(model, dofs)
        reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)
        free = reducer.free

        try:
            requested = int(parameters.get("modes", 6))
            dense_limit = int(parameters.get("dense_modal_max_dofs", 2000))
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
            parameters,
            method=model.analysis.method,
            mode_count=mode_count,
            system_size=reducer.reduced_size,
        )
        backend_selection = select_backend(
            "petsc" if use_slepc_modal else requested_backend,
            problem_size=reducer.reduced_size,
            parameters=parameters,
        )
        default_preconditioner = (
            "spilu" if reducer.diagnostics.get("lazy_condensation", False) else "diagonal"
        )
        modal_preconditioner = str(
            parameters.get("lobpcg_preconditioner", default_preconditioner)
        )
        default_drop_tol = 1.0e-6 if reducer.diagnostics.get("lazy_condensation", False) else 1.0e-4
        default_fill_factor = 20.0 if reducer.diagnostics.get("lazy_condensation", False) else 10.0
        lobpcg_drop_tol = _positive_parameter(
            parameters.get("lobpcg_drop_tol", default_drop_tol),
            "lobpcg_drop_tol",
        )
        lobpcg_fill_factor = _positive_parameter(
            parameters.get("lobpcg_fill_factor", default_fill_factor),
            "lobpcg_fill_factor",
        )
        inner_rtol = _positive_parameter(
            parameters.get("modal_inner_rtol", 1.0e-8),
            "modal_inner_rtol",
        )
        inner_maxiter = _positive_int_parameter(
            parameters.get("modal_inner_maxiter", 500),
            "modal_inner_maxiter",
        )
        inner_restart = _positive_int_parameter(
            parameters.get("modal_inner_restart", 50),
            "modal_inner_restart",
        )
        try:
            if backend_selection.selected == "petsc":
                if not hasattr(kff, "tocsr") or not hasattr(mff, "tocsr"):
                    raise InputValidationError("SLEPc modal backend requires explicit sparse K and M operators.")
                values, vectors = solve_with_slepc(kff, mff, mode_count, parameters)
                used_method = "slepc"
            else:
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
                    lobpcg_preconditioner=modal_preconditioner,
                    lobpcg_drop_tol=lobpcg_drop_tol,
                    lobpcg_fill_factor=lobpcg_fill_factor,
                    inner_rtol=inner_rtol,
                    inner_maxiter=inner_maxiter,
                    inner_restart=inner_restart,
                    prefer_dense=bool(parameters.get("prefer_dense_modal", False)),
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
        refinement_iterations = _nonnegative_int_parameter(
            parameters.get("modal_eigenpair_refinement_iterations", 0),
            "modal_eigenpair_refinement_iterations",
        )
        refinement = _refine_eigenpairs(
            kff, mff, values, vectors, iterations=refinement_iterations
        )
        values, vectors = refinement["values"], refinement["vectors"]
        influences = {
            direction: reducer.reduce_state(_direction_vector(dofs, direction))
            for direction in ("UX", "UY", "UZ")
        }
        diagnostics = _modal_diagnostics(kff, mff, values, vectors, influences)
        diagnostics["dense_modal_max_dofs"] = dense_limit
        diagnostics["dense_conversion_used"] = used_method == "eigh"
        diagnostics["backend"] = backend_selection.to_dict()
        diagnostics["arpack"] = options.to_dict()
        diagnostics["assembly"] = {"stiffness": stiffness_assembly, "mass": mass_assembly}
        diagnostics["dynamic_reduction"] = dict(reducer.diagnostics)
        diagnostics["eigenpair_refinement"] = {
            "iterations_requested": refinement_iterations,
            "iterations_performed": int(refinement["iterations_performed"]),
            "maximum_residual_before": float(refinement["maximum_residual_before"]),
            "maximum_residual_after": float(refinement["maximum_residual_after"]),
        }
        residual_limit = float(parameters.get("modal_residual_failure_tolerance", 1.0e-7))
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
        lobpcg_drop_tol: float = 1.0e-4,
        lobpcg_fill_factor: float = 10.0,
        inner_rtol: float = 1.0e-8,
        inner_maxiter: int = 500,
        inner_restart: int = 50,
        prefer_dense: bool = False,
    ) -> tuple[np.ndarray, np.ndarray, str]:
        if prefer_dense and kff.shape[0] <= dense_limit and hasattr(kff, "toarray"):
            values, vectors = _dense_generalized_eigh(kff, mff, mode_count)
            return values, vectors, "eigh"
        if method == "lobpcg" and mode_count < kff.shape[0] - 1:
            preconditioner = _lobpcg_preconditioner(
                kff,
                lobpcg_preconditioner,
                drop_tol=lobpcg_drop_tol,
                fill_factor=lobpcg_fill_factor,
            )
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
            # Shift-invert is also required for ordinary reduced sparse matrices.
            # Falling back to ``which=SM`` makes fine shell models converge very
            # slowly because the smallest generalized eigenvalues are clustered.
            sigma = shift if shift != 0.0 else 0.0
            op_inverse = None
            if sigma is not None and hasattr(kff, "physical_stiffness"):
                op_inverse = _shift_inverse_operator(
                    kff,
                    mff,
                    sigma,
                    preconditioner_name=lobpcg_preconditioner,
                    drop_tol=lobpcg_drop_tol,
                    fill_factor=lobpcg_fill_factor,
                    rtol=inner_rtol,
                    maxiter=inner_maxiter,
                    restart=inner_restart,
                )
            try:
                values, vectors = eigsh(
                    kff,
                    k=mode_count,
                    M=mff,
                    sigma=sigma,
                    # With shift-invert ARPACK orders eigenvalues by the
                    # transformed operator; LM returns the modes closest to
                    # sigma. Passing SM here can stall on fine shell meshes.
                    which="LM" if sigma is not None else which,
                    OPinv=op_inverse,
                    tol=tolerance,
                    maxiter=maxiter,
                    ncv=ncv,
                )
                return values, vectors, "eigsh"
            except ArpackNoConvergence:
                if kff.shape[0] > dense_limit or not hasattr(kff, "toarray"):
                    raise
                values, vectors = _dense_generalized_eigh(kff, mff, mode_count)
                return values, vectors, "eigh"
        if kff.shape[0] > dense_limit:
            raise InputValidationError(
                f"Dense modal solve refused for {kff.shape[0]} free dofs; limit={dense_limit}. "
                "Use method='eigsh' and request fewer modes, or raise dense_modal_max_dofs explicitly."
            )
        values, vectors = _dense_generalized_eigh(kff, mff, mode_count)
        return values, vectors, "eigh"


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


def _lobpcg_preconditioner(
    matrix: object,
    name: str,
    *,
    drop_tol: float = 1.0e-4,
    fill_factor: float = 10.0,
) -> LinearOperator:
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
        factor = spilu(
            physical.tocsc(),
            drop_tol=float(drop_tol),
            fill_factor=float(fill_factor),
        )

        def apply_factor(vector: np.ndarray) -> np.ndarray:
            values = np.asarray(vector, dtype=float)
            def solve_symmetric(rhs: np.ndarray) -> np.ndarray:
                forward = np.asarray(factor.solve(rhs), dtype=float)
                return np.asarray(factor.solve(forward, trans="T"), dtype=float)

            if values.ndim == 1:
                return solve_symmetric(values)
            return np.column_stack(
                [solve_symmetric(values[:, index]) for index in range(values.shape[1])]
            )

        return LinearOperator(shape=matrix.shape, dtype=float, matvec=apply_factor, matmat=apply_factor)

    diagonal = _preconditioner_diagonal(matrix)

    def apply_diagonal(vector: np.ndarray) -> np.ndarray:
        values = np.asarray(vector, dtype=float)
        if values.ndim == 1:
            return values / diagonal
        return values / diagonal[:, None]

    return LinearOperator(shape=matrix.shape, dtype=float, matvec=apply_diagonal, matmat=apply_diagonal)

def _shift_inverse_operator(
    stiffness: object,
    mass: object,
    sigma: float,
    *,
    preconditioner_name: str,
    drop_tol: float,
    fill_factor: float,
    rtol: float,
    maxiter: int,
    restart: int,
) -> LinearOperator:
    """Build a memory-bounded inverse for ``K - sigma M``.

    A lazy drilling Schur complement cannot be passed to SciPy's default
    shift-invert factorization.  GMRES applies that operator matrix-free,
    while the preconditioner is assembled only on the physical stiffness
    block and therefore does not create the dense Schur transfer matrix.
    """
    physical = getattr(stiffness, "physical_stiffness", stiffness)
    if not hasattr(physical, "tocsr") or not hasattr(mass, "tocsr"):
        raise InputValidationError("Shift-invert modal solve requires sparse stiffness and mass matrices.")
    shifted_physical = (physical - sigma * mass).tocsr()
    shifted_operator = LinearOperator(
        shape=stiffness.shape,
        dtype=float,
        matvec=lambda vector: np.asarray(stiffness @ vector - sigma * (mass @ vector)).ravel(),
        matmat=lambda vectors: np.asarray(stiffness @ vectors - sigma * (mass @ vectors)),
    )
    exact_inverse = _exact_lazy_shift_inverse(stiffness, shifted_physical, max_dofs=6000)
    if exact_inverse is not None:
        return exact_inverse
    preconditioner_matrix = _shifted_preconditioner_matrix(stiffness, shifted_physical)
    preconditioner = _gmres_preconditioner(
        preconditioner_matrix,
        preconditioner_name,
        drop_tol=drop_tol,
        fill_factor=fill_factor,
    )

    def solve(vector: np.ndarray) -> np.ndarray:
        values = np.asarray(vector, dtype=float)

        def solve_one(rhs: np.ndarray) -> np.ndarray:
            result, info = gmres(
                shifted_operator,
                rhs,
                M=preconditioner,
                rtol=rtol,
                atol=0.0,
                restart=restart,
                maxiter=maxiter,
            )
            if info != 0 or not np.all(np.isfinite(result)):
                raise NumericalConvergenceError(
                    "Shift-invert GMRES failed for the condensed modal operator: "
                    f"info={info}."
                )
            return np.asarray(result, dtype=float)

        if values.ndim == 1:
            return solve_one(values)
        return np.column_stack([solve_one(values[:, index]) for index in range(values.shape[1])])

    return LinearOperator(shape=stiffness.shape, dtype=float, matvec=solve, matmat=solve)

def _exact_lazy_shift_inverse(
    stiffness: object,
    shifted_physical: object,
    *,
    max_dofs: int,
) -> LinearOperator | None:
    """Factorize an exact sparse Schur complement for controlled-size cases."""
    if not hasattr(stiffness, "physical_stiffness") or stiffness.shape[0] > max_dofs:
        return None
    coupling_pd = getattr(stiffness, "stiffness_pd", None)
    coupling_dp = getattr(stiffness, "stiffness_dp", None)
    drilling_factor = getattr(stiffness, "drilling_factor", None)
    if coupling_pd is None or coupling_dp is None or drilling_factor is None:
        return None
    try:
        transfer = np.asarray(drilling_factor.solve(coupling_dp.toarray()), dtype=float)
        correction = csr_matrix(np.asarray(coupling_pd @ transfer, dtype=float))
        schur = (shifted_physical - correction).tocsr()
        schur = (0.5 * (schur + schur.T)).tocsr()
        factor = splu(schur.tocsc())
    except (MemoryError, RuntimeError, ValueError, np.linalg.LinAlgError):
        return None

    def solve(values: np.ndarray) -> np.ndarray:
        array = np.asarray(values, dtype=float)
        if array.ndim == 1:
            return np.asarray(factor.solve(array), dtype=float)
        return np.asarray(factor.solve(array), dtype=float)

    return LinearOperator(shape=stiffness.shape, dtype=float, matvec=solve, matmat=solve)

def _shifted_preconditioner_matrix(stiffness: object, shifted_physical: object) -> object:
    """Build a sparse Schur approximation for a lazy drilling condensation.

    The exact condensed operator applies ``K_pd K_dd^-1 K_dp`` through a
    sparse factorization.  For the inner GMRES solve, replacing ``K_dd^-1``
    by its diagonal inverse preserves locality and captures the dominant
    drilling coupling without materializing the dense transfer matrix.
    """
    coupling_pd = getattr(stiffness, "stiffness_pd", None)
    coupling_dp = getattr(stiffness, "stiffness_dp", None)
    drilling_diagonal = getattr(stiffness, "drilling_diagonal", None)
    if coupling_pd is None or coupling_dp is None or drilling_diagonal is None:
        return shifted_physical
    diagonal = np.asarray(drilling_diagonal, dtype=float).ravel()
    if diagonal.size == 0 or not np.all(np.isfinite(diagonal)):
        return shifted_physical
    scale = max(float(np.max(np.abs(diagonal), initial=0.0)), 1.0)
    safe_diagonal = np.where(np.abs(diagonal) > 1.0e-14 * scale, diagonal, 1.0e-14 * scale)
    correction = coupling_pd @ diags(1.0 / safe_diagonal, format="csr") @ coupling_dp
    return (shifted_physical - correction).tocsr()


def _gmres_preconditioner(
    matrix: object,
    name: str,
    *,
    drop_tol: float,
    fill_factor: float,
) -> LinearOperator:
    normalized = str(name).strip().lower()
    if normalized not in {"diagonal", "ssor", "spilu"}:
        raise InputValidationError("Modal preconditioner must be 'diagonal', 'ssor' or 'spilu'.")
    if normalized == "spilu":
        factor = spilu(matrix.tocsc(), drop_tol=drop_tol, fill_factor=fill_factor)

        def apply_ilu(vector: np.ndarray) -> np.ndarray:
            values = np.asarray(vector, dtype=float)
            if values.ndim == 1:
                return np.asarray(factor.solve(values), dtype=float)
            return np.column_stack(
                [np.asarray(factor.solve(values[:, index]), dtype=float) for index in range(values.shape[1])]
            )

        return LinearOperator(shape=matrix.shape, dtype=float, matvec=apply_ilu, matmat=apply_ilu)
    diagonal = np.asarray(matrix.diagonal(), dtype=float)
    scale = max(float(np.max(np.abs(diagonal), initial=0.0)), 1.0)
    diagonal = np.where(np.abs(diagonal) > 1.0e-14 * scale, diagonal, 1.0e-14 * scale)
    if normalized == "diagonal":
        return LinearOperator(
            shape=matrix.shape,
            dtype=float,
            matvec=lambda vector: np.asarray(vector, dtype=float) / diagonal,
            matmat=lambda vectors: np.asarray(vectors, dtype=float) / diagonal[:, None],
        )
    lower = tril(matrix, format="csr")
    upper = triu(matrix, format="csr")

    def apply_ssor(vector: np.ndarray) -> np.ndarray:
        values = np.asarray(vector, dtype=float)
        forward = spsolve_triangular(lower, values, lower=True)
        scaled = forward * diagonal if forward.ndim == 1 else forward * diagonal[:, None]
        return np.asarray(spsolve_triangular(upper, scaled, lower=False))

    return LinearOperator(shape=matrix.shape, dtype=float, matvec=apply_ssor, matmat=apply_ssor)


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


def _refine_eigenpairs(
    stiffness: object,
    mass: object,
    values: np.ndarray,
    vectors: np.ndarray,
    *,
    iterations: int,
) -> dict[str, object]:
    """Apply bounded inverse/Rayleigh corrections to sparse eigenpairs."""
    before = _maximum_modal_residual(stiffness, mass, values, vectors)
    if iterations <= 0 or not hasattr(stiffness, "tocsc") or not hasattr(mass, "tocsc"):
        return {
            "values": values,
            "vectors": vectors,
            "iterations_performed": 0,
            "maximum_residual_before": before,
            "maximum_residual_after": before,
        }
    current_values = np.asarray(values, dtype=float).copy()
    current_vectors = np.asarray(vectors, dtype=float).copy()
    performed = 0
    for _ in range(iterations):
        for index, value in enumerate(current_values):
            vector = current_vectors[:, index]
            residual = np.asarray(stiffness @ vector - value * (mass @ vector)).ravel()
            shift = 1.0e-2 * max(abs(float(value)), 1.0)
            shifted = (stiffness - (float(value) - shift) * mass).tocsc()
            try:
                correction = np.asarray(spsolve(shifted, -residual), dtype=float).ravel()
            except Exception:
                correction = np.full_like(vector, np.nan)
            if not np.all(np.isfinite(correction)):
                continue
            correction -= current_vectors @ (current_vectors.T @ (mass @ correction))
            candidate = vector + correction
            norm = float(np.sqrt(max(float(candidate @ (mass @ candidate)), 0.0)))
            if not np.isfinite(norm) or norm <= 0.0:
                continue
            candidate /= norm
            current_vectors[:, index] = candidate
            current_values[index] = float(candidate @ (stiffness @ candidate))
        performed += 1
    after = _maximum_modal_residual(stiffness, mass, current_values, current_vectors)
    return {
        "values": current_values,
        "vectors": current_vectors,
        "iterations_performed": performed,
        "maximum_residual_before": before,
        "maximum_residual_after": after,
    }


def _maximum_modal_residual(
    stiffness: object, mass: object, values: np.ndarray, vectors: np.ndarray
) -> float:
    if values.size == 0:
        return 0.0
    return float(
        max(
            _relative_modal_residual(stiffness, mass, float(value), vectors[:, index])
            for index, value in enumerate(values)
        )
    )


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
