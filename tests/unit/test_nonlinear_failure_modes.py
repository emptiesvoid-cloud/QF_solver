from __future__ import annotations

from dataclasses import replace

import numpy as np
import pytest
from scipy.sparse import eye

from solveur.core.errors import NumericalConvergenceError
from solveur.core.material_state import state_is_finite
from solveur.core.nonlinear_assembly import assemble_internal_tangent
from solveur.core.nonlinear_contracts import NonlinearFailureReason
from solveur.core.nonlinear_iteration import _nonfinite_failure_reason, solve_full_newton
from tests.unit.test_analysis_features import elastoplastic_tet4_model


def test_nested_state_finiteness_rejects_nan_and_inf() -> None:
    assert state_is_finite({"plastic": [0.0, np.asarray([1.0, 2.0])]})
    assert not state_is_finite({"plastic": [0.0, np.asarray([1.0, np.nan])]})
    assert not state_is_finite({"stress": {"value": float("inf")}})


def test_nonlinear_failure_exposes_a_stable_non_converged_record() -> None:
    error = NumericalConvergenceError(
        "singular tangent",
        reason=NonlinearFailureReason.SINGULAR_TANGENT,
        diagnostics={"step": 2, "iterations": 4},
    )

    assert error.to_dict() == {
        "converged": False,
        "reason": "SINGULAR_TANGENT",
        "message": "singular tangent",
        "diagnostics": {"step": 2, "iterations": 4},
    }


def test_nonlinear_assembly_classifies_nonfinite_trial_state(monkeypatch: pytest.MonkeyPatch) -> None:
    model = elastoplastic_tet4_model()
    dofs = model.dof_manager()

    def nonfinite_state(*args, **kwargs):
        return np.zeros(12), eye(12, format="csr").toarray(), [{"equivalent_plastic_strain": np.nan}]

    monkeypatch.setattr(
        "solveur.elements.solid.tet4.Tet4Element.internal_force_tangent_state",
        nonfinite_state,
    )
    with pytest.raises(NumericalConvergenceError) as error:
        assemble_internal_tangent(model, dofs, np.zeros(dofs.ndof), {})

    assert error.value.reason is NonlinearFailureReason.NAN_DETECTED
    assert error.value.diagnostics == {"element_index": 0, "state": "trial"}


def test_nonlinear_assembly_classifies_element_update_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    model = elastoplastic_tet4_model()
    dofs = model.dof_manager()

    def invalid_element(*args, **kwargs):
        raise ValueError("Invalid TET4 orientation")

    monkeypatch.setattr(
        "solveur.elements.solid.tet4.Tet4Element.internal_force_tangent_state",
        invalid_element,
    )
    with pytest.raises(NumericalConvergenceError) as error:
        assemble_internal_tangent(model, dofs, np.zeros(dofs.ndof), {})

    assert error.value.reason is NonlinearFailureReason.INVALID_ELEMENT
    assert error.value.diagnostics == {"element_index": 0, "element_type": "TET4"}

    def material_failure(*args, **kwargs):
        raise ValueError("material constitutive update failed")

    monkeypatch.setattr(
        "solveur.elements.solid.tet4.Tet4Element.internal_force_tangent_state",
        material_failure,
    )
    with pytest.raises(NumericalConvergenceError) as material_error:
        assemble_internal_tangent(model, dofs, np.zeros(dofs.ndof), {})

    assert material_error.value.reason is NonlinearFailureReason.MATERIAL_UPDATE_FAILURE


@pytest.mark.parametrize(
    ("message", "reason"),
    [
        ("Invalid HEX8 orientation", NonlinearFailureReason.INVALID_ELEMENT),
        ("material constitutive update failed", NonlinearFailureReason.MATERIAL_UPDATE_FAILURE),
        ("contact projection produced a non-finite gap", NonlinearFailureReason.CONTACT_UPDATE_FAILURE),
    ],
)
def test_full_newton_classifies_assembly_failures(message: str, reason: NonlinearFailureReason) -> None:
    class FailingAssembly:
        ndof = 2

        def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
            raise ValueError(message)

    with pytest.raises(NumericalConvergenceError) as error:
        solve_full_newton(
            FailingAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=2,
        )

    assert error.value.reason is reason
    assert error.value.to_dict()["converged"] is False
    assert error.value.diagnostics["step"] == 1
    assert error.value.diagnostics["iterations"] == 1


def test_full_newton_classifies_linear_backend_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class ValidAssembly:
        ndof = 2

        def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
            return np.zeros(2), eye(2, format="csr")

    def fail(*args, **kwargs):
        raise RuntimeError("controlled sparse factorization failure")

    monkeypatch.setattr("solveur.core.nonlinear_iteration.spsolve", fail)
    with pytest.raises(NumericalConvergenceError) as error:
        solve_full_newton(
            ValidAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=2,
        )

    assert error.value.reason is NonlinearFailureReason.LINEAR_SOLVER_FAILURE
    assert error.value.diagnostics["backend_error"] == "controlled sparse factorization failure"


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        (np.nan, NonlinearFailureReason.NAN_DETECTED),
        (np.inf, NonlinearFailureReason.INF_DETECTED),
        (-np.inf, NonlinearFailureReason.INF_DETECTED),
    ],
)
def test_full_newton_distinguishes_nan_and_inf_residuals(
    value: float, reason: NonlinearFailureReason
) -> None:
    class NonFiniteAssembly:
        ndof = 2

        def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
            return np.array([value, 0.0]), eye(2, format="csr")

    with pytest.raises(NumericalConvergenceError) as error:
        solve_full_newton(
            NonFiniteAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=2,
        )

    assert error.value.reason is reason
    assert error.value.to_dict()["converged"] is False


@pytest.mark.parametrize(
    ("value", "reason"),
    [
        (np.nan, NonlinearFailureReason.NAN_DETECTED),
        (np.inf, NonlinearFailureReason.INF_DETECTED),
        (-np.inf, NonlinearFailureReason.INF_DETECTED),
    ],
)
def test_full_newton_distinguishes_nonfinite_linear_corrections(
    monkeypatch: pytest.MonkeyPatch,
    value: float,
    reason: NonlinearFailureReason,
) -> None:
    class ValidAssembly:
        ndof = 2

        def assemble(self, displacement: np.ndarray, *, tangent_required: bool = True):
            return np.zeros(2), eye(2, format="csr")

    monkeypatch.setattr(
        "solveur.core.nonlinear_iteration.spsolve",
        lambda *args, **kwargs: np.array([value, 0.0]),
    )
    with pytest.raises(NumericalConvergenceError) as error:
        solve_full_newton(
            ValidAssembly(),
            np.array([1.0, 0.0]),
            np.array([1]),
            increments=1,
            tolerance=1.0e-8,
            max_iterations=2,
        )

    payload = error.value.to_dict()
    assert error.value.reason is reason
    assert payload["converged"] is False
    assert payload["diagnostics"]["solver"] == "full_newton"


@pytest.mark.parametrize(
    ("values", "reason"),
    [
        (np.array([np.nan, 0.0]), NonlinearFailureReason.NAN_DETECTED),
        (np.array([np.inf, 0.0]), NonlinearFailureReason.INF_DETECTED),
        (np.array([np.nan, -np.inf]), NonlinearFailureReason.INF_DETECTED),
    ],
)
def test_nonfinite_failure_reason_is_deterministic_for_arrays(
    values: np.ndarray, reason: NonlinearFailureReason
) -> None:
    assert _nonfinite_failure_reason(values) is reason


def test_arc_length_does_not_hide_nonfinite_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    model = elastoplastic_tet4_model()
    model.analysis = replace(
        model.analysis,
        method="arc_length",
        parameters={"load_steps": 2, "max_arc_steps": 2, "min_arc_length_radius": 1.0e-8},
    )

    def fail(*args, **kwargs):
        raise NumericalConvergenceError(
            "controlled nonfinite continuation failure",
            reason=NonlinearFailureReason.NAN_DETECTED,
        )

    monkeypatch.setattr("solveur.core.nonlinear.NonlinearStaticSolver._solve_arc_length_step", fail)
    with pytest.raises(NumericalConvergenceError) as error:
        from solveur.api import solve_model

        solve_model(model)

    assert error.value.reason is NonlinearFailureReason.NAN_DETECTED
