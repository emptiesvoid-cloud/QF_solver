"""Small algebraic-only WP-D01 core checks; no QF model or FEM route is used."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.residual_flexibility import ResidualFlexibilityCorrector
from solveur.core.errors import InputValidationError


def _fixture(mode_count: int) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, ModalBasis]:
    q = 0.5 * np.asarray(
        [[1.0, 1.0, 1.0, 1.0], [1.0, -1.0, 1.0, -1.0], [1.0, 1.0, -1.0, -1.0], [1.0, -1.0, -1.0, 1.0]]
    )
    mass = np.eye(4)
    stiffness = q @ np.diag([1.0, 4.0, 9.0, 16.0]) @ q.T
    screens = {
        name: {"minimum_scaled_eigenvalue_estimate": 1.0, "threshold": 1.0e-12}
        for name in ("mass", "stiffness")
    }
    basis = ModalBasis._from_operators(
        csr_matrix(stiffness),
        csr_matrix(mass),
        operator_identity="synthetic-wp-d01-km",
        dof_signature=(),
        requested_modes=mode_count,
        method="dense",
        dense_limit=4,
        spectral_screens=screens,
    )
    return stiffness, mass, q, basis.modes, basis


def _corrector(stiffness: np.ndarray, mass: np.ndarray, basis: ModalBasis, alpha: float = 0.0, beta: float = 0.0):
    damping = alpha * mass + beta * stiffness
    return ResidualFlexibilityCorrector(
        csr_matrix(stiffness),
        csr_matrix(mass),
        csr_matrix(damping),
        basis,
        operator_identity="synthetic-wp-d01-km",
        rayleigh_alpha=alpha,
        rayleigh_beta=beta,
    )


def _reduced_response(
    stiffness: np.ndarray,
    mass: np.ndarray,
    damping: np.ndarray,
    modes: np.ndarray,
    force: np.ndarray,
    omega: float,
) -> tuple[np.ndarray, np.ndarray]:
    impedance = stiffness + 1j * omega * damping - omega**2 * mass
    reduced_impedance = modes.T @ impedance @ modes
    coordinates = np.linalg.solve(reduced_impedance, modes.T @ force)
    return modes @ coordinates, coordinates


def test_truncated_static_correction_recovers_independent_direct_solution() -> None:
    stiffness, mass, q, modes, basis = _fixture(2)
    force = np.asarray([1.0, 0.0, 0.0, 1.0], dtype=np.complex128)
    damping = np.zeros_like(stiffness)
    uncorrected, coordinates = _reduced_response(stiffness, mass, damping, modes, force, 0.0)

    result = _corrector(stiffness, mass, basis).correct(
        0.0, force, uncorrected, coordinates, excitation_identity="synthetic-force"
    )
    direct = np.linalg.solve(stiffness, force)

    assert np.allclose(result.corrected, direct, rtol=1.0e-13, atol=1.0e-14)
    assert result.diagnostics["C1"]["status"] == "PASS"
    assert result.diagnostics["frequency_eligibility"]["status"] == "IN_BAND_ELIGIBLE"
    assert result.diagnostics["first_omitted_mode"]["retained_cutoff_cluster_complete"] is True
    assert np.linalg.norm(q[:, :2].T @ result.correction) < 1.0e-13


def test_complex_rayleigh_response_preserves_phasor_and_reports_dynamic_residual() -> None:
    stiffness, mass, _, modes, basis = _fixture(2)
    alpha, beta, omega = 0.03, 0.01, 0.30
    damping = alpha * mass + beta * stiffness
    force = np.asarray([1.0 + 0.5j, -0.25j, 0.75, 0.2 - 0.1j])
    uncorrected, coordinates = _reduced_response(stiffness, mass, damping, modes, force, omega)

    result = _corrector(stiffness, mass, basis, alpha, beta).correct(
        omega, force, uncorrected, coordinates, excitation_identity="synthetic-complex-force"
    )
    direct = np.linalg.solve(stiffness + 1j * omega * damping - omega**2 * mass, force)

    assert np.any(result.corrected.imag != 0.0)
    assert np.linalg.norm(result.corrected - direct) < np.linalg.norm(uncorrected - direct)
    assert result.diagnostics["corrected_full_dynamic_residual"]["status"] == "AVAILABLE"
    assert result.diagnostics["frequency_eligibility"]["status"] == "IN_BAND_ELIGIBLE"


def test_complete_basis_has_negligible_correction_and_factorization_is_reused() -> None:
    stiffness, mass, _, modes, basis = _fixture(4)
    force = np.asarray([1.0, 0.0, 0.0, 1.0], dtype=np.complex128)
    damping = np.zeros_like(stiffness)
    uncorrected, coordinates = _reduced_response(stiffness, mass, damping, modes, force, 0.15)
    corrector = _corrector(stiffness, mass, basis)

    first = corrector.correct(0.15, force, uncorrected, coordinates, excitation_identity="fixture")
    second = corrector.correct(0.30, force, uncorrected, coordinates, excitation_identity="fixture")

    assert np.linalg.norm(first.correction) < 1.0e-13
    assert np.linalg.norm(second.correction) < 1.0e-13
    assert first.diagnostics["frequency_eligibility"]["status"] == "NOT_APPLICABLE_FULL_BASIS"
    assert corrector.telemetry["stiffness_factorization_count"] == 1
    assert corrector.telemetry["stiffness_factorization_reuse_count"] == 1
    assert corrector.telemetry["stiffness_rhs_solve_count"] >= 2


@pytest.mark.parametrize("omega", [0.0, 0.15, 0.30, 0.60])
def test_frozen_mixed_fixture_runs_c7_gate(omega: float) -> None:
    stiffness, mass, q, modes, basis = _fixture(2)
    force = q[:, 0] + q[:, 3]
    uncorrected, coordinates = _reduced_response(stiffness, mass, np.zeros_like(stiffness), modes, force, omega)

    result = _corrector(stiffness, mass, basis).correct(
        omega,
        force,
        uncorrected,
        coordinates,
        excitation_identity="frozen-mixed-fixture",
        verification_fixture_id="MIXED_RETAINED_OMITTED",
    )

    assert result.diagnostics["C7"]["applicability"] == "MANDATORY_FIXTURE_GATE"
    assert result.diagnostics["C7"]["status"] == "PASS"
    assert result.diagnostics["C7"]["e_ret"] <= 1.0e-8


def test_declared_c7_fixture_with_mismatched_force_is_rejected() -> None:
    stiffness, mass, _, modes, basis = _fixture(2)
    force = np.asarray([1.0, 0.0, 0.0, 0.0], dtype=np.complex128)
    uncorrected, coordinates = _reduced_response(stiffness, mass, np.zeros_like(stiffness), modes, force, 0.15)

    with pytest.raises(InputValidationError, match="does not match its frozen"):
        _corrector(stiffness, mass, basis).correct(
            0.15,
            force,
            uncorrected,
            coordinates,
            excitation_identity="wrong-load",
            verification_fixture_id="MIXED_RETAINED_OMITTED",
        )


def test_out_of_band_result_is_characterization_only_not_ineligible_computation() -> None:
    stiffness, mass, _, modes, basis = _fixture(2)
    omega = 0.61
    force = np.asarray([1.0, 0.0, 0.0, 1.0], dtype=np.complex128)
    uncorrected, coordinates = _reduced_response(stiffness, mass, np.zeros_like(stiffness), modes, force, omega)

    result = _corrector(stiffness, mass, basis).correct(
        omega, force, uncorrected, coordinates, excitation_identity="synthetic-force"
    )

    assert result.diagnostics["frequency_eligibility"]["status"] == "CHARACTERIZATION_ONLY"
    assert "accuracy guarantee" in result.diagnostics["frequency_eligibility"]["accuracy_claim"]


def test_incompatible_damping_and_basis_identity_fail_closed() -> None:
    stiffness, mass, _, _, basis = _fixture(2)
    with pytest.raises(InputValidationError, match="Rayleigh operator"):
        ResidualFlexibilityCorrector(
            csr_matrix(stiffness),
            csr_matrix(mass),
            csr_matrix(np.eye(4)),
            basis,
            operator_identity="synthetic-wp-d01-km",
            rayleigh_alpha=0.0,
            rayleigh_beta=0.0,
        )
    with pytest.raises(InputValidationError, match="identities do not match"):
        ResidualFlexibilityCorrector(
            csr_matrix(stiffness),
            csr_matrix(mass),
            csr_matrix(np.zeros_like(stiffness)),
            basis,
            operator_identity="stale-operator",
            rayleigh_alpha=0.0,
            rayleigh_beta=0.0,
        )


def test_invalid_complex_operator_and_nonfinite_rhs_are_rejected() -> None:
    stiffness, mass, _, modes, basis = _fixture(2)
    with pytest.raises(InputValidationError, match="must be real-valued"):
        ResidualFlexibilityCorrector(
            csr_matrix(stiffness.astype(np.complex128) * (1.0 + 1.0j)),
            csr_matrix(mass),
            csr_matrix(np.zeros_like(stiffness)),
            basis,
            operator_identity="synthetic-wp-d01-km",
            rayleigh_alpha=0.0,
            rayleigh_beta=0.0,
        )
    corrector = _corrector(stiffness, mass, basis)
    with pytest.raises(InputValidationError, match="finite and have shape"):
        corrector.correct(
            0.0,
            np.asarray([1.0, np.nan, 0.0, 0.0]),
            np.zeros(4),
            np.zeros(2),
            excitation_identity="synthetic-force",
        )
