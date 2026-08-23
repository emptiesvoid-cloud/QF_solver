from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix, diags, eye

from solveur.core.errors import InputValidationError
from solveur.core.modal import _exact_lazy_shift_inverse, _shift_inverse_operator, _shifted_preconditioner_matrix
from solveur.large import solver
from solveur.large.audit import LargeAuditReport


class _IdentityDrillingFactor:
    def solve(self, values: np.ndarray) -> np.ndarray:
        return np.asarray(values, dtype=float)


def test_exact_lazy_shift_inverse_is_sparse_and_reusable() -> None:
    physical = diags([4.0, 5.0], format="csr")
    coupling_pd = csr_matrix(np.asarray([[1.0], [2.0]]))
    stiffness = SimpleNamespace(
        physical_stiffness=physical,
        stiffness_pd=coupling_pd,
        stiffness_dp=coupling_pd.T,
        drilling_factor=_IdentityDrillingFactor(),
        shape=(2, 2),
    )
    inverse = _exact_lazy_shift_inverse(stiffness, physical, max_dofs=10)
    assert inverse is not None
    assert np.all(np.isfinite(inverse @ np.ones(2)))

    shifted = _shift_inverse_operator(
        stiffness,
        eye(2, format="csr"),
        0.5,
        preconditioner_name="diagonal",
        drop_tol=1.0e-6,
        fill_factor=5.0,
        rtol=1.0e-8,
        maxiter=20,
        restart=5,
    )
    assert np.all(np.isfinite(shifted @ np.ones(2)))


def test_shifted_preconditioner_handles_missing_and_invalid_drilling_data() -> None:
    physical = diags([2.0, 3.0], format="csr")
    assert _shifted_preconditioner_matrix(SimpleNamespace(), physical) is physical
    invalid = SimpleNamespace(
        stiffness_pd=csr_matrix([[1.0], [2.0]]),
        stiffness_dp=csr_matrix([[1.0, 2.0]]),
        drilling_diagonal=np.asarray([np.nan]),
    )
    assert _shifted_preconditioner_matrix(invalid, physical) is physical
    empty = SimpleNamespace(
        stiffness_pd=csr_matrix([[1.0], [2.0]]),
        stiffness_dp=csr_matrix([[1.0, 2.0]]),
        drilling_diagonal=np.zeros(0),
    )
    assert _shifted_preconditioner_matrix(empty, physical) is physical


class _FakePetsc:
    DOUBLE = "double"


class _GatherComm:
    rank = 0
    size = 1

    def allgather(self, value):
        return [value]

    def Gatherv(self, send, receive, root=0) -> None:
        receive[0][:] = send


class _GatherVector:
    def getArray(self, readonly=False):
        return np.asarray([1.0, 2.0, 3.0, 4.0])

    def getOwnershipRange(self):
        return 0, 4


def test_petsc_displacement_gather_helper_is_deterministic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(solver, "_mpi", lambda: _FakePetsc)
    values, ownership = solver._gather_petsc_displacement(_GatherVector(), 4, _GatherComm())
    assert np.array_equal(values, [1.0, 2.0, 3.0, 4.0])
    assert ownership == [[0, 4]]


def test_petsc_restart_validation_reports_bad_metadata_and_payload(tmp_path) -> None:
    source = tmp_path / "displacements.bin"
    metadata = source.with_name("displacements_metadata.json")
    source.write_bytes(np.zeros(6, dtype=np.float64).tobytes())
    metadata.write_text(json.dumps({"shape": [2, 3], "dtype": "float32", "byte_order": "little"}), encoding="utf-8")
    vector = SimpleNamespace(getOwnershipRange=lambda: (0, 2), getArray=lambda: np.zeros(2), norm=lambda: 0.0)
    with pytest.raises(InputValidationError, match="incompatible"):
        solver._load_petsc_restart(vector, source, SimpleNamespace(node_count=2, ndof=6))

    metadata.write_text(json.dumps({"shape": [2, 3], "dtype": "float64", "byte_order": "little"}), encoding="utf-8")
    source.write_bytes(np.asarray([np.nan] * 6, dtype=np.float64).tobytes())
    with pytest.raises(InputValidationError, match="non-finite"):
        solver._load_petsc_restart(vector, source, SimpleNamespace(node_count=2, ndof=6))


def test_large_solver_summary_and_audit_conversion_are_serializable() -> None:
    audit = solver._audit_from_dict({"status": "PASS", "errors": [], "warnings": ["w"], "details": {"ok": True}})
    assert isinstance(audit, LargeAuditReport)
    model = SimpleNamespace(analysis={"type": "linear_static"}, node_count=2, element_count=1, ndof=6, nodes=np.zeros((2, 3)), tet4=np.zeros((1, 4)))
    summary = solver._summary(model, "matrix_free", {"converged": True}, 0.1, 0.2, audit)
    assert summary["backend"] == "matrix_free"
    assert summary["audit_status"] == "PASS"
