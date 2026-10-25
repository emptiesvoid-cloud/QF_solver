from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix

import solveur.core.analyses.modal_basis as modal_basis_module
from solveur.core.analyses.modal_basis import ModalBasis
from solveur.core.analyses.modal_basis_numerics import (
    SYMMETRY_TOL,
    is_exactly_sparse_symmetric,
    project_exact_symmetric_bilinear,
    relative_sparse_symmetry_error,
    sparse_symmetry_metrics,
)
from solveur.core.analyses.prepared_dynamic_system import PreparedDynamicSystem
from solveur.core.errors import InputValidationError


def test_structured_symmetric_projection_matches_dense_bilinear_form() -> None:
    stiffness = csr_matrix(
        np.asarray(
            [
                [8.0, -1.0, 0.0, 0.5],
                [-1.0, 6.0, 2.0, 0.0],
                [0.0, 2.0, 5.0, -0.25],
                [0.5, 0.0, -0.25, 4.0],
            ]
        )
    )
    modes = np.asarray(
        [[0.5, 0.25], [-0.25, 0.5], [0.75, -0.5], [0.125, 0.375]],
        dtype=np.float64,
    )

    assert is_exactly_sparse_symmetric(stiffness)
    assert sparse_symmetry_metrics(stiffness) == (0.0, True)
    projected = project_exact_symmetric_bilinear(stiffness, modes)
    direct = modes.T @ (stiffness @ modes)

    np.testing.assert_array_equal(projected, projected.T)
    np.testing.assert_allclose(projected, direct, rtol=2e-16, atol=2e-16)
    np.testing.assert_array_equal(stiffness.toarray(), stiffness.toarray().T)


def test_modal_basis_uses_structured_projection_for_exact_symmetric_k(monkeypatch: pytest.MonkeyPatch) -> None:
    stiffness = np.diag([1.0, 2.0, 4.0, 8.0])
    mass = np.eye(4)
    original = modal_basis_module._project_exact_symmetric_bilinear
    calls: list[int] = []

    def observed(k_matrix: csr_matrix, modes: np.ndarray, **kwargs: object) -> np.ndarray:
        calls.append(modes.shape[1])
        return original(k_matrix, modes, **kwargs)

    monkeypatch.setattr(modal_basis_module, "_project_exact_symmetric_bilinear", observed)
    basis = ModalBasis._from_operators(
        csr_matrix(stiffness),
        csr_matrix(mass),
        operator_identity="synthetic-structured-projection",
        dof_signature=(),
        requested_modes=2,
        method="dense",
        dense_limit=8,
    )

    assert calls == [2]
    np.testing.assert_array_equal(basis.projected_stiffness, basis.projected_stiffness.T)
    np.testing.assert_allclose(basis.projected_mass, basis.modes.T @ (mass @ basis.modes), rtol=0.0, atol=0.0)
    np.testing.assert_allclose(basis.eigenvalues, [1.0, 2.0], rtol=0.0, atol=0.0)
    assert basis.diagnostics["projected_stiffness_relative_eigenpair_error"] <= 1e-8


def test_from_prepared_reuses_one_sparse_symmetry_difference(monkeypatch: pytest.MonkeyPatch) -> None:
    prepared = object.__new__(PreparedDynamicSystem)
    prepared._stiffness_reduced = csr_matrix(np.diag([1.0, 2.0, 4.0, 8.0]))
    prepared._mass_reduced = csr_matrix(np.eye(4))
    prepared._reducer = SimpleNamespace(reduced_size=4, free=np.arange(4, dtype=np.int64))
    prepared._operator_identity = "synthetic-single-symmetry-pass"
    prepared._dof_signature = ()
    prepared._source_sha = "a" * 40
    prepared._physical_identity = "synthetic-physical-identity"

    original_metrics = modal_basis_module._sparse_symmetry_metrics
    calls: list[int] = []

    def observed_metrics(matrix: csr_matrix) -> tuple[float, bool]:
        calls.append(matrix.shape[0])
        return original_metrics(matrix)

    monkeypatch.setattr(modal_basis_module, "_sparse_symmetry_metrics", observed_metrics)
    monkeypatch.setattr(modal_basis_module, "_positive_definite_screen", lambda *_: {"method": "test"})

    def duplicate_exact_check_must_not_run(*_args: object, **_kwargs: object) -> bool:
        raise AssertionError("from_prepared must reuse exact symmetry from the relative-error pass")

    monkeypatch.setattr(modal_basis_module, "_is_exactly_sparse_symmetric", duplicate_exact_check_must_not_run)
    basis = ModalBasis.from_prepared(prepared, mode_count=2, method="dense", dense_limit=8)

    assert calls == [4]
    np.testing.assert_array_equal(basis.projected_stiffness, basis.projected_stiffness.T)


def test_tolerated_near_symmetric_k_falls_back_to_historical_bilinear_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stiffness = np.diag([2.0, 4.0, 7.0, 11.0])
    stiffness[0, 1] = 1.0e-13
    sparse_stiffness = csr_matrix(stiffness)
    mass = csr_matrix(np.eye(4))
    assert not is_exactly_sparse_symmetric(sparse_stiffness)
    assert relative_sparse_symmetry_error(sparse_stiffness) < SYMMETRY_TOL
    error, exact = sparse_symmetry_metrics(sparse_stiffness)
    assert error < SYMMETRY_TOL and not exact

    prepared = object.__new__(PreparedDynamicSystem)
    prepared._stiffness_reduced = sparse_stiffness
    prepared._mass_reduced = mass
    prepared._reducer = SimpleNamespace(reduced_size=4, free=np.arange(4, dtype=np.int64))
    prepared._operator_identity = "synthetic-near-symmetric-fallback"
    prepared._dof_signature = ()
    prepared._source_sha = "b" * 40
    prepared._physical_identity = "synthetic-near-symmetric-physical-identity"
    monkeypatch.setattr(modal_basis_module, "_positive_definite_screen", lambda *_: {"method": "test"})

    def structured_route_must_not_run(*_args: object, **_kwargs: object) -> np.ndarray:
        raise AssertionError("near-symmetric input must retain the historical projection route")

    monkeypatch.setattr(modal_basis_module, "_project_exact_symmetric_bilinear", structured_route_must_not_run)
    monkeypatch.setattr(
        modal_basis_module,
        "_is_exactly_sparse_symmetric",
        lambda *_: (_ for _ in ()).throw(AssertionError("prepared route must reuse combined symmetry metrics")),
    )
    basis = ModalBasis.from_prepared(prepared, mode_count=2, method="dense", dense_limit=8)
    expected = basis.modes.T @ (sparse_stiffness @ basis.modes)

    np.testing.assert_array_equal(basis.projected_stiffness, expected)
    np.testing.assert_array_equal(basis.projected_mass, basis.modes.T @ (mass @ basis.modes))
    assert 0.0 < relative_sparse_symmetry_error(csr_matrix(basis.projected_stiffness)) <= SYMMETRY_TOL


def test_from_prepared_rejects_significantly_asymmetric_stiffness() -> None:
    prepared = object.__new__(PreparedDynamicSystem)
    stiffness = np.diag([2.0, 3.0, 5.0, 7.0])
    stiffness[0, 1] = 0.25
    prepared._stiffness_reduced = csr_matrix(stiffness)
    prepared._mass_reduced = csr_matrix(np.eye(4))
    prepared._reducer = SimpleNamespace(reduced_size=4)

    with pytest.raises(InputValidationError, match="requires symmetric K/M"):
        ModalBasis.from_prepared(prepared, mode_count=2, method="dense", dense_limit=8)
