import numpy as np
import pytest
from scipy.sparse import csr_matrix

from solveur.core.analysis import AnalysisSettings
from solveur.core.errors import InputValidationError
from solveur.core.linear_policy import LinearSolverPolicy
from solveur.core.solver import LinearStaticSolver
from tests.unit.test_mesh_validation import valid_tet4_model


def test_policy_recommends_cg_for_symmetric_positive_diagonal_matrix():
    selection = LinearSolverPolicy.assess(
        csr_matrix(np.array([[4.0, 1.0], [1.0, 3.0]])), "direct", {}
    )

    assert selection.recommended_method == "cg"
    assert selection.matrix_symmetric is True
    assert selection.positive_diagonal is True
    assert selection.positive_definite_evidence == "dense_cholesky"
    assert selection.direct_budget_exceeded is False


def test_policy_recommends_gmres_for_nonsymmetric_matrix():
    selection = LinearSolverPolicy.assess(
        csr_matrix(np.array([[2.0, 1.0], [0.0, 3.0]])), "direct", {}
    )

    assert selection.recommended_method == "gmres"
    assert selection.matrix_symmetric is False


def test_policy_rejects_direct_solve_when_configured_budget_is_exceeded():
    with pytest.raises(InputValidationError, match="Direct solver refused"):
        LinearSolverPolicy.assess(
            csr_matrix(np.array([[4.0, 1.0], [1.0, 3.0]])),
            "direct",
            {"direct_memory_budget_mb": 1.0e-9, "enforce_direct_memory_budget": True},
        )


def test_policy_auto_avoids_direct_when_memory_budget_is_exceeded():
    matrix = csr_matrix(np.diag(np.full(257, 2.0)))
    selection = LinearSolverPolicy.assess(
        matrix,
        "auto",
        {"assume_spd": True, "direct_memory_budget_mb": 1.0e-9},
    )

    assert selection.recommended_method == "cg"
    assert selection.direct_budget_exceeded is True
    assert any("avoided direct" in warning for warning in selection.warnings)


def test_policy_rejects_cg_outside_real_symmetric_contract():
    selection = LinearSolverPolicy.assess(
        csr_matrix(np.array([[2.0, 1.0], [0.0, 3.0]])), "cg", {}
    )
    with pytest.raises(InputValidationError, match="CG requires"):
        LinearSolverPolicy.enforce_method_contract(selection, {})


def test_policy_requires_explicit_spd_evidence_for_large_cg_systems():
    matrix = csr_matrix(np.diag(np.full(257, 2.0)))
    selection = LinearSolverPolicy.assess(matrix, "cg", {})

    assert selection.recommended_method == "minres"
    assert selection.positive_definite_evidence == "not_proven"
    with pytest.raises(InputValidationError, match="CG requires"):
        LinearSolverPolicy.enforce_method_contract(selection, {})

    declared = LinearSolverPolicy.assess(matrix, "cg", {"assume_spd": True})
    assert declared.recommended_method == "cg"
    assert declared.positive_definite_evidence == "user_declared"
    LinearSolverPolicy.enforce_method_contract(declared, {"assume_spd": True})


def test_policy_rejects_incompatible_krylov_preconditioner():
    selection = LinearSolverPolicy.assess(
        csr_matrix(np.array([[4.0, 1.0], [1.0, 3.0]])), "minres", {"preconditioner": "ilu"}
    )
    with pytest.raises(InputValidationError, match="only 'none' or 'jacobi'"):
        LinearSolverPolicy.enforce_method_contract(selection, {"preconditioner": "ilu"})


def test_policy_allows_petsc_amg_preconditioner_only_on_petsc_backend() -> None:
    matrix = csr_matrix(np.array([[4.0, 1.0], [1.0, 3.0]]))
    parameters = {"assume_spd": True, "backend": "petsc", "preconditioner": "gamg"}
    selection = LinearSolverPolicy.assess(matrix, "cg", parameters)

    LinearSolverPolicy.enforce_method_contract(selection, parameters)

    with pytest.raises(InputValidationError, match="requires backend='petsc'"):
        LinearSolverPolicy.enforce_method_contract(selection, {"preconditioner": "gamg"})


def test_static_solver_applies_krylov_preconditioner_contract():
    model = valid_tet4_model()
    model.analysis = AnalysisSettings.from_raw(
        {"type": "linear_static", "method": "cg", "preconditioner": "ilu"}
    )
    with pytest.raises(InputValidationError, match="only 'none' or 'jacobi'"):
        LinearStaticSolver().solve(model)


def test_static_result_records_solver_selection():
    result = LinearStaticSolver().solve(valid_tet4_model()).to_dict()

    selection = result["solver"]["selection"]
    assert selection["requested_method"] == "direct"
    assert selection["used_method"] == "direct"
    assert selection["recommended_method"] == "cg"
    assert result["audit"]["solver_selection"] == selection


def test_static_auto_method_records_recommendation_and_effective_method():
    model = valid_tet4_model()
    model.analysis = AnalysisSettings.from_raw({"type": "linear_static", "method": "auto"})

    data = LinearStaticSolver().solve(model).to_dict()

    assert data["solver"]["selection"]["requested_method"] == "auto"
    assert data["solver"]["selection"]["used_method"] == "direct"
    assert data["solver"]["execution"]["requested_method"] == "auto"
    assert data["solver"]["execution"]["used_method"] == "direct"
    assert data["solver"]["execution"]["backend_used"] == "scipy"
    assert data["solver"]["backend"]["selected"] == "scipy"
    assert data["solver"]["relative_residual_norm"] < 1.0e-10


def test_static_result_records_effective_solver_settings_and_resource_estimate():
    model = valid_tet4_model()
    model.analysis = AnalysisSettings.from_raw(
        {
            "type": "linear_static",
            "method": "cg",
            "rtol": 1.0e-9,
            "atol": 1.0e-12,
            "maxiter": 50,
            "preconditioner": "jacobi",
        }
    )

    execution = LinearStaticSolver().solve(model).to_dict()["solver"]["execution"]

    assert execution["requested_method"] == "cg"
    assert execution["used_method"] == "cg"
    assert execution["preconditioner"] == "jacobi"
    assert execution["rtol"] == pytest.approx(1.0e-9)
    assert execution["atol"] == pytest.approx(1.0e-12)
    assert execution["maxiter"] == 50
    assert execution["fallback_used"] is False
    assert execution["assembly_seconds"] >= 0.0
    assert execution["linear_solve_seconds"] >= 0.0
    assert execution["total_seconds"] >= execution["linear_solve_seconds"]
    assert execution["resource_estimate"]["nnz"] > 0
