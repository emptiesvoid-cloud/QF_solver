from __future__ import annotations

import json
from fractions import Fraction
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csc_matrix, csr_matrix, diags

from solveur.core.analyses import modal_residual_validation
from solveur.core.analyses import modal as modal_module
from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.settings import AnalysisSettings
from solveur.core.analyses.modal_residual_validation import (
    MAX_STORED_TERMS,
    ModalEigenpairValidation,
    ModalResidualCheck,
    _Refuse,
    _matrix_entries,
    check_modal_residual_exact,
    is_budget_limited_inconclusive,
    modal_response_status,
    modal_diagnostics_are_finite,
    modal_result_components_are_finite,
    validate_modal_eigenpairs,
)
from solveur.core.errors import ModalResidualValidationError
from solveur.core.dofs import DOF_ORDER, DofManager
from solveur.execution.diagnostics import DiagnosticCategory, DiagnosticCode, diagnostic_from_exception
from solveur.core.results import ModalNewmarkResult, ModalResult, ReducedHarmonicResult
from solveur.mesh.validation import MeshReport
from solveur.io.json_reader import JsonModelReader


def test_modal_validation_policy_is_opt_in_and_route_scoped() -> None:
    compatible = AnalysisSettings.from_raw(
        {
            "type": "harmonic_response",
            "method": "modal_superposition",
            "parameters": {"modal_validation_policy": "allow_inconclusive"},
        }
    )
    strict_default = AnalysisSettings.from_raw(
        {"type": "transient_dynamic", "method": "modal_newmark", "parameters": {}}
    )
    assert compatible.parameters["modal_validation_policy"] == "allow_inconclusive"
    assert strict_default.parameters.get("modal_validation_policy", "strict") == "strict"
    with pytest.raises(ValueError, match="modal_validation_policy"):
        AnalysisSettings.from_raw(
            {
                "type": "linear_static",
                "method": "direct",
                "parameters": {"modal_validation_policy": "allow_inconclusive"},
            }
        )


def test_json_model_input_preserves_explicit_modal_compatibility_policy() -> None:
    model = JsonModelReader().from_dict(
        {
            "nodes": [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
            "materials": {"steel": {"type": "isotropic_3d", "E": 1.0, "nu": 0.25}},
            "analysis": {
                "type": "modal",
                "method": "eigsh",
                "parameters": {"modal_validation_policy": "allow_inconclusive"},
            },
        }
    )
    assert model.analysis.parameters["modal_validation_policy"] == "allow_inconclusive"


def test_direct_modal_route_returns_computed_inconclusive_result_only_when_opted_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    size = 132
    stiffness_matrix = diags(np.arange(1.0, size + 1.0), format="csr")
    mass_matrix = csr_matrix(np.eye(size))
    dofs = DofManager.from_node_requirements(
        {node: set(DOF_ORDER) for node in range(1, size // len(DOF_ORDER) + 1)}
    )
    assert dofs.ndof == size

    class SyntheticReducer:
        free = np.arange(size, dtype=int)
        reduced_size = size
        stiffness = stiffness_matrix
        mass = mass_matrix
        diagnostics = {"lazy_condensation": False}

        @staticmethod
        def expand_state(vector: np.ndarray) -> np.ndarray:
            return np.asarray(vector, dtype=np.float64)

        @staticmethod
        def reduce_state(vector: np.ndarray) -> np.ndarray:
            return np.asarray(vector, dtype=np.float64)

    report = SimpleNamespace(status="PASS", errors=[], to_dict=lambda: {"status": "PASS"})
    model = SimpleNamespace(
        analysis=SimpleNamespace(
            type="modal",
            method="eigsh",
            parameters={"modes": 6, "modal_validation_policy": "allow_inconclusive"},
        ),
        node_count=size // len(DOF_ORDER),
        elements=[],
        dof_manager=lambda: dofs,
    )
    solver = modal_module.ModalAnalysisSolver()
    monkeypatch.setattr(solver.validator, "validate", lambda _model: report)
    monkeypatch.setattr(
        solver.assembler,
        "assemble_stiffness_and_mass",
        lambda _model, _dofs: (stiffness_matrix, mass_matrix, {}, {}),
    )
    monkeypatch.setattr(solver.assembler, "fixed_indices", lambda _model, _dofs: np.asarray([], dtype=int))
    monkeypatch.setattr(
        modal_module.DynamicDofReducer,
        "from_system",
        staticmethod(lambda *_args, **_kwargs: SyntheticReducer()),
    )
    monkeypatch.setattr(
        solver,
        "_solve_eigenproblem",
        lambda *_args, **_kwargs: (
            np.arange(1.0, 7.0),
            np.eye(size, 6),
            "synthetic_matrix_eigensolver",
        ),
    )
    monkeypatch.setattr(modal_module.SolverAudit, "from_state", staticmethod(lambda **_kwargs: None))

    model.analysis.parameters["modal_validation_policy"] = "strict"
    with pytest.raises(ModalResidualValidationError) as strict_error:
        solver.solve(model)  # type: ignore[arg-type]
    assert strict_error.value.validation_status == "INCONCLUSIVE"
    assert strict_error.value.computed_result["modes"].shape == (size, 6)

    model.analysis.parameters["modal_validation_policy"] = "allow_inconclusive"
    result = solver.solve(model)  # type: ignore[arg-type]

    assert result.status == "INCONCLUSIVE"
    assert result.solver["calculation_status"] == "COMPUTED"
    assert result.solver["modal_validation_status"] == "INCONCLUSIVE"
    assert result.solver["modal_use_policy"] == "ALLOW_INCONCLUSIVE_COMPUTED_MODES"
    assert result.to_dict()["run_verdict"] == "WARNING"


def test_only_pure_budget_inconclusive_aggregates_are_compatibility_eligible() -> None:
    budget_only = ModalEigenpairValidation(
        "INCONCLUSIVE",
        "one_or_more_residuals_not_certified",
        (ModalResidualCheck("INCONCLUSIVE", "dimension_budget", 129, 1, 3, 53),),
    )
    mixed = ModalEigenpairValidation(
        "INCONCLUSIVE",
        "one_or_more_residuals_not_certified",
        (
            ModalResidualCheck("INCONCLUSIVE", "dimension_budget", 129, 1, 3, 53),
            ModalResidualCheck("INCONCLUSIVE", "nonfinite_input", 1, 1, 3, 0),
        ),
    )
    failed = ModalEigenpairValidation(
        "FAIL",
        "one_or_more_represented_residuals_fail",
        (ModalResidualCheck("FAIL", "exact_represented_input_residual_exceeds_tolerance", 1, 1, 3, 53),),
    )

    assert is_budget_limited_inconclusive(budget_only)
    assert not is_budget_limited_inconclusive(mixed)
    assert not is_budget_limited_inconclusive(failed)
    assert modal_response_status("PASS_CERTIFIED") == "PASS"
    assert modal_response_status("INCONCLUSIVE") == "INCONCLUSIVE"
    assert modal_response_status("FAIL") == "FAIL"


def test_uncertified_reduced_result_serializes_computation_and_validation_separately() -> None:
    result = ReducedHarmonicResult(
        numerical_status="INCONCLUSIVE",
        frequencies_hz=np.asarray([1.0]),
        responses=(np.asarray([1.0 + 0.0j]),),
        modal_coordinates=(np.asarray([1.0 + 0.0j]),),
        dof_signature=((1, ("UX",)),),
        full_dof_count=1,
        node_count=1,
        element_count=0,
        solver={
            "modal_basis_calculation_status": "COMPUTED",
            "modal_basis_validation_status": "INCONCLUSIVE",
            "modal_basis_use_policy": "ALLOW_INCONCLUSIVE_COMPUTED_MODES",
        },
        provenance={},
        result_availability={
            "modal_basis_validation": {
                "status": "INCONCLUSIVE",
                "calculation_status": "COMPUTED",
                "usable_as_certified_evidence": False,
            }
        },
        execution_identity={},
        execution_key="synthetic-inconclusive-modal-result",
        qualification_scope_id="not-assessed",
        mesh_report={},
    )

    payload = result.to_dict()
    json.dumps(payload, allow_nan=False)
    assert payload["status"] == "INCONCLUSIVE"
    assert payload["solver"]["modal_basis_validation_status"] == "INCONCLUSIVE"
    assert payload["result_availability"]["modal_basis_validation"]["usable_as_certified_evidence"] is False
    assert payload["run_verdict"] == "WARNING"


def test_inconclusive_modal_and_newmark_results_remain_available_without_pass_status() -> None:
    dofs = DofManager.from_node_requirements({1: {"UX"}})
    modal = ModalResult(
        status="INCONCLUSIVE",
        eigenvalues=np.asarray([1.0]),
        frequencies_hz=np.asarray([1.0 / (2.0 * np.pi)]),
        modes=np.asarray([[1.0]]),
        dofs=dofs,
        mesh_report=MeshReport(status="PASS"),
        node_count=1,
        element_count=0,
        solver={
            "calculation_status": "COMPUTED",
            "modal_validation_status": "INCONCLUSIVE",
            "modal_use_policy": "ALLOW_INCONCLUSIVE_COMPUTED_MODES",
        },
    )
    transient = ModalNewmarkResult(
        numerical_status="INCONCLUSIVE",
        times=np.asarray([0.0, 1.0]),
        displacements=np.asarray([0.0]),
        velocities=np.asarray([0.0]),
        accelerations=np.asarray([0.0]),
        modal_displacements=np.asarray([0.0]),
        modal_velocities=np.asarray([0.0]),
        modal_accelerations=np.asarray([0.0]),
        dofs=dofs,
        node_count=1,
        element_count=0,
        solver={
            "modal_basis_calculation_status": "COMPUTED",
            "modal_basis_validation_status": "INCONCLUSIVE",
            "modal_basis_use_policy": "ALLOW_INCONCLUSIVE_COMPUTED_MODES",
        },
        provenance={},
        result_availability={
            "modal_basis_validation": {
                "status": "INCONCLUSIVE",
                "calculation_status": "COMPUTED",
                "usable_as_certified_evidence": False,
            }
        },
        execution_identity={},
        execution_key="synthetic-newmark-inconclusive",
        qualification_scope_id="not-assessed",
        mesh_report={},
    )

    modal_payload = modal.to_dict()
    newmark_payload = transient.to_dict()
    json.dumps(modal_payload, allow_nan=False)
    json.dumps(newmark_payload, allow_nan=False)
    assert modal_payload["status"] == "INCONCLUSIVE"
    assert modal_payload["run_verdict"] == "WARNING"
    assert modal_payload["solver"]["modal_validation_status"] == "INCONCLUSIVE"
    assert newmark_payload["status"] == "INCONCLUSIVE"
    assert newmark_payload["run_verdict"] == "WARNING"
    assert newmark_payload["result_availability"]["modal_basis_validation"][
        "usable_as_certified_evidence"
    ] is False


def _duplicate_stiffness_csr() -> csr_matrix:
    return csr_matrix(
        (
            np.asarray([1.0, 1.0, -1.0, -1.0, 1.0, 1.0]),
            np.asarray([0, 0, 1, 0, 1, 1]),
            np.asarray([0, 3, 6]),
        ),
        shape=(2, 2),
    )


def _duplicate_stiffness_csc() -> csc_matrix:
    return csc_matrix(
        (
            np.asarray([1.0, 1.0, -1.0, -1.0, 1.0, 1.0]),
            np.asarray([0, 0, 1, 0, 1, 1]),
            np.asarray([0, 3, 6]),
        ),
        shape=(2, 2),
    )


@pytest.mark.parametrize("matrix_format", ["dense", "csr_duplicates", "csc_duplicates"])
def test_production_contract_certifies_simple_nondiagonal_pair(matrix_format: str) -> None:
    stiffness = np.asarray([[2.0, -1.0], [-1.0, 2.0]])
    mass = np.eye(2)
    if matrix_format == "csr_duplicates":
        stiffness = _duplicate_stiffness_csr()
        mass = csr_matrix(mass)
    elif matrix_format == "csc_duplicates":
        stiffness = _duplicate_stiffness_csc()
        mass = csc_matrix(mass)

    check = check_modal_residual_exact(stiffness, mass, 1.0, np.asarray([1.0, 1.0]), 1.0e-7)

    assert check.status == "PASS_CERTIFIED"
    assert check.residual_ratio_squared == "0/1"


@pytest.mark.parametrize("matrix_format", ["dense", "csr", "csc"])
def test_production_contract_rejects_historical_small_scale_false_pass(matrix_format: str) -> None:
    stiffness = np.asarray([[1.0e-16, 1.0e-17], [1.0e-17, 2.0e-18]])
    mass = np.diag([1.0e-16, 1.0e-18])
    vector = np.asarray([1.0e-307, 0.0])
    if matrix_format == "csr":
        stiffness, mass = csr_matrix(stiffness), csr_matrix(mass)
    elif matrix_format == "csc":
        stiffness, mass = csc_matrix(stiffness), csc_matrix(mass)

    validation = validate_modal_eigenpairs(
        stiffness,
        mass,
        np.asarray([1.0]),
        vector[:, None],
        1.0e-7,
        legacy_residuals=np.asarray([0.0]),
    )

    assert validation.status == "FAIL"
    check = validation.checks[0]
    assert check.residual_ratio_squared is not None
    assert Fraction(check.residual_ratio_squared) > 0


def test_production_contract_preserves_scale_invariant_ratio() -> None:
    stiffness = np.asarray([[2.0, -1.0], [-1.0, 2.0]])
    mass = np.eye(2)
    vector = np.asarray([1.0, 1.0 + 2.0**-20])
    checks = [
        check_modal_residual_exact(scale * stiffness, scale * mass, 1.0, vector, 1.0e-7)
        for scale in (2.0**-500, 1.0, 2.0**500)
    ]

    assert all(check.status == "FAIL" for check in checks)
    assert len({check.residual_ratio_squared for check in checks}) == 1


def test_production_contract_refuses_nonfinite_inputs_and_diagnostics() -> None:
    stiffness = np.eye(2)
    mass = np.eye(2)
    vector = np.asarray([1.0, 0.0])
    nonfinite_input = check_modal_residual_exact(
        stiffness, mass, np.nan, vector, 1.0e-7
    )
    nonfinite_matrix = stiffness.copy()
    nonfinite_matrix[0, 0] = np.inf
    nonfinite_vector = vector.copy()
    nonfinite_vector[0] = np.nan
    nonfinite_tolerance = check_modal_residual_exact(
        stiffness, mass, 1.0, vector, float("inf")
    )
    nonfinite_diagnostic = validate_modal_eigenpairs(
        stiffness,
        mass,
        np.asarray([1.0]),
        vector[:, None],
        1.0e-7,
        legacy_residuals=np.asarray([np.nan]),
    )

    assert nonfinite_input.status == "INCONCLUSIVE"
    assert check_modal_residual_exact(
        nonfinite_matrix, mass, 1.0, vector, 1.0e-7
    ).status == "INCONCLUSIVE"
    assert check_modal_residual_exact(
        stiffness, mass, 1.0, nonfinite_vector, 1.0e-7
    ).status == "INCONCLUSIVE"
    assert nonfinite_tolerance.status == "INCONCLUSIVE"
    assert nonfinite_diagnostic.status == "INCONCLUSIVE"
    assert not modal_diagnostics_are_finite({"nested": [float("inf")]})
    assert modal_diagnostics_are_finite({"nested": [1.0, 2, "ok"]})
    assert not modal_diagnostics_are_finite({"expanded_modes": np.asarray([np.inf])})
    assert not modal_result_components_are_finite(
        {"all_finite": True}, np.asarray([1.0]), np.asarray([[np.nan]])
    )
    assert modal_result_components_are_finite(
        {"all_finite": True}, np.asarray([1.0]), np.asarray([[2.0]])
    )


def test_production_contract_refuses_zero_reference_and_invalid_tolerance() -> None:
    zero = np.zeros((2, 2))
    vector = np.asarray([1.0, 0.0])
    zero_reference = check_modal_residual_exact(zero, zero, 1.0, vector, 1.0e-7)
    invalid_tolerance = check_modal_residual_exact(np.eye(2), np.eye(2), 1.0, vector, 0.0)
    boolean_tolerance = check_modal_residual_exact(np.eye(2), np.eye(2), 1.0, vector, True)
    string_tolerance = check_modal_residual_exact(np.eye(2), np.eye(2), 1.0, vector, "1e-7")

    assert zero_reference.status == "INCONCLUSIVE"
    assert invalid_tolerance.status == "INCONCLUSIVE"
    assert boolean_tolerance.status == "INCONCLUSIVE"
    assert string_tolerance.status == "INCONCLUSIVE"


def test_production_contract_refuses_unverified_float_platform(monkeypatch: pytest.MonkeyPatch) -> None:
    class UnsupportedFloatInfo:
        radix = 10
        mant_dig = 7
        min_exp = -37
        max_exp = 38

    monkeypatch.setattr(modal_residual_validation.sys, "float_info", UnsupportedFloatInfo())
    result = check_modal_residual_exact(np.eye(2), np.eye(2), 1.0, np.asarray([1.0, 0.0]), 1.0e-7)

    assert result.status == "INCONCLUSIVE"
    assert result.reason == "unsupported_python_float_format"


def test_production_contract_budget_refusal_is_aggregate_and_explicit() -> None:
    stiffness = csr_matrix(np.eye(128))
    mass = csr_matrix(np.eye(128))
    values = np.ones(43)
    vectors = np.eye(128, 43)

    result = validate_modal_eigenpairs(stiffness, mass, values, vectors, 1.0e-7)

    assert result.status == "INCONCLUSIVE"
    assert result.reason == "aggregate_work_budget"
    assert result.checks == ()


def test_modal_validation_error_serializes_the_nonpass_candidate() -> None:
    candidate = {"status": "INCONCLUSIVE", "eigenvalues": [1.0, 2.0]}
    error = ModalResidualValidationError(
        "modal validation unavailable",
        validation_status="INCONCLUSIVE",
        diagnostics={"reason": "dimension_budget"},
        computed_result=candidate,
    )

    serialized = error.to_dict()

    assert serialized["converged"] is False
    assert serialized["modal_validation_status"] == "INCONCLUSIVE"
    assert serialized["computed_result"] == candidate


def test_modal_validation_error_emits_strict_json_for_nonfinite_diagnostics() -> None:
    error = ModalResidualValidationError(
        "modal validation unavailable",
        validation_status="INCONCLUSIVE",
        diagnostics={"bad": float("nan")},
        computed_result={
            "values": np.asarray([np.nan, np.inf, -np.inf], dtype=np.float64),
            "wide_scalar": np.longdouble("inf"),
        },
    )

    serialized = error.to_dict()
    json.dumps(serialized, allow_nan=False)

    assert serialized["diagnostics"]["bad"] == {"nonfinite": "NaN"}
    assert serialized["computed_result"]["values"] == [
        {"nonfinite": "NaN"}, {"nonfinite": "+Infinity"}, {"nonfinite": "-Infinity"}
    ]
    assert serialized["computed_result"]["wide_scalar"] == {"nonfinite": "+Infinity"}


def test_execution_diagnostic_preserves_inconclusive_status_and_candidate() -> None:
    error = ModalResidualValidationError(
        "modal residual validation is outside supported domain",
        validation_status="INCONCLUSIVE",
        diagnostics={"reason": "dimension_budget"},
        computed_result={"eigenvalues_rad2_s2": np.asarray([1.0]), "modes": np.asarray([[1.0]])},
    )

    diagnostic = diagnostic_from_exception(error, context={"route": "modal"})
    serialized = diagnostic.to_dict()
    json.dumps(serialized, allow_nan=False)

    assert diagnostic.category is DiagnosticCategory.RESOURCE_LIMITATION
    assert diagnostic.code is DiagnosticCode.RESOURCE_LIMITATION
    assert serialized["context"]["modal_validation"]["modal_validation_status"] == "INCONCLUSIVE"
    assert serialized["context"]["modal_validation"]["computed_result"]["modes"] == [[1.0]]

    nested_budget_error = ModalResidualValidationError(
        "modal residual validation is inconclusive",
        validation_status="INCONCLUSIVE",
        diagnostics={
            "reason": "one_or_more_residuals_not_certified",
            "checks": [{"reason": "integer_bit_budget"}],
        },
    )
    nested_unsupported_error = ModalResidualValidationError(
        "modal residual validation is inconclusive",
        validation_status="INCONCLUSIVE",
        diagnostics={
            "reason": "one_or_more_residuals_not_certified",
            "checks": [{"reason": "unsupported_scalar_type"}],
        },
    )

    assert diagnostic_from_exception(nested_budget_error).category is DiagnosticCategory.RESOURCE_LIMITATION
    assert (
        diagnostic_from_exception(nested_unsupported_error).category
        is DiagnosticCategory.UNSUPPORTED_CAPABILITY
    )


def test_direct_modal_basis_constructor_is_visible_but_not_usable_as_certified() -> None:
    basis = ModalBasis(
        operator_identity="manual-unverified-identity",
        dof_signature=((1, ("UX",)),),
        system_size=1,
        eigenvalues=np.asarray([1.0]),
        modes=np.asarray([[1.0]]),
        projected_mass=np.asarray([[1.0]]),
        projected_stiffness=np.asarray([[1.0]]),
        clusters=((0,),),
        diagnostics={"modal_residual_validation": {"status": "PASS_CERTIFIED"}},
        extraction={"modal_residual_validation": {"status": "PASS_CERTIFIED"}},
    )

    assert basis.diagnostics["modal_residual_validation"]["status"] == "INCONCLUSIVE"
    with pytest.raises(ModalResidualValidationError) as captured:
        basis.assert_compatible(None)  # type: ignore[arg-type]
    assert captured.value.validation_status == "INCONCLUSIVE"
    assert captured.value.computed_result["modes"].tolist() == [[1.0]]


@pytest.mark.parametrize("matrix_kind", ["dense", "csr"])
def test_matrix_term_budget_precedes_nonfinite_scan(matrix_kind: str, monkeypatch: pytest.MonkeyPatch) -> None:
    if matrix_kind == "dense":
        matrix = np.full((33, 33), np.nan)
    else:
        data = np.full(MAX_STORED_TERMS + 1, np.nan)
        indices = np.zeros(MAX_STORED_TERMS + 1, dtype=np.int32)
        indptr = np.zeros(34, dtype=np.int32)
        indptr[1:] = MAX_STORED_TERMS + 1
        matrix = csr_matrix((data, indices, indptr), shape=(33, 33))

    def forbidden_scan(_: object) -> np.ndarray:
        raise AssertionError("nonfinite scan ran before the matrix term budget")

    monkeypatch.setattr("solveur.core.analyses.modal_residual_validation.np.isfinite", forbidden_scan)

    with pytest.raises(_Refuse, match="stored_term_budget"):
        _matrix_entries(matrix, 33)


def test_aggregate_budget_precedes_eigenpair_finiteness_scans(monkeypatch: pytest.MonkeyPatch) -> None:
    stiffness = np.eye(23)
    mass = np.eye(23)
    values = np.ones(1)
    vectors = np.ones((23, 1))

    def forbidden_scan(_: object) -> np.ndarray:
        raise AssertionError("eigenpair scan ran before aggregate budget")

    monkeypatch.setattr("solveur.core.analyses.modal_residual_validation.np.isfinite", forbidden_scan)
    result = validate_modal_eigenpairs(stiffness, mass, values, vectors, 1.0e-7)

    assert result.status == "INCONCLUSIVE"
    assert result.reason == "aggregate_work_budget"


def test_dimension_budget_precedes_eigenpair_finiteness_scans(monkeypatch: pytest.MonkeyPatch) -> None:
    values = np.ones(1)
    vectors = np.ones((129, 1))
    stiffness = csr_matrix((129, 129))
    mass = csr_matrix((129, 129))

    def forbidden_scan(_: object) -> np.ndarray:
        raise AssertionError("eigenpair scan ran before dimension budget")

    monkeypatch.setattr("solveur.core.analyses.modal_residual_validation.np.isfinite", forbidden_scan)
    result = validate_modal_eigenpairs(stiffness, mass, values, vectors, 1.0e-7)

    assert result.status == "INCONCLUSIVE"
    assert result.reason == "dimension_budget"


def test_eigenpair_count_budget_precedes_finiteness_scans(monkeypatch: pytest.MonkeyPatch) -> None:
    stiffness = np.ones((1, 1))
    mass = np.ones((1, 1))
    values = np.ones(129)
    vectors = np.ones((1, 129))

    def forbidden_scan(_: object) -> np.ndarray:
        raise AssertionError("eigenpair scan ran before count budget")

    monkeypatch.setattr("solveur.core.analyses.modal_residual_validation.np.isfinite", forbidden_scan)
    result = validate_modal_eigenpairs(stiffness, mass, values, vectors, 1.0e-7)

    assert result.status == "INCONCLUSIVE"
    assert result.reason == "eigenpair_count_budget"


def test_modal_validation_error_keeps_full_large_result_and_serializes_hash() -> None:
    modes = np.arange(5_000, dtype=np.float64)
    candidate = {"status": "INCONCLUSIVE", "modes": modes}
    error = ModalResidualValidationError(
        "modal validation unavailable",
        validation_status="INCONCLUSIVE",
        diagnostics={"reason": "dimension_budget"},
        computed_result=candidate,
    )

    serialized = error.to_dict()

    assert error.computed_result is candidate
    assert serialized["computed_result"]["modes"]["values_omitted"].startswith("array exceeds")
    assert serialized["computed_result"]["modes"]["shape"] == [5_000]
    assert len(serialized["computed_result"]["modes"]["sha256"]) == 64


def test_large_array_serialization_does_not_call_tobytes() -> None:
    class NoBytesArray(np.ndarray):
        def tobytes(self, *args: object, **kwargs: object) -> bytes:
            raise AssertionError("serializer must hash through a view, not copy with tobytes")

    modes = np.arange(5_000, dtype=np.float64).view(NoBytesArray)
    error = ModalResidualValidationError(
        "modal validation unavailable",
        validation_status="INCONCLUSIVE",
        diagnostics={},
        computed_result={"modes": modes},
    )

    serialized = error.to_dict()

    assert len(serialized["computed_result"]["modes"]["sha256"]) == 64


def test_noncontiguous_large_array_serialization_skips_hash_without_copy() -> None:
    modes = np.arange(10_000, dtype=np.float64)[::2]
    error = ModalResidualValidationError(
        "modal validation unavailable",
        validation_status="INCONCLUSIVE",
        diagnostics={},
        computed_result={"modes": modes},
    )

    serialized = error.to_dict()

    assert serialized["computed_result"]["modes"]["sha256"] is None
    assert serialized["computed_result"]["modes"]["hash_omitted_reason"] == (
        "non-contiguous or unsupported buffer layout"
    )
