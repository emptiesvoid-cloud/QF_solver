"""Contract tests for the supported qf_solver facade."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

import qf_solver
from qf_solver import InputValidationError


ROOT = Path(__file__).resolve().parents[2]

EXPECTED_PUBLIC_SYMBOLS = (
    "__version__",
    "assess_result",
    "analyze_large_scaling",
    "analyze_petsc_tuning",
    "ExitCode",
    "InfrastructureError",
    "InputValidationError",
    "MeshValidationError",
    "NumericalConvergenceError",
    "QualificationGateError",
    "RunVerdict",
    "ConstraintTerm",
    "FiniteElementModel",
    "LinearConstraint",
    "Rbe2Definition",
    "Rbe3Definition",
    "MeshQualityThresholds",
    "MeshValidator",
    "OrthotropicLamina",
    "StructuredTet4ConvergencePlan",
    "benchmark_large_model",
    "collect_large_runtime_environment",
    "check_large_readiness",
    "check_mesh",
    "convert_model_to_large",
    "generate_large_tet4_block",
    "generate_large_tet4_cantilever",
    "inspect_model",
    "inspect_large_model",
    "import_gmsh_model",
    "import_cantilever_vnv_study",
    "import_torsion_vnv_study",
    "list_benchmarks",
    "list_demonstrations",
    "list_methods",
    "load_large_model",
    "load_distributed_large_model",
    "load_mixed_results_hdf5",
    "load_model",
    "read_inp",
    "parse_petsc_log_view",
    "postprocess_large_model",
    "qualify_large_tet4_pipeline",
    "qualification_readiness",
    "recover_harmonic_stress",
    "recover_modal_transient_stress",
    "recover_solid_stress_field",
    "recommended_large_block",
    "run_large_scale_campaign",
    "run_large_preconditioner_campaign",
    "run_qualification_campaign",
    "run_qualification_case",
    "run_release_vv",
    "run_benchmark",
    "run_demonstration",
    "run_contact_verification",
    "run_linear_solver_verification",
    "run_mitc4_validation",
    "run_torsion_stress_probe",
    "run_structured_tet4_study",
    "run_vnv_study",
    "save_audit_markdown",
    "save_evidence",
    "save_large_readiness",
    "save_large_runtime_environment",
    "save_large_verification",
    "save_mixed_results_hdf5",
    "save_model",
    "save_result",
    "save_result_csv",
    "save_result_vtu",
    "solve_large_model",
    "solve_model",
    "mixed_results_semantic_digest",
    "verify_evidence",
    "verify_large_qualification",
    "write_petsc_profile_report",
)

STABLE_SYMBOLS = {
    "__version__",
    "assess_result",
    "ExitCode",
    "InfrastructureError",
    "InputValidationError",
    "MeshValidationError",
    "NumericalConvergenceError",
    "QualificationGateError",
    "RunVerdict",
    "ConstraintTerm",
    "FiniteElementModel",
    "LinearConstraint",
    "Rbe2Definition",
    "Rbe3Definition",
    "MeshQualityThresholds",
    "MeshValidator",
    "OrthotropicLamina",
    "check_mesh",
    "import_gmsh_model",
    "inspect_model",
    "list_methods",
    "load_model",
    "save_audit_markdown",
    "save_evidence",
    "save_model",
    "save_result",
    "save_result_csv",
    "save_result_vtu",
    "solve_model",
    "verify_evidence",
}


PROVISIONAL_SYMBOLS = set(EXPECTED_PUBLIC_SYMBOLS) - STABLE_SYMBOLS


def test_public_facade_matches_documented_export_inventory() -> None:
    assert tuple(qf_solver.__all__) == EXPECTED_PUBLIC_SYMBOLS
    assert len(EXPECTED_PUBLIC_SYMBOLS) == 77
    assert all(name == "__version__" or not name.startswith("_") for name in qf_solver.__all__)
    assert all(hasattr(qf_solver, name) for name in qf_solver.__all__)


def test_documented_stability_classification_covers_every_export() -> None:
    text = (ROOT / "docs" / "reference" / "qf_solver_api.md").read_text(encoding="utf-8")
    assert len(STABLE_SYMBOLS) == 30
    assert len(PROVISIONAL_SYMBOLS) == 47
    assert STABLE_SYMBOLS | PROVISIONAL_SYMBOLS == set(EXPECTED_PUBLIC_SYMBOLS)
    for name in STABLE_SYMBOLS:
        assert f"- `{name}" in text
    for name in PROVISIONAL_SYMBOLS:
        assert f"- `{name}" in text
    assert not any(f"- `{name}" in text and f"- `{name}` — `DEPRECATED`" in text for name in EXPECTED_PUBLIC_SYMBOLS)


def test_reference_pages_match_the_0_2_12_api_candidate() -> None:
    api_contract = (ROOT / "docs" / "reference" / "qf_solver_api.md").read_text(encoding="utf-8")
    stability = (ROOT / "docs" / "reference" / "api_stability.md").read_text(encoding="utf-8")

    assert "applicable_version: 0.2.12" in api_contract
    assert "public `qf_solver` API for release 0.2.12" in api_contract
    assert "applicable_version: 0.2.12" in stability
    assert "public API surface of QF Solver 0.2.12" in stability
    assert "qf-dynamic-solid-stress/v1" in api_contract
    assert "qf-dynamic-solid-stress/v1" in stability
    # Retain route history: 0.2.11 is still named as the introduction version.
    assert "Version 0.2.11 added" in api_contract


def test_critical_workflow_signatures_are_stable() -> None:
    expected = {
        "load_model": "(path: 'str | Path') -> 'FiniteElementModel'",
        "check_mesh": "(model: 'FiniteElementModel') -> 'MeshReport'",
        "solve_model": "(model: 'FiniteElementModel', *, enforce_policy: 'bool' = True, telemetry: 'TelemetryEmitter | None' = None) -> 'object'",
        "save_result": "(result: 'object', path: 'str | Path') -> 'None'",
    }
    for name, signature in expected.items():
        assert str(inspect.signature(getattr(qf_solver, name))) == signature


def test_02x_compatibility_imports_remain_available() -> None:
    from solveur import check_mesh, load_model, save_result, solve_model
    from solveur.api import check_mesh as api_check_mesh

    assert all(callable(symbol) for symbol in (check_mesh, load_model, save_result, solve_model, api_check_mesh))


def test_minimal_documented_workflow_is_executable(tmp_path: Path) -> None:
    from qf_solver import check_mesh, load_model, save_result, solve_model

    model = load_model(ROOT / "examples" / "tet4_static.json")
    report = check_mesh(model)
    assert report.status == "PASS"
    result = solve_model(model)
    output = tmp_path / "result.json"
    save_result(result, output)
    assert output.is_file()


def test_documented_input_and_serialization_exceptions(tmp_path: Path) -> None:
    from qf_solver import save_result

    class InvalidResult:
        def to_dict(self) -> object:
            return object()

    with pytest.raises(InputValidationError):
        qf_solver.load_model(ROOT / "does-not-exist.json")
    with pytest.raises(InputValidationError):
        save_result(InvalidResult(), tmp_path / "invalid-result.json")


def test_public_recover_solid_stress_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    from solveur.post import dynamic_stress

    model = object()
    displacement = object()
    expected = {"recovered": object()}
    observed: dict[str, object] = {}

    def fake_recovery(actual_model: object, actual_displacement: object, *, stress_convention: str) -> dict[str, object]:
        observed.update(
            model=actual_model,
            displacement=actual_displacement,
            stress_convention=stress_convention,
        )
        return expected

    monkeypatch.setattr(dynamic_stress, "recover_solid_stress_field", fake_recovery)
    result = qf_solver.recover_solid_stress_field(model, displacement)

    assert observed["model"] is model
    assert observed["displacement"] is displacement
    assert observed["stress_convention"] == "GLOBAL_SMALL_STRAIN_CAUCHY_VOIGT_XX_YY_ZZ_XY_YZ_ZX"
    assert result is expected


def test_public_recover_harmonic_stress_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    from solveur.post import dynamic_stress

    model, result, prepared, basis = (object() for _ in range(4))
    selected_frequencies = [10.0, 25.0]
    convention = "TEST_HARMONIC_CONVENTION"
    expected = {"harmonic": object()}
    observed: dict[str, object] = {}

    def fake_recovery(
        actual_model: object,
        actual_result: object,
        *,
        prepared: object,
        basis: object,
        selected_frequencies_hz: list[float] | tuple[float, ...],
        stress_convention: str,
    ) -> dict[str, object]:
        observed.update(
            model=actual_model,
            result=actual_result,
            prepared=prepared,
            basis=basis,
            selected_frequencies_hz=selected_frequencies_hz,
            stress_convention=stress_convention,
        )
        return expected

    monkeypatch.setattr(dynamic_stress, "recover_harmonic_stress", fake_recovery)
    recovered = qf_solver.recover_harmonic_stress(
        model,
        result,
        prepared=prepared,
        basis=basis,
        selected_frequencies_hz=selected_frequencies,
        stress_convention=convention,
    )

    assert observed["model"] is model
    assert observed["result"] is result
    assert observed["prepared"] is prepared
    assert observed["basis"] is basis
    assert observed["selected_frequencies_hz"] is selected_frequencies
    assert observed["stress_convention"] == convention
    assert recovered is expected


def test_public_recover_modal_transient_stress_forwards_arguments(monkeypatch: pytest.MonkeyPatch) -> None:
    from solveur.post import dynamic_stress

    model, result, prepared, basis = (object() for _ in range(4))
    selected_times = (0.0, 0.125, 0.25)
    convention = "TEST_TRANSIENT_CONVENTION"
    expected = {"transient": object()}
    observed: dict[str, object] = {}

    def fake_recovery(
        actual_model: object,
        actual_result: object,
        *,
        prepared: object,
        basis: object,
        selected_times_s: list[float] | tuple[float, ...],
        stress_convention: str,
    ) -> dict[str, object]:
        observed.update(
            model=actual_model,
            result=actual_result,
            prepared=prepared,
            basis=basis,
            selected_times_s=selected_times_s,
            stress_convention=stress_convention,
        )
        return expected

    monkeypatch.setattr(dynamic_stress, "recover_modal_transient_stress", fake_recovery)
    recovered = qf_solver.recover_modal_transient_stress(
        model,
        result,
        prepared=prepared,
        basis=basis,
        selected_times_s=selected_times,
        stress_convention=convention,
    )

    assert observed["model"] is model
    assert observed["result"] is result
    assert observed["prepared"] is prepared
    assert observed["basis"] is basis
    assert observed["selected_times_s"] is selected_times
    assert observed["stress_convention"] == convention
    assert recovered is expected
