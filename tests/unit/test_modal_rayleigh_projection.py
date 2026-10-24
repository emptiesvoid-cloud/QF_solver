from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.analyses.reduced_harmonic import _resolve_damping
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.io.schema import JsonSchemaValidator


def _synthetic_prepared_and_basis() -> tuple[PreparedDynamicSystem, ModalBasis]:
    mass = np.diag([2.0, 1.0, 0.5])
    stiffness = np.diag([20.0, 8.0, 4.0])
    identity = "synthetic-rayleigh-projection-v1"

    prepared = object.__new__(PreparedDynamicSystem)
    prepared._operator_identity = identity
    prepared._dof_signature = ()
    prepared._reducer = SimpleNamespace(reduced_size=3)
    prepared._mass_reduced = csr_matrix(mass)
    prepared._stiffness_reduced = csr_matrix(stiffness)

    basis = ModalBasis._from_operators(
        csr_matrix(stiffness),
        csr_matrix(mass),
        operator_identity=identity,
        dof_signature=(),
        requested_modes=2,
        method="dense",
        dense_limit=3,
    )
    return prepared, basis


def test_rayleigh_structured_projection_is_explicit_and_matches_legacy_physics() -> None:
    prepared, basis = _synthetic_prepared_and_basis()
    alpha, beta = 0.2, 2.0e-5

    legacy, _ = _resolve_damping(
        basis,
        prepared,
        {"rayleigh_alpha": alpha, "rayleigh_beta": beta},
    )
    structured, coefficients = _resolve_damping(
        basis,
        prepared,
        {
            "rayleigh_alpha": alpha,
            "rayleigh_beta": beta,
            "reduced_damping_projection": "rayleigh_structured",
        },
    )

    expected = alpha * basis.projected_mass + beta * basis.projected_stiffness
    np.testing.assert_array_equal(structured.matrix, expected)
    np.testing.assert_allclose(structured.matrix, legacy.matrix, rtol=0.0, atol=1e-15)
    assert coefficients == (alpha, beta)
    assert structured.parameters["projection_method"] == "rayleigh_structured"
    assert structured.parameters["direct_projection_relative_consistency_error"] <= 1e-8
    assert legacy.parameters == {
        "source": "explicit_rayleigh",
        "rayleigh_alpha": alpha,
        "rayleigh_beta": beta,
        "modal_targets": [],
    }


@pytest.mark.parametrize("method", [None, [], "average"])
def test_unknown_projection_method_fails_closed(method: object) -> None:
    prepared, basis = _synthetic_prepared_and_basis()
    with pytest.raises(InputValidationError, match="reduced_damping_projection"):
        _resolve_damping(
            basis,
            prepared,
            {"rayleigh_alpha": 0.2, "rayleigh_beta": 2.0e-5, "reduced_damping_projection": method},
        )


def test_rayleigh_structured_method_cannot_be_used_for_prescribed_modal_damping() -> None:
    prepared, basis = _synthetic_prepared_and_basis()
    with pytest.raises(InputValidationError, match="only to physical Rayleigh"):
        _resolve_damping(
            basis,
            prepared,
            {
                "reduced_damping_model": "prescribed_modal",
                "modal_damping_ratios": [0.02, 0.02],
                "reduced_damping_projection": "rayleigh_structured",
            },
        )


def test_structured_projection_rejects_inconsistent_modal_operators() -> None:
    prepared, basis = _synthetic_prepared_and_basis()
    prepared._stiffness_reduced = prepared._stiffness_reduced * 2.0
    with pytest.raises(NumericalConvergenceError, match="disagrees with projected K/M"):
        basis.rayleigh_damping_from_parameters(
            prepared,
            {"rayleigh_alpha": 0.2, "rayleigh_beta": 2.0e-5},
            projection_method="rayleigh_structured",
        )


@pytest.mark.parametrize("method", ["legacy_direct", "rayleigh_structured"])
def test_harmonic_schema_accepts_only_registered_projection_methods(method: str) -> None:
    errors: list[str] = []
    JsonSchemaValidator()._validate_analysis_parameters(
        "harmonic_response",
        {"frequencies_hz": [1.0], "reduced_damping_projection": method},
        errors,
        method="modal_superposition",
    )
    assert not errors


@pytest.mark.parametrize("method", [[], "average", None])
def test_harmonic_schema_rejects_unregistered_projection_methods(method: object) -> None:
    errors: list[str] = []
    JsonSchemaValidator()._validate_analysis_parameters(
        "harmonic_response",
        {"frequencies_hz": [1.0], "reduced_damping_projection": method},
        errors,
        method="modal_superposition",
    )
    assert any("reduced_damping_projection" in error for error in errors)


@pytest.mark.parametrize("method", ["direct_frequency", "harmonic_direct"])
def test_projection_option_is_rejected_outside_modal_superposition(method: str) -> None:
    errors: list[str] = []
    JsonSchemaValidator()._validate_analysis(
        {
            "type": "harmonic_response",
            "method": method,
            "parameters": {"frequencies_hz": [1.0], "reduced_damping_projection": "rayleigh_structured"},
        },
        errors,
    )
    assert any("requires method='modal_superposition'" in error for error in errors)


def test_projection_option_without_method_is_rejected_by_harmonic_default() -> None:
    errors: list[str] = []
    JsonSchemaValidator()._validate_analysis(
        {
            "type": "harmonic_response",
            "parameters": {"frequencies_hz": [1.0], "reduced_damping_projection": "rayleigh_structured"},
        },
        errors,
    )
    assert any("requires method='modal_superposition'" in error for error in errors)


@pytest.mark.parametrize(
    "extra",
    [
        {"reduced_damping_model": "prescribed_modal"},
        {"modal_damping_ratios": [0.02]},
        {"damping_model": "non_rayleigh"},
    ],
)
def test_projection_option_is_rejected_for_non_rayleigh_damping(extra: dict[str, object]) -> None:
    errors: list[str] = []
    parameters = {"frequencies_hz": [1.0], "reduced_damping_projection": "rayleigh_structured", **extra}
    JsonSchemaValidator()._validate_analysis(
        {"type": "harmonic_response", "method": "modal_superposition", "parameters": parameters},
        errors,
    )
    assert any("reduced_damping_projection" in error for error in errors)


@pytest.mark.parametrize(
    "method,extra",
    [
        ("direct_frequency", {}),
        ("modal_superposition", {"reduced_damping_model": "prescribed_modal"}),
        ("modal_superposition", {"modal_damping_ratios": [0.02]}),
        ("modal_superposition", {"damping_model": "non_rayleigh"}),
    ],
)
def test_programmatic_model_rejects_projection_before_any_preparation(
    method: str, extra: dict[str, object]
) -> None:
    settings = AnalysisSettings(
        type="harmonic_response",
        method=method,
        parameters={"frequencies_hz": [1.0], "reduced_damping_projection": "rayleigh_structured", **extra},
    )
    with pytest.raises(ValueError, match="reduced_damping_projection"):
        FiniteElementModel(nodes=np.zeros((1, 3)), elements=[], materials={}, analysis=settings)
