"""3D isotropic material definitions."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property
from typing import Protocol, runtime_checkable

import numpy as np

from solveur.core.nonlinear_contracts import ConstitutiveResponse


@runtime_checkable
class SolidConstitutiveMaterial(Protocol):
    """Runtime-checkable interface shared by isotropic and orthotropic solids."""

    density: float

    @property
    def elasticity_matrix(self) -> np.ndarray: ...

    def stress_tangent(self, strain: np.ndarray) -> tuple[np.ndarray, np.ndarray]: ...


@dataclass(frozen=True)
class SolidMaterial:
    """Linear isotropic 3D elastic material."""

    E: float
    nu: float
    density: float = 0.0

    def __post_init__(self) -> None:
        if self.E <= 0.0:
            raise ValueError("Young modulus E must be positive.")
        if not (-1.0 < self.nu < 0.5):
            raise ValueError("Poisson ratio nu must be in (-1, 0.5).")
        if self.density < 0.0:
            raise ValueError("Density must be non-negative.")

    @cached_property
    def elasticity_matrix(self) -> np.ndarray:
        factor = self.E / ((1.0 + self.nu) * (1.0 - 2.0 * self.nu))
        lam = self.nu * factor
        mu = self.E / (2.0 * (1.0 + self.nu))
        matrix = np.zeros((6, 6), dtype=float)
        matrix[:3, :3] = lam
        np.fill_diagonal(matrix[:3, :3], lam + 2.0 * mu)
        matrix[3, 3] = mu
        matrix[4, 4] = mu
        matrix[5, 5] = mu
        return matrix

    def stress_tangent(self, strain: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return Cauchy stress and tangent for small-strain linear elasticity."""
        tangent = self.elasticity_matrix
        return tangent @ np.asarray(strain, dtype=float), tangent

    def evaluate(
        self,
        strain: np.ndarray,
        committed_state: dict[str, object] | None = None,
    ) -> ConstitutiveResponse:
        """Evaluate through the common constitutive contract."""
        stress, tangent = self.stress_tangent(strain)
        return ConstitutiveResponse(stress, tangent, {}, {"stateful": False, "elastic": True})


@dataclass(frozen=True)
class NonlinearSolidMaterial(SolidMaterial):
    """Small-strain nonlinear elastic isotropic material with cubic hardening."""

    hardening: float = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.hardening < 0.0:
            raise ValueError("Hardening must be non-negative.")

    def stress_tangent(self, strain: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        strain = np.asarray(strain, dtype=float)
        elastic = self.elasticity_matrix
        strain_norm2 = float(strain @ strain)
        stress = elastic @ strain + self.hardening * strain_norm2 * strain
        tangent = elastic + self.hardening * (strain_norm2 * np.eye(6) + 2.0 * np.outer(strain, strain))
        return stress, tangent

    def evaluate(
        self,
        strain: np.ndarray,
        committed_state: dict[str, object] | None = None,
    ) -> ConstitutiveResponse:
        stress, tangent = self.stress_tangent(strain)
        return ConstitutiveResponse(stress, tangent, {}, {"stateful": False, "elastic": False})


@dataclass(frozen=True)
class VonMisesElastoplasticMaterial(SolidMaterial):
    """Small-strain J2 material with isotropic hardening and radial return."""

    yield_stress: float = 1.0
    hardening_modulus: float = 0.0

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.yield_stress <= 0.0:
            raise ValueError("Yield stress must be positive.")
        if self.hardening_modulus < 0.0:
            raise ValueError("Hardening modulus must be non-negative.")

    @property
    def shear_modulus(self) -> float:
        return self.E / (2.0 * (1.0 + self.nu))

    @property
    def bulk_modulus(self) -> float:
        return self.E / (3.0 * (1.0 - 2.0 * self.nu))

    def initial_state(self) -> dict[str, object]:
        return {"equivalent_plastic_strain": 0.0, "plastic_strain": [0.0] * 6}

    def stress_tangent(self, strain: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        stress, tangent, _ = self.stress_tangent_state(strain, self.initial_state())
        return stress, tangent

    def internal_state(self, strain: np.ndarray) -> dict[str, object]:
        _, _, state = self.stress_tangent_state(strain, self.initial_state())
        return state

    def stress_tangent_state(
        self,
        strain: np.ndarray,
        previous_state: dict[str, object] | None,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
        strain = np.asarray(strain, dtype=float)
        previous_state = previous_state or self.initial_state()
        old_plastic = np.asarray(previous_state.get("plastic_strain", [0.0] * 6), dtype=float)
        old_equivalent = float(previous_state.get("equivalent_plastic_strain", 0.0))
        trial = self.elasticity_matrix @ (strain - old_plastic)
        tensor = _voigt_stress_tensor(trial)
        mean = float(np.trace(tensor) / 3.0)
        deviator = tensor - mean * np.eye(3)
        q_trial = _von_mises_from_deviator(deviator)
        current_yield = self.yield_stress + self.hardening_modulus * old_equivalent
        yield_value = q_trial - current_yield
        if yield_value <= 0.0:
            state = {
                "model": "von_mises_isotropic_hardening",
                "elastic": True,
                "stress": trial.tolist(),
                "equivalent_stress": float(q_trial),
                "yield_stress": float(current_yield),
                "yield_function": float(yield_value),
                "plastic_multiplier": 0.0,
                "equivalent_plastic_strain": old_equivalent,
                "plastic_strain": old_plastic.tolist(),
            }
            return trial, self.elasticity_matrix, state
        shear = self.shear_modulus
        delta_gamma = yield_value / (3.0 * shear + self.hardening_modulus)
        equivalent = old_equivalent + delta_gamma
        q_updated = self.yield_stress + self.hardening_modulus * equivalent
        scale = q_updated / q_trial if q_trial > 0.0 else 0.0
        updated_deviator = scale * deviator
        stress_tensor = updated_deviator + mean * np.eye(3)
        plastic_increment = _plastic_strain_tensor(deviator, q_trial, delta_gamma)
        plastic_strain = _voigt_strain_tensor(old_plastic) + plastic_increment
        stress = _stress_tensor_to_voigt(stress_tensor)
        tangent = self._algorithmic_tangent(deviator, q_trial, delta_gamma)
        state = {
            "model": "von_mises_isotropic_hardening",
            "elastic": False,
            "stress": stress.tolist(),
            "equivalent_stress": float(q_updated),
            "yield_stress": float(q_updated),
            "yield_function": 0.0,
            "plastic_multiplier": float(delta_gamma),
            "equivalent_plastic_strain": float(equivalent),
            "plastic_strain": _strain_tensor_to_voigt(plastic_strain).tolist(),
        }
        return stress, tangent, state

    def evaluate(
        self,
        strain: np.ndarray,
        committed_state: dict[str, object] | None = None,
    ) -> ConstitutiveResponse:
        """Evaluate J2 from committed state without mutating that state."""
        stress, tangent, state = self.stress_tangent_state(strain, committed_state)
        return ConstitutiveResponse(
            stress,
            tangent,
            state,
            {
                "stateful": True,
                "elastic": bool(state.get("elastic", False)),
                "yield_function": float(state.get("yield_function", 0.0)),
            },
        )

    def _algorithmic_tangent(
        self,
        trial_deviator: np.ndarray,
        trial_equivalent_stress: float,
        plastic_multiplier: float,
    ) -> np.ndarray:
        """Return the consistent radial-return tangent in engineering Voigt form."""
        shear = self.shear_modulus
        hardening = self.hardening_modulus
        q_trial = float(trial_equivalent_stress)
        if q_trial <= np.finfo(float).eps:
            return self.elasticity_matrix

        radial_scale = 1.0 - 3.0 * shear * plastic_multiplier / q_trial
        scale_derivative = -3.0 * shear * (
            1.0 / (q_trial * (3.0 * shear + hardening)) - plastic_multiplier / q_trial**2
        )
        elastic = self.elasticity_matrix
        tangent = np.zeros((6, 6), dtype=float)
        identity = np.eye(3)
        for column in range(6):
            trial_increment = _voigt_stress_tensor(elastic[:, column])
            mean_increment = float(np.trace(trial_increment) / 3.0)
            deviator_increment = trial_increment - mean_increment * identity
            dq = 1.5 * float(np.sum(trial_deviator * deviator_increment)) / q_trial
            updated_increment = (
                mean_increment * identity
                + radial_scale * deviator_increment
                + scale_derivative * dq * trial_deviator
            )
            tangent[:, column] = _stress_tensor_to_voigt(updated_increment)
        return 0.5 * (tangent + tangent.T)


def _voigt_stress_tensor(values: np.ndarray) -> np.ndarray:
    sx, sy, sz, txy, tyz, txz = np.asarray(values, dtype=float)
    return np.array([[sx, txy, txz], [txy, sy, tyz], [txz, tyz, sz]], dtype=float)


def _stress_tensor_to_voigt(values: np.ndarray) -> np.ndarray:
    return np.array([values[0, 0], values[1, 1], values[2, 2], values[0, 1], values[1, 2], values[0, 2]], dtype=float)


def _strain_tensor_to_voigt(values: np.ndarray) -> np.ndarray:
    return np.array([values[0, 0], values[1, 1], values[2, 2], 2.0 * values[0, 1], 2.0 * values[1, 2], 2.0 * values[0, 2]], dtype=float)


def _voigt_strain_tensor(values: np.ndarray) -> np.ndarray:
    ex, ey, ez, gxy, gyz, gxz = np.asarray(values, dtype=float)
    return np.array([[ex, 0.5 * gxy, 0.5 * gxz], [0.5 * gxy, ey, 0.5 * gyz], [0.5 * gxz, 0.5 * gyz, ez]], dtype=float)


def _von_mises_from_deviator(deviator: np.ndarray) -> float:
    return float(np.sqrt(max(1.5 * float(np.sum(deviator * deviator)), 0.0)))


def _plastic_strain_tensor(deviator: np.ndarray, equivalent_stress: float, delta_gamma: float) -> np.ndarray:
    if equivalent_stress <= 0.0:
        return np.zeros((3, 3), dtype=float)
    return 1.5 * delta_gamma * deviator / equivalent_stress
