"""Independent continuum solution for a guided axial bar under end force."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

import numpy as np


ForceSegment = tuple[float, float, float, float]


def constrained_axial_modulus(young_modulus_pa: float, poisson_ratio: float) -> float:
    """Return lambda + 2 mu for a 3D isotropic bar guided in both transverse directions."""
    young = float(young_modulus_pa)
    nu = float(poisson_ratio)
    if not math.isfinite(young) or young <= 0.0:
        raise ValueError("Young's modulus must be finite and positive")
    if not math.isfinite(nu) or not -1.0 < nu < 0.5:
        raise ValueError("Poisson ratio must lie in (-1, 0.5)")
    lame_lambda = young * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
    shear_mu = young / (2.0 * (1.0 + nu))
    return lame_lambda + 2.0 * shear_mu


def _primitive(
    x: np.ndarray,
    time: np.ndarray,
    omega: float,
    slope: float,
    intercept: float,
) -> np.ndarray:
    """Antiderivative in x of ``F(time-x) * sin(omega*x)`` for affine F."""
    linear_at_time = slope * time + intercept
    return (
        -linear_at_time * np.cos(omega * x) / omega
        + slope * x * np.cos(omega * x) / omega
        - slope * np.sin(omega * x) / (omega * omega)
    )


def piecewise_linear_force_convolution(
    times_s: Sequence[float] | np.ndarray,
    omega_rad_s: float,
    segments: Iterable[ForceSegment],
) -> np.ndarray:
    """Evaluate ``integral F(s) sin(omega (t-s)) ds`` for piecewise-linear force."""
    times = np.asarray(times_s, dtype=np.float64)
    omega = float(omega_rad_s)
    if times.ndim != 1 or not np.all(np.isfinite(times)) or np.any(times < 0.0):
        raise ValueError("Times must be a finite, non-negative one-dimensional array")
    if not math.isfinite(omega) or omega <= 0.0:
        raise ValueError("Angular frequency must be finite and positive")

    result = np.zeros_like(times)
    previous_end = -math.inf
    for start, end, force_start, force_end in segments:
        start, end = float(start), float(end)
        force_start, force_end = float(force_start), float(force_end)
        if not all(math.isfinite(value) for value in (start, end, force_start, force_end)):
            raise ValueError("Force segments must contain finite values")
        if start < 0.0 or end <= start or start < previous_end:
            raise ValueError("Force segments must be non-negative, ordered, and have positive duration")
        previous_end = end
        slope = (force_end - force_start) / (end - start)
        intercept = force_start - slope * start
        upper = np.minimum(times, end)
        active = upper > start
        if not np.any(active):
            continue
        x_lower = times - upper
        x_upper = times - start
        segment_integral = _primitive(x_upper, times, omega, slope, intercept) - _primitive(
            x_lower, times, omega, slope, intercept
        )
        result += np.where(active, segment_integral, 0.0)
    return result


def axial_bar_response(
    times_s: Sequence[float] | np.ndarray,
    *,
    length_m: float,
    area_m2: float,
    density_kg_m3: float,
    axial_modulus_pa: float,
    force_segments: Sequence[ForceSegment],
    position_m: float,
    mode_count: int = 1024,
) -> np.ndarray:
    """Exact continuum displacement from the fixed-free axial-bar mode series.

    The force is the total axial end force in newtons. The bar is fixed at
    x=0 and uniformly loaded at x=L. Zero displacement and velocity are used
    initially. The series is independent of the QF assembled matrices.
    """
    length = float(length_m)
    area = float(area_m2)
    density = float(density_kg_m3)
    modulus = float(axial_modulus_pa)
    position = float(position_m)
    if not all(math.isfinite(value) for value in (length, area, density, modulus, position)):
        raise ValueError("Bar properties and position must be finite")
    if min(length, area, density, modulus) <= 0.0 or not 0.0 <= position <= length:
        raise ValueError("Bar dimensions/properties must be positive and position must lie within the bar")
    if isinstance(mode_count, bool) or mode_count <= 0:
        raise ValueError("mode_count must be a positive integer")

    times = np.asarray(times_s, dtype=np.float64)
    if times.ndim != 1:
        raise ValueError("Times must be one-dimensional")
    wave_speed = math.sqrt(modulus / density)
    response = np.zeros_like(times)
    modal_mass = density * area * length / 2.0
    for mode in range(int(mode_count)):
        wave_number = (mode + 0.5) * math.pi / length
        omega = wave_speed * wave_number
        convolution = piecewise_linear_force_convolution(times, omega, force_segments)
        generalized_force_sign = -1.0 if mode % 2 else 1.0
        modal_coordinate = generalized_force_sign * convolution / (modal_mass * omega)
        response += math.sin(wave_number * position) * modal_coordinate
    return response
