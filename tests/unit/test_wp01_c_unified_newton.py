"""WP01-C focused integration tests for the unified fixed-load Newton path."""

from __future__ import annotations

import inspect

import numpy as np
import pytest
from scipy.sparse import diags

from solveur.api import solve_model
from solveur.core.errors import NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.driver import ContributionResponse, UnifiedNewtonEngine
from solveur.core.nonlinear.iteration import solve_full_newton
from solveur.core.nonlinear.state import NonlinearState
from solveur.verification.tet4_total_lagrangian_assembly import _structured_tet4_mesh


class _LinearContribution:
    name = "linear"

    def __init__(self, internal: np.ndarray | None = None, *, trial_value: int | None = None) -> None:
        self.internal = None if internal is None else np.asarray(internal, dtype=float)
        self.trial_value = trial_value
        self.calls = 0
        self.load_factors: list[float] = []

    def evaluate(self, state: NonlinearState) -> ContributionResponse:
        self.calls += 1
        self.load_factors.append(state.load_factor)
        trial_state = None if self.trial_value is None else {"value": self.calls}
        return ContributionResponse(
            name=self.name,
            internal_force=(state.displacement.copy() if self.internal is None else self.internal.copy()),
            tangent=diags([1.0, 1.0], format="csr"),
            trial_state=trial_state,
        )


def _engine(
    state: NonlinearState,
    contribution: _LinearContribution,
    *,
    factors: tuple[float, ...] = (1.0,),
    max_iterations: int = 5,
    apply_trial_state=None,
    line_search=None,
):
    return UnifiedNewtonEngine().solve(
        initial_state=state,
        external_force=np.asarray([1.0, 0.0]),
        fixed=np.asarray([1]),
        target_load_factors=factors,
        tolerance=1.0e-12,
        max_iterations=max_iterations,
        contributions=(contribution,),
        linear_solve=lambda matrix, rhs: (np.asarray(rhs, dtype=float), None),
        apply_trial_state=apply_trial_state,
        line_search=line_search,
    )


def test_t19_one_accepted_increment_performs_one_composite_commit() -> None:
    state = NonlinearState(np.zeros(2))
    result = _engine(state, _LinearContribution())
    assert result.diagnostics["commit_count"] == 1
    assert result.state.load_factor == 1.0


def test_t20_multiple_iterations_do_not_commit_intermediate_material_state() -> None:
    state = NonlinearState(np.zeros(2), material_state={"value": 0})
    contribution = _LinearContribution(trial_value=1)

    def apply(trial: NonlinearState, response: object) -> None:
        trial.material_state = {"value": contribution.calls}

    result = _engine(state, contribution, max_iterations=3, apply_trial_state=apply)
    assert contribution.calls == 2
    assert state.material_state == {"value": 0}
    assert result.state.material_state == {"value": 2}
    assert result.diagnostics["commit_count"] == 1


def test_t21_failed_increment_preserves_accepted_displacement_digest() -> None:
    state = NonlinearState(np.zeros(2))
    before = state.digest
    with pytest.raises(NumericalConvergenceError) as error:
        _engine(state, _LinearContribution(internal=np.asarray([0.0, 0.0])), max_iterations=1)
    assert error.value.reason is NonlinearFailureReason.MAX_ITERATIONS
    assert state.digest == before


def test_t22_failed_increment_preserves_material_state_digest() -> None:
    state = NonlinearState(np.zeros(2), material_state={"alpha": 0.25})
    before = state.component_digests["material_state"]
    with pytest.raises(NumericalConvergenceError):
        _engine(state, _LinearContribution(), max_iterations=1)
    assert state.component_digests["material_state"] == before


def test_t23_failed_contact_coupled_increment_preserves_contact_state_digest() -> None:
    state = NonlinearState(np.zeros(2), contact_state={"active": [1], "gap": np.asarray([0.0])})
    before = state.component_digests["contact_state"]
    with pytest.raises(NumericalConvergenceError):
        _engine(state, _LinearContribution(), max_iterations=1)
    assert state.component_digests["contact_state"] == before


def test_t24_load_factor_advances_only_after_acceptance() -> None:
    state = NonlinearState(np.zeros(2))
    contribution = _LinearContribution()
    result = _engine(state, contribution, factors=(0.5, 1.0))
    assert contribution.load_factors == [0.0, 0.0, 0.5, 0.5]
    assert result.state.load_factor == 1.0
    assert state.load_factor == 0.0


def test_t25_solve_full_newton_delegates_to_authoritative_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    original = UnifiedNewtonEngine.solve

    def spy(self, **kwargs):
        nonlocal calls
        calls += 1
        return original(self, **kwargs)

    monkeypatch.setattr("solveur.core.nonlinear.iteration.UnifiedNewtonEngine.solve", spy)

    class IdentityAssembly:
        ndof = 2

        def assemble(self, displacement, *, tangent_required=True):
            return np.asarray(displacement), diags([1.0, 1.0], format="csr")

    solve_full_newton(
        IdentityAssembly(),
        np.asarray([1.0, 0.0]),
        np.asarray([1]),
        increments=1,
        tolerance=1.0e-10,
        max_iterations=3,
    )
    assert calls == 1


def _geometric_model() -> FiniteElementModel:
    nodes, elements = _structured_tet4_mesh(2, 1, 1, 2.0, 0.5, 0.5)
    fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    tip = np.flatnonzero(np.isclose(nodes[:, 0], 2.0))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "TET4", "nodes": row.tolist(), "material": "solid"} for row in elements],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed],
        loads=[{"node": int(node), "dof": "UZ", "value": -1.0 / len(tip)} for node in tip],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"load_increments": 6},
        },
    )


def _j2_model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        analysis={"type": "nonlinear_static", "method": "newton_raphson", "load_steps": 2},
        nodes=[[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
        elements=[{"type": "TET4", "nodes": [0, 1, 2, 3], "material": "plastic"}],
        materials={
            "plastic": {
                "type": "von_mises_elastoplastic_3d",
                "E": 1000.0,
                "nu": 0.25,
                "yield_stress": 5.0,
                "hardening_modulus": 100.0,
            }
        },
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UX", "UY", "UZ"]},
            {"node": 3, "dofs": ["UX", "UY", "UZ"]},
        ],
        loads=[{"node": 1, "dof": "UX", "value": 10.0}],
    )


def test_t26_geometric_solver_uses_the_same_authoritative_lifecycle(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    original = UnifiedNewtonEngine.solve

    def spy(self, **kwargs):
        nonlocal calls
        calls += 1
        return original(self, **kwargs)

    monkeypatch.setattr("solveur.core.nonlinear.iteration.UnifiedNewtonEngine.solve", spy)
    result = solve_model(_geometric_model(), enforce_policy=False)
    assert result.status == "success"
    assert calls == 1


def test_t27_j2_standard_load_control_uses_the_same_authoritative_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0
    original = UnifiedNewtonEngine.solve

    def spy(self, **kwargs):
        nonlocal calls
        calls += 1
        return original(self, **kwargs)

    monkeypatch.setattr("solveur.core.nonlinear.load_control.UnifiedNewtonEngine.solve", spy)
    result = solve_model(_j2_model(), enforce_policy=False)
    assert result.status == "PASS"
    assert calls == 2


def test_t28_line_search_rejection_does_not_leak_trial_state() -> None:
    state = NonlinearState(np.zeros(2), material_state={"alpha": 0.5})
    before = state.digest

    def reject(*_args):
        raise NumericalConvergenceError(
            "controlled line-search rejection", reason=NonlinearFailureReason.LINE_SEARCH_FAILURE
        )

    with pytest.raises(NumericalConvergenceError) as error:
        _engine(state, _LinearContribution(), line_search=reject)
    assert error.value.reason is NonlinearFailureReason.LINE_SEARCH_FAILURE
    assert state.digest == before


def test_t29_replayed_failure_has_identical_reason_and_diagnostic_digest() -> None:
    class SingularAssembly:
        ndof = 2

        def assemble(self, displacement, *, tangent_required=True):
            return np.zeros(2), diags([0.0, 0.0], format="csr")

    def run() -> dict[str, object]:
        with pytest.raises(NumericalConvergenceError) as error:
            solve_full_newton(
                SingularAssembly(),
                np.asarray([1.0, 0.0]),
                np.asarray([1]),
                increments=1,
                tolerance=1.0e-8,
                max_iterations=3,
            )
        return error.value.to_dict()

    assert run() == run()


def test_t30_compatibility_adapter_contains_no_second_newton_loop() -> None:
    source = inspect.getsource(solve_full_newton)
    assert "UnifiedNewtonEngine" in source
    assert "for iteration" not in source
    assert "for step in" not in source
