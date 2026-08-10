"""First-ply failure indicators for linear orthotropic laminates."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite, sqrt

import numpy as np


@dataclass(frozen=True)
class PlyStrengths:
    """Positive material-axis stress allowables for one lamina.

    ``Xt``/``Xc`` and ``Yt``/``Yc`` are tensile/compressive magnitudes in
    axes 1 and 2. ``S12`` is the in-plane shear magnitude. ``f12_star``
    defines the normalized Tsai-Wu interaction coefficient.
    """

    Xt: float
    Xc: float
    Yt: float
    Yc: float
    S12: float
    f12_star: float = -0.5

    def __post_init__(self) -> None:
        values = (self.Xt, self.Xc, self.Yt, self.Yc, self.S12, self.f12_star)
        if not all(isfinite(value) for value in values):
            raise ValueError("Ply strengths must be finite.")
        if min(self.Xt, self.Xc, self.Yt, self.Yc, self.S12) <= 0.0:
            raise ValueError("Xt, Xc, Yt, Yc and S12 must be positive.")
        if not -1.0 < self.f12_star < 1.0:
            raise ValueError("f12_star must lie strictly between -1 and 1.")


@dataclass(frozen=True)
class PlyStrainAllowables:
    """Positive material-axis engineering-strain allowables."""

    e1t: float
    e1c: float
    e2t: float
    e2c: float
    g12: float

    def __post_init__(self) -> None:
        values = (self.e1t, self.e1c, self.e2t, self.e2c, self.g12)
        if not all(isfinite(value) for value in values):
            raise ValueError("Ply strain allowables must be finite.")
        if min(values) <= 0.0:
            raise ValueError("Ply strain allowables must be positive.")


@dataclass(frozen=True)
class FailureCriterionResult:
    """One non-degrading first-ply failure indicator."""

    criterion: str
    index: float
    reserve_factor: float | None
    margin_of_safety: float | None
    passed: bool
    components: dict[str, float]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class CompositeFailureEvaluator:
    """Evaluate documented first-ply criteria in material axes 1-2."""

    @staticmethod
    def maximum_stress(stress: np.ndarray, strengths: PlyStrengths) -> FailureCriterionResult:
        sigma1, sigma2, tau12 = _vector3(stress, "stress")
        components = {
            "fiber": sigma1 / strengths.Xt if sigma1 >= 0.0 else -sigma1 / strengths.Xc,
            "transverse": sigma2 / strengths.Yt if sigma2 >= 0.0 else -sigma2 / strengths.Yc,
            "shear": abs(tau12) / strengths.S12,
        }
        index = max(components.values())
        return _linear_result("maximum_stress", index, components)

    @staticmethod
    def maximum_strain(
        strain: np.ndarray,
        allowables: PlyStrainAllowables,
    ) -> FailureCriterionResult:
        epsilon1, epsilon2, gamma12 = _vector3(strain, "strain")
        components = {
            "fiber": epsilon1 / allowables.e1t if epsilon1 >= 0.0 else -epsilon1 / allowables.e1c,
            "transverse": epsilon2 / allowables.e2t if epsilon2 >= 0.0 else -epsilon2 / allowables.e2c,
            "shear": abs(gamma12) / allowables.g12,
        }
        index = max(components.values())
        return _linear_result("maximum_strain", index, components)

    @staticmethod
    def tsai_hill(stress: np.ndarray, strengths: PlyStrengths) -> FailureCriterionResult:
        sigma1, sigma2, tau12 = _vector3(stress, "stress")
        x = strengths.Xt if sigma1 >= 0.0 else strengths.Xc
        y = strengths.Yt if sigma2 >= 0.0 else strengths.Yc
        components = {
            "sigma1_squared": (sigma1 / x) ** 2,
            "interaction": -sigma1 * sigma2 / x**2,
            "sigma2_squared": (sigma2 / y) ** 2,
            "shear_squared": (tau12 / strengths.S12) ** 2,
        }
        index = max(sum(components.values()), 0.0)
        reserve = None if index == 0.0 else 1.0 / sqrt(index)
        return _result("tsai_hill", index, reserve, components)

    @staticmethod
    def tsai_wu(stress: np.ndarray, strengths: PlyStrengths) -> FailureCriterionResult:
        sigma1, sigma2, tau12 = _vector3(stress, "stress")
        f1 = 1.0 / strengths.Xt - 1.0 / strengths.Xc
        f2 = 1.0 / strengths.Yt - 1.0 / strengths.Yc
        f11 = 1.0 / (strengths.Xt * strengths.Xc)
        f22 = 1.0 / (strengths.Yt * strengths.Yc)
        f66 = 1.0 / strengths.S12**2
        f12 = strengths.f12_star * sqrt(f11 * f22)
        linear = f1 * sigma1 + f2 * sigma2
        quadratic = f11 * sigma1**2 + f22 * sigma2**2 + 2.0 * f12 * sigma1 * sigma2 + f66 * tau12**2
        components = {
            "linear": linear,
            "quadratic": quadratic,
            "F12": f12,
        }
        index = linear + quadratic
        reserve = _positive_tsai_wu_root(linear, quadratic)
        return _result("tsai_wu", index, reserve, components)

    @classmethod
    def evaluate(
        cls,
        stress: np.ndarray,
        strain: np.ndarray,
        strengths: PlyStrengths,
        strain_allowables: PlyStrainAllowables | None = None,
    ) -> tuple[FailureCriterionResult, ...]:
        results = [cls.maximum_stress(stress, strengths)]
        if strain_allowables is not None:
            results.append(cls.maximum_strain(strain, strain_allowables))
        results.extend((cls.tsai_hill(stress, strengths), cls.tsai_wu(stress, strengths)))
        return tuple(results)


def _vector3(value: np.ndarray, name: str) -> np.ndarray:
    result = np.asarray(value, dtype=float)
    if result.shape != (3,) or not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain three finite components.")
    return result


def _linear_result(criterion: str, index: float, components: dict[str, float]) -> FailureCriterionResult:
    reserve = None if index == 0.0 else 1.0 / index
    return _result(criterion, index, reserve, components)


def _result(
    criterion: str,
    index: float,
    reserve: float | None,
    components: dict[str, float],
) -> FailureCriterionResult:
    margin = None if reserve is None else reserve - 1.0
    return FailureCriterionResult(
        criterion=criterion,
        index=float(index),
        reserve_factor=None if reserve is None else float(reserve),
        margin_of_safety=None if margin is None else float(margin),
        passed=bool(index <= 1.0 + 1.0e-12),
        components={key: float(value) for key, value in components.items()},
    )


def _positive_tsai_wu_root(linear: float, quadratic: float) -> float | None:
    if abs(linear) + abs(quadratic) <= np.finfo(float).tiny:
        return None
    if abs(quadratic) <= np.finfo(float).eps:
        return 1.0 / linear if linear > 0.0 else None
    discriminant = linear**2 + 4.0 * quadratic
    if discriminant < 0.0:
        return None
    roots = (
        (-linear + sqrt(discriminant)) / (2.0 * quadratic),
        (-linear - sqrt(discriminant)) / (2.0 * quadratic),
    )
    positive = [root for root in roots if root > 0.0 and isfinite(root)]
    return min(positive) if positive else None
