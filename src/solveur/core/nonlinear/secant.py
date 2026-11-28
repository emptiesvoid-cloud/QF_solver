"""Detached secant initial guesses for bounded experimental Newton runs."""

from __future__ import annotations

import math

import numpy as np

from solveur.core.errors import InputValidationError
from solveur.core.nonlinear.state import NonlinearState


def secant_trial(
    previous: NonlinearState,
    accepted: NonlinearState,
    target_factor: float,
    fixed: np.ndarray,
) -> tuple[NonlinearState, float]:
    """Build a detached displacement predictor without mutating accepted data.

    The predictor is deliberately limited to stateless problems. A non-empty
    material or contact state needs a formulation-specific extrapolation and
    must not be silently copied from the current state.
    """

    previous.validate()
    accepted.validate()
    if (
        previous.displacement.shape != accepted.displacement.shape
        or previous.material_state
        or accepted.material_state
        or previous.contact_state
        or accepted.contact_state
    ):
        raise InputValidationError("The secant predictor requires matching stateless accepted states.")

    fixed_values = np.asarray(fixed)
    if (
        fixed_values.ndim != 1
        or fixed_values.dtype.kind not in "iu"
        or np.unique(fixed_values).size != fixed_values.size
        or np.any(fixed_values < 0)
        or np.any(fixed_values >= accepted.displacement.size)
        or not np.array_equal(previous.displacement[fixed_values], accepted.displacement[fixed_values])
    ):
        raise InputValidationError("The secant predictor received invalid or changing fixed degrees of freedom.")

    target = float(target_factor)
    previous_increment = accepted.load_factor - previous.load_factor
    next_increment = target - accepted.load_factor
    if (
        not math.isfinite(target)
        or not math.isfinite(previous_increment)
        or not math.isfinite(next_increment)
        or previous_increment <= 0.0
        or next_increment <= 0.0
    ):
        raise InputValidationError("Secant prediction requires finite, strictly increasing load factors.")

    ratio = next_increment / previous_increment
    if not math.isfinite(ratio) or ratio <= 0.0:
        raise InputValidationError("The secant predictor produced an invalid step ratio.")
    trial = accepted.detached_copy()
    trial.displacement = accepted.displacement + ratio * (accepted.displacement - previous.displacement)
    trial.displacement[fixed_values] = accepted.displacement[fixed_values]
    trial.validate()
    return trial, ratio
