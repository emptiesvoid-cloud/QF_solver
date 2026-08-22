from __future__ import annotations

import numpy as np
from types import SimpleNamespace

from scipy.sparse import csr_matrix, diags, eye

from solveur.core.modal import ModalAnalysisSolver, _lobpcg_preconditioner, _shifted_preconditioner_matrix


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
