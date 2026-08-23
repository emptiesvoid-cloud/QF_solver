from __future__ import annotations

import numpy as np
from types import SimpleNamespace

from scipy.sparse import csr_matrix, diags, eye

from solveur.core.modal import (
    ModalAnalysisSolver,
    _dense_generalized_eigh,
    _gmres_preconditioner,
    _lobpcg_preconditioner,
    _modal_diagnostics,
    _preconditioner_diagonal,
    _refine_eigenpairs,
    _shifted_preconditioner_matrix,
)


def test_spilu_preconditioner_supports_vector_blocks() -> None:
    matrix = diags([1.0, 2.0, 3.0, 4.0], format="csr")
    wrapped = SimpleNamespace(physical_stiffness=matrix, shape=matrix.shape)
    preconditioner = _lobpcg_preconditioner(wrapped, "spilu")
    block = np.arange(8.0).reshape(4, 2)

    result = preconditioner @ block

    assert result.shape == block.shape
    assert np.all(np.isfinite(result))
    assert np.all(np.sum(block * result, axis=0) > 0.0)


def test_shift_invert_modal_operator_can_use_external_inverse() -> None:
    stiffness = diags([1.0, 2.0, 3.0, 4.0, 5.0, 6.0], format="csr")
    mass = eye(6, format="csr")

    values, _, method = ModalAnalysisSolver._solve_eigenproblem(
        stiffness,
        mass,
        2,
        "eigsh",
        dense_limit=2,
        shift=0.5,
        which="LM",
        tolerance=1.0e-10,
        maxiter=100,
        ncv=4,
    )

    assert method == "eigsh"
    assert np.allclose(values, [1.0, 2.0])


def test_shifted_preconditioner_captures_lazy_drilling_coupling() -> None:
    physical = diags([4.0, 5.0], format="csr")
    coupling_pd = np.asarray([[1.0], [2.0]])
    coupling_dp = coupling_pd.T
    wrapped = SimpleNamespace(
        physical_stiffness=physical,
        stiffness_pd=csr_matrix(coupling_pd),
        stiffness_dp=csr_matrix(coupling_dp),
        drilling_diagonal=np.array([2.0]),
    )

    result = _shifted_preconditioner_matrix(wrapped, physical)

    assert np.allclose(result.toarray(), [[3.5, -1.0], [-1.0, 3.0]])


def test_modal_preconditioners_cover_diagonal_and_ssor_vector_and_block_paths() -> None:
    matrix = diags([2.0, 3.0, 4.0], format="csr")
    wrapped = SimpleNamespace(physical_stiffness=matrix, shape=matrix.shape)
    vector = np.array([2.0, 3.0, 4.0])
    block = np.column_stack((vector, 2.0 * vector))

    diagonal = _lobpcg_preconditioner(wrapped, "diagonal")
    assert np.allclose(diagonal @ vector, [1.0, 1.0, 1.0])
    assert np.allclose(diagonal @ block, block / np.array([2.0, 3.0, 4.0])[:, None])

    ssor = _lobpcg_preconditioner(wrapped, "ssor")
    assert np.all(np.isfinite(ssor @ vector))
    assert np.all(np.isfinite(ssor @ block))

    assert np.allclose(_preconditioner_diagonal(wrapped), [2.0, 3.0, 4.0])
    with np.testing.assert_raises(ValueError):
        _lobpcg_preconditioner(wrapped, "unknown")


def test_gmres_preconditioners_cover_all_supported_modes() -> None:
    matrix = diags([2.0, 3.0, 4.0], format="csr")
    vector = np.array([2.0, 3.0, 4.0])
    block = np.column_stack((vector, 2.0 * vector))

    for name in ("diagonal", "ssor", "spilu"):
        preconditioner = _gmres_preconditioner(matrix, name, drop_tol=1.0e-6, fill_factor=5.0)
        assert np.all(np.isfinite(preconditioner @ vector))
        assert np.all(np.isfinite(preconditioner @ block))

    with np.testing.assert_raises(ValueError):
        _gmres_preconditioner(matrix, "unknown", drop_tol=1.0e-6, fill_factor=5.0)


def test_modal_quality_helpers_report_invariants_and_refinement() -> None:
    stiffness = diags([1.0, 2.0, 3.0], format="csr")
    mass = eye(3, format="csr")
    values = np.array([1.0, 2.0])
    vectors = np.eye(3, 2)
    influences = {direction: np.ones(3) for direction in ("UX", "UY", "UZ")}

    diagnostics = _modal_diagnostics(stiffness, mass, values, vectors, influences)
    assert diagnostics["mode_count"] == 2
    assert diagnostics["max_relative_residual"] == 0.0
    assert diagnostics["effective_modal_mass"]["total_direction_mass"]["UX"] == 3.0

    empty = _modal_diagnostics(stiffness, mass, np.zeros(0), np.zeros((3, 0)), influences)
    assert empty == {"mode_count": 0, "max_relative_residual": 0.0}

    unchanged = _refine_eigenpairs(stiffness, mass, values, vectors, iterations=0)
    assert unchanged["iterations_performed"] == 0
    assert unchanged["maximum_residual_after"] == unchanged["maximum_residual_before"]

    refined = _refine_eigenpairs(stiffness, mass, values, vectors, iterations=1)
    assert refined["iterations_performed"] == 1
    assert np.all(np.isfinite(refined["vectors"]))


def test_dense_modal_scaling_returns_requested_generalized_modes() -> None:
    stiffness = diags([4.0, 9.0, 16.0], format="csr")
    mass = diags([2.0, 3.0, 4.0], format="csr")

    values, vectors = _dense_generalized_eigh(stiffness, mass, 2)

    assert np.allclose(values, [2.0, 3.0])
    assert vectors.shape == (3, 2)
