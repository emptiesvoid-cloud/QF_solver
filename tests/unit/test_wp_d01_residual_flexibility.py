"""Small algebraic-only WP-D01 core checks; no QF model or FEM route is used."""

from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.residual_flexibility import ResidualFlexibilityCorrector
from solveur.core.analyses.residual_flexibility_config import (
    RESIDUAL_FLEXIBILITY_CONFIG_SCHEMA,
    residual_flexibility_implementation_hashes,
)
from solveur.core.analyses.residual_flexibility_results import (
    ResidualFlexibilityFrequencyResult,
    ResidualFlexibilityHarmonicResult,
)
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.errors import InputValidationError
from solveur.core.results import ReducedHarmonicResult
from solveur.io.schema import JsonSchemaValidator
from solveur.io.checkpoint_common import checkpoint_signature


def _fixture(
    mode_count: int, include_first_omitted_evidence: bool = True
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, ModalBasis]:
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
        include_first_omitted_evidence=include_first_omitted_evidence,
        spectral_screens=screens,
    )
    return stiffness, mass, q, basis.modes, basis


def _extension_identity(base: ReducedHarmonicResult) -> dict[str, object]:
    return {
        "schema_version": 1,
        "method": "mode_acceleration",
        "wp05_execution_key": base.execution_key,
        "source_sha": base.execution_identity["source_sha"],
        "operator_identity": base.execution_identity["case_definition"]["operator_identity"],
        "modal_basis_identity": base.execution_identity["case_definition"]["basis_identity"],
    }


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


def test_core_rejects_uncorrected_state_inconsistent_with_modal_coordinates() -> None:
    stiffness, mass, _, modes, basis = _fixture(2)
    force = np.asarray([1.0, 0.0, 0.0, 1.0], dtype=np.complex128)
    valid, coordinates = _reduced_response(stiffness, mass, np.zeros_like(stiffness), modes, force, 0.0)
    inconsistent = valid.copy()
    inconsistent[0] += 1.0e-4

    with pytest.raises(InputValidationError, match=r"equal Phi @ q_solve"):
        _corrector(stiffness, mass, basis).correct(
            0.0,
            force,
            inconsistent,
            coordinates,
            excitation_identity="inconsistent-modal-state",
        )


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

    first = corrector.correct(
        0.15,
        force,
        uncorrected,
        coordinates,
        excitation_identity="fixture",
        verification_fixture_id="COMPLETE_MODAL_BASIS",
    )
    second = corrector.correct(0.30, force, uncorrected, coordinates, excitation_identity="fixture")

    assert np.linalg.norm(first.correction) < 1.0e-13
    assert first.diagnostics["C3"]["status"] == "PASS"
    assert np.linalg.norm(second.correction) < 1.0e-13
    assert first.diagnostics["frequency_eligibility"]["status"] == "NOT_APPLICABLE_FULL_BASIS"
    assert corrector.telemetry["stiffness_factorization_count"] == 1
    assert corrector.telemetry["stiffness_factorization_reuse_count"] == 1
    assert corrector.telemetry["stiffness_rhs_solve_count"] >= 2


def test_omitted_evidence_is_opt_in_and_does_not_change_wp04_basis_identity() -> None:
    _, _, _, _, default_basis = _fixture(2, include_first_omitted_evidence=False)
    _, _, _, _, d01_basis = _fixture(2, include_first_omitted_evidence=True)

    assert default_basis.first_omitted_eigenpair is None
    assert d01_basis.first_omitted_eigenpair["status"] == "AVAILABLE"
    assert default_basis.basis_identity == d01_basis.basis_identity
    assert default_basis.extraction == d01_basis.extraction
    assert default_basis.diagnostics == d01_basis.diagnostics


def test_missing_omitted_mode_evidence_is_not_evaluable() -> None:
    stiffness, mass, _, modes, basis = _fixture(2, include_first_omitted_evidence=False)
    force = np.asarray([1.0, 0.0, 0.0, 1.0], dtype=np.complex128)
    uncorrected, coordinates = _reduced_response(stiffness, mass, np.zeros_like(stiffness), modes, force, 0.15)

    result = _corrector(stiffness, mass, basis).correct(
        0.15, force, uncorrected, coordinates, excitation_identity="missing-cutoff-evidence"
    )

    assert result.diagnostics["frequency_eligibility"]["status"] == "NOT_EVALUABLE"
    assert result.diagnostics["frequency_eligibility"]["accuracy_claim"] == "NONE"
    assert result.diagnostics["first_omitted_mode"]["status"] == "NOT_EVALUABLE"


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


def test_zero_retained_response_uses_frozen_absolute_floor_without_claiming_c7_pass() -> None:
    stiffness, mass, q, modes, basis = _fixture(2)
    force = q[:, 3].astype(np.complex128)
    uncorrected, coordinates = _reduced_response(stiffness, mass, np.zeros_like(stiffness), modes, force, 0.15)

    result = _corrector(stiffness, mass, basis).correct(
        0.15, force, uncorrected, coordinates, excitation_identity="omitted-only-load"
    )

    c7 = result.diagnostics["C7"]
    assert c7["status"] == "CHARACTERIZATION_ONLY"
    assert c7["reference_flags"] == ["FLOOR_ACTIVE"]
    assert c7["numerator_mass_norm"] < c7["absolute_reference_floor_m_sqrt_kg"]
    assert np.isfinite(c7["e_ret"])
    assert c7["absolute_reference_floor_scope"].startswith("frozen four-DOF")


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


def test_opt_in_configuration_is_strict_and_disabled_is_default_compatible() -> None:
    default = AnalysisSettings.from_raw(
        {"type": "harmonic_response", "method": "modal_superposition", "frequencies_hz": [1.0]}
    )
    assert "residual_flexibility" not in default.parameters

    enabled = {
        "schema": RESIDUAL_FLEXIBILITY_CONFIG_SCHEMA,
        "enabled": True,
        "method": "mode_acceleration",
    }
    settings = AnalysisSettings.from_raw(
        {
            "type": "harmonic_response",
            "method": "modal_superposition",
            "parameters": {"frequencies_hz": [1.0], "residual_flexibility": enabled},
        }
    )
    assert settings.parameters["residual_flexibility"]["enabled"] is True

    with pytest.raises(InputValidationError, match="only for harmonic_response/modal_superposition"):
        AnalysisSettings.from_raw(
            {
                "type": "harmonic_response",
                "method": "direct_frequency",
                "parameters": {"frequencies_hz": [1.0], "residual_flexibility": enabled},
            }
        )
    with pytest.raises(InputValidationError, match="does not support WP07"):
        AnalysisSettings.from_raw(
            {
                "type": "harmonic_response",
                "method": "modal_superposition",
                "parameters": {
                    "frequencies_hz": [1.0],
                    "residual_flexibility": enabled,
                    "uniform_base_acceleration": {},
                },
            }
        )
    with pytest.raises(InputValidationError, match="physical Rayleigh damping only"):
        AnalysisSettings.from_raw(
            {
                "type": "harmonic_response",
                "method": "modal_superposition",
                "parameters": {
                    "frequencies_hz": [1.0],
                    "residual_flexibility": enabled,
                    "reduced_damping_model": "prescribed_modal",
                },
            }
        )


def test_json_analysis_schema_uses_same_opt_in_contract() -> None:
    validator = JsonSchemaValidator()
    enabled = {
        "schema": RESIDUAL_FLEXIBILITY_CONFIG_SCHEMA,
        "enabled": True,
        "method": "mode_acceleration",
    }
    errors: list[str] = []
    validator._validate_analysis(
        {
            "type": "harmonic_response",
            "method": "modal_superposition",
            "parameters": {"frequencies_hz": [1.0], "residual_flexibility": enabled},
        },
        errors,
    )
    assert not errors

    errors = []
    validator._validate_analysis(
        {
            "type": "harmonic_response",
            "method": "direct_frequency",
            "parameters": {"frequencies_hz": [1.0], "residual_flexibility": enabled},
        },
        errors,
    )
    assert any("only for harmonic_response/modal_superposition" in error for error in errors)


def test_extension_identity_fingerprints_core_and_integration_dependencies() -> None:
    fingerprints = residual_flexibility_implementation_hashes()

    assert {
        "core/analyses/reduced_harmonic.py",
        "core/analyses/modal_basis.py",
        "core/analyses/prepared_dynamic_system.py",
        "io/schema_analysis.py",
        "core/analyses/residual_flexibility.py",
        "core/analyses/residual_flexibility_results.py",
    }.issubset(fingerprints)
    assert all(len(value) == 64 for value in fingerprints.values())


def _base_result(response: np.ndarray) -> ReducedHarmonicResult:
    return ReducedHarmonicResult(
        numerical_status="PASS",
        frequencies_hz=np.asarray([0.5]),
        responses=(response,),
        modal_coordinates=(np.asarray([0.2 + 0.1j]),),
        dof_signature=((1, ("UX",)),),
        full_dof_count=1,
        node_count=1,
        element_count=0,
        solver={},
        provenance={},
        result_availability={"physical_reactions": {"status": "UNAVAILABLE"}},
        execution_identity={
            "source_sha": "synthetic-source-identity",
            "case_definition": {"operator_identity": "operator", "basis_identity": "basis"},
        },
        execution_key="wp05-key",
        qualification_scope_id="experimental-scope",
        mesh_report={},
    )


def test_versioned_result_wrapper_round_trips_without_rewriting_wp05_v1() -> None:
    uncorrected = np.asarray([1.0 + 0.5j])
    correction = np.asarray([0.125 - 0.25j])
    corrected = uncorrected + correction
    base = _base_result(uncorrected)
    extension_identity = _extension_identity(base)
    wrapper = ResidualFlexibilityHarmonicResult(
        wp05_result=base,
        frequency_results=(
            ResidualFlexibilityFrequencyResult(
                frequency_hz=0.5,
                uncorrected=uncorrected,
                correction=correction,
                corrected=corrected,
                diagnostics={"C1": {"status": "PASS", "normalized_backward_error": 0.0}},
            ),
        ),
        telemetry={"stiffness_factorization_count": 1, "peak_memory_bytes": None},
        extension_identity=extension_identity,
        extension_execution_key=checkpoint_signature(
            extension_identity, label="WP-D01 residual-flexibility execution identity"
        ),
    )

    payload = wrapper.to_dict()
    restored = ResidualFlexibilityHarmonicResult.from_dict(payload)

    assert payload["wp05_result"]["schema"] == ReducedHarmonicResult.CONTRACT
    assert np.array_equal(restored.uncorrected_responses[0], uncorrected)
    assert np.array_equal(restored.corrections[0], correction)
    assert np.array_equal(restored.responses[0], corrected)
    assert restored.execution_key == wrapper.extension_execution_key
    assert restored.wp05_result.execution_key == base.execution_key


def test_versioned_result_wrapper_rejects_forged_correction_and_schema() -> None:
    uncorrected = np.asarray([1.0 + 0.5j])
    base = _base_result(uncorrected)
    row = ResidualFlexibilityFrequencyResult(
        frequency_hz=0.5,
        uncorrected=uncorrected,
        correction=np.asarray([0.1 + 0.0j]),
        corrected=np.asarray([1.1 + 0.5j]),
        diagnostics={},
    )
    extension_identity = _extension_identity(base)
    wrapper = ResidualFlexibilityHarmonicResult(
        wp05_result=base,
        frequency_results=(row,),
        telemetry={},
        extension_identity=extension_identity,
        extension_execution_key=checkpoint_signature(
            extension_identity, label="WP-D01 residual-flexibility execution identity"
        ),
    )
    payload = wrapper.to_dict()
    payload["residual_flexibility"]["frequency_results"][0]["corrected_response"]["real"][0] = 2.0
    with pytest.raises(ValueError, match="incomplete, inconsistent or malformed"):
        ResidualFlexibilityHarmonicResult.from_dict(payload)
    with pytest.raises(ValueError, match="Unsupported WP-D01"):
        ResidualFlexibilityHarmonicResult.from_dict({"schema": "wrong"})


def test_versioned_result_wrapper_rejects_tampered_extension_provenance() -> None:
    uncorrected = np.asarray([1.0 + 0.5j])
    correction = np.asarray([0.1 - 0.1j])
    base = _base_result(uncorrected)
    identity = _extension_identity(base)
    wrapper = ResidualFlexibilityHarmonicResult(
        wp05_result=base,
        frequency_results=(
            ResidualFlexibilityFrequencyResult(
                frequency_hz=0.5,
                uncorrected=uncorrected,
                correction=correction,
                corrected=uncorrected + correction,
                diagnostics={"C1": {"status": "PASS"}},
            ),
        ),
        telemetry={},
        extension_identity=identity,
        extension_execution_key=checkpoint_signature(
            identity, label="WP-D01 residual-flexibility execution identity"
        ),
    )
    payload = wrapper.to_dict()
    payload["residual_flexibility"]["extension_identity"]["source_sha"] = "tampered-source"

    with pytest.raises(ValueError, match="incomplete, inconsistent or malformed"):
        ResidualFlexibilityHarmonicResult.from_dict(payload)
