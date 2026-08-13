"""Validated controls for nonlinear load stepping."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.core.material_state import MaterialStateTable


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

    def to_dict(self) -> dict[str, float | int]:
        return {
            "step": self.step,
            "load_factor": self.load_factor,
            "iterations": self.iterations,
            "residual_norm": self.residual_norm,
            "relative_residual": self.relative_residual,
            "line_search_reductions": self.line_search_reductions,
            "min_line_search_factor": self.min_line_search_factor,
            "load_increment": self.load_increment,
            "equivalent_plastic_strain_max": self.equivalent_plastic_strain_max,
            "state_committed": self.state_committed,
            "last_correction_norm": self.last_correction_norm,
            "cumulative_correction_norm": self.cumulative_correction_norm,
            "incremental_internal_work": self.incremental_internal_work,
            "incremental_external_work": self.incremental_external_work,
            "relative_work_imbalance": self.relative_work_imbalance,
            "load_step_cutbacks": self.load_step_cutbacks,
            "work_diagnostics_available": self.work_diagnostics_available,
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
