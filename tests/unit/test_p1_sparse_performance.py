import numpy as np
import pytest
from scipy.sparse import csr_matrix, eye

from solveur.core.analysis import AnalysisSettings
from solveur.core.dynamic import NewmarkDynamicSolver
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.linear_methods import LinearSystemSolver
from solveur.core.modal import ModalAnalysisSolver, ModalSolverOptions
from solveur.io.json_reader import JsonModelReader


def test_reusable_sparse_factorization_solves_multiple_right_hand_sides():
    matrix = csr_matrix(np.array([[4.0, 1.0], [1.0, 3.0]]))
    factorization = LinearSystemSolver.factorize(matrix)
    first, first_info = factorization.solve(np.array([1.0, 2.0]))
    second, second_info = factorization.solve(np.array([3.0, -1.0]))
    assert np.allclose(matrix @ first, [1.0, 2.0])
    assert np.allclose(matrix @ second, [3.0, -1.0])
    assert first_info.converged and second_info.converged
    assert factorization.factorization_count == 1
    assert factorization.solve_count == 2


def test_reusable_sparse_factorization_rejects_singular_matrix():
    with pytest.raises(NumericalConvergenceError, match="factorization failed"):
        LinearSystemSolver.factorize(csr_matrix((2, 2)))


def test_newmark_initial_acceleration_stays_sparse(monkeypatch: pytest.MonkeyPatch):
    def fail_toarray(_: object) -> np.ndarray:
        raise AssertionError("initial acceleration must not convert the mass matrix to dense")

    monkeypatch.setattr(csr_matrix, "toarray", fail_toarray)
    mass = eye(2, format="csr")
    zero = csr_matrix((2, 2))
    acceleration = NewmarkDynamicSolver()._initial_acceleration(
        mass,
        zero,
        zero,
        np.array([0, 1]),
        np.zeros(2),
        np.zeros(2),
        np.array([2.0, -3.0]),
    )
    assert np.allclose(acceleration, [2.0, -3.0])


def test_modal_defaults_to_sparse_and_refuses_oversized_dense_conversion():
    assert AnalysisSettings.from_raw("modal").method == "eigsh"
    stiffness = csr_matrix(np.diag([1.0, 2.0, 3.0, 4.0, 5.0]))
    mass = eye(5, format="csr")
    with pytest.raises(InputValidationError, match="Dense modal solve refused"):
        ModalAnalysisSolver._solve_eigenproblem(stiffness, mass, 2, "eigh", dense_limit=4)
    values, vectors, method = ModalAnalysisSolver._solve_eigenproblem(
        stiffness,
        mass,
        2,
        "eigsh",
        dense_limit=4,
    )
    assert method == "eigsh"
    assert values.shape == (2,)
    assert vectors.shape == (5, 2)


def test_modal_shift_targets_nearest_eigenvalues_and_reports_hz_conversion():
    stiffness = csr_matrix(np.diag([1.0, 2.0, 3.0, 4.0, 5.0]))
    mass = eye(5, format="csr")
    values, _, method = ModalAnalysisSolver._solve_eigenproblem(
        stiffness,
        mass,
        2,
        "eigsh",
        dense_limit=4,
        shift=3.7,
    )
    options = ModalSolverOptions.from_parameters(
        {"modal_shift_hz": 2.0, "arpack_tolerance": 1.0e-9, "arpack_ncv": 4},
        method="eigsh",
        mode_count=2,
        system_size=5,
    )
    assert method == "eigsh"
    assert np.allclose(np.sort(values), [3.0, 4.0])
    assert options.shift_eigenvalue == pytest.approx((4.0 * np.pi) ** 2)
    assert options.to_dict()["tolerance"] == 1.0e-9


def test_modal_smallest_mode_path_avoids_zero_shift_invert():
    stiffness = csr_matrix(np.diag([1.0, 2.0, 3.0, 4.0, 5.0]))
    mass = eye(5, format="csr")
    values, _, method = ModalAnalysisSolver._solve_eigenproblem(
        stiffness,
        mass,
        2,
        "eigsh",
        dense_limit=4,
        which="SM",
    )
    assert method == "eigsh"
    assert np.allclose(np.sort(values), [1.0, 2.0])


def test_modal_lobpcg_returns_smallest_modes():
    stiffness = csr_matrix(np.diag(np.arange(1.0, 21.0)))
    mass = eye(20, format="csr")
    values, _, method = ModalAnalysisSolver._solve_eigenproblem(
        stiffness,
        mass,
        2,
        "lobpcg",
        dense_limit=4,
        tolerance=1.0e-8,
        maxiter=200,
    )
    assert method == "lobpcg"
    assert np.allclose(np.sort(values), [1.0, 2.0], rtol=1.0e-6)


def test_modal_lobpcg_rejects_spilu_without_physical_block():
    stiffness = csr_matrix(np.diag(np.arange(1.0, 21.0)))
    mass = eye(20, format="csr")
    with pytest.raises(InputValidationError, match="physical stiffness block"):
        ModalAnalysisSolver._solve_eigenproblem(
            stiffness,
            mass,
            2,
            "lobpcg",
            dense_limit=4,
            lobpcg_preconditioner="spilu",
        )


def test_modal_lobpcg_accepts_ssor_on_physical_block():
    stiffness = csr_matrix(np.diag(np.arange(1.0, 21.0)))
    mass = eye(20, format="csr")
    with pytest.raises(InputValidationError, match="physical stiffness block"):
        ModalAnalysisSolver._solve_eigenproblem(
            stiffness,
            mass,
            2,
            "lobpcg",
            dense_limit=4,
            lobpcg_preconditioner="ssor",
        )


@pytest.mark.parametrize(
    "parameters",
    [
        {"modal_shift_hz": 1.0, "modal_shift_eigenvalue": 2.0},
        {"modal_shift_eigenvalue": -1.0},
        {"arpack_which": "INVALID"},
        {"arpack_ncv": 2},
    ],
)
def test_modal_sparse_options_reject_incoherent_parameters(parameters: dict[str, object]):
    with pytest.raises(InputValidationError):
        ModalSolverOptions.from_parameters(parameters, method="eigsh", mode_count=2, system_size=5)


@pytest.mark.parametrize(("field", "value"), [("modes", 0), ("dense_modal_max_dofs", 0)])
def test_json_rejects_invalid_modal_sizing(field: str, value: int):
    analysis = {"type": "modal", "method": "eigsh", field: value}
    with pytest.raises(InputValidationError):
        JsonModelReader().from_dict(
            {
                "analysis": analysis,
                "nodes": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
                "elements": [{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "steel"}],
                "materials": {
                    "steel": {"type": "isotropic_3d", "E": 1000.0, "nu": 0.25, "density": 1.0}
                },
            }
        )


@pytest.mark.parametrize("analysis_type", ["modal", "transient_dynamic", "harmonic_response"])
def test_dynamic_analyses_reject_lumped_mass_formulation(analysis_type: str):
    with pytest.raises(ValueError, match="outside the qualified scope"):
        AnalysisSettings.from_raw(
            {"type": analysis_type, "mass_formulation": "lumped"}
        )


def test_dynamic_analyses_accept_explicit_consistent_mass_formulation():
    settings = AnalysisSettings.from_raw(
        {"type": "modal", "mass_formulation": "consistent"}
    )
    assert settings.parameters["mass_formulation"] == "consistent"
