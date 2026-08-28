"""Validated controls for nonlinear load stepping."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.core.nonlinear.material_state import MaterialStateTable


@dataclass(frozen=True)
class NonlinearSolverOptions:
    """Validated snapshot of the common Newton controls.

    The defaults intentionally mirror the legacy parameter extraction so this
    first migration changes ownership of configuration, not numerical results.
    """

    load_steps: int = 1
    max_iterations: int = 25
    tolerance: float = 1.0e-8
    linear_method: str = "direct"
    line_search_min_alpha: float = 1.0e-4
    line_search_max_reductions: int = 12
    line_search_c: float = 1.0e-4
    adaptive_load_steps: bool = False

    @classmethod
    def from_parameters(cls, parameters: dict[str, object]) -> "NonlinearSolverOptions":
        """Build options with the compatibility defaults of the current solver."""
        return cls(
            load_steps=max(1, int(parameters.get("load_steps", 1))),
            max_iterations=max(1, int(parameters.get("max_iterations", 25))),
            tolerance=float(parameters.get("tolerance", 1.0e-8)),
            linear_method=str(parameters.get("linear_method", "direct")).lower(),
            line_search_min_alpha=float(parameters.get("line_search_min_alpha", 1.0e-4)),
            line_search_max_reductions=max(0, int(parameters.get("line_search_max_reductions", 12))),
            line_search_c=float(parameters.get("line_search_c", 1.0e-4)),
            adaptive_load_steps=bool(parameters.get("adaptive_load_steps", False)),
        )


@dataclass(frozen=True)
class NonlinearStep:
    """Convergence data for one committed load step."""

    step: int
    load_factor: float
    iterations: int
    residual_norm: float
    relative_residual: float
    line_search_reductions: int = 0
    min_line_search_factor: float = 1.0
    load_increment: float = 0.0
    equivalent_plastic_strain_max: float = 0.0
    state_committed: bool = True
    last_correction_norm: float = 0.0
    cumulative_correction_norm: float = 0.0
    incremental_internal_work: float = 0.0
    incremental_external_work: float = 0.0
    relative_work_imbalance: float = 0.0
    load_step_cutbacks: int = 0
    work_diagnostics_available: bool = False
    residual_initial: float = 0.0
    failure_reason: str | None = None
    residual_history: tuple[float, ...] = ()
    plastic_dissipation_max: float = 0.0
    assembly_seconds: float = 0.0
    linear_solve_seconds: float = 0.0
    line_search_seconds: float = 0.0
    element_setup_seconds: float = 0.0
    element_kernel_seconds: float = 0.0
    element_scatter_seconds: float = 0.0
    sparse_conversion_seconds: float = 0.0
    contact_assembly_seconds: float = 0.0
    element_kernel_calls: int = 0
    contact_assembly_calls: int = 0
    element_cache_hits: int = 0
    element_cache_misses: int = 0
    reference_cache_hits: int = 0
    reference_cache_misses: int = 0
    sparse_chunk_count: int = 0
    sparse_peak_chunk_entries: int = 0
    sparse_peak_chunk_bytes_estimate: int = 0
    sparse_accumulator_levels: int = 0
    tangent_nnz: int = 0
    contact_active_contacts: tuple[int, ...] = ()
    contact_gaps: tuple[float, ...] = ()
    contact_tangent_nnz: int = 0
    contact_master_face_indices: tuple[int, ...] = ()
    contact_search_mode: str | None = None
    contact_finite_sliding: bool = False
    contact_projection_clamped: tuple[bool, ...] = ()
    contact_closest_distances: tuple[float, ...] = ()
    contact_projection_modes: tuple[str, ...] = ()
    arc_length_radius: float | None = None
    arc_length_control_displacement: float | None = None
    arc_length_predictor_sign: int | None = None
    arc_length_branch_direction: int | None = None
    arc_length_direction_alignment: float | None = None
    arc_length_constraint_residual: float | None = None

    def to_dict(self) -> dict[str, float | int | bool | str | None]:
        return {
            "step": self.step,
            "load_factor": self.load_factor,
            "iterations": self.iterations,
            "residual_norm": self.residual_norm,
            "relative_residual": self.relative_residual,
            "line_search_reductions": self.line_search_reductions,
            "min_line_search_factor": self.min_line_search_factor,
            "load_increment": self.load_increment,
            "arc_length_radius": self.arc_length_radius,
            "equivalent_plastic_strain_max": self.equivalent_plastic_strain_max,
            "state_committed": self.state_committed,
            "last_correction_norm": self.last_correction_norm,
            "cumulative_correction_norm": self.cumulative_correction_norm,
            "incremental_internal_work": self.incremental_internal_work,
            "incremental_external_work": self.incremental_external_work,
            "relative_work_imbalance": self.relative_work_imbalance,
            "load_step_cutbacks": self.load_step_cutbacks,
            "work_diagnostics_available": self.work_diagnostics_available,
            "residual_initial": self.residual_initial,
            "failure_reason": self.failure_reason,
            "residual_history": list(self.residual_history),
            "plastic_dissipation_max": self.plastic_dissipation_max,
            "assembly_seconds": self.assembly_seconds,
            "linear_solve_seconds": self.linear_solve_seconds,
            "line_search_seconds": self.line_search_seconds,
            "element_setup_seconds": self.element_setup_seconds,
            "element_kernel_seconds": self.element_kernel_seconds,
            "element_scatter_seconds": self.element_scatter_seconds,
            "sparse_conversion_seconds": self.sparse_conversion_seconds,
            "contact_assembly_seconds": self.contact_assembly_seconds,
            "element_kernel_calls": self.element_kernel_calls,
            "contact_assembly_calls": self.contact_assembly_calls,
            "element_cache_hits": self.element_cache_hits,
            "element_cache_misses": self.element_cache_misses,
            "reference_cache_hits": self.reference_cache_hits,
            "reference_cache_misses": self.reference_cache_misses,
            "sparse_chunk_count": self.sparse_chunk_count,
            "sparse_peak_chunk_entries": self.sparse_peak_chunk_entries,
            "sparse_peak_chunk_bytes_estimate": self.sparse_peak_chunk_bytes_estimate,
            "sparse_accumulator_levels": self.sparse_accumulator_levels,
            "tangent_nnz": self.tangent_nnz,
            "contact_active_contacts": list(self.contact_active_contacts),
            "contact_gaps": list(self.contact_gaps),
            "contact_tangent_nnz": self.contact_tangent_nnz,
            "contact_master_face_indices": list(self.contact_master_face_indices),
            "contact_search_mode": self.contact_search_mode,
            "contact_finite_sliding": self.contact_finite_sliding,
            "contact_projection_clamped": list(self.contact_projection_clamped),
            "contact_closest_distances": list(self.contact_closest_distances),
            "contact_projection_modes": list(self.contact_projection_modes),
            "arc_length_control_displacement": self.arc_length_control_displacement,
            "arc_length_predictor_sign": self.arc_length_predictor_sign,
            "arc_length_branch_direction": self.arc_length_branch_direction,
            "arc_length_direction_alignment": self.arc_length_direction_alignment,
            "arc_length_constraint_residual": self.arc_length_constraint_residual,
        }


@dataclass(frozen=True)
class AdaptiveLoadControls:
    """Numerical controls for adaptive load increments."""

    initial_increment: float
    minimum_increment: float
    maximum_increment: float
    cutback_factor: float
    growth_factor: float
    grow_below_iterations: int
    shrink_above_iterations: int
    maximum_cutbacks: int

    @classmethod
    def from_parameters(
        cls,
        parameters: dict[str, object],
        *,
        load_steps: int,
        max_iterations: int,
    ) -> AdaptiveLoadControls:
        """Build controls and reject inconsistent nonlinear settings."""
        default_increment = 1.0 / load_steps
        initial = _finite_float(parameters, "initial_load_increment", default_increment)
        minimum = _finite_float(parameters, "min_load_increment", min(1.0e-4, initial))
        maximum = _finite_float(parameters, "max_load_increment", max(initial, default_increment))
        cutback = _finite_float(parameters, "cutback_factor", 0.5)
        growth = _finite_float(parameters, "growth_factor", 1.5)
        grow_below = _integer(parameters, "grow_below_iterations", max(2, max_iterations // 4))
        shrink_above = _integer(parameters, "shrink_above_iterations", max(3, max_iterations // 2))
        maximum_cutbacks = _integer(parameters, "max_cutbacks", 25)

        if minimum <= 0.0 or initial <= 0.0 or maximum <= 0.0:
            raise InputValidationError("Adaptive load increments must be strictly positive.")
        if not minimum <= initial <= maximum:
            raise InputValidationError(
                "Adaptive increments must satisfy min_load_increment <= initial_load_increment "
                "<= max_load_increment."
            )
        if not 0.0 < cutback < 1.0:
            raise InputValidationError("cutback_factor must be strictly between 0 and 1.")
        if growth < 1.0:
            raise InputValidationError("growth_factor must be greater than or equal to 1.")
        if grow_below < 0 or shrink_above < 1 or grow_below >= shrink_above:
            raise InputValidationError(
                "Adaptive iteration thresholds must satisfy 0 <= grow_below_iterations "
                "< shrink_above_iterations."
            )
        if maximum_cutbacks < 0:
            raise InputValidationError("max_cutbacks must be greater than or equal to zero.")
        return cls(
            initial,
            minimum,
            maximum,
            cutback,
            growth,
            grow_below,
            shrink_above,
            maximum_cutbacks,
        )


@dataclass(frozen=True)
class ArcLengthControls:
    """Validated controls for optional arc-length radius adaptation."""

    adaptive_radius: bool
    minimum_radius: float
    growth_factor: float
    shrink_factor: float
    grow_below_iterations: int
    shrink_above_iterations: int

    @classmethod
    def from_parameters(
        cls,
        parameters: dict[str, object],
        *,
        max_iterations: int,
    ) -> "ArcLengthControls":
        """Build radius controls without changing legacy fixed-radius defaults."""
        minimum = _finite_float(parameters, "min_arc_length_radius", 1.0e-10)
        growth = _finite_float(parameters, "arc_length_growth_factor", 1.5)
        shrink = _finite_float(parameters, "arc_length_shrink_factor", 0.5)
        grow_below = _integer(
            parameters,
            "arc_length_grow_below_iterations",
            max(2, max_iterations // 4),
        )
        shrink_above = _integer(
            parameters,
            "arc_length_shrink_above_iterations",
            max(3, max_iterations // 2),
        )
        if minimum <= 0.0:
            raise InputValidationError("min_arc_length_radius must be strictly positive.")
        if growth < 1.0:
            raise InputValidationError("arc_length_growth_factor must be greater than or equal to 1.")
        if not 0.0 < shrink < 1.0:
            raise InputValidationError("arc_length_shrink_factor must be strictly between 0 and 1.")
        if grow_below < 0 or shrink_above < 1 or grow_below >= shrink_above:
            raise InputValidationError(
                "Arc-length iteration thresholds must satisfy 0 <= "
                "arc_length_grow_below_iterations < arc_length_shrink_above_iterations."
            )
        return cls(
            adaptive_radius=bool(parameters.get("adaptive_arc_length", False)),
            minimum_radius=minimum,
            growth_factor=growth,
            shrink_factor=shrink,
            grow_below_iterations=grow_below,
            shrink_above_iterations=shrink_above,
        )


def validated_load_path(parameters: dict[str, object], load_steps: int) -> list[float] | None:
    """Return a finite signed load path or reject malformed input."""
    raw = parameters.get("load_path")
    if raw is None:
        return None
    if not isinstance(raw, list) or not raw:
        raise InputValidationError("analysis.load_path must be a non-empty list of finite load factors.")
    factors: list[float] = []
    for index, value in enumerate(raw):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not np.isfinite(float(value)):
            raise InputValidationError(f"analysis.load_path[{index}] must be a finite scalar load factor.")
        factors.append(float(value))
    if len(factors) > max(10000, 10 * load_steps):
        raise InputValidationError("analysis.load_path contains an unreasonable number of increments.")
    return factors


def incremental_work_diagnostics(
    base_displacement: np.ndarray,
    displacement: np.ndarray,
    base_internal: np.ndarray,
    internal: np.ndarray,
    previous_load: np.ndarray,
    target_load: np.ndarray,
) -> tuple[float, float, float]:
    """Integrate force work over one converged increment by the trapezoidal rule."""
    increment = displacement - base_displacement
    internal_work = 0.5 * float((base_internal + internal) @ increment)
    external_work = 0.5 * float((previous_load + target_load) @ increment)
    scale = max(abs(internal_work), abs(external_work), np.finfo(float).tiny)
    return internal_work, external_work, abs(internal_work - external_work) / scale


def maximum_equivalent_plastic_strain(states: MaterialStateTable) -> float:
    """Return the largest committed equivalent plastic strain."""
    values = [
        float(state.get("equivalent_plastic_strain", 0.0))
        for integration_states in states.values()
        for state in integration_states
    ]
    return max(values, default=0.0)


def maximum_plastic_dissipation(states: MaterialStateTable) -> float:
    """Return the maximum accumulated material-point plastic dissipation."""
    values = [
        float(state.get("plastic_dissipation", 0.0))
        for integration_states in states.values()
        for state in integration_states
    ]
    return max(values, default=0.0)


def _finite_float(parameters: dict[str, object], key: str, default: float) -> float:
    value = parameters.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)):
        raise InputValidationError(f"{key} must be a finite scalar.")
    return float(value)


def _integer(parameters: dict[str, object], key: str, default: int) -> int:
    value = parameters.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise InputValidationError(f"{key} must be an integer.")
    return int(value)
