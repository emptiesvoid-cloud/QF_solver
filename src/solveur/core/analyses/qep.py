"""Dense generalized quadratic eigenproblem for the bounded rotor route."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.linalg import eig
from scipy.optimize import linear_sum_assignment

from solveur.core.errors import InputValidationError, NumericalConvergenceError


_SYMMETRY_TOLERANCE = 1.0e-12
_NORMALIZATION_TOLERANCE = 1.0e-10
_RESIDUAL_TOLERANCE = 1.0e-8
_GROWTH_RATIO_TOLERANCE = 1.0e-8
_SPECTRAL_PAIR_TOLERANCE = 1.0e-8
_MAX_EIGENVALUE_CONDITION = 1.0e12


@dataclass(frozen=True)
class QuadraticEigenResult:
    eigenvalues: np.ndarray
    modes: np.ndarray
    residuals: np.ndarray
    diagnostics: dict[str, object]


class QuadraticEigenSolver:
    """Solve the real conservative QEP by a dense generalized companion pencil."""

    def solve(
        self,
        mass: object,
        stiffness: object,
        gyro: object,
        omega_rad_s: float,
        *,
        length_reference: float,
        dof_names: tuple[str, ...],
    ) -> QuadraticEigenResult:
        m = _as_real_square(mass, "M")
        k = _as_real_square(stiffness, "K")
        g = _as_real_square(gyro, "G")
        if m.shape != k.shape or m.shape != g.shape:
            raise InputValidationError("QEP matrices M, K, and G must have identical shapes.")
        if m.shape[0] == 0:
            raise InputValidationError("QEP requires at least one free physical DOF.")
        omega = float(omega_rad_s)
        if not np.isfinite(omega):
            raise InputValidationError("QEP signed speed must be finite in rad/s.")
        if len(dof_names) != m.shape[0]:
            raise InputValidationError("QEP DOF scale labels must match the reduced matrix size.")
        length = float(length_reference)
        if not np.isfinite(length) or length <= 0.0:
            raise InputValidationError("QEP length reference must be finite and positive.")

        symmetry_m = _relative_frobenius(m - m.T, m)
        symmetry_k = _relative_frobenius(k - k.T, k)
        skew_g = _relative_frobenius(g + g.T, g)
        if symmetry_m > _SYMMETRY_TOLERANCE or symmetry_k > _SYMMETRY_TOLERANCE:
            raise InputValidationError(
                "QEP requires symmetric M/K within 1e-12 relative Frobenius error; "
                f"M={symmetry_m:.6e}, K={symmetry_k:.6e}."
            )
        if skew_g > _SYMMETRY_TOLERANCE:
            raise InputValidationError(f"QEP requires skew-symmetric G within 1e-12; error={skew_g:.6e}.")
        try:
            np.linalg.cholesky(m)
            np.linalg.cholesky(k)
        except np.linalg.LinAlgError as exc:
            raise InputValidationError("QEP reduced M and K must both be positive definite.") from exc

        coordinate_scale = np.asarray(
            [length if name in {"UX", "UY", "UZ"} else 1.0 for name in dof_names],
            dtype=float,
        )
        ms = coordinate_scale[:, None] * m * coordinate_scale[None, :]
        ks = coordinate_scale[:, None] * k * coordinate_scale[None, :]
        gs = coordinate_scale[:, None] * g * coordinate_scale[None, :]
        mass_reference = float(np.linalg.norm(ms, ord="fro"))
        stiffness_reference = float(np.linalg.norm(ks, ord="fro"))
        if not np.isfinite(mass_reference + stiffness_reference) or min(mass_reference, stiffness_reference) <= 0.0:
            raise InputValidationError("QEP physical matrix scaling references must be finite and positive.")
        omega_reference = float(np.sqrt(stiffness_reference / mass_reference))
        if not np.isfinite(omega_reference) or omega_reference <= 0.0:
            raise InputValidationError("QEP frequency reference must be finite and positive.")

        m_hat = omega_reference**2 * ms / stiffness_reference
        k_hat = ks / stiffness_reference
        g_hat = omega_reference**2 * gs / stiffness_reference
        omega_hat = omega / omega_reference
        size = m.shape[0]
        zero = np.zeros((size, size), dtype=float)
        identity = np.eye(size, dtype=float)
        a = np.block([[zero, identity], [-k_hat, -omega_hat * g_hat]])
        b = np.block([[identity, zero], [zero, m_hat]])
        try:
            scaled_roots, left, right = eig(a, b, left=True, right=True, check_finite=True)
        except (ValueError, np.linalg.LinAlgError) as exc:
            raise NumericalConvergenceError(f"Dense generalized QEP eigensolve failed: {exc}") from exc
        if scaled_roots.shape != (2 * size,) or right.shape != (2 * size, 2 * size):
            raise NumericalConvergenceError("Dense generalized QEP returned malformed eigenpair dimensions.")
        if not np.all(np.isfinite(scaled_roots)) or not np.all(np.isfinite(right)) or not np.all(np.isfinite(left)):
            raise NumericalConvergenceError("Dense generalized QEP returned non-finite roots or vectors.")

        roots = omega_reference * scaled_roots
        modes = coordinate_scale[:, None] * right[:size, :]
        condition_numbers = _generalized_eigenvalue_conditions(left, right, b)
        if not np.all(np.isfinite(condition_numbers)) or np.max(condition_numbers) > _MAX_EIGENVALUE_CONDITION:
            raise NumericalConvergenceError(
                "Dense QEP contains an ill-conditioned generalized eigenvalue; "
                f"maximum condition estimate={float(np.max(condition_numbers)):.6e}, "
                f"limit={_MAX_EIGENVALUE_CONDITION:.1e}."
            )

        normalized_modes = np.empty_like(modes, dtype=np.complex128)
        normalization_errors = np.empty(roots.size, dtype=float)
        residuals = np.empty(roots.size, dtype=float)
        for index, (root, vector) in enumerate(zip(roots, modes.T)):
            quadratic_mass = np.vdot(vector, m @ vector)
            if not np.isfinite(quadratic_mass.real + quadratic_mass.imag) or quadratic_mass.real <= 0.0:
                raise NumericalConvergenceError(f"QEP mode {index} cannot be mass-normalized.")
            if abs(float(quadratic_mass.imag)) > _NORMALIZATION_TOLERANCE * max(1.0, abs(quadratic_mass.real)):
                raise NumericalConvergenceError(f"QEP mode {index} has a non-real mass norm.")
            normalized = vector / np.sqrt(float(quadratic_mass.real))
            pivot = int(np.argmax(np.abs(normalized)))
            if abs(normalized[pivot]) == 0.0 or not np.isfinite(normalized[pivot]):
                raise NumericalConvergenceError(f"QEP mode {index} has no finite nonzero normalization pivot.")
            normalized *= np.exp(-1j * np.angle(normalized[pivot]))
            if normalized[pivot].real < 0.0:
                normalized *= -1.0
            normalized_modes[:, index] = normalized
            normalized_mass = np.vdot(normalized, m @ normalized)
            normalization_errors[index] = abs(normalized_mass - 1.0)
            residuals[index] = _qep_relative_residual(root, normalized, m, k, g, omega)

        if not np.all(np.isfinite(residuals)) or float(np.max(residuals)) > _RESIDUAL_TOLERANCE:
            raise NumericalConvergenceError(
                "QEP residual gate failed on the original quadratic polynomial; "
                f"maximum={float(np.max(residuals)):.6e}, limit={_RESIDUAL_TOLERANCE:.1e}."
            )
        if float(np.max(normalization_errors)) > _NORMALIZATION_TOLERANCE:
            raise NumericalConvergenceError(
                "QEP mass-normalization gate failed; "
                f"maximum error={float(np.max(normalization_errors)):.6e}."
            )

        growth_ratio = float(np.max(np.abs(roots.real) / np.maximum(omega_reference, np.abs(roots))))
        if not np.isfinite(growth_ratio) or growth_ratio > _GROWTH_RATIO_TOLERANCE:
            raise NumericalConvergenceError(
                "Undamped conservative QEP growth-ratio gate failed; "
                f"maximum={growth_ratio:.6e}, limit={_GROWTH_RATIO_TOLERANCE:.1e}."
            )
        pair_mismatch = _conjugate_spectrum_mismatch(roots, omega_reference)
        if not np.isfinite(pair_mismatch) or pair_mismatch > _SPECTRAL_PAIR_TOLERANCE:
            raise NumericalConvergenceError(
                "QEP conjugate-spectrum gate failed; "
                f"normalized mismatch={pair_mismatch:.6e}, limit={_SPECTRAL_PAIR_TOLERANCE:.1e}."
            )

        diagnostics: dict[str, object] = {
            "backend": "scipy.linalg.eig_generalized_dense",
            "linearized_dimension": int(2 * size),
            "physical_dofs": int(size),
            "length_reference_m": length,
            "mass_reference_frobenius": mass_reference,
            "stiffness_reference_frobenius": stiffness_reference,
            "frequency_reference_rad_s": omega_reference,
            "signed_speed_rad_s": omega,
            "scaled_signed_speed": omega_hat,
            "maximum_relative_qep_residual": float(np.max(residuals)),
            "maximum_mass_normalization_error": float(np.max(normalization_errors)),
            "maximum_generalized_eigenvalue_condition": float(np.max(condition_numbers)),
            "maximum_conservative_growth_ratio": growth_ratio,
            "normalized_conjugate_spectrum_mismatch": pair_mismatch,
            "matrix_symmetry_relative_error": {"M": symmetry_m, "K": symmetry_k},
            "gyro_skew_relative_error": skew_g,
            "raw_root_count": int(roots.size),
        }
        return QuadraticEigenResult(roots, normalized_modes, residuals, diagnostics)


def _as_real_square(value: object, name: str) -> np.ndarray:
    if hasattr(value, "toarray"):
        array = np.asarray(value.toarray())
    else:
        array = np.asarray(value)
    if array.ndim != 2 or array.shape[0] != array.shape[1]:
        raise InputValidationError(f"QEP matrix {name} must be square.")
    if np.iscomplexobj(array) or not np.all(np.isfinite(array)):
        raise InputValidationError(f"QEP matrix {name} must contain only finite real values.")
    return np.asarray(array, dtype=float)


def _relative_frobenius(difference: np.ndarray, reference: np.ndarray) -> float:
    return float(np.linalg.norm(difference, ord="fro") / max(np.linalg.norm(reference, ord="fro"), np.finfo(float).tiny))


def _qep_relative_residual(
    root: complex,
    mode: np.ndarray,
    mass: np.ndarray,
    stiffness: np.ndarray,
    gyro: np.ndarray,
    omega: float,
) -> float:
    mass_term = root**2 * (mass @ mode)
    gyro_term = root * omega * (gyro @ mode)
    stiffness_term = stiffness @ mode
    numerator = float(np.linalg.norm(mass_term + gyro_term + stiffness_term))
    denominator = float(
        np.linalg.norm(stiffness_term)
        + abs(root * omega) * np.linalg.norm(gyro @ mode)
        + abs(root) ** 2 * np.linalg.norm(mass @ mode)
    )
    if not np.isfinite(numerator + denominator) or denominator <= 0.0:
        return float("inf")
    return numerator / denominator


def _generalized_eigenvalue_conditions(left: np.ndarray, right: np.ndarray, b: np.ndarray) -> np.ndarray:
    conditions = np.empty(right.shape[1], dtype=float)
    for index in range(right.shape[1]):
        left_vector = left[:, index]
        right_vector = right[:, index]
        b_right = b @ right_vector
        denominator = abs(np.vdot(left_vector, b_right))
        numerator = float(np.linalg.norm(left_vector) * np.linalg.norm(b_right))
        conditions[index] = numerator / denominator if denominator > 0.0 else float("inf")
    return conditions


def _conjugate_spectrum_mismatch(roots: np.ndarray, omega_reference: float) -> float:
    scale = np.maximum.reduce((np.full(roots.size, omega_reference), np.abs(roots), np.abs(roots.conj())))
    cost = np.abs(roots[:, None] - roots.conj()[None, :]) / np.maximum(scale[:, None], scale[None, :])
    rows, columns = linear_sum_assignment(cost)
    if rows.size != roots.size:
        return float("inf")
    return float(np.max(cost[rows, columns], initial=0.0))
