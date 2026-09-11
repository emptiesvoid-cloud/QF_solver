"""Focused WP01-B tests for formulation-neutral nonlinear foundation APIs."""

from __future__ import annotations

from dataclasses import fields

import numpy as np
import pytest
from scipy.sparse import diags

from solveur.core.errors import NumericalConvergenceError
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.driver import (
    ContributionResponse,
    DriverDecision,
    RetryClassification,
    UnifiedNonlinearDriverFoundation,
    canonical_residual,
    compose_contribution_responses,
)
from solveur.core.nonlinear.state import NonlinearState, NonlinearStateTransaction


def _state() -> NonlinearState:
    return NonlinearState(
        displacement=np.asarray([1.0, -2.0]),
        load_factor=0.25,
        material_state={0: [{"alpha": 0.1, "strain": np.asarray([0.0, 0.02])}]},
        contact_state={"active": [1], "gap": np.asarray([0.0])},
        continuation_state={"radius": 0.5},
        accepted_increment_metadata={"step": 2, "method": "load_control"},
    )


def _response(
    name: str = "material",
    *,
    trial_state: dict[str, object] | None = None,
    diagnostics: dict[str, object] | None = None,
    admissible: bool = True,
    failure_reason: NonlinearFailureReason | None = None,
) -> ContributionResponse:
    return ContributionResponse(
        name=name,
        internal_force=np.asarray([2.0, 3.0]),
        tangent=diags([2.0, 3.0], format="csr"),
        trial_state=trial_state,
        diagnostics=diagnostics or {},
        admissible=admissible,
        failure_reason=failure_reason,
    )


class _Contribution:
    def __init__(self, response: ContributionResponse):
        self.response = response

    def evaluate(self, state: NonlinearState) -> ContributionResponse:
        return self.response


def test_t01_equivalent_composite_states_have_identical_digest() -> None:
    first = _state()
    second = NonlinearState(
        displacement=np.asarray([1.0, -2.0]),
        load_factor=0.25,
        material_state={0: [{"strain": np.asarray([0.0, 0.02]), "alpha": 0.1}]},
        contact_state={"gap": np.asarray([0.0]), "active": [1]},
        continuation_state={"radius": 0.5},
        accepted_increment_metadata={"method": "load_control", "step": 2},
    )
    assert first.digest == second.digest
    assert first.component_digests == second.component_digests


def test_t02_changed_displacement_changes_composite_digest() -> None:
    changed = _state()
    changed.displacement[0] += 1.0
    assert changed.digest != _state().digest


def test_t03_changed_material_state_changes_composite_digest() -> None:
    changed = _state()
    changed.material_state[0][0]["alpha"] = 0.2
    assert changed.digest != _state().digest


def test_t04_changed_contact_state_changes_composite_digest() -> None:
    changed = _state()
    changed.contact_state["active"].append(2)
    assert changed.digest != _state().digest


def test_t05_changed_continuation_state_changes_composite_digest() -> None:
    changed = _state()
    changed.continuation_state["radius"] = 0.75
    assert changed.digest != _state().digest


def test_t06_begin_trial_does_not_alter_accepted_state() -> None:
    transaction = NonlinearStateTransaction(_state())
    before = transaction.accepted_digest
    transaction.begin_trial()
    assert transaction.accepted_digest == before


def test_t07_trial_modifications_do_not_leak_to_accepted_state() -> None:
    transaction = NonlinearStateTransaction(_state())
    trial = transaction.begin_trial()
    trial.displacement[0] = 99.0
    trial.material_state[0][0]["alpha"] = 9.0
    trial.contact_state["active"].append(9)
    assert transaction.accepted_state.displacement[0] == 1.0
    assert transaction.accepted_state.material_state[0][0]["alpha"] == 0.1
    assert transaction.accepted_state.contact_state["active"] == [1]


def test_t08_rollback_preserves_exact_component_and_composite_digests() -> None:
    transaction = NonlinearStateTransaction(_state())
    before_components = transaction.accepted_component_digests
    before = transaction.accepted_digest
    trial = transaction.begin_trial()
    trial.contact_state["active"].append(3)
    transaction.rollback()
    assert transaction.accepted_component_digests == before_components
    assert transaction.accepted_digest == before


def test_t09_successful_commit_publishes_all_components_together() -> None:
    transaction = NonlinearStateTransaction(_state())
    trial = transaction.begin_trial()
    trial.displacement[:] = [4.0, 5.0]
    trial.load_factor = 0.5
    trial.material_state[0][0]["alpha"] = 0.3
    trial.contact_state["active"] = [2]
    trial.continuation_state["radius"] = 0.75
    trial.accepted_increment_metadata["step"] = 3
    accepted = transaction.commit()
    np.testing.assert_allclose(accepted.displacement, [4.0, 5.0])
    assert accepted.load_factor == 0.5
    assert accepted.material_state[0][0]["alpha"] == 0.3
    assert accepted.contact_state["active"] == [2]
    assert accepted.continuation_state["radius"] == 0.75
    assert accepted.accepted_increment_metadata["step"] == 3
    assert transaction.commit_count == 1


def test_t10_invalid_trial_commit_publishes_no_component() -> None:
    transaction = NonlinearStateTransaction(_state())
    before = transaction.accepted_digest
    trial = transaction.begin_trial()
    trial.displacement[0] = np.nan
    with pytest.raises(NumericalConvergenceError) as error:
        transaction.commit()
    assert error.value.reason is NonlinearFailureReason.STATE_CORRUPTION
    assert transaction.accepted_digest == before


def test_t11_external_accepted_state_mutation_is_detected() -> None:
    transaction = NonlinearStateTransaction(_state())
    transaction.begin_trial()
    transaction.accepted_state.contact_state["active"].append(7)
    with pytest.raises(NumericalConvergenceError) as error:
        transaction.rollback()
    assert error.value.reason is NonlinearFailureReason.STATE_CORRUPTION


def test_t12_stateless_contribution_requires_no_persistent_state() -> None:
    response = _response(trial_state=None)
    composite = compose_contribution_responses([response])
    assert composite.trial_state_updates == {}
    np.testing.assert_allclose(canonical_residual(np.asarray([4.0, 6.0]), 1.0, composite), [2.0, 3.0])


def test_t13_multiple_contributions_compose_force_and_sparse_tangent() -> None:
    material = _response("material")
    geometric = ContributionResponse(
        name="geometric",
        internal_force=np.asarray([1.0, 2.0]),
        tangent=diags([1.0, 2.0], format="csr"),
    )
    composite = compose_contribution_responses([material, geometric])
    np.testing.assert_allclose(composite.internal_force, [3.0, 5.0])
    np.testing.assert_allclose(composite.tangent.diagonal(), [3.0, 5.0])
    assert composite.tangent.nnz == 2


def test_t14_contribution_diagnostics_are_isolated_and_traceable() -> None:
    raw = {"nested": {"iterations": 2}}
    material = _response("material", diagnostics=raw)
    contact = _response("contact", diagnostics={"gap": 0.0})
    raw["nested"]["iterations"] = 99
    composite = compose_contribution_responses([material, contact])
    assert set(composite.diagnostics) == {"material", "contact"}
    assert composite.diagnostics["material"]["nested"]["iterations"] == 2
    assert composite.diagnostics["contact"]["gap"] == 0.0


def test_t15_driver_rejection_invokes_rollback() -> None:
    transaction = NonlinearStateTransaction(_state())
    before = transaction.accepted_digest
    result = UnifiedNonlinearDriverFoundation().execute_increment(
        transaction,
        [_Contribution(_response())],
        convergence=lambda _trial, _response: DriverDecision(False, NonlinearFailureReason.MAX_ITERATIONS),
    )
    assert result.accepted is False
    assert result.reason is NonlinearFailureReason.MAX_ITERATIONS
    assert result.retry_class is RetryClassification.RETRYABLE
    assert result.lifecycle[-1] == "rollback"
    assert transaction.trial_state is None
    assert transaction.accepted_digest == before


def test_t16_driver_acceptance_invokes_exactly_one_global_commit() -> None:
    transaction = NonlinearStateTransaction(_state())

    def correction(trial: NonlinearState, _response: object) -> None:
        trial.displacement += 1.0

    result = UnifiedNonlinearDriverFoundation().execute_increment(
        transaction,
        [_Contribution(_response("material", trial_state={"alpha": 0.2}))],
        correction=correction,
        convergence=lambda _trial, _response: DriverDecision(True),
    )
    assert result.accepted is True
    assert result.lifecycle[-1] == "commit"
    assert transaction.commit_count == 1
    np.testing.assert_allclose(transaction.accepted_state.displacement, [2.0, -1.0])


def test_t17_contribution_receives_only_trial_state_not_accepted_state() -> None:
    class _TrialMutatingContribution:
        def evaluate(self, state: NonlinearState) -> ContributionResponse:
            state.material_state[0][0]["alpha"] = 8.0
            return _response()

    transaction = NonlinearStateTransaction(_state())
    result = UnifiedNonlinearDriverFoundation().execute_increment(
        transaction,
        [_TrialMutatingContribution()],
        convergence=lambda _trial, _response: DriverDecision(False, NonlinearFailureReason.MAX_ITERATIONS),
    )
    assert result.accepted is False
    assert transaction.accepted_state.material_state[0][0]["alpha"] == 0.1


def test_t18_identical_failure_runs_have_identical_failure_metadata() -> None:
    def run_failure() -> tuple[object, ...]:
        transaction = NonlinearStateTransaction(_state())
        result = UnifiedNonlinearDriverFoundation().execute_increment(
            transaction,
            [_Contribution(_response(failure_reason=NonlinearFailureReason.LINE_SEARCH_FAILURE))],
            convergence=lambda _trial, _response: DriverDecision(True),
        )
        return result.reason, result.retry_class, result.lifecycle, result.diagnostics

    assert run_failure() == run_failure()


def test_state_boundary_contains_no_model_or_global_matrix_payload() -> None:
    names = {entry.name for entry in fields(NonlinearState)}
    assert names == {
        "displacement",
        "load_factor",
        "material_state",
        "contact_state",
        "continuation_state",
        "accepted_increment_metadata",
        "schema_version",
    }
