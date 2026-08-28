"""Validated damping calibration and multi-component dynamic load controls."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from solveur.core.errors import InputValidationError


@dataclass(frozen=True)
class RayleighDampingDefinition:
    """Rayleigh coefficients and their traceable source."""

    alpha: float
    beta: float
    source: str
    modal_targets: tuple[dict[str, float], ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "source": self.source,
            "rayleigh_alpha": self.alpha,
            "rayleigh_beta": self.beta,
            "modal_targets": list(self.modal_targets),
        }


def rayleigh_damping_definition(
    parameters: dict[str, object],
) -> RayleighDampingDefinition:
    """Return explicit coefficients or fit them to two modal damping targets."""
    raw_targets = parameters.get("modal_damping_targets")
    if raw_targets is None:
        alpha = _nonnegative_float(parameters.get("rayleigh_alpha", 0.0), "rayleigh_alpha")
        beta = _nonnegative_float(parameters.get("rayleigh_beta", 0.0), "rayleigh_beta")
        return RayleighDampingDefinition(alpha, beta, "explicit_rayleigh")
    if "rayleigh_alpha" in parameters or "rayleigh_beta" in parameters:
        raise InputValidationError(
            "modal_damping_targets cannot be combined with rayleigh_alpha or rayleigh_beta."
        )
    targets = _modal_targets(raw_targets)
    omegas = np.asarray([2.0 * math.pi * item["frequency_hz"] for item in targets])
    ratios = np.asarray([item["damping_ratio"] for item in targets])
    system = np.column_stack((0.5 / omegas, 0.5 * omegas))
    try:
        alpha, beta = np.linalg.solve(system, ratios)
    except np.linalg.LinAlgError as exc:
        raise InputValidationError(
            "modal_damping_targets frequencies must be distinct."
        ) from exc
    tolerance = 1.0e-12 * max(abs(float(alpha)), abs(float(beta)), 1.0)
    if alpha < -tolerance or beta < -tolerance:
        raise InputValidationError(
            "modal_damping_targets produce a negative Rayleigh coefficient; "
            "choose physically compatible frequencies and damping ratios."
        )
    return RayleighDampingDefinition(
        max(float(alpha), 0.0),
        max(float(beta), 0.0),
        "rayleigh_fitted_to_modal_targets",
        tuple(targets),
    )


def validate_per_load_factors(value: object, load_count: int) -> None:
    """Validate independent factor histories indexed by assembled load order."""
    if value is None:
        return
    if not isinstance(value, dict):
        raise InputValidationError("load_factors_by_load must be an object keyed by load index.")
    for raw_index, raw_factors in value.items():
        try:
            index = int(raw_index)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(
                f"load_factors_by_load key {raw_index!r} must be an integer index."
            ) from exc
        if str(index) != str(raw_index) or not 0 <= index < load_count:
            raise InputValidationError(
                f"load_factors_by_load index {raw_index!r} is outside 0..{load_count - 1}."
            )
        if not isinstance(raw_factors, list) or not raw_factors:
            raise InputValidationError(
                f"load_factors_by_load[{index}] must be a non-empty list."
            )
        try:
            factors = np.asarray(raw_factors, dtype=float)
        except (TypeError, ValueError) as exc:
            raise InputValidationError(
                f"load_factors_by_load[{index}] must contain numeric factors."
            ) from exc
        if factors.ndim != 1 or not np.all(np.isfinite(factors)):
            raise InputValidationError(
                f"load_factors_by_load[{index}] must contain finite scalar factors."
            )


def component_load_factors(
    value: object,
    load_count: int,
    step: int,
    fallback: float,
) -> list[float]:
    """Return one auditable factor per assembled load contribution."""
    if not isinstance(value, dict):
        return [float(fallback)] * load_count
    factors: list[float] = []
    for index in range(load_count):
        sequence = value.get(str(index))
        if sequence is None:
            factors.append(float(fallback))
            continue
        values = list(sequence)
        position = min(step, len(values) - 1)
        factors.append(float(values[position]))
    return factors


def _modal_targets(value: object) -> list[dict[str, float]]:
    if not isinstance(value, list) or len(value) != 2:
        raise InputValidationError("modal_damping_targets must contain exactly two targets.")
    targets: list[dict[str, float]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict) or set(item) != {"frequency_hz", "damping_ratio"}:
            raise InputValidationError(
                f"modal_damping_targets[{index}] must contain frequency_hz and damping_ratio."
            )
        frequency = _positive_float(item["frequency_hz"], f"modal_damping_targets[{index}].frequency_hz")
        ratio = _nonnegative_float(
            item["damping_ratio"], f"modal_damping_targets[{index}].damping_ratio"
        )
        targets.append({"frequency_hz": frequency, "damping_ratio": ratio})
    return targets


def _positive_float(value: object, name: str) -> float:
    result = _nonnegative_float(value, name)
    if result <= 0.0:
        raise InputValidationError(f"{name} must be positive.")
    return result


def _nonnegative_float(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise InputValidationError(f"{name} must be a finite non-negative number.") from exc
    if not np.isfinite(result) or result < 0.0:
        raise InputValidationError(f"{name} must be a finite non-negative number.")
    return result
