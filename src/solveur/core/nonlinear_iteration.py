"""Newton iteration helpers shared by nonlinear drivers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Protocol
import warnings
from time import perf_counter

import numpy as np

from solveur.core.dofs import DofManager
from solveur.core.errors import NumericalConvergenceError
from solveur.core.material_state import MaterialStateTable
from solveur.core.nonlinear_contracts import NonlinearFailureReason, NonlinearIterationDiagnostics
from solveur.core.model import FiniteElementModel
from scipy.sparse import bmat, csr_matrix, csc_matrix
from scipy.sparse.linalg import MatrixRankWarning, spsolve


class NonlinearAssemblyProtocol(Protocol):
    """Minimal assembly contract consumed by the shared Full Newton driver."""

    ndof: int

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, csr_matrix | None]:
        """Return internal force and an optional tangent."""


class CompositeNonlinearAssembly:
    """Add sparse nonlinear contributions behind one Newton assembly contract.

    Each component may represent a material, geometric or contact contribution.
    The composite owns only accumulation and consistency checks; it does not
    interpret the component physics or duplicate a Newton loop.
    """

    def __init__(self, components: Sequence[NonlinearAssemblyProtocol]):
        if not components:
            raise ValueError("Composite nonlinear assembly requires at least one component.")
        self.components = tuple(components)
        self.ndof = int(self.components[0].ndof)
        if any(int(component.ndof) != self.ndof for component in self.components):
            raise ValueError("Composite nonlinear assembly components must share ndof.")

    def assemble(
        self, displacement: np.ndarray, *, tangent_required: bool = True
    ) -> tuple[np.ndarray, csr_matrix | None]:
        values = np.asarray(displacement, dtype=float)
        if values.shape != (self.ndof,) or not np.all(np.isfinite(values)):
            raise ValueError(f"Composite nonlinear displacement must be a finite vector of size {self.ndof}.")
        internal = np.zeros(self.ndof, dtype=float)
        tangent = csr_matrix((self.ndof, self.ndof)) if tangent_required else None
        for component in self.components:
            component_internal, component_tangent = component.assemble(
                values, tangent_required=tangent_required
            )
            component_internal = np.asarray(component_internal, dtype=float)
            if component_internal.shape != (self.ndof,) or not np.all(np.isfinite(component_internal)):
                raise ValueError("Composite nonlinear component returned an invalid internal force.")
            internal += component_internal
            if tangent_required:
                if component_tangent is None or component_tangent.shape != (self.ndof, self.ndof):
                    raise ValueError("Composite nonlinear component must return a sparse tangent.")
                tangent = tangent + csr_matrix(component_tangent)
        if not np.all(np.isfinite(internal)) or (tangent is not None and not np.all(np.isfinite(tangent.data))):
            raise ValueError("Composite nonlinear assembly produced non-finite values.")
        return internal, tangent


def solve_full_newton(
    assembly: NonlinearAssemblyProtocol,
    external: np.ndarray,
    fixed: np.ndarray,
    *,
    increments: int,
    tolerance: float,
    max_iterations: int,
) -> tuple[np.ndarray, dict[str, object]]:
    """Solve a dead-load path with the shared Full Newton contract.

    Element-specific assemblies only provide force/tangent evaluations. The
    driver owns load increments, residual criteria, line search and structured
    iteration histories, so geometric and future coupled paths do not grow
    independent Newton implementations.
    """
    if increments < 1 or max_iterations < 1:
        raise ValueError("Full Newton requires positive increments and max_iterations.")
    fixed = np.asarray(fixed, dtype=int)
    free = np.setdiff1d(np.arange(assembly.ndof), fixed)
    if free.size == 0:
        raise ValueError("Full Newton requires at least one free degree of freedom.")
    displacement = np.zeros(assembly.ndof, dtype=float)
    history: list[dict[str, object]] = []
    total_iterations = 0
    for step in range(1, increments + 1):
        target = (step / increments) * np.asarray(external, dtype=float)
        scale = max(float(np.linalg.norm(target[free])), 1.0)
        residual_history: list[float] = []
        line_search_iterations = 0
        assembly_seconds = 0.0
        linear_solve_seconds = 0.0
        line_search_seconds = 0.0
        for iteration in range(1, max_iterations + 1):
            assembly_started = perf_counter()
            try:
                internal, tangent = assembly.assemble(displacement)
            except NumericalConvergenceError as exc:
                diagnostics = _failure_diagnostics(
                    step, iteration, residual_history, float("inf"), tolerance, line_search_iterations
                )
                diagnostics.update(exc.diagnostics)
                raise NumericalConvergenceError(str(exc), reason=exc.reason, diagnostics=diagnostics) from exc
            except (ValueError, FloatingPointError) as exc:
                diagnostics = _failure_diagnostics(
                    step, iteration, residual_history, float("inf"), tolerance, line_search_iterations
                )
                raise NumericalConvergenceError(
                    f"Full Newton assembly failed at increment {step}: {exc}",
                    reason=_assembly_failure_reason(str(exc)),
                    diagnostics=diagnostics,
                ) from exc
            finally:
                assembly_seconds += perf_counter() - assembly_started
            if tangent is None:
                raise NumericalConvergenceError(
                    "Full Newton assembly returned no tangent.",
                    reason=NonlinearFailureReason.INVALID_ELEMENT,
                    diagnostics=_failure_diagnostics(
                        step, iteration, residual_history, float("inf"), tolerance, line_search_iterations
                    ),
                )
            if not np.all(np.isfinite(internal)):
                reason = _nonfinite_failure_reason(internal)
                raise NumericalConvergenceError(
                    f"Full Newton assembly returned non-finite internal force at increment {step}.",
                    reason=reason,
                    diagnostics=_failure_diagnostics(
                        step, iteration, residual_history, float("inf"), tolerance, line_search_iterations
                    ),
                )
            if not np.all(np.isfinite(tangent.data)):
                reason = _nonfinite_failure_reason(tangent.data)
                raise NumericalConvergenceError(
                    f"Full Newton assembly returned a non-finite tangent at increment {step}.",
                    reason=reason,
                    diagnostics=_failure_diagnostics(
                        step, iteration, residual_history, float("inf"), tolerance, line_search_iterations
                    ),
                )
            residual = target - internal
            if not np.all(np.isfinite(residual)):
                reason = _nonfinite_failure_reason(residual)
                raise NumericalConvergenceError(
                    f"Full Newton residual is non-finite at increment {step}.",
                    reason=reason,
                    diagnostics=_failure_diagnostics(
                        step, iteration, residual_history, float("inf"), tolerance, line_search_iterations
                    ),
                )
            residual_norm = float(np.linalg.norm(residual[free]))
            relative = residual_norm / scale
            residual_history.append(residual_norm)
            if relative <= tolerance:
                break
            if len(residual_history) >= 4 and residual_history[-1] >= residual_history[-4] * (1.0 - 1.0e-10):
                raise NumericalConvergenceError(
                    f"Full Newton stagnated at increment {step}; relative residual={relative:.6e}.",
                    reason=NonlinearFailureReason.CONVERGENCE_STAGNATION,
                    diagnostics=_failure_diagnostics(
                        step, iteration, residual_history, relative, tolerance, line_search_iterations
                    ),
                )
            try:
                linear_solve_started = perf_counter()
                with warnings.catch_warnings():
                    warnings.simplefilter("error", MatrixRankWarning)
                    correction = spsolve(tangent[free, :][:, free], residual[free])
                linear_solve_seconds += perf_counter() - linear_solve_started
            except (MatrixRankWarning, ValueError) as exc:
                raise NumericalConvergenceError(
                    f"Full Newton tangent is singular at increment {step}.",
                    reason=NonlinearFailureReason.SINGULAR_TANGENT,
                    diagnostics=_failure_diagnostics(
                        step, iteration, residual_history, relative, tolerance, line_search_iterations
                    ),
                ) from exc
            except RuntimeError as exc:
                diagnostics = _failure_diagnostics(
                    step, iteration, residual_history, relative, tolerance, line_search_iterations
                )
                diagnostics["backend_error"] = str(exc)
                raise NumericalConvergenceError(
                    f"Full Newton linear solver failed at increment {step}: {exc}",
                    reason=NonlinearFailureReason.LINEAR_SOLVER_FAILURE,
                    diagnostics=diagnostics,
                ) from exc
            if not np.all(np.isfinite(correction)):
                raise NumericalConvergenceError(
                    f"Full Newton correction is non-finite at increment {step}.",
                    reason=NonlinearFailureReason.NAN_DETECTED,
                    diagnostics=_failure_diagnostics(
                        step, iteration, residual_history, relative, tolerance, line_search_iterations
                    ),
                )
            try:
                line_search_started = perf_counter()
                displacement, reductions = _line_search_assembly_with_diagnostics(
                    assembly, displacement, free, correction, target, residual_norm
                )
                line_search_seconds += perf_counter() - line_search_started
                line_search_iterations += reductions
            except NumericalConvergenceError as exc:
                diagnostics = _failure_diagnostics(
                    step, iteration, residual_history, relative, tolerance, line_search_iterations
                )
                diagnostics.update(exc.diagnostics)
                raise NumericalConvergenceError(
                    str(exc), reason=exc.reason, diagnostics=diagnostics
                ) from exc
            total_iterations += 1
        else:
            raise NumericalConvergenceError(
                f"Full Newton did not converge at increment {step}; relative residual={relative:.6e}.",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
                diagnostics={
                    **_failure_diagnostics(
                        step,
                        max_iterations,
                        residual_history,
                        relative,
                        tolerance,
                        line_search_iterations,
                    ),
                },
            )
        step_diagnostics = NonlinearIterationDiagnostics(
            converged=True,
            iterations=iteration,
            residual_initial=residual_history[0],
            residual_final=residual_history[-1],
            relative_residual=relative,
            tolerance=tolerance,
            solver="full_newton",
            backend="scipy.sparse.linalg.spsolve",
            residual_history=tuple(residual_history),
            line_search_iterations=line_search_iterations,
        ).to_dict()
        step_diagnostics.update(
            {
                "assembly_seconds": assembly_seconds,
                "linear_solve_seconds": linear_solve_seconds,
                "line_search_seconds": line_search_seconds,
            }
        )
        history.append(
            {
                "increment": step,
                "load_factor": step / increments,
                "iterations": iteration,
                "relative_residual": relative,
                "residual_initial": residual_history[0],
                "residual_final": residual_history[-1],
                "residual_history": tuple(residual_history),
                "assembly_seconds": assembly_seconds,
                "linear_solve_seconds": linear_solve_seconds,
                "line_search_seconds": line_search_seconds,
                "diagnostics": step_diagnostics,
            }
        )
    return displacement, {
        "converged": True,
        "newton_iterations": total_iterations,
        "final_relative_residual": history[-1]["relative_residual"],
        "increments": history,
    }


def _failure_diagnostics(
    step: int,
    iterations: int,
    residual_history: list[float],
    relative_residual: float,
    tolerance: float,
    line_search_iterations: int = 0,
) -> dict[str, object]:
    """Build the common diagnostic payload for a failed Full Newton step."""
    return {
        "step": step,
        "iterations": iterations,
        "residual_initial": residual_history[0] if residual_history else None,
        "residual_final": residual_history[-1] if residual_history else None,
        "relative_residual": relative_residual,
        "tolerance": tolerance,
        "solver": "full_newton",
        "backend": "scipy.sparse.linalg.spsolve",
        "residual_history": tuple(residual_history),
        "line_search_iterations": line_search_iterations,
    }


def _assembly_failure_reason(message: str) -> NonlinearFailureReason:
    """Map an assembly exception to a stable nonlinear failure category."""

    lowered = message.lower()
    if "material" in lowered or "constitutive" in lowered:
        return NonlinearFailureReason.MATERIAL_UPDATE_FAILURE
    if "contact" in lowered:
        return NonlinearFailureReason.CONTACT_UPDATE_FAILURE
    if "inf" in lowered:
        return NonlinearFailureReason.INF_DETECTED
    if "nan" in lowered or "finite" in lowered:
        return NonlinearFailureReason.NAN_DETECTED
    return NonlinearFailureReason.INVALID_ELEMENT


def _nonfinite_failure_reason(values: np.ndarray) -> NonlinearFailureReason:
    """Distinguish an infinite value from a NaN in a numerical payload."""

    return (
        NonlinearFailureReason.INF_DETECTED
        if np.any(np.isinf(np.asarray(values)))
        else NonlinearFailureReason.NAN_DETECTED
    )


def _line_search_assembly(
    assembly: NonlinearAssemblyProtocol,
    displacement: np.ndarray,
    free: np.ndarray,
    correction: np.ndarray,
    target: np.ndarray,
    residual_norm: float,
) -> np.ndarray:
    """Apply a bounded residual-decreasing line search to an assembly."""
    trial, _ = _line_search_assembly_with_diagnostics(
        assembly, displacement, free, correction, target, residual_norm
    )
    return trial


def _line_search_assembly_with_diagnostics(
    assembly: NonlinearAssemblyProtocol,
    displacement: np.ndarray,
    free: np.ndarray,
    correction: np.ndarray,
    target: np.ndarray,
    residual_norm: float,
) -> tuple[np.ndarray, int]:
    """Return the accepted trial and the number of reductions used."""
    alpha = 1.0
    for reductions in range(15):
        trial = displacement.copy()
        trial[free] += alpha * correction
        try:
            trial_internal, _ = assembly.assemble(trial, tangent_required=False)
        except ValueError:
            alpha *= 0.5
            continue
        if np.linalg.norm((target - trial_internal)[free]) < residual_norm:
            return trial, reductions
        alpha *= 0.5
    raise NumericalConvergenceError(
        "Full Newton line search failed to reduce the residual.",
        reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
    )


def line_search_factor(
    assemble: Callable[..., tuple[np.ndarray, object, MaterialStateTable]],
    model: FiniteElementModel,
    dofs: DofManager,
    displacement: np.ndarray,
    free: np.ndarray,
    target_load: np.ndarray,
    material_states: MaterialStateTable,
    increment: np.ndarray,
    residual_norm: float,
    min_alpha: float,
    max_reductions: int,
    armijo: float,
) -> tuple[float, int]:
    """Find an Armijo factor while keeping trial assembly delegated to the driver."""
    alpha = 1.0
    for reductions in range(max_reductions + 1):
        trial = displacement.copy()
        trial[free] += alpha * increment
        trial_internal, _, _ = assemble(model, dofs, trial, material_states)
        trial_norm = float(np.linalg.norm((target_load - trial_internal)[free]))
        if trial_norm <= (1.0 - armijo * alpha) * residual_norm:
            return alpha, reductions
        alpha *= 0.5
        if alpha < min_alpha:
            break
    raise NumericalConvergenceError(
        "Newton line-search failed to reduce the residual.",
        reason=NonlinearFailureReason.LINE_SEARCH_FAILURE,
    )


def solve_arc_length_correction(
    tangent: csr_matrix,
    reference_load: np.ndarray,
    residual: np.ndarray,
    delta_u_step: np.ndarray,
    delta_lambda: float,
    constraint: float,
    load_scale: float,
) -> tuple[np.ndarray, float]:
    """Solve the sparse augmented correction system for arc-length continuation.

    The augmented system has one extra scalar unknown, so its sparse block
    structure is retained instead of converting the global tangent to a dense
    array. This keeps the correction compatible with the sparse backend and
    makes accidental large-system densification testable.
    """
    size = residual.size
    if tangent.shape != (size, size):
        raise ValueError("Arc-length tangent shape must match the residual dimension.")
    if reference_load.shape != (size,) or delta_u_step.shape != (size,):
        raise ValueError("Arc-length vectors must have the reduced tangent dimension.")
    matrix = bmat(
        [
            [csr_matrix(tangent), csc_matrix((-reference_load).reshape(size, 1))],
            [csr_matrix((2.0 * delta_u_step).reshape(1, size)), csc_matrix([[2.0 * load_scale**2 * delta_lambda]])],
        ],
        format="csc",
    )
    rhs = np.concatenate((np.asarray(residual, dtype=float), np.asarray([-constraint], dtype=float)))
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", MatrixRankWarning)
            solution = spsolve(matrix, rhs)
    except (MatrixRankWarning, ValueError, RuntimeError) as exc:
        raise NumericalConvergenceError(
            "Arc-length augmented system is singular.",
            reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
        ) from exc
    if not np.all(np.isfinite(solution)):
        raise NumericalConvergenceError(
            "Arc-length correction produced non-finite values.",
            reason=NonlinearFailureReason.ARC_LENGTH_FAILURE,
        )
    return solution[:size], float(solution[size])
