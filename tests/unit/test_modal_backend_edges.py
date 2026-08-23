from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from scipy.sparse import csr_matrix, diags

from solveur.core import modal
from solveur.core.errors import InputValidationError
from solveur.core.modal_options import validate_slepc_modal_scale


def _matrix() -> csr_matrix:
    return diags([2.0, 3.0, 4.0], format="csr")


def test_modal_dense_and_diagonal_preconditioner_contracts() -> None:
    stiffness = _matrix()
    mass = diags([1.0, 2.0, 4.0], format="csr")
    values, vectors = modal._dense_generalized_eigh(stiffness, mass, 2)
    assert values.shape == (2,)
    assert vectors.shape == (3, 2)
    assert np.all(values > 0.0)
    assert np.allclose(modal._preconditioner_diagonal(stiffness), [2.0, 3.0, 4.0])

    physical = SimpleNamespace(diagonal=lambda: np.asarray([0.0, 2.0, -4.0]))
    lazy = SimpleNamespace(physical_stiffness=physical)
    diagonal = modal._preconditioner_diagonal(lazy)
    assert diagonal[0] > 0.0
    with pytest.raises(InputValidationError, match="diagonal"):
        modal._preconditioner_diagonal(SimpleNamespace())

    operator = modal._lobpcg_preconditioner(stiffness, "diagonal")
    assert np.allclose(operator @ np.ones(3), [0.5, 1.0 / 3.0, 0.25])
    assert np.allclose(operator.matmat(np.eye(3)), np.diag([0.5, 1.0 / 3.0, 0.25]))
    with pytest.raises(InputValidationError, match="lobpcg_preconditioner"):
        modal._lobpcg_preconditioner(stiffness, "unknown")


def test_modal_ssor_and_spilu_preconditioners_apply_vectors_and_blocks() -> None:
    stiffness = diags([2.0, 3.0, 4.0], format="csr")
    physical_wrapper = SimpleNamespace(shape=stiffness.shape, physical_stiffness=stiffness)
    for name in ("ssor", "spilu"):
        operator = modal._lobpcg_preconditioner(physical_wrapper, name)
        assert np.all(np.isfinite(operator @ np.ones(3)))
        assert operator.matmat(np.eye(3)).shape == (3, 3)

    with pytest.raises(InputValidationError, match="SSOR"):
        modal._lobpcg_preconditioner(SimpleNamespace(shape=(3, 3)), "ssor")
    with pytest.raises(InputValidationError, match="spilu"):
        modal._lobpcg_preconditioner(SimpleNamespace(shape=(3, 3)), "spilu")


def test_modal_shift_inverse_helpers_cover_exact_and_sparse_fallback_paths() -> None:
    physical = _matrix()
    no_coupling = SimpleNamespace(shape=physical.shape, physical_stiffness=physical)
    assert modal._exact_lazy_shift_inverse(no_coupling, physical, max_dofs=10) is None
    assert modal._shifted_preconditioner_matrix(no_coupling, physical) is physical

    coupling = SimpleNamespace(
        shape=physical.shape,
        physical_stiffness=physical,
        stiffness_pd=csr_matrix((3, 3)),
        stiffness_dp=csr_matrix((3, 3)),
        drilling_factor=SimpleNamespace(solve=lambda values: values),
        drilling_diagonal=np.asarray([2.0, 0.0, 4.0]),
    )
    exact = modal._exact_lazy_shift_inverse(coupling, physical, max_dofs=10)
    assert exact is not None
    assert np.allclose(exact @ np.ones(3), [0.5, 1.0 / 3.0, 0.25])
    approximate = modal._shifted_preconditioner_matrix(coupling, physical)
    assert approximate.shape == (3, 3)

    bad_diagonal = SimpleNamespace(
        stiffness_pd=csr_matrix((3, 3)),
        stiffness_dp=csr_matrix((3, 3)),
        drilling_diagonal=np.asarray([np.nan]),
    )
    assert modal._shifted_preconditioner_matrix(bad_diagonal, physical) is physical
    with pytest.raises(InputValidationError, match="sparse stiffness"):
        modal._shift_inverse_operator(SimpleNamespace(shape=(3, 3)), np.eye(3), 0.0, preconditioner_name="diagonal", drop_tol=1e-4, fill_factor=10.0, rtol=1e-8, maxiter=10, restart=5)

    fallback = modal._shift_inverse_operator(
        physical,
        diags([1.0, 1.0, 1.0], format="csr"),
        0.1,
        preconditioner_name="diagonal",
        drop_tol=1e-4,
        fill_factor=10.0,
        rtol=1e-10,
        maxiter=20,
        restart=5,
    )
    assert np.allclose(fallback @ np.ones(3), [1.0 / 1.9, 1.0 / 2.9, 1.0 / 3.9])

    failing_factor = SimpleNamespace(
        shape=physical.shape,
        physical_stiffness=physical,
        stiffness_pd=csr_matrix((3, 3)),
        stiffness_dp=csr_matrix((3, 3)),
        drilling_factor=SimpleNamespace(solve=lambda values: (_ for _ in ()).throw(RuntimeError("factor"))),
    )
    assert modal._exact_lazy_shift_inverse(failing_factor, physical, max_dofs=10) is None
    assert modal._shifted_preconditioner_matrix(SimpleNamespace(drilling_diagonal=np.empty(0)), physical) is physical


def test_modal_gmres_preconditioners_and_diagnostics() -> None:
    stiffness = _matrix()
    for name in ("diagonal", "ssor", "spilu"):
        operator = modal._gmres_preconditioner(stiffness, name, drop_tol=1e-4, fill_factor=10.0)
        assert np.all(np.isfinite(operator @ np.ones(3)))
    with pytest.raises(InputValidationError, match="Modal preconditioner"):
        modal._gmres_preconditioner(stiffness, "bad", drop_tol=1e-4, fill_factor=10.0)

    values = np.asarray([2.0, 3.0])
    vectors = np.eye(2)
    mass = diags([1.0, 1.0], format="csr")
    stiffness2 = diags([2.0, 3.0], format="csr")
    empty = modal._modal_diagnostics(stiffness2, mass, np.empty(0), np.empty((2, 0)), {})
    assert empty["mode_count"] == 0
    diagnostics = modal._modal_diagnostics(
        stiffness2, mass, values, vectors, {"UX": np.ones(2), "UY": np.zeros(2), "UZ": np.zeros(2)}
    )
    assert diagnostics["mode_count"] == 2
    assert diagnostics["effective_modal_mass"]["total_direction_mass"]["UX"] == 2.0
    assert modal._maximum_modal_residual(stiffness2, mass, np.empty(0), np.empty((2, 0))) == 0.0


def test_modal_eigenpair_refinement_bounded_paths() -> None:
    stiffness = diags([2.0, 3.0], format="csr")
    mass = diags([1.0, 1.0], format="csr")
    values = np.asarray([2.0])
    vectors = np.asarray([[1.0], [0.0]])
    skipped = modal._refine_eigenpairs(stiffness, mass, values, vectors, iterations=0)
    assert skipped["iterations_performed"] == 0
    refined = modal._refine_eigenpairs(stiffness, mass, values, vectors, iterations=1)
    assert refined["iterations_performed"] == 1
    assert refined["maximum_residual_after"] <= refined["maximum_residual_before"]

    monkeypatch = pytest.MonkeyPatch()
    try:
        monkeypatch.setattr(modal, "spsolve", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("solve")))
        failed = modal._refine_eigenpairs(stiffness, mass, values, vectors, iterations=1)
        assert failed["iterations_performed"] == 1
    finally:
        monkeypatch.undo()

    zero_vectors = np.zeros((2, 1))
    zero = modal._refine_eigenpairs(stiffness, mass, values, zero_vectors, iterations=1)
    assert zero["iterations_performed"] == 1


def test_slepc_modal_scale_guard_is_explicit_and_conservative() -> None:
    validate_slepc_modal_scale(500_000, requested=True)
    validate_slepc_modal_scale(2_000_000, requested=False)
    with pytest.raises(InputValidationError, match="before sparse assembly") as error:
        validate_slepc_modal_scale(500_001, requested=True)
    message = str(error.value)
    assert "107,811" in message
    assert "500,000" in message
    assert "theoretical R&D ceiling" in message


@pytest.mark.parametrize(
    "parameters",
    ({"use_slepc_modal": True}, {"backend": "petsc"}),
)
def test_standard_modal_slepc_guard_runs_before_assembly(
    monkeypatch: pytest.MonkeyPatch, parameters: dict[str, object]
) -> None:
    model = SimpleNamespace(
        analysis=SimpleNamespace(parameters=parameters, method="eigsh"),
        dof_manager=lambda: SimpleNamespace(ndof=500_001),
    )
    solver = modal.ModalAnalysisSolver()
    monkeypatch.setattr(solver.validator, "validate", lambda _: SimpleNamespace(status="PASS"))

    def assembly_must_not_run(*args, **kwargs):
        raise AssertionError("modal assembly must not run past the SLEPc scale guard")

    monkeypatch.setattr(solver.assembler, "assemble_stiffness_and_mass", assembly_must_not_run)
    with pytest.raises(InputValidationError, match="before sparse assembly"):
        solver.solve(model)


def test_large_modal_slepc_guard_runs_before_petsc_assembly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from solveur.large import dynamic as large_dynamic

    model = SimpleNamespace(ndof=500_001)
    monkeypatch.setattr(
        large_dynamic,
        "_optional_slepc",
        lambda: (_ for _ in ()).throw(AssertionError("PETSc import must not run past the scale guard")),
    )
    with pytest.raises(InputValidationError, match="before sparse assembly"):
        large_dynamic.solve_large_modal(model)
