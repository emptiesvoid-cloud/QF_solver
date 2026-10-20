"""Bounded WP-D01 residual-flexibility algebra for harmonic modal response.

This module operates only on already prepared constrained operators.  It does
not assemble a model or invoke a solver route.  The WP05 adapter is responsible
for binding the inputs to a compatible ``PreparedDynamicSystem`` and
``ModalBasis``.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from time import perf_counter
from typing import Any, Mapping

import numpy as np
from scipy.linalg import cho_factor, cho_solve
from scipy.sparse import csr_matrix, issparse
from scipy.sparse.linalg import SuperLU, splu

from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.modal_basis_numerics import (
    SYMMETRY_TOL,
    relative_sparse_symmetry_error,
    require_sparse_finite_square,
)
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.io.checkpoint_common import checkpoint_signature


CORRECTION_SOLVE_BACKWARD_ERROR_MAX = 1.0e-8
MASS_ORTHOGONALITY_MAX = 1.0e-8
PROJECTED_STIFFNESS_RELATIVE_MAX = 1.0e-8
_FLOAT_TINY = np.finfo(np.float64).tiny
_S_M_ABS = math.sqrt(0.25 * (1.0 + 1.0 / 16.0 + 1.0 / 81.0 + 1.0 / 256.0))
_C7_FREQUENCIES_RAD_S = (0.0, 0.15, 0.30, 0.60)


@dataclass(frozen=True)
class ResidualFlexibilityCorrection:
    """One corrected reduced-coordinate harmonic response and its diagnostics."""

    uncorrected: np.ndarray
    correction: np.ndarray
    corrected: np.ndarray
    diagnostics: dict[str, Any]


class ResidualFlexibilityCorrector:
    """Reuse sparse constrained-stiffness factorization for modal corrections."""

    def __init__(
        self,
        stiffness: object,
        mass: object,
        damping: object,
        basis: ModalBasis,
        *,
        operator_identity: str,
        rayleigh_alpha: float,
        rayleigh_beta: float,
    ) -> None:
        if not isinstance(basis, ModalBasis):
            raise InputValidationError("Residual flexibility requires a validated WP04 ModalBasis.")
        if not isinstance(operator_identity, str) or not operator_identity:
            raise InputValidationError("Residual flexibility requires an explicit operator identity.")
        if basis.operator_identity != operator_identity:
            raise InputValidationError("Residual-flexibility basis and operator identities do not match.")
        self._stiffness = _as_real_sparse(stiffness, "constrained stiffness")
        self._mass = _as_real_sparse(mass, "constrained mass")
        self._damping = _as_real_sparse(damping, "constrained damping")
        n = self._stiffness.shape[0]
        if self._mass.shape != (n, n) or self._damping.shape != (n, n):
            raise InputValidationError("Residual-flexibility K, M and C dimensions must agree.")
        if basis.system_size != n or basis.modes.shape[0] != n:
            raise InputValidationError("Residual-flexibility ModalBasis dimensions do not match the operators.")
        for name, matrix in (("stiffness", self._stiffness), ("mass", self._mass), ("damping", self._damping)):
            symmetry = relative_sparse_symmetry_error(matrix)
            if symmetry > SYMMETRY_TOL:
                raise InputValidationError(
                    f"Residual-flexibility {name} must be symmetric; relative error={symmetry:.3e}."
                )

        self._basis = basis
        self._modes = np.asarray(basis.modes, dtype=np.float64)
        self._operator_identity = operator_identity
        self._basis_identity = basis.basis_identity
        self._alpha = _finite_nonnegative(rayleigh_alpha, "Rayleigh alpha")
        self._beta = _finite_nonnegative(rayleigh_beta, "Rayleigh beta")
        expected_damping = (self._alpha * self._mass + self._beta * self._stiffness).tocsr()
        damping_error = _relative_sparse_difference(self._damping, expected_damping)
        if damping_error > 1.0e-12:
            raise InputValidationError(
                "Residual flexibility supports only the declared physical Rayleigh operator C=alpha*M+beta*K; "
                f"relative mismatch={damping_error:.3e}."
            )

        basis_diagnostics = basis.diagnostics
        screens = basis_diagnostics.get("spectral_screens")
        if not isinstance(screens, Mapping) or not _screen_is_positive(screens.get("stiffness")) or not _screen_is_positive(
            screens.get("mass")
        ):
            raise InputValidationError(
                "Residual flexibility requires the inherited WP04 positive-definiteness screens for K and M."
            )

        gram = np.asarray(self._modes.T @ (self._mass @ self._modes), dtype=np.float64)
        projected_stiffness = np.asarray(self._modes.T @ (self._stiffness @ self._modes), dtype=np.float64)
        if not np.all(np.isfinite(gram)) or not np.all(np.isfinite(projected_stiffness)):
            raise InputValidationError("Residual-flexibility modal projections contain non-finite values.")
        gram_error = float(np.linalg.norm(gram - basis.projected_mass, ord="fro")) / max(
            float(np.linalg.norm(gram, ord="fro")), _FLOAT_TINY
        )
        modal_orthogonality = float(np.linalg.norm(gram - np.eye(basis.mode_count), ord="fro"))
        stiffness_projection_error = float(
            np.linalg.norm(projected_stiffness - basis.projected_stiffness, ord="fro")
            / max(float(np.linalg.norm(projected_stiffness, ord="fro")), _FLOAT_TINY)
        )
        if gram_error > MASS_ORTHOGONALITY_MAX or modal_orthogonality > MASS_ORTHOGONALITY_MAX:
            raise InputValidationError("Residual-flexibility basis violates the inherited WP04 mass Gram contract.")
        if stiffness_projection_error > PROJECTED_STIFFNESS_RELATIVE_MAX:
            raise InputValidationError("Residual-flexibility basis has inconsistent projected stiffness evidence.")

        try:
            self._gram_factor = cho_factor(0.5 * (gram + gram.T), lower=True, check_finite=True)
            self._modal_stiffness_factor = cho_factor(
                0.5 * (projected_stiffness + projected_stiffness.T), lower=True, check_finite=True
            )
        except (np.linalg.LinAlgError, ValueError) as exc:
            raise InputValidationError("Residual-flexibility modal Gram or stiffness matrix is not SPD.") from exc

        factor_started = perf_counter()
        try:
            self._stiffness_factor: SuperLU = splu(self._stiffness.tocsc())
        except (RuntimeError, ValueError) as exc:
            raise NumericalConvergenceError(
                "Residual-flexibility constrained stiffness factorization failed; no regularization was applied."
            ) from exc
        self._factorization_seconds = perf_counter() - factor_started
        if not math.isfinite(self._factorization_seconds) or self._factorization_seconds < 0.0:
            raise NumericalConvergenceError("Residual-flexibility factorization timing is invalid.")
        self._stiffness_frobenius = _sparse_frobenius(self._stiffness)
        self._uses = 0
        self._stiffness_rhs_solves = 0
        self._modal_stiffness_rhs_solves = 0
        self._modal_projection_rhs_solves = 0
        self._calculation_seconds = 0.0

    @classmethod
    def from_prepared(
        cls,
        prepared: object,
        basis: ModalBasis,
        *,
        rayleigh_alpha: float,
        rayleigh_beta: float,
    ) -> "ResidualFlexibilityCorrector":
        """Bind the algebraic core to WP02 operators and the WP04 basis."""
        from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem

        if not isinstance(prepared, PreparedDynamicSystem):
            raise InputValidationError("Residual flexibility requires a PreparedDynamicSystem.")
        basis.assert_compatible(prepared)
        damping = rayleigh_alpha * prepared.mass + rayleigh_beta * prepared.stiffness
        return cls(
            prepared.stiffness,
            prepared.mass,
            damping,
            basis,
            operator_identity=prepared.operator_identity,
            rayleigh_alpha=rayleigh_alpha,
            rayleigh_beta=rayleigh_beta,
        )

    def correct(
        self,
        omega_rad_s: float,
        force: object,
        uncorrected: object,
        modal_coordinates: object,
        *,
        excitation_identity: str,
        verification_fixture_id: str | None = None,
    ) -> ResidualFlexibilityCorrection:
        """Apply the frozen mode-acceleration residual correction once."""
        started = perf_counter()
        omega = _finite_nonnegative(omega_rad_s, "angular frequency")
        f = _complex_vector(force, self._stiffness.shape[0], "harmonic force")
        um = _complex_vector(uncorrected, self._stiffness.shape[0], "uncorrected reduced response")
        q_solve = _complex_vector(modal_coordinates, self._basis.mode_count, "reduced harmonic solve coordinates")
        if not isinstance(excitation_identity, str) or not excitation_identity:
            raise InputValidationError("Residual flexibility requires the bound excitation identity.")

        impedance = (
            self._stiffness.astype(np.complex128)
            + 1j * omega * self._damping
            - omega**2 * self._mass
        ).tocsr()
        residual = np.asarray(f - impedance @ um, dtype=np.complex128)
        modal_rhs = np.asarray(self._basis.modes.T @ residual, dtype=np.complex128)
        try:
            modal_coefficients = np.asarray(
                cho_solve(self._modal_stiffness_factor, modal_rhs, check_finite=True), dtype=np.complex128
            )
        except (np.linalg.LinAlgError, ValueError) as exc:
            raise NumericalConvergenceError("Residual-flexibility modal stiffness solve failed.") from exc
        self._modal_stiffness_rhs_solves += 1
        residual_perpendicular = np.asarray(
            residual - self._stiffness @ (self._basis.modes @ modal_coefficients), dtype=np.complex128
        )
        correction = self._solve_real_sparse_factor(residual_perpendicular)
        corrected = np.asarray(um + correction, dtype=np.complex128)

        correction_residual = np.asarray(self._stiffness @ correction - residual_perpendicular, dtype=np.complex128)
        c1_denominator = self._stiffness_frobenius * float(np.linalg.norm(correction)) + float(
            np.linalg.norm(residual_perpendicular)
        )
        c1_eta = _normalized_residual(correction_residual, c1_denominator, "C1 correction solve")
        if c1_eta > CORRECTION_SOLVE_BACKWARD_ERROR_MAX:
            raise NumericalConvergenceError(
                f"Residual-flexibility correction solve backward error {c1_eta:.3e} exceeds "
                f"{CORRECTION_SOLVE_BACKWARD_ERROR_MAX:.3e}.",
                diagnostics={"C1_eta": c1_eta, "C1_limit": CORRECTION_SOLVE_BACKWARD_ERROR_MAX},
            )

        b_m_um, q_projected_um, projected_um = self._mass_projection(um)
        b_m_correction, q_projected_correction, projected_correction = self._mass_projection(correction)
        b_m_corrected, q_projected_corrected, projected_corrected = self._mass_projection(corrected)
        projected_um_norm = _mass_norm(self._mass, projected_um, "projected uncorrected response")
        projected_correction_norm = _mass_norm(self._mass, projected_correction, "projected correction")
        c7_denominator = max(projected_um_norm, _S_M_ABS)
        if not math.isfinite(c7_denominator) or c7_denominator <= 0.0:
            raise NumericalConvergenceError("C7 retained-subspace reference denominator is invalid.")
        c7_metric = projected_correction_norm / c7_denominator
        fixture_match = _matches_c7_fixture(
            self._stiffness,
            self._mass,
            self._basis.modes,
            f,
            self._alpha,
            self._beta,
        )
        if verification_fixture_id not in {None, "MIXED_RETAINED_OMITTED"}:
            raise InputValidationError(f"Unsupported WP-D01 verification fixture {verification_fixture_id!r}.")
        if verification_fixture_id == "MIXED_RETAINED_OMITTED" and not fixture_match:
            raise InputValidationError(
                "The declared MIXED_RETAINED_OMITTED fixture does not match its frozen operator, basis, load, "
                "or damping definition."
            )
        c7_mandatory = (
            verification_fixture_id == "MIXED_RETAINED_OMITTED"
            and any(_same_frequency(omega, value) for value in _C7_FREQUENCIES_RAD_S)
        )
        c7_status = "PASS" if c7_mandatory and c7_metric <= 1.0e-8 else (
            "FAIL" if c7_mandatory else "CHARACTERIZATION_ONLY"
        )
        if c7_status == "FAIL":
            raise NumericalConvergenceError(
                f"Fixture-specific C7 retained-subspace leakage {c7_metric:.3e} exceeds 1e-8.",
                diagnostics={"C7_e_ret": c7_metric, "C7_limit": 1.0e-8},
            )

        stiffness_orthogonality = np.asarray(self._basis.modes.T @ (self._stiffness @ correction))
        mass_leakage = np.asarray(self._basis.modes.T @ (self._mass @ correction))
        modal_residual_orthogonality = np.asarray(self._basis.modes.T @ residual_perpendicular)
        dynamic_residual = np.asarray(f - impedance @ corrected, dtype=np.complex128)
        dynamic_denominator = _sparse_frobenius(impedance) * float(np.linalg.norm(corrected)) + float(
            np.linalg.norm(f)
        )
        dynamic_eta = _normalized_residual(dynamic_residual, dynamic_denominator, "corrected dynamic residual")

        q_projected_change = q_projected_corrected - q_projected_um
        projection_reconstruction_error = float(
            np.linalg.norm(projected_um - self._basis.modes @ q_solve)
            / max(float(np.linalg.norm(um)), _FLOAT_TINY)
        )
        reference_flags: list[str] = []
        if projected_um_norm <= _S_M_ABS:
            reference_flags.append("FLOOR_ACTIVE")
        if projected_um_norm == 0.0:
            reference_flags.append("ZERO_REFERENCE")

        duration = perf_counter() - started
        if not math.isfinite(duration) or duration < 0.0:
            raise NumericalConvergenceError("Residual-flexibility per-frequency timing is invalid.")
        self._calculation_seconds += duration
        self._uses += 1
        diagnostics: dict[str, Any] = {
            "status": "AVAILABLE",
            "frequency_eligibility": self._frequency_eligibility(omega),
            "frequency_hz": omega / (2.0 * math.pi),
            "omega_rad_s": omega,
            "operator_identity": self._operator_identity,
            "modal_basis_identity": self._basis_identity,
            "excitation_identity": excitation_identity,
            "q_solve": _complex_pair(q_solve),
            "b_M_uncorrected": _complex_pair(b_m_um),
            "b_M_correction": _complex_pair(b_m_correction),
            "b_M_corrected": _complex_pair(b_m_corrected),
            "q_projected_uncorrected": _complex_pair(q_projected_um),
            "q_projected_correction": _complex_pair(q_projected_correction),
            "q_projected_corrected": _complex_pair(q_projected_corrected),
            "q_projected_change": _complex_pair(q_projected_change),
            "modal_projection_reconstruction_relative_error": projection_reconstruction_error,
            "correction_norm_euclidean": float(np.linalg.norm(correction)),
            "correction_norm_mass": _mass_norm(self._mass, correction, "correction"),
            "C1": {
                "status": "PASS",
                "normalized_backward_error": c1_eta,
                "limit": CORRECTION_SOLVE_BACKWARD_ERROR_MAX,
                "absolute_residual_norm": float(np.linalg.norm(correction_residual)),
                "denominator": c1_denominator,
            },
            "C7": {
                "status": c7_status,
                "applicability": "MANDATORY_FIXTURE_GATE" if c7_mandatory else "CHARACTERIZATION_ONLY",
                "e_ret": c7_metric,
                "limit": 1.0e-8 if c7_mandatory else None,
                "numerator_mass_norm": projected_correction_norm,
                "denominator_mass_norm": c7_denominator,
                "absolute_reference_floor_m_sqrt_kg": _S_M_ABS,
                "reference_flags": reference_flags,
            },
            "mass_projection_leakage_vector": _complex_pair(mass_leakage),
            "mass_projection_leakage_norm": float(np.linalg.norm(mass_leakage)),
            "stiffness_orthogonality_vector": _complex_pair(stiffness_orthogonality),
            "stiffness_orthogonality_norm": float(np.linalg.norm(stiffness_orthogonality)),
            "modal_residual_orthogonality_vector": _complex_pair(modal_residual_orthogonality),
            "modal_residual_orthogonality_norm": float(np.linalg.norm(modal_residual_orthogonality)),
            "corrected_full_dynamic_residual": {
                "status": "AVAILABLE",
                "coordinate_scope": "FULL_CONSTRAINED_OPERATOR_COORDINATES_NOT_MODAL_SUBSPACE",
                "normalized_backward_error": dynamic_eta,
                "absolute_residual_norm": float(np.linalg.norm(dynamic_residual)),
                "denominator": dynamic_denominator,
                "assessment": "DIAGNOSTIC_ONLY; does not certify truncated response accuracy",
            },
            "first_omitted_mode": self._first_omitted_evidence(),
            "calculation_seconds": duration,
        }
        return ResidualFlexibilityCorrection(
            uncorrected=_readonly(um),
            correction=_readonly(correction),
            corrected=_readonly(corrected),
            diagnostics=diagnostics,
        )

    @property
    def telemetry(self) -> dict[str, Any]:
        return {
            "stiffness_factorization_seconds": self._factorization_seconds,
            "stiffness_factorization_count": 1,
            "stiffness_factorization_reuse_count": max(self._uses - 1, 0),
            "stiffness_rhs_solve_count": self._stiffness_rhs_solves,
            "modal_stiffness_rhs_solve_count": self._modal_stiffness_rhs_solves,
            "modal_projection_rhs_solve_count": self._modal_projection_rhs_solves,
            "frequency_calculation_seconds_total": self._calculation_seconds,
            "peak_memory_bytes": None,
            "peak_memory_status": "UNAVAILABLE_NOT_RELIABLY_MEASURABLE_IN_LIBRARY_CALL",
        }

    def _solve_real_sparse_factor(self, rhs: np.ndarray) -> np.ndarray:
        values = np.asarray(rhs, dtype=np.complex128)
        try:
            real = np.asarray(self._stiffness_factor.solve(values.real), dtype=np.float64)
            self._stiffness_rhs_solves += 1
            if np.any(values.imag != 0.0):
                imag = np.asarray(self._stiffness_factor.solve(values.imag), dtype=np.float64)
                self._stiffness_rhs_solves += 1
            else:
                imag = np.zeros_like(real)
            result = np.asarray(real + 1j * imag, dtype=np.complex128)
        except (RuntimeError, ValueError) as exc:
            raise NumericalConvergenceError("Residual-flexibility sparse stiffness solve failed.") from exc
        if not np.all(np.isfinite(result)):
            raise NumericalConvergenceError("Residual-flexibility correction contains non-finite values.")
        return result

    def _mass_projection(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        b_m = np.asarray(self._basis.modes.T @ (self._mass @ values), dtype=np.complex128)
        try:
            coordinates = np.asarray(cho_solve(self._gram_factor, b_m, check_finite=True), dtype=np.complex128)
        except (np.linalg.LinAlgError, ValueError) as exc:
            raise NumericalConvergenceError("Residual-flexibility mass-Gram projection solve failed.") from exc
        self._modal_projection_rhs_solves += 1
        projected = np.asarray(self._basis.modes @ coordinates, dtype=np.complex128)
        if not np.all(np.isfinite(projected)):
            raise NumericalConvergenceError("Residual-flexibility mass projection produced non-finite values.")
        return b_m, coordinates, projected

    def _first_omitted_evidence(self) -> dict[str, Any]:
        evidence = self._basis.first_omitted_eigenpair
        if evidence is None:
            return {"status": "NOT_APPLICABLE_FULL_BASIS" if self._basis.is_full_basis else "NOT_EVALUABLE"}
        return dict(evidence)

    def _frequency_eligibility(self, omega: float) -> dict[str, Any]:
        evidence = self._basis.first_omitted_eigenpair
        if self._basis.is_full_basis:
            return {"status": "NOT_APPLICABLE_FULL_BASIS", "accuracy_claim": "NONE"}
        if not isinstance(evidence, Mapping) or evidence.get("status") != "AVAILABLE":
            return {"status": "NOT_EVALUABLE", "accuracy_claim": "NONE"}
        first_omitted = evidence.get("omega_rad_s")
        residual = evidence.get("relative_eigenpair_residual")
        valid_evidence = (
            evidence.get("operator_identity") == self._operator_identity
            and evidence.get("retained_cutoff_cluster_complete") is True
            and isinstance(evidence.get("eigenvector_sha256"), str)
            and bool(evidence.get("eigenvector_sha256"))
            and isinstance(evidence.get("evidence_identity"), str)
            and bool(evidence.get("evidence_identity"))
            and isinstance(residual, (int, float))
            and math.isfinite(float(residual))
            and float(residual) <= 1.0e-8
        )
        if valid_evidence:
            evidence_body = {key: value for key, value in evidence.items() if key != "evidence_identity"}
            valid_evidence = checkpoint_signature(
                evidence_body, label="WP04 first omitted eigenpair evidence"
            ) == evidence.get("evidence_identity")
        if (
            not valid_evidence
            or not isinstance(first_omitted, (int, float))
            or not math.isfinite(float(first_omitted))
            or float(first_omitted) <= 0.0
        ):
            return {"status": "NOT_EVALUABLE", "accuracy_claim": "NONE"}
        eligible = omega <= 0.2 * float(first_omitted)
        return {
            "status": "IN_BAND_ELIGIBLE" if eligible else "CHARACTERIZATION_ONLY",
            "omega_first_omitted_rad_s": float(first_omitted),
            "eligibility_boundary_rad_s": 0.2 * float(first_omitted),
            "cutoff_cluster_complete": bool(evidence.get("retained_cutoff_cluster_complete", False)),
            "accuracy_claim": "NONE; frequency eligibility is not an accuracy guarantee",
        }


def _as_real_sparse(values: object, label: str) -> csr_matrix:
    if issparse(values):
        raw = values
        if np.iscomplexobj(raw.data):
            raise InputValidationError(f"Residual-flexibility {label} must be real-valued.")
    else:
        raw = np.asarray(values)
        if np.iscomplexobj(raw):
            raise InputValidationError(f"Residual-flexibility {label} must be real-valued.")
    try:
        matrix = csr_matrix(values, dtype=np.float64, copy=True)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError(f"Residual-flexibility {label} must be a finite numeric matrix.") from exc
    require_sparse_finite_square(matrix, label)
    return matrix


def _complex_vector(values: object, expected: int, label: str) -> np.ndarray:
    try:
        vector = np.asarray(values, dtype=np.complex128)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError(f"Residual-flexibility {label} must be a finite complex vector.") from exc
    if vector.ndim != 1 or vector.shape != (expected,) or not np.all(np.isfinite(vector)):
        raise InputValidationError(f"Residual-flexibility {label} must be finite and have shape ({expected},).")
    return vector


def _finite_nonnegative(value: object, label: str) -> float:
    if isinstance(value, (bool, np.bool_)):
        raise InputValidationError(f"Residual-flexibility {label} must be finite and non-negative.")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise InputValidationError(f"Residual-flexibility {label} must be finite and non-negative.") from exc
    if not math.isfinite(result) or result < 0.0:
        raise InputValidationError(f"Residual-flexibility {label} must be finite and non-negative.")
    return result


def _sparse_frobenius(matrix: object) -> float:
    values = csr_matrix(matrix).data
    result = float(np.linalg.norm(values))
    if not math.isfinite(result):
        raise InputValidationError("Residual-flexibility matrix Frobenius norm is non-finite.")
    return result


def _relative_sparse_difference(left: csr_matrix, right: csr_matrix) -> float:
    difference = (left - right).tocsr()
    return _sparse_frobenius(difference) / max(_sparse_frobenius(left), _sparse_frobenius(right), _FLOAT_TINY)


def _normalized_residual(residual: np.ndarray, denominator: float, label: str) -> float:
    absolute = float(np.linalg.norm(residual))
    if not math.isfinite(absolute) or not math.isfinite(denominator) or denominator < 0.0:
        raise NumericalConvergenceError(f"{label} contains invalid residual or denominator values.")
    if denominator == 0.0:
        if absolute == 0.0:
            return 0.0
        raise NumericalConvergenceError(f"{label} has a zero denominator and nonzero residual.")
    return absolute / denominator


def _mass_norm(mass: csr_matrix, values: np.ndarray, label: str) -> float:
    vector = np.asarray(values, dtype=np.complex128)
    quadratic = np.vdot(vector, mass @ vector)
    if not np.isfinite(quadratic.real) or not np.isfinite(quadratic.imag):
        raise NumericalConvergenceError(f"{label} mass norm is non-finite.")
    if abs(float(quadratic.imag)) > 1.0e-12 * max(abs(float(quadratic.real)), _FLOAT_TINY):
        raise NumericalConvergenceError(f"{label} mass norm has a material imaginary component.")
    if float(quadratic.real) < 0.0:
        raise NumericalConvergenceError(f"{label} mass norm has a negative quadratic form.")
    return math.sqrt(float(quadratic.real))


def _screen_is_positive(screen: object) -> bool:
    if not isinstance(screen, Mapping):
        return False
    estimate = screen.get("minimum_scaled_eigenvalue_estimate")
    threshold = screen.get("threshold")
    return (
        isinstance(estimate, (int, float))
        and math.isfinite(float(estimate))
        and isinstance(threshold, (int, float))
        and math.isfinite(float(threshold))
        and float(estimate) > float(threshold)
    )


def _complex_pair(values: np.ndarray) -> dict[str, list[float]]:
    vector = np.asarray(values, dtype=np.complex128)
    if not np.all(np.isfinite(vector)):
        raise NumericalConvergenceError("Residual-flexibility diagnostic vector is non-finite.")
    return {"real": vector.real.tolist(), "imag": vector.imag.tolist()}


def _readonly(values: np.ndarray) -> np.ndarray:
    result = np.asarray(values, dtype=np.complex128).copy()
    result.setflags(write=False)
    return result


def _matches_c7_fixture(
    stiffness: csr_matrix,
    mass: csr_matrix,
    modes: np.ndarray,
    force: np.ndarray,
    alpha: float,
    beta: float,
) -> bool:
    if stiffness.shape != (4, 4) or modes.shape != (4, 2) or alpha != 0.0 or beta != 0.0:
        return False
    q = 0.5 * np.asarray(
        [[1.0, 1.0, 1.0, 1.0], [1.0, -1.0, 1.0, -1.0], [1.0, 1.0, -1.0, -1.0], [1.0, -1.0, -1.0, 1.0]],
        dtype=np.float64,
    )
    expected_k = q @ np.diag([1.0, 4.0, 9.0, 16.0]) @ q.T
    expected_f = q[:, 0] + q[:, 3]
    actual_m = mass.toarray()
    actual_k = stiffness.toarray()
    basis_projector = modes @ modes.T
    expected_projector = q[:, :2] @ q[:, :2].T
    return bool(
        np.allclose(actual_m, np.eye(4), rtol=0.0, atol=1.0e-14)
        and np.allclose(actual_k, expected_k, rtol=1.0e-13, atol=1.0e-14)
        and np.allclose(force, expected_f, rtol=0.0, atol=1.0e-14)
        and np.allclose(basis_projector, expected_projector, rtol=0.0, atol=1.0e-12)
    )


def _same_frequency(left: float, right: float) -> bool:
    return abs(left - right) <= 8.0 * np.finfo(np.float64).eps * max(abs(left), abs(right), 1.0)
