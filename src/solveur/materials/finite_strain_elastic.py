"""Isolated material-point kernels for Total-Lagrangian elastic laws.

These kernels do not register with or alter an element, Newton, public-solver,
or result-serialization route.  They use reference-configuration kinematics and
return full tensor stress/tangent fields so that stress measures are explicit.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

import numpy as np


@dataclass(frozen=True)
class FiniteStrainElasticResponse:
    """Material-point response with explicit finite-strain measures.

    Stress components and tangent entries use the caller's consistent stress
    unit (normally Pa); ``strain_energy_density`` uses stress units, e.g. J/m³.
    Tensor axes are in the reference frame except ``cauchy_stress``, whose two
    axes are in the current frame.  Tangents are full fourth-order tensors.
    """

    deformation_gradient: np.ndarray
    green_lagrange_strain: np.ndarray
    jacobian_determinant: float
    strain_energy_density: float
    second_piola_kirchhoff_stress: np.ndarray
    first_piola_kirchhoff_stress: np.ndarray
    cauchy_stress: np.ndarray
    material_tangent_dS_dE: np.ndarray
    first_piola_tangent_dP_dF: np.ndarray


def _validated_lame_parameters(lambda_lame: float, mu: float) -> tuple[float, float]:
    try:
        lam = float(lambda_lame)
        shear = float(mu)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Lamé parameters must be finite real scalars.") from error
    if not isfinite(lam) or not isfinite(shear):
        raise ValueError("Lamé parameters must be finite.")
    if shear <= 0.0 or lam + (2.0 / 3.0) * shear <= 0.0:
        raise ValueError("Elasticity requires mu > 0 and bulk modulus lambda + 2 mu / 3 > 0.")
    return lam, shear


def _validated_bulk_shear(bulk_modulus: float, mu: float) -> tuple[float, float]:
    try:
        bulk = float(bulk_modulus)
        shear = float(mu)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Bulk and shear moduli must be finite real scalars.") from error
    if not isfinite(bulk) or not isfinite(shear) or bulk <= 0.0 or shear <= 0.0:
        raise ValueError("Compressible Neo-Hookean elasticity requires K > 0 and mu > 0.")
    return bulk, shear


def _validated_deformation_gradient(value: np.ndarray) -> tuple[np.ndarray, float, float]:
    deformation = np.asarray(value, dtype=float)
    if deformation.shape != (3, 3) or not np.all(np.isfinite(deformation)):
        raise ValueError("Deformation gradient F must be a finite 3-by-3 tensor.")
    try:
        sign, log_j = np.linalg.slogdet(deformation)
    except np.linalg.LinAlgError as error:
        raise ValueError("Deformation gradient F is singular or invalid.") from error
    if sign <= 0.0 or not isfinite(float(log_j)):
        raise ValueError("Total-Lagrangian elasticity requires finite positive J = det(F).")
    # Exponentiating log(J) makes overflow/underflow explicit.  No arbitrary
    # physical J_min is imposed here; a route must declare its own admissible
    # lower bound if its application requires one.
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        jacobian = float(np.exp(log_j))
    if not isfinite(jacobian) or jacobian <= 0.0:
        raise ValueError("Positive J is outside the representable finite domain.")
    try:
        inverse = np.linalg.inv(deformation)
    except np.linalg.LinAlgError as error:
        raise ValueError("Deformation gradient F cannot be inverted reliably.") from error
    if not np.all(np.isfinite(inverse)):
        raise ValueError("Inverse deformation gradient is non-finite.")
    return deformation.copy(), jacobian, float(log_j)


def _elasticity_tensor(lambda_lame: float, mu: float) -> np.ndarray:
    identity = np.eye(3)
    return (
        lambda_lame * np.einsum("IJ,KL->IJKL", identity, identity)
        + mu * np.einsum("IK,JL->IJKL", identity, identity)
        + mu * np.einsum("IL,JK->IJKL", identity, identity)
    )


def _response(
    deformation: np.ndarray,
    jacobian: float,
    green: np.ndarray,
    energy: float,
    second: np.ndarray,
    first: np.ndarray,
    material_tangent: np.ndarray,
    first_tangent: np.ndarray,
) -> FiniteStrainElasticResponse:
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        cauchy = first @ deformation.T / jacobian
    arrays = (green, second, first, cauchy, material_tangent, first_tangent)
    if not isfinite(float(energy)) or any(not np.all(np.isfinite(item)) for item in arrays):
        raise ValueError("Finite-strain constitutive response is non-finite.")
    return FiniteStrainElasticResponse(
        deformation_gradient=deformation,
        green_lagrange_strain=green,
        jacobian_determinant=jacobian,
        strain_energy_density=float(energy),
        second_piola_kirchhoff_stress=second,
        first_piola_kirchhoff_stress=first,
        cauchy_stress=cauchy,
        material_tangent_dS_dE=material_tangent,
        first_piola_tangent_dP_dF=first_tangent,
    )


@dataclass(frozen=True)
class StVenantKirchhoff:
    """StVK material-point law, restricted to orientation-preserving F."""

    lambda_lame: float
    mu: float

    def __post_init__(self) -> None:
        _validated_lame_parameters(self.lambda_lame, self.mu)

    def evaluate(self, deformation_gradient: np.ndarray) -> FiniteStrainElasticResponse:
        """Evaluate W, S, P, Cauchy stress, and consistent material tangents."""
        lam, shear = _validated_lame_parameters(self.lambda_lame, self.mu)
        deformation, jacobian, _ = _validated_deformation_gradient(deformation_gradient)
        identity = np.eye(3)
        green = 0.5 * (deformation.T @ deformation - identity)
        elasticity = _elasticity_tensor(lam, shear)
        second = lam * float(np.trace(green)) * identity + 2.0 * shear * green
        first = deformation @ second
        energy = 0.5 * lam * float(np.trace(green)) ** 2 + shear * float(np.sum(green * green))
        first_tangent = np.einsum(
            "iA,AJBL,kB->iJkL", deformation, elasticity, deformation
        ) + np.einsum("ik,LJ->iJkL", identity, second)
        return _response(
            deformation,
            jacobian,
            green,
            energy,
            second,
            first,
            elasticity,
            first_tangent,
        )


@dataclass(frozen=True)
class CompressibleNeoHookean:
    r"""Isochoric/volumetric compressible Neo-Hookean material point.

    ``W = mu/2 (J^(-2/3) tr(C) - 3) + K/2 (ln J)^2``.
    Its domain is orientation-preserving, representable, nonsingular ``F``.
    This class intentionally has no application-independent positive ``J_min``.
    """

    bulk_modulus: float
    mu: float

    def __post_init__(self) -> None:
        _validated_bulk_shear(self.bulk_modulus, self.mu)

    def evaluate(self, deformation_gradient: np.ndarray) -> FiniteStrainElasticResponse:
        """Evaluate the energy, PK stresses, and exact consistent tangents."""
        bulk, shear = _validated_bulk_shear(self.bulk_modulus, self.mu)
        deformation, jacobian, log_j = _validated_deformation_gradient(deformation_gradient)
        identity = np.eye(3)
        right_cauchy_green = deformation.T @ deformation
        try:
            inverse_c = np.linalg.inv(right_cauchy_green)
        except np.linalg.LinAlgError as error:
            raise ValueError("Right Cauchy-Green tensor is singular or invalid.") from error
        with np.errstate(over="ignore", under="ignore", invalid="ignore"):
            isochoric_scale = float(np.exp(-(2.0 / 3.0) * log_j))
        if not isfinite(isochoric_scale) or isochoric_scale <= 0.0:
            raise ValueError("Isochoric Neo-Hookean scale is not representable.")
        green = 0.5 * (right_cauchy_green - identity)
        first_invariant = float(np.trace(right_cauchy_green))
        second = (
            shear * isochoric_scale * (identity - (first_invariant / 3.0) * inverse_c)
            + bulk * log_j * inverse_c
        )
        first = deformation @ second
        energy = (
            0.5 * shear * (isochoric_scale * first_invariant - 3.0)
            + 0.5 * bulk * log_j**2
        )
        material_tangent = 2.0 * shear * isochoric_scale * (
            -(1.0 / 3.0) * np.einsum("KL,IJ->IJKL", inverse_c, identity)
            + (first_invariant / 9.0) * np.einsum("KL,IJ->IJKL", inverse_c, inverse_c)
            - (1.0 / 3.0) * np.einsum("KL,IJ->IJKL", identity, inverse_c)
            + (first_invariant / 6.0)
            * (
                np.einsum("IK,LJ->IJKL", inverse_c, inverse_c)
                + np.einsum("IL,KJ->IJKL", inverse_c, inverse_c)
            )
        )
        material_tangent += (
            bulk * np.einsum("IJ,KL->IJKL", inverse_c, inverse_c)
            - bulk
            * log_j
            * (
                np.einsum("IK,JL->IJKL", inverse_c, inverse_c)
                + np.einsum("IL,JK->IJKL", inverse_c, inverse_c)
            )
        )
        first_tangent = np.einsum(
            "iA,AJBL,kB->iJkL", deformation, material_tangent, deformation
        ) + np.einsum("ik,LJ->iJkL", identity, second)
        return _response(
            deformation,
            jacobian,
            green,
            energy,
            second,
            first,
            material_tangent,
            first_tangent,
        )


__all__ = [
    "CompressibleNeoHookean",
    "FiniteStrainElasticResponse",
    "StVenantKirchhoff",
]
