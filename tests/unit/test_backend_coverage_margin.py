from __future__ import annotations

import numpy as np
import pytest
from scipy.sparse import csr_matrix, diags

from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.linear_methods import LinearSolveInfo, LinearSystemSolver
from solveur.core.modal_options import ModalSolverOptions
from solveur.io.laminate_schema import validate_laminate_plies
from solveur.large.readiness import (
    _multi_million_gate_check,
    check_large_readiness,
    estimate_structured_tet4_size,
)
from solveur.materials.beam import BeamSectionMaterial


def _ply(**updates: object) -> dict[str, object]:
    value: dict[str, object] = {
        "E1": 10.0,
        "E2": 8.0,
        "nu12": 0.2,
        "G12": 3.0,
        "G13": 3.0,
        "G23": 3.0,
        "density": 1.0,
        "thickness": 0.01,
    }
    value.update(updates)
    return value


def _beam(**updates: object) -> BeamSectionMaterial:
    values: dict[str, object] = {
        "E": 70.0e9,
        "G": 27.0e9,
        "A": 1.0e-4,
        "Iy": 1.0e-8,
        "Iz": 2.0e-8,
        "J": 3.0e-8,
        "density": 2700.0,
    }
    values.update(updates)
    return BeamSectionMaterial(**values)


def test_modal_options_defaults_are_sparse_safe() -> None:
    options = ModalSolverOptions.from_parameters({}, method="eigsh", mode_count=2, system_size=8)
    assert options.which == "SM"
    assert options.shift_eigenvalue == 0.0
    assert options.to_dict()["maxiter"] is None


def test_modal_options_convert_frequency_shift() -> None:
    options = ModalSolverOptions.from_parameters(
        {"modal_shift_hz": 2.0}, method="eigsh", mode_count=2, system_size=8
    )
    assert options.shift_hz == pytest.approx(2.0)
    assert options.shift_eigenvalue == pytest.approx((4.0 * np.pi) ** 2)


def test_modal_options_accept_eigenvalue_shift() -> None:
    options = ModalSolverOptions.from_parameters(
        {"modal_shift_eigenvalue": 4.5, "arpack_which": "la"},
        method="lanczos",
        mode_count=2,
        system_size=8,
    )
    assert options.shift_eigenvalue == pytest.approx(4.5)
    assert options.which == "LA"


def test_modal_options_reject_two_shift_conventions() -> None:
    with pytest.raises(InputValidationError, match="only one"):
        ModalSolverOptions.from_parameters(
            {"modal_shift_hz": 1.0, "modal_shift_eigenvalue": 1.0},
            method="eigsh",
            mode_count=1,
            system_size=4,
        )


def test_modal_options_reject_unknown_arpack_selection() -> None:
    with pytest.raises(InputValidationError, match="arpack_which"):
        ModalSolverOptions.from_parameters(
            {"arpack_which": "invalid"}, method="eigsh", mode_count=1, system_size=4
        )


def test_modal_options_reject_non_numeric_tolerance() -> None:
    with pytest.raises(InputValidationError, match="arpack_tolerance"):
        ModalSolverOptions.from_parameters(
            {"arpack_tolerance": "bad"}, method="eigsh", mode_count=1, system_size=4
        )


def test_modal_options_reject_boolean_iteration_limit() -> None:
    with pytest.raises(InputValidationError, match="arpack_maxiter"):
        ModalSolverOptions.from_parameters(
            {"arpack_maxiter": True}, method="eigsh", mode_count=1, system_size=4
        )


def test_modal_options_reject_bad_ncv_and_incompatible_shift() -> None:
    with pytest.raises(InputValidationError, match="arpack_ncv"):
        ModalSolverOptions.from_parameters(
            {"arpack_ncv": 1}, method="eigsh", mode_count=1, system_size=4
        )
    with pytest.raises(InputValidationError, match="modal shift"):
        ModalSolverOptions.from_parameters(
            {"modal_shift_eigenvalue": 1.0}, method="lobpcg", mode_count=1, system_size=4
        )


def test_beam_section_reports_mass_per_length() -> None:
    assert _beam().mass_per_length == pytest.approx(0.27)


def test_beam_section_accepts_a_finite_reference_vector() -> None:
    assert _beam(reference_vector=(0.0, 1.0, 0.0)).reference_vector == (0.0, 1.0, 0.0)


def test_beam_section_rejects_non_positive_stiffness() -> None:
    with pytest.raises(ValueError, match="section E"):
        _beam(E=0.0)


def test_beam_section_rejects_negative_density() -> None:
    with pytest.raises(ValueError, match="density"):
        _beam(density=-1.0)


def test_beam_section_rejects_zero_reference_vector() -> None:
    with pytest.raises(ValueError, match="reference_vector"):
        _beam(reference_vector=(0.0, 0.0, 0.0))


def test_readiness_size_estimate_preserves_structured_counts() -> None:
    size = estimate_structured_tet4_size(2, 3, 4)
    assert size["node_count"] == 60
    assert size["element_count"] == 144
    assert size["ndof"] == 180
    assert size["recommended_free_disk_bytes"] > size["model_arrays_bytes"]


def test_readiness_rejects_non_positive_block_dimension() -> None:
    with pytest.raises(ValueError, match="dimensions"):
        estimate_structured_tet4_size(0, 2, 2)


def test_readiness_rejects_partial_explicit_dimensions(tmp_path) -> None:
    with pytest.raises(ValueError, match="all of nx"):
        check_large_readiness(tmp_path, target_dofs=24, nx=2, solver_backend="matrix_free")


def test_readiness_accepts_small_scipy_run(tmp_path) -> None:
    report = check_large_readiness(tmp_path, target_dofs=24, solver_backend="scipy")
    assert report["status"] == "PASS"
    assert report["checks"][3]["id"] == "BACKEND-SCALE"


def test_readiness_rejects_oversized_scipy_run(tmp_path) -> None:
    report = check_large_readiness(
        tmp_path, target_dofs=1000, solver_backend="scipy", scipy_max_dofs=10
    )
    assert report["status"] == "FAIL"
    assert any(item["id"] == "BACKEND-SCALE" and item["status"] == "FAIL" for item in report["checks"])


def test_readiness_rejects_unknown_backend(tmp_path) -> None:
    report = check_large_readiness(tmp_path, target_dofs=24, solver_backend="unknown")
    assert report["status"] == "FAIL"
    assert any("unsupported backend" in item["detail"] for item in report["checks"])


def test_readiness_rejects_non_positive_chunk_size(tmp_path) -> None:
    report = check_large_readiness(
        tmp_path, target_dofs=24, solver_backend="matrix_free", chunk_size=0
    )
    assert report["status"] == "FAIL"
    assert any(item["id"] == "CHUNK-SIZE" and item["status"] == "FAIL" for item in report["checks"])


def test_readiness_warns_for_excessive_chunk_size(tmp_path) -> None:
    report = check_large_readiness(
        tmp_path, target_dofs=24, solver_backend="matrix_free", chunk_size=100001
    )
    assert report["status"] == "WARNING"
    assert any(item["id"] == "CHUNK-SIZE" and item["status"] == "WARNING" for item in report["checks"])


def test_multi_million_gate_warns_without_explicit_budget() -> None:
    sizing = estimate_structured_tet4_size(64, 64, 64)
    gate = _multi_million_gate_check(2_000_000, "petsc", sizing, None)
    assert gate["status"] == "WARNING"
    assert "memory budget" in gate["detail"]


def test_multi_million_gate_passes_matrix_free_with_budget() -> None:
    sizing = estimate_structured_tet4_size(64, 64, 64)
    gate = _multi_million_gate_check(
        2_000_000, "matrix_free", sizing, sizing["petsc_rule_of_thumb_bytes"]
    )
    assert gate["status"] == "PASS"


def test_laminate_schema_rejects_non_list() -> None:
    errors: list[str] = []
    validate_laminate_plies("material", {}, errors)
    assert errors == ["material.plies must be a non-empty list."]


def test_laminate_schema_rejects_empty_list() -> None:
    errors: list[str] = []
    validate_laminate_plies("material", [], errors)
    assert "non-empty list" in errors[0]


def test_laminate_schema_rejects_non_mapping_ply() -> None:
    errors: list[str] = []
    validate_laminate_plies("material", ["ply"], errors)
    assert "must be an object" in errors[0]


def test_laminate_schema_reports_unknown_and_missing_fields() -> None:
    errors: list[str] = []
    validate_laminate_plies("material", [{"unexpected": 1}], errors)
    assert any("unexpected" in error for error in errors)
    assert any("is required" in error for error in errors)


def test_laminate_schema_rejects_non_positive_mechanical_properties() -> None:
    errors: list[str] = []
    validate_laminate_plies("material", [_ply(E1=0.0, thickness=-1.0)], errors)
    assert any("E1" in error and "positive" in error for error in errors)
    assert any("thickness" in error and "positive" in error for error in errors)


def test_laminate_schema_rejects_malformed_strengths() -> None:
    errors: list[str] = []
    validate_laminate_plies("material", [_ply(strengths={"Xt": -1.0})], errors)
    assert any("strengths" in error and "required" in error for error in errors)
    assert any("Xt" in error and "positive" in error for error in errors)


def test_laminate_schema_rejects_malformed_strain_allowables() -> None:
    errors: list[str] = []
    validate_laminate_plies("material", [_ply(strain_allowables={"e1t": 0.0})], errors)
    assert any("strain_allowables" in error and "required" in error for error in errors)
    assert any("e1t" in error and "positive" in error for error in errors)


def test_laminate_schema_rejects_non_stable_poisson_pair() -> None:
    errors: list[str] = []
    validate_laminate_plies("material", [_ply(nu12=2.0)], errors)
    assert any("nu12" in error and "nu21" in error for error in errors)


def test_linear_solve_info_serializes_diagnostics() -> None:
    info = LinearSolveInfo("cg", 3, 1.0e-12, True, residual_history=[1.0, 1.0e-12])
    data = info.to_dict()
    assert data["method"] == "cg"
    assert data["iterations"] == 3
    assert data["residual_history"] == [1.0, 1.0e-12]


def test_linear_solver_supports_spsolve_alias() -> None:
    matrix = csr_matrix([[4.0, 1.0], [1.0, 3.0]])
    solution, info = LinearSystemSolver().solve(matrix, np.array([1.0, 2.0]), method="spsolve")
    assert np.allclose(matrix @ solution, [1.0, 2.0])
    assert info.method == "spsolve"


def test_linear_solver_supports_cg_with_jacobi() -> None:
    matrix = diags([2.0, 3.0, 4.0], format="csr")
    solution, info = LinearSystemSolver().solve(
        matrix, np.ones(3), method="cg", parameters={"preconditioner": "jacobi"}
    )
    assert np.allclose(matrix @ solution, np.ones(3))
    assert info.preconditioner == "jacobi"


def test_linear_solver_supports_gmres() -> None:
    matrix = csr_matrix([[3.0, 1.0], [0.0, 2.0]])
    solution, info = LinearSystemSolver().solve(matrix, np.array([4.0, 2.0]), method="gmres")
    assert np.allclose(matrix @ solution, [4.0, 2.0])
    assert info.method == "gmres"


def test_linear_solver_supports_bicgstab() -> None:
    matrix = csr_matrix([[3.0, 1.0], [0.0, 2.0]])
    solution, info = LinearSystemSolver().solve(matrix, np.array([4.0, 2.0]), method="bicgstab")
    assert np.allclose(matrix @ solution, [4.0, 2.0])
    assert info.method == "bicgstab"


def test_linear_solver_supports_minres() -> None:
    matrix = csr_matrix([[4.0, 1.0], [1.0, 3.0]])
    solution, info = LinearSystemSolver().solve(matrix, np.array([1.0, 2.0]), method="minres")
    assert np.allclose(matrix @ solution, [1.0, 2.0])
    assert info.method == "minres"


def test_linear_solver_supports_complex_frequency_systems() -> None:
    matrix = csr_matrix(np.array([[2.0 + 0.1j, 0.0], [0.0, 3.0 + 0.2j]]))
    rhs = np.array([2.0 + 0.1j, 3.0 + 0.2j])
    solution, info = LinearSystemSolver().solve_complex(matrix, rhs)
    assert np.allclose(matrix @ solution, rhs)
    assert info.method == "direct_frequency"


def test_linear_solver_rejects_unresolved_auto_method() -> None:
    with pytest.raises(ValueError, match="effective method"):
        LinearSystemSolver().solve(csr_matrix(np.eye(2)), np.ones(2), method="auto")


def test_linear_solver_reports_bad_residual_and_nonfinite_solution() -> None:
    matrix = csr_matrix(np.eye(2))
    with pytest.raises(NumericalConvergenceError, match="abnormal"):
        LinearSystemSolver._validated_residual_metrics(
            matrix, np.ones(2), np.zeros(2), "test", {"residual_failure_tolerance": 1.0e-12}
        )
    with pytest.raises(NumericalConvergenceError, match="non-finite"):
        LinearSystemSolver._validated_residual(matrix, np.ones(2), np.array([np.nan, 0.0]), "test", {})
