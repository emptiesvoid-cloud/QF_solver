"""Independent NumPy reference for the WP09 co-rotational J2 kernel.

This module is intentionally self-contained.  It does not import production
element, material, assembly, or solver code.  Its purpose is to provide a
transparent material-point/reference-path recomputation for the bounded WP09
benchmark, not an independent global FEM solve.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np


Array = np.ndarray
State = dict[str, Any]


def _array(value: Any, shape: tuple[int, ...] | None = None) -> Array:
    result = np.asarray(value, dtype=float)
    if shape is not None and result.shape != shape:
        raise ValueError(f"expected shape {shape}, received {result.shape}")
    if not np.all(np.isfinite(result)):
        raise ValueError("reference input contains a non-finite value")
    return result


def polar_decomposition(deformation_gradient: Any) -> tuple[Array, Array, float]:
    """Return the proper rotation, right stretch, and determinant of ``F``."""

    F = _array(deformation_gradient, (3, 3))
    left, singular_values, right_transpose = np.linalg.svd(F)
    R = left @ right_transpose
    if np.linalg.det(R) < 0.0:
        left = left.copy()
        left[:, -1] *= -1.0
        singular_values = singular_values.copy()
        singular_values[-1] *= -1.0
        R = left @ right_transpose
    V = right_transpose.T @ np.diag(singular_values) @ right_transpose
    V = 0.5 * (V + V.T)
    determinant = float(np.linalg.det(F))
    if determinant <= 0.0:
        raise ValueError("reference deformation gradient has non-positive determinant")
    return R, V, determinant


def strain_voigt(tensor: Any) -> Array:
    """Convert a symmetric tensor to engineering-strain Voigt ordering."""

    value = _array(tensor, (3, 3))
    return np.array(
        [
            value[0, 0],
            value[1, 1],
            value[2, 2],
            2.0 * value[0, 1],
            2.0 * value[1, 2],
            2.0 * value[0, 2],
        ],
        dtype=float,
    )


def stress_voigt(tensor: Any) -> Array:
    """Convert a symmetric stress tensor to Voigt ordering."""

    value = _array(tensor, (3, 3))
    return np.array(
        [
            value[0, 0],
            value[1, 1],
            value[2, 2],
            value[0, 1],
            value[1, 2],
            value[0, 2],
        ],
        dtype=float,
    )


def strain_tensor(voigt: Any) -> Array:
    """Convert engineering-strain Voigt ordering to a symmetric tensor."""

    value = _array(voigt, (6,))
    return np.array(
        [
            [value[0], 0.5 * value[3], 0.5 * value[5]],
            [0.5 * value[3], value[1], 0.5 * value[4]],
            [0.5 * value[5], 0.5 * value[4], value[2]],
        ],
        dtype=float,
    )


def stress_tensor(voigt: Any) -> Array:
    """Convert stress Voigt ordering to a symmetric tensor."""

    value = _array(voigt, (6,))
    return np.array(
        [
            [value[0], value[3], value[5]],
            [value[3], value[1], value[4]],
            [value[5], value[4], value[2]],
        ],
        dtype=float,
    )


def _elasticity_matrix(young: float, poisson: float) -> Array:
    if young <= 0.0 or not (-1.0 < poisson < 0.5):
        raise ValueError("invalid isotropic elastic constants")
    factor = young / ((1.0 + poisson) * (1.0 - 2.0 * poisson))
    lame = poisson * factor
    shear = young / (2.0 * (1.0 + poisson))
    matrix: Array = np.zeros((6, 6), dtype=float)
    matrix[:3, :3] = lame
    matrix[0, 0] += 2.0 * shear
    matrix[1, 1] += 2.0 * shear
    matrix[2, 2] += 2.0 * shear
    matrix[3, 3] = shear
    matrix[4, 4] = shear
    matrix[5, 5] = shear
    return matrix


def initial_state() -> State:
    """Return a fresh zero plastic state for the reference path."""

    return {
        "equivalent_plastic_strain": 0.0,
        "plastic_strain": np.zeros(6, dtype=float),
        "plastic_dissipation": 0.0,
        "strain": np.zeros(6, dtype=float),
        "stress": np.zeros(6, dtype=float),
    }


def transport_state(state: State | None, rotation: Any) -> State | None:
    """Transport tensorial history into the current co-rotated frame."""

    if state is None:
        return None
    R = _array(rotation, (3, 3))
    transported = deepcopy(state)
    old_rotation = _array(state.get("corotation", np.eye(3)), (3, 3))
    relative = R.T @ old_rotation

    for field, converter in (
        ("plastic_strain", strain_tensor),
        ("stress", stress_tensor),
        ("strain", strain_tensor),
    ):
        if field in state:
            tensor = converter(state[field])
            transported[field] = strain_voigt(relative @ tensor @ relative.T) if field in {
                "plastic_strain",
                "strain",
            } else stress_voigt(relative @ tensor @ relative.T)
    transported["corotation"] = R.copy()
    return transported


def integrate_j2(
    local_strain: Any,
    state: State | None,
    *,
    young: float,
    poisson: float,
    yield_stress: float,
    hardening_modulus: float,
) -> tuple[Array, State]:
    """Apply the additive small-strain radial-return J2 update independently."""

    strain = _array(local_strain, (6,))
    if yield_stress <= 0.0 or hardening_modulus < 0.0:
        raise ValueError("invalid J2 parameters")
    old = initial_state() if state is None else deepcopy(state)
    old_plastic = _array(old.get("plastic_strain", np.zeros(6)), (6,))
    old_equivalent = float(old.get("equivalent_plastic_strain", 0.0))
    old_dissipation = float(old.get("plastic_dissipation", 0.0))
    old_stress = _array(old.get("stress", np.zeros(6)), (6,))
    if old_equivalent < 0.0 or old_dissipation < 0.0:
        raise ValueError("invalid reference state")

    trial = _elasticity_matrix(young, poisson) @ (strain - old_plastic)
    trial_tensor = stress_tensor(trial)
    mean = float(np.trace(trial_tensor) / 3.0)
    deviator = trial_tensor - mean * np.eye(3)
    q_trial = float(np.sqrt(1.5 * np.sum(deviator * deviator)))
    current_yield = float(yield_stress + hardening_modulus * old_equivalent)
    yield_function = q_trial - current_yield

    updated = deepcopy(old)
    updated["strain"] = strain.copy()
    updated["model"] = "von_mises_elastoplastic"
    updated["yield_stress"] = current_yield
    updated["elastic"] = bool(yield_function <= 0.0)

    if yield_function <= 0.0:
        stress = trial
        equivalent = old_equivalent
        plastic_strain = old_plastic
        dissipation = old_dissipation
        delta_gamma = 0.0
        equivalent_stress = q_trial
    else:
        shear = young / (2.0 * (1.0 + poisson))
        delta_gamma = float(yield_function / (3.0 * shear + hardening_modulus))
        equivalent = old_equivalent + delta_gamma
        equivalent_stress = float(yield_stress + hardening_modulus * equivalent)
        if q_trial <= 0.0:
            raise ValueError("plastic reference update has zero trial deviator")
        updated_deviator = (equivalent_stress / q_trial) * deviator
        stress_tensor_value = updated_deviator + mean * np.eye(3)
        stress = stress_voigt(stress_tensor_value)
        plastic_increment_tensor = 1.5 * delta_gamma * deviator / q_trial
        plastic_strain = old_plastic + strain_voigt(plastic_increment_tensor)
        dissipation = old_dissipation + float(
            0.5 * np.dot(old_stress + stress, strain_voigt(plastic_increment_tensor))
        )
        updated["yield_function"] = 0.0

    updated["stress"] = stress.copy()
    updated["equivalent_stress"] = equivalent_stress
    updated["yield_stress"] = float(yield_stress + hardening_modulus * equivalent)
    updated["yield_function"] = float(equivalent_stress - updated["yield_stress"])
    updated["plastic_multiplier"] = delta_gamma
    updated["equivalent_plastic_strain"] = equivalent
    updated["plastic_strain"] = plastic_strain.copy()
    updated["plastic_dissipation"] = dissipation
    return stress, updated


def evaluate_corotational_history(
    deformation_gradients: list[Any],
    *,
    young: float,
    poisson: float,
    yield_stress: float,
    hardening_modulus: float,
    max_strain_norm: float = 0.25,
) -> list[dict[str, Any]]:
    """Evaluate a finite deformation path with the frozen WP09 equations."""

    history: list[dict[str, Any]] = []
    committed: State | None = None
    for index, deformation_gradient in enumerate(deformation_gradients):
        F = _array(deformation_gradient, (3, 3))
        rotation, stretch, determinant = polar_decomposition(F)
        local_strain = strain_voigt(stretch - np.eye(3))
        if float(np.linalg.norm(local_strain)) > max_strain_norm:
            raise ValueError("reference local strain exceeds the frozen bound")
        transported = transport_state(committed, rotation)
        local_stress, state = integrate_j2(
            local_strain,
            transported,
            young=young,
            poisson=poisson,
            yield_stress=yield_stress,
            hardening_modulus=hardening_modulus,
        )
        state["corotation"] = rotation.copy()
        state["kinematics"] = "corotational_small_strain"
        first_piola = rotation @ stress_tensor(local_stress)
        cauchy = first_piola @ F.T / determinant
        history.append(
            {
                "index": index,
                "deformation_gradient": F.copy(),
                "rotation": rotation.copy(),
                "stretch": stretch.copy(),
                "local_strain": local_strain.copy(),
                "local_stress": local_stress.copy(),
                "cauchy_stress": cauchy.copy(),
                "equivalent_stress": float(state["equivalent_stress"]),
                "equivalent_plastic_strain": float(state["equivalent_plastic_strain"]),
                "yield_function": float(state["yield_function"]),
                "plastic_dissipation": float(state["plastic_dissipation"]),
                "state": state,
            }
        )
        committed = state
    return history


def von_mises(stress: Any) -> float:
    """Return the von Mises invariant of a symmetric stress tensor/Voigt vector."""

    tensor = stress_tensor(stress) if np.asarray(stress).shape == (6,) else _array(stress, (3, 3))
    deviator = tensor - np.trace(tensor) / 3.0 * np.eye(3)
    return float(np.sqrt(1.5 * np.sum(deviator * deviator)))
