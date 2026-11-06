"""Experimental 3D Hencky kinematics and elastic material-point response.

This module is intentionally isolated from material factories, global element
dispatch, Newton routes, and result serialization. It provides direct element
force algebra but no consistent tangent and must not be used by a solver route.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from numbers import Real

import numpy as np

_FLOAT_EPS = np.finfo(float).eps
_SPD_RESOLUTION_FACTOR = 64.0


def _finite_real_array(value: object, shape: tuple[int, ...], name: str) -> np.ndarray:
    """Return a finite float64 array without silently discarding complex parts."""
    try:
        raw = np.asarray(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite real array with shape {shape}.") from error
    if raw.shape != shape or raw.dtype.kind not in "fiu":
        raise ValueError(f"{name} must be a finite real array with shape {shape}.")
    try:
        result = np.asarray(raw, dtype=np.float64)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be representable as float64.") from error
    if not np.all(np.isfinite(result)):
        raise ValueError(f"{name} must contain only finite values.")
    return result.copy()


def _readonly(value: np.ndarray) -> np.ndarray:
    result = np.array(value, dtype=np.float64, copy=True)
    result.setflags(write=False)
    return result


def _validated_moduli(mu: object, kappa: object) -> tuple[float, float]:
    if (
        isinstance(mu, bool)
        or isinstance(kappa, bool)
        or not isinstance(mu, Real)
        or not isinstance(kappa, Real)
    ):
        raise ValueError("Hencky shear modulus mu and bulk modulus kappa must be real scalars in Pa.")
    shear, bulk = float(mu), float(kappa)
    if not isfinite(shear) or not isfinite(bulk) or shear <= 0.0 or bulk <= 0.0:
        raise ValueError("Hencky elasticity requires finite mu > 0 Pa and kappa > 0 Pa.")
    return shear, bulk


@dataclass(frozen=True)
class HenckyKinematics3D:
    """Spectral kinematics for one orientation-preserving deformation gradient.

    Principal stretches and logarithmic strains are ordered from smallest to
    largest. Tensor components use the reference basis. Arrays are read-only.
    """

    deformation_gradient: np.ndarray
    right_cauchy_green: np.ndarray
    jacobian_determinant: float
    principal_stretches: np.ndarray
    principal_logarithmic_strains: np.ndarray
    logarithmic_strain: np.ndarray


@dataclass(frozen=True)
class HenckyElasticResponse:
    """Experimental energy and stress response with explicit stress measures.

    Energy density and stresses use the input modulus unit (normally Pa, with
    energy density equivalently J/m^3). ``logarithmic_strain_conjugate_stress``
    is conjugate to E_H. PK2 is its chain-rule transform and is the stress
    measure required by a total-Lagrangian Green--Lagrange virtual-work form.
    No algorithmic or material tangent is supplied.
    """

    deformation_gradient: np.ndarray
    right_cauchy_green: np.ndarray
    jacobian_determinant: float
    principal_stretches: np.ndarray
    principal_logarithmic_strains: np.ndarray
    logarithmic_strain: np.ndarray
    strain_energy_density: float
    logarithmic_strain_conjugate_stress: np.ndarray
    second_piola_kirchhoff_stress: np.ndarray
    first_piola_kirchhoff_stress: np.ndarray
    cauchy_stress: np.ndarray
    tangent_status: str = "NOT_IMPLEMENTED"


def _validated_kinematics(
    deformation_gradient: object,
) -> tuple[np.ndarray, np.ndarray, float, np.ndarray, np.ndarray, np.ndarray]:
    deformation = _finite_real_array(deformation_gradient, (3, 3), "F")
    try:
        sign, log_j = np.linalg.slogdet(deformation)
    except np.linalg.LinAlgError as error:
        raise ValueError("F is singular or cannot be factored reliably.") from error
    if sign <= 0.0 or not isfinite(float(log_j)):
        raise ValueError("Hencky elasticity requires an orientation-preserving F with finite log(J).")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        jacobian = float(np.exp(log_j))
    if not isfinite(jacobian) or jacobian <= 0.0:
        raise ValueError("J = det(F) is outside the representable positive float64 range.")

    with np.errstate(over="ignore", invalid="ignore"):
        right_cauchy_green = deformation.T @ deformation
    if not np.all(np.isfinite(right_cauchy_green)):
        raise ValueError("C = F^T F is outside the finite float64 range.")
    right_cauchy_green = 0.5 * (right_cauchy_green + right_cauchy_green.T)
    try:
        eigenvalues, eigenvectors = np.linalg.eigh(right_cauchy_green)
    except np.linalg.LinAlgError as error:
        raise ValueError("C could not be resolved by symmetric spectral decomposition.") from error
    largest = float(eigenvalues[-1])
    smallest = float(eigenvalues[0])
    if not np.all(np.isfinite(eigenvalues)) or largest <= 0.0 or smallest <= 0.0:
        raise ValueError("C must be numerically positive definite; eigenvalues are not clipped.")
    # This relative threshold identifies loss of float64 spectral resolution;
    # it is not a physical minimum stretch or a universal element admissibility rule.
    if smallest <= _SPD_RESOLUTION_FACTOR * _FLOAT_EPS * largest:
        raise ValueError("C is too ill-conditioned for a resolved float64 logarithm.")

    principal_stretches = np.sqrt(eigenvalues)
    principal_logarithmic_strains = 0.5 * np.log(eigenvalues)
    logarithmic_strain = (eigenvectors * principal_logarithmic_strains) @ eigenvectors.T
    logarithmic_strain = 0.5 * (logarithmic_strain + logarithmic_strain.T)
    if not np.all(np.isfinite(logarithmic_strain)):
        raise ValueError("The spectral logarithmic strain is non-finite.")
    return (
        deformation,
        right_cauchy_green,
        jacobian,
        principal_stretches,
        principal_logarithmic_strains,
        logarithmic_strain,
    )


def hencky_kinematics_3d(deformation_gradient: object) -> HenckyKinematics3D:
    """Compute ``E_H = 1/2 log(F^T F)`` through a symmetric eigendecomposition.

    The operator rejects non-finite, singular, inverted, non-representable, or
    float64-unresolved inputs. No eigenvalue clipping or complex matrix log is
    used. The relative spectral-resolution factor is 64 machine epsilons.
    """
    deformation, right_cauchy_green, jacobian, stretches, principal, strain = _validated_kinematics(
        deformation_gradient
    )
    return HenckyKinematics3D(
        deformation_gradient=_readonly(deformation),
        right_cauchy_green=_readonly(right_cauchy_green),
        jacobian_determinant=jacobian,
        principal_stretches=_readonly(stretches),
        principal_logarithmic_strains=_readonly(principal),
        logarithmic_strain=_readonly(strain),
    )


def logarithmic_strain_3d(deformation_gradient: object) -> np.ndarray:
    """Return the read-only symmetric Hencky strain ``1/2 log(F^T F)``."""
    return hencky_kinematics_3d(deformation_gradient).logarithmic_strain


def _log_divided_difference(left: float, right: float) -> float:
    """Stable first divided difference of log on positive eigenvalues."""
    relative_difference = (left - right) / right
    if relative_difference == 0.0:
        return 1.0 / right
    return float(np.log1p(relative_difference) / (left - right))


def _frechet_log_symmetric(
    eigenvalues: np.ndarray,
    eigenvectors: np.ndarray,
    direction: np.ndarray,
) -> np.ndarray:
    """Apply the self-adjoint Frechet derivative of log(C) to a symmetric tensor."""
    local = eigenvectors.T @ direction @ eigenvectors
    factors = np.empty((3, 3), dtype=np.float64)
    for row in range(3):
        for column in range(3):
            factors[row, column] = _log_divided_difference(
                float(eigenvalues[row]), float(eigenvalues[column])
            )
    result = eigenvectors @ (factors * local) @ eigenvectors.T
    return 0.5 * (result + result.T)


@dataclass(frozen=True)
class ExperimentalHenckyElastic:
    r"""Isotropic quadratic Hencky elastic law for isolated material-point use.

    ``W = mu ||dev(E_H)||^2 + kappa/2 (tr(E_H))^2`` with positive shear
    modulus ``mu`` and bulk modulus ``kappa`` in Pa. The law is objective and
    has zero energy/stress for every proper rigid rotation. Positive moduli and
    an admissible F make the energy nonnegative, but do not establish global
    rank-one convexity or stability for arbitrary large distortions.
    """

    mu: float
    kappa: float

    def __post_init__(self) -> None:
        shear, bulk = _validated_moduli(self.mu, self.kappa)
        object.__setattr__(self, "mu", shear)
        object.__setattr__(self, "kappa", bulk)

    def evaluate(self, deformation_gradient: object) -> HenckyElasticResponse:
        """Return energy and stress measures; consistent tangent is unsupported."""
        deformation, cauchy_green, jacobian, stretches, principal, strain = _validated_kinematics(
            deformation_gradient
        )
        identity = np.eye(3)
        trace = float(np.trace(strain))
        deviator = strain - (trace / 3.0) * identity
        with np.errstate(over="ignore", invalid="ignore"):
            energy = float(
                self.mu * np.sum(deviator * deviator)
                + 0.5 * self.kappa * np.square(np.float64(trace))
            )
        conjugate = 2.0 * self.mu * deviator + self.kappa * trace * identity

        # Work conjugacy: dE_H = 1/2 Dlog_C[dC], dC = 2 dE_GL, and
        # Dlog_C is self-adjoint on symmetric tensors; hence S = Dlog_C[M_H].
        eigenvalues, eigenvectors = np.linalg.eigh(cauchy_green)
        second = _frechet_log_symmetric(eigenvalues, eigenvectors, conjugate)
        first = deformation @ second
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            cauchy = first @ deformation.T / jacobian
        cauchy = 0.5 * (cauchy + cauchy.T)
        fields = (conjugate, second, first, cauchy)
        if not isfinite(energy) or any(not np.all(np.isfinite(field)) for field in fields):
            raise ValueError("Hencky energy or stress response is non-finite.")
        return HenckyElasticResponse(
            deformation_gradient=_readonly(deformation),
            right_cauchy_green=_readonly(cauchy_green),
            jacobian_determinant=jacobian,
            principal_stretches=_readonly(stretches),
            principal_logarithmic_strains=_readonly(principal),
            logarithmic_strain=_readonly(strain),
            strain_energy_density=float(energy),
            logarithmic_strain_conjugate_stress=_readonly(conjugate),
            second_piola_kirchhoff_stress=_readonly(second),
            first_piola_kirchhoff_stress=_readonly(first),
            cauchy_stress=_readonly(cauchy),
        )


def _validated_reference_geometry(
    reference_coordinates: object, displacement: object, node_count: int, label: str
) -> tuple[np.ndarray, np.ndarray, float]:
    coordinates = _finite_real_array(reference_coordinates, (node_count, 3), f"{label} reference coordinates")
    local_displacement = _finite_real_array(displacement, (node_count, 3), f"{label} displacement")
    characteristic_length = float(np.max(np.ptp(coordinates, axis=0)))
    if not isfinite(characteristic_length) or characteristic_length <= 0.0:
        raise ValueError(f"{label} reference geometry has no positive length scale.")
    return coordinates, local_displacement, characteristic_length


def _tet4_reference_data(
    reference_coordinates: object, local_displacement: object
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    coordinates, displacement, length = _validated_reference_geometry(
        reference_coordinates, local_displacement, 4, "TET4"
    )
    scaled = (coordinates - coordinates[0]) / length
    signed_scaled_volume6 = float(np.linalg.det(scaled[1:] - scaled[0]))
    if not isfinite(signed_scaled_volume6) or signed_scaled_volume6 <= 64.0 * _FLOAT_EPS:
        raise ValueError("TET4 reference geometry must be positively oriented and numerically nondegenerate.")
    try:
        from solveur.elements.solid.tet4 import Tet4Element

        gradients = Tet4Element.shape_gradients(scaled) / length
    except np.linalg.LinAlgError as error:
        raise ValueError("TET4 reference shape gradients are singular.") from error
    if not np.all(np.isfinite(gradients)):
        raise ValueError("TET4 reference shape gradients are outside the finite float64 range.")
    with np.errstate(over="ignore", under="ignore", invalid="ignore"):
        volume = float((signed_scaled_volume6 / 6.0) * np.float64(length) ** 3)
    if not isfinite(volume) or volume <= 0.0:
        raise ValueError("TET4 reference volume is outside the representable positive float64 range.")
    return coordinates, displacement, gradients, volume


def tet4_deformation_gradients(reference_coordinates: object, local_displacement: object) -> np.ndarray:
    """Return one total-Lagrangian TET4 F tensor, shape ``(1, 3, 3)``.

    The geometry check uses a dimensionless signed-volume threshold of 64
    float64 epsilons relative to the bounding-box scale. The existing TET4
    shape-gradient implementation supplies the actual nodal ordering.
    """
    _, displacement, gradients, _ = _tet4_reference_data(reference_coordinates, local_displacement)
    deformation = np.eye(3) + displacement.T @ gradients
    _validated_kinematics(deformation)
    return _readonly(deformation.reshape((1, 3, 3)))


def _hex8_reference_data(
    reference_coordinates: object, local_displacement: object
) -> tuple[np.ndarray, np.ndarray, tuple[tuple[np.ndarray, float], ...]]:
    coordinates, displacement, length = _validated_reference_geometry(
        reference_coordinates, local_displacement, 8, "HEX8"
    )
    scaled = (coordinates - coordinates[0]) / length
    try:
        from solveur.elements.solid.hex8 import Hex8Element

        data: list[tuple[np.ndarray, float]] = []
        for point in Hex8Element.integration_points:
            derivatives = Hex8Element.shape_derivatives_reference(point)
            jacobian = derivatives.T @ scaled
            determinant = float(np.linalg.det(jacobian))
            if not isfinite(determinant) or determinant <= 64.0 * _FLOAT_EPS:
                raise ValueError("HEX8 reference Jacobian is inverted or numerically degenerate at a Gauss point.")
            gradients = derivatives @ np.linalg.inv(jacobian).T / length
            if not np.all(np.isfinite(gradients)):
                raise ValueError("HEX8 reference shape gradients are outside the finite float64 range.")
            with np.errstate(over="ignore", under="ignore", invalid="ignore"):
                measure = float(determinant * np.float64(length) ** 3)
            if not isfinite(measure) or measure <= 0.0:
                raise ValueError("HEX8 reference quadrature measure is not representable and positive.")
            data.append((gradients, measure))
    except np.linalg.LinAlgError as error:
        raise ValueError("HEX8 reference Jacobian is singular.") from error
    return coordinates, displacement, tuple(data)


def hex8_deformation_gradients(reference_coordinates: object, local_displacement: object) -> np.ndarray:
    """Return HEX8 total-Lagrangian F at its eight existing 2x2x2 Gauss points.

    Each reference Jacobian is checked after nondimensionalization by the
    element bounding-box length. This samples the integration points only; it
    is not a proof that a curved/trilinear map stays positive between them.
    """
    _, displacement, reference_data = _hex8_reference_data(reference_coordinates, local_displacement)
    tensors = []
    for gradients, _ in reference_data:
        deformation = np.eye(3) + displacement.T @ gradients
        _validated_kinematics(deformation)
        tensors.append(deformation)
    return _readonly(np.stack(tensors, axis=0))


def tet4_hencky_internal_force(
    material: ExperimentalHenckyElastic,
    reference_coordinates: object,
    local_displacement: object,
) -> np.ndarray:
    """Return isolated TET4 total-Lagrangian internal nodal forces in N.

    This force-only adapter integrates ``f_ai = integral(P_iJ N_a,J dV0)``.
    It does not form a tangent or participate in a solver/assembly route.
    """
    _, displacement, gradients, volume = _tet4_reference_data(reference_coordinates, local_displacement)
    deformation = np.eye(3) + displacement.T @ gradients
    response = material.evaluate(deformation)
    with np.errstate(over="ignore", invalid="ignore"):
        force = volume * np.einsum("iJ,aJ->ai", response.first_piola_kirchhoff_stress, gradients)
    if not np.all(np.isfinite(force)):
        raise ValueError("TET4 Hencky internal force is non-finite.")
    return _readonly(force.reshape(12))


def hex8_hencky_internal_force(
    material: ExperimentalHenckyElastic,
    reference_coordinates: object,
    local_displacement: object,
) -> np.ndarray:
    """Return isolated HEX8 total-Lagrangian internal nodal forces in N.

    The existing eight-point Gauss rule evaluates ``f_ai = integral(P_iJ
    N_a,J dV0)``. No element tangent, global scatter, or Newton route is used.
    """
    _, displacement, reference_data = _hex8_reference_data(reference_coordinates, local_displacement)
    force = np.zeros((8, 3), dtype=np.float64)
    for gradients, measure in reference_data:
        deformation = np.eye(3) + displacement.T @ gradients
        response = material.evaluate(deformation)
        with np.errstate(over="ignore", invalid="ignore"):
            force += measure * np.einsum("iJ,aJ->ai", response.first_piola_kirchhoff_stress, gradients)
    if not np.all(np.isfinite(force)):
        raise ValueError("HEX8 Hencky internal force is non-finite.")
    return _readonly(force.reshape(24))


__all__ = [
    "ExperimentalHenckyElastic",
    "HenckyElasticResponse",
    "HenckyKinematics3D",
    "hencky_kinematics_3d",
    "hex8_hencky_internal_force",
    "hex8_deformation_gradients",
    "logarithmic_strain_3d",
    "tet4_hencky_internal_force",
    "tet4_deformation_gradients",
]
