"""Linear harmonic frequency-response solver."""

from __future__ import annotations

import math
from time import perf_counter
import warnings
from typing import Any

import numpy as np
from scipy.sparse.linalg import MatrixRankWarning, spsolve

from solveur.core.assembler import GlobalAssembler
from solveur.core.audit import SolverAudit
from solveur.core.dynamic_reduction import DynamicDofReducer
from solveur.core.dynamic_controls import rayleigh_damping_definition
from solveur.core.errors import InputValidationError, MeshValidationError, NumericalConvergenceError
from solveur.core.linear_policy import LinearSolverPolicy, linear_execution_settings
from solveur.core.model import FiniteElementModel
from solveur.core.results import HarmonicResult
from solveur.mesh.validation import MeshValidator
from solveur.post.harmonic_shell import HarmonicShellStressPostProcessor


class HarmonicResponseSolver:
    """Solve steady-state linear response for harmonic nodal loading."""

    supported_methods = ("direct_frequency", "harmonic_direct")

    def __init__(self) -> None:
        self.validator = MeshValidator()
        self.assembler = GlobalAssembler()

    def solve(self, model: FiniteElementModel) -> HarmonicResult:
        if model.analysis.method not in self.supported_methods:
            raise InputValidationError(f"Unsupported harmonic method {model.analysis.method!r}.")
        report = self.validator.validate(model)
        if report.status == "FAIL":
            raise MeshValidationError("Mesh validation failed: " + "; ".join(report.errors))
        dofs = model.dof_manager()
        stiffness = self.assembler.assemble_stiffness(model, dofs)
        mass = self.assembler.assemble_mass(model, dofs)
        damping_definition = rayleigh_damping_definition(model.analysis.parameters)
        damping = (
            damping_definition.alpha * mass + damping_definition.beta * stiffness
        ).tocsr()
        loads = self.assembler.assemble_loads(model, dofs)
        fixed = self.assembler.fixed_indices(model, dofs)
        reducer = DynamicDofReducer.from_system(model, dofs, mass, stiffness, fixed)
        free = reducer.free
        alpha = damping_definition.alpha
        beta = damping_definition.beta
        reduced_stiffness = reducer.stiffness
        reduced_mass = reducer.mass
        reduced_damping = (alpha * reduced_mass + beta * reduced_stiffness).tocsr()
        reduced_loads = reducer.reduce_load(loads)

        frequencies = frequency_grid(model.analysis.parameters)
        responses: list[np.ndarray] = []
        residuals: list[float] = []
        relative_residuals: list[float] = []
        selections: list[dict[str, Any]] = []
        solve_seconds: list[float] = []
        for frequency in frequencies:
            omega = 2.0 * math.pi * frequency
            dynamic_stiffness = reduced_stiffness + (1j * omega) * reduced_damping
            dynamic_stiffness = dynamic_stiffness - (omega**2) * reduced_mass
            selection = LinearSolverPolicy.assess(dynamic_stiffness.tocsr(), model.analysis.method, model.analysis.parameters)
            selections.append({"frequency_hz": float(frequency), **selection.to_dict(used_method="spsolve")})
            solve_started = perf_counter()
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("error", MatrixRankWarning)
                    reduced_response = spsolve(dynamic_stiffness.astype(complex), reduced_loads.astype(complex))
            except MatrixRankWarning as exc:
                raise NumericalConvergenceError(
                    f"Harmonic dynamic stiffness is singular at {frequency:.9g} Hz."
                ) from exc
            except (FloatingPointError, RuntimeError, ValueError) as exc:
                raise NumericalConvergenceError(
                    f"Harmonic solve failed at {frequency:.9g} Hz: {exc}"
                ) from exc
            solve_seconds.append(perf_counter() - solve_started)
            if not np.all(np.isfinite(reduced_response)):
                raise NumericalConvergenceError(f"Harmonic solve produced non-finite response at {frequency:.9g} Hz.")
            response = reducer.expand_complex_state(
                reduced_response,
                loads,
                stiffness_factor=1.0 + 1j * omega * beta,
            )
            residual = stiffness @ response + 1j * omega * (damping @ response) - omega**2 * (mass @ response) - loads
            responses.append(response)
            residual_norm = float(np.linalg.norm(residual[free]))
            reference = max(float(np.linalg.norm(loads[free])), 1.0)
            relative_residual = residual_norm / reference
            limit = float(model.analysis.parameters.get("harmonic_residual_failure_tolerance", 1.0e-7))
            if not np.isfinite(relative_residual) or relative_residual > limit:
                raise NumericalConvergenceError(
                    f"Harmonic residual is abnormal at {frequency:.9g} Hz: "
                    f"relative={relative_residual:.6e}, allowed={limit:.6e}."
                )
            residuals.append(residual_norm)
            relative_residuals.append(relative_residual)

        audit = SolverAudit.from_state(
            model=model,
            dofs=dofs,
            report=report,
            fixed=fixed,
            free=free,
            method=model.analysis.method,
            vectors={"harmonic_load_amplitude": loads},
            load_assembly=self.assembler.last_load_diagnostics,
            matrices={
                "stiffness": stiffness,
                "mass": mass,
                "damping": damping,
                "reduced_stiffness": reduced_stiffness,
                "reduced_mass": reduced_mass,
                "reduced_damping": reduced_damping,
            },
            solver_selection=_harmonic_selection_summary(selections),
            notes=[
                "Harmonic response audit uses assembled real K, M, C matrices and complex solves per frequency.",
                "Massless shell drilling directions are statically condensed and reconstructed.",
                "Rayleigh stiffness damping uses the exact scalar harmonic condensation factor.",
            ],
        )
        shell_stress_response = HarmonicShellStressPostProcessor().frequency_results(
            model,
            dofs,
            frequencies,
            responses,
        )
        return HarmonicResult(
            status="PASS",
            frequencies_hz=frequencies,
            responses=responses,
            dofs=dofs,
            mesh_report=report,
            node_count=model.node_count,
            element_count=len(model.elements),
            method=model.analysis.method,
            solver={
                "method": model.analysis.method,
                "frequency_count": len(frequencies),
                "linear_selection": _harmonic_selection_summary(selections),
                "linear_execution": {
                    **linear_execution_settings(model.analysis.method, model.analysis.parameters),
                    "used_method": "spsolve",
                    "frequency_solve_seconds": solve_seconds,
                    "total_frequency_solve_seconds": float(sum(solve_seconds)),
                    "fallback_used": False,
                },
                "rayleigh_alpha": alpha,
                "rayleigh_beta": beta,
                "damping_definition": damping_definition.to_dict(),
                "residual_norms": residuals,
                "max_residual_norm": float(max(residuals) if residuals else 0.0),
                "relative_residual_norms": relative_residuals,
                "max_relative_residual_norm": float(
                    max(relative_residuals) if relative_residuals else 0.0
                ),
                "load_assembly": dict(self.assembler.last_load_diagnostics),
                "dynamic_reduction": dict(reducer.diagnostics),
                "harmonic_condensation": {
                    "strategy": "exact_scalar_schur_complement",
                    "stiffness_factor": "1 + i*omega*rayleigh_beta",
                    "supports_stiffness_proportional_damping": True,
                },
            },
            shell_stress_response=shell_stress_response,
            audit=audit,
        )


def _harmonic_selection_summary(selections: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize complex direct-solver decisions without duplicating result fields."""
    estimates = [
        int(dict(row.get("resource_estimate", {})).get("direct_memory_estimate_bytes", 0))
        for row in selections
    ]
    return {
        "requested_method": "direct_frequency",
        "used_method": "spsolve",
        "frequency_count": len(selections),
        "recommendation": "direct",
        "rationale": "complex dynamic stiffness is solved by the direct complex sparse route",
        "max_direct_memory_estimate_bytes": max(estimates, default=0),
        "direct_budget_exceeded": any(
            bool(dict(row.get("resource_estimate", {})).get("direct_budget_exceeded", False)) for row in selections
        ),
        "samples": selections,
    }


def frequency_grid(params: dict[str, Any]) -> np.ndarray:
    """Build the frequency vector for harmonic response in Hz."""
    if "frequencies_hz" in params:
        values = np.asarray(params["frequencies_hz"], dtype=float)
    else:
        start = float(params.get("frequency_start_hz", params.get("start_hz", 0.0)))
        stop = float(params.get("frequency_stop_hz", params.get("stop_hz", start)))
        count = max(1, int(params.get("frequency_count", params.get("count", 1))))
        values = np.linspace(start, stop, count)
    if values.ndim != 1 or values.size == 0:
        raise InputValidationError("Harmonic frequencies must be a non-empty one-dimensional list.")
    if np.any(values < 0.0) or not np.all(np.isfinite(values)):
        raise InputValidationError("Harmonic frequencies must be finite and non-negative.")
    return values
