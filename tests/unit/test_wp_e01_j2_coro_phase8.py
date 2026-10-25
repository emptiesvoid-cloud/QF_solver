from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import inspect
import json
import logging

import numpy as np
import pytest

from solveur.core.errors import NonlinearFailureReason, NumericalConvergenceError
from solveur.core.nonlinear.driver import UnifiedContinuationController, UnifiedNewtonEngine
from solveur.core.nonlinear.checkpoint import checkpoint_acceptance_status
from solveur.core.nonlinear.material_state import deterministic_state_digest
from solveur.core.nonlinear.solver import NonlinearStaticSolver
from solveur.core.nonlinear.state import NonlinearStateTransaction
from solveur.elements.solid.corotational_j2 import (
    CORRECTED_COROTATIONAL_J2,
    CORRECTED_TANGENT_POLAR_ANALYTIC_VERSION,
)
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from solveur.verification.robustness_mesh import _refinement_model


_FAMILIES = ("TET4", "HEX8", "HEX20")


def _phase8_model(family: str, *, adaptive: bool, load_path: list[float] | None = None):
    base = _refinement_model(family, 1)
    parameters = {
        **base.analysis.parameters,
        "kinematics": "corotational_j2",
        "corotational_formulation": CORRECTED_COROTATIONAL_J2,
        "j2_corotational_tangent": "analytic_experimental",
        "adaptive_load_steps": adaptive,
        "max_iterations": 35,
        "tolerance": 1.0e-8,
    }
    if adaptive:
        parameters.update(
            {
                "load_steps": 1,
                "initial_load_increment": 0.8,
                "min_load_increment": 0.03125,
                "max_load_increment": 1.0,
                "max_cutbacks": 20,
            }
        )
        parameters.pop("load_path", None)
    else:
        assert load_path is not None
        parameters["load_steps"] = len(load_path)
        parameters["load_path"] = list(load_path)
    return replace(
        base,
        analysis=replace(base.analysis, parameters=parameters),
        loads=[replace(load, value=load.value * 0.25) for load in base.loads],
    )


def _maximum_peeq(states) -> float:
    return max(
        float(point["equivalent_plastic_strain"])
        for points in states.values()
        for point in points
    )


def _maximum_guard_norm(contributions, displacement: np.ndarray) -> float:
    values: list[float] = []
    for contribution in contributions:
        plan = getattr(getattr(contribution, "owner", None), "_assembly_plan", None)
        if plan is None:
            continue
        for entry in plan.elements:
            element = entry.element
            local = np.asarray(displacement[entry.global_dofs], dtype=float).reshape(element.node_count, 3)
            relative = local - local[0]
            reference_data, _, _ = element._corrected_reference_data(entry.coordinates)
            identity = np.eye(3)
            for _, gradient in reference_data:
                deformation = identity + relative.T @ np.asarray(gradient, dtype=float)
                _, singular_values, right = np.linalg.svd(deformation)
                stretch = right.T @ np.diag(singular_values) @ right
                values.append(float(np.linalg.norm(stretch - identity)))
    assert values, "the material assembly plan must expose corrected corotational guard points"
    return max(values)


@pytest.mark.parametrize("family", _FAMILIES)
def test_phase8_controlled_recoverable_failure_rolls_back_and_retries_on_same_partition(
    family: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Inject after an evolved admissible trial and before Newton commits it."""
    model = _phase8_model(family, adaptive=True)
    original_solve_increment = UnifiedNewtonEngine._solve_increment
    injected: list[dict[str, object]] = []

    def fail_in_apply_trial_state(engine, *args, **kwargs):
        bound = inspect.signature(original_solve_increment).bind(engine, *args, **kwargs)
        transaction = bound.arguments["transaction"]
        original_apply = bound.arguments.get("apply_trial_state")

        def apply_then_inject(trial, composite):
            if original_apply is not None:
                original_apply(trial, composite)
            accepted = transaction.accepted_state
            if injected or accepted.load_factor != 0.8:
                return
            response_states = composite.trial_state_updates.get("material")
            assert response_states is not None, "material response must supply trial history before injection"
            response_states = deepcopy(dict(response_states))
            accepted_digest = accepted.digest
            accepted_peeq = _maximum_peeq(accepted.material_state)
            trial_peeq = _maximum_peeq(response_states)
            assert accepted_peeq > 0.0, "injection must start from an already plastically evolved accepted state"
            if trial_peeq <= accepted_peeq:
                return
            guard_norm = _maximum_guard_norm(bound.arguments["contributions"], trial.displacement)
            assert guard_norm < 0.05, "injected trial must remain strictly inside the unchanged corotational guard"
            trial.material_state = response_states
            assert transaction.accepted_state.digest == accepted_digest
            assert checkpoint_acceptance_status(trial) == "TRIAL"
            injected.append(
                {
                    "accepted_digest_before": accepted_digest,
                    "transaction_id": id(transaction),
                    "accepted_load_factor": float(accepted.load_factor),
                    "accepted_peeq": accepted_peeq,
                    "trial_digest": trial.digest,
                    "trial_peeq": trial_peeq,
                    "guard_norm": guard_norm,
                    "trial_acceptance_status": checkpoint_acceptance_status(trial),
                    "accepted_state_snapshot": accepted.detached_copy(),
                }
            )
            raise NumericalConvergenceError(
                "Phase 8 controlled recoverable failure after admissible material evolution.",
                reason=NonlinearFailureReason.MAX_ITERATIONS,
                diagnostics={"phase8_injection": True, "guard_norm": guard_norm},
            )

        bound.arguments["apply_trial_state"] = apply_then_inject
        return original_solve_increment(*bound.args, **bound.kwargs)

    rollback_records: list[dict[str, object]] = []
    original_rollback = UnifiedContinuationController.rollback
    transaction_rollback_records: list[dict[str, object]] = []
    original_transaction_rollback = NonlinearStateTransaction.rollback

    def observe_transaction_rollback(transaction):
        accepted_digest_before = transaction.accepted_state.digest
        observed_trial = transaction.trial_state is not None
        result = original_transaction_rollback(transaction)
        transaction_rollback_records.append(
            {
                "transaction_id": id(transaction),
                "accepted_digest_before": accepted_digest_before,
                "accepted_digest_after": transaction.accepted_state.digest,
                "trial_existed_before": observed_trial,
                "trial_cleared": transaction.trial_state is None,
            }
        )
        return result

    def observe_rollback(controller, error, **kwargs):
        before = controller.accepted_state.digest
        observed = original_rollback(controller, error, **kwargs)
        rollback_records.append(
            {
                "failure_reason": getattr(error, "reason", None),
                "transaction_id": id(controller.transaction),
                "accepted_digest_before": before,
                "accepted_digest_after": controller.accepted_state.digest,
                "trial_cleared": controller.transaction.trial_state is None,
                "rejection_log_entry": deepcopy(controller.rejection_log[-1]),
            }
        )
        return observed

    monkeypatch.setattr(UnifiedNewtonEngine, "_solve_increment", fail_in_apply_trial_state)
    monkeypatch.setattr(NonlinearStateTransaction, "rollback", observe_transaction_rollback)
    monkeypatch.setattr(UnifiedContinuationController, "rollback", observe_rollback)
    retried = NonlinearStaticSolver().solve(model)

    assert len(injected) == 1
    assert len(rollback_records) == 1
    assert injected[0]["trial_acceptance_status"] == "TRIAL"
    assert injected[0]["accepted_load_factor"] == 0.8
    assert injected[0]["accepted_peeq"] > 0.0
    assert injected[0]["trial_peeq"] > injected[0]["accepted_peeq"]
    assert injected[0]["guard_norm"] < 0.05
    inner_rollbacks = [
        record for record in transaction_rollback_records
        if record["transaction_id"] == injected[0]["transaction_id"]
    ]
    assert len(inner_rollbacks) == 1
    assert inner_rollbacks[0]["trial_existed_before"] is True
    assert inner_rollbacks[0]["accepted_digest_before"] == injected[0]["accepted_digest_before"]
    assert inner_rollbacks[0]["accepted_digest_after"] == injected[0]["accepted_digest_before"]
    assert inner_rollbacks[0]["trial_cleared"] is True
    assert rollback_records[0]["transaction_id"] != injected[0]["transaction_id"]
    assert rollback_records[0]["accepted_digest_before"] == rollback_records[0]["accepted_digest_after"]
    assert rollback_records[0]["trial_cleared"] is True
    assert rollback_records[0]["rejection_log_entry"]["rollback_before_retry"] is True
    assert rollback_records[0]["rejection_log_entry"]["failure_reason"] == "MAX_ITERATIONS"
    assert retried.status == "PASS"
    assert retried.solver["tangent_strategy_version"] == CORRECTED_TANGENT_POLAR_ANALYTIC_VERSION
    assert retried.solver["rejected_increments"] == 1
    accepted_partition = list(retried.solver["load_path"])
    assert accepted_partition == [0.8, 0.9, 1.0]

    reference = NonlinearStaticSolver().solve(
        _phase8_model(family, adaptive=False, load_path=accepted_partition)
    )
    assert reference.status == "PASS"
    np.testing.assert_allclose(retried.displacements, reference.displacements, rtol=1.0e-11, atol=1.0e-12)
    assert deterministic_state_digest(retried.material_states) == deterministic_state_digest(reference.material_states)
    assert _maximum_peeq(retried.material_states) > 0.0


@pytest.mark.parametrize("family", _FAMILIES)
def test_phase8_checkpoint_restart_matches_continuous_valid_run(family: str, tmp_path) -> None:
    """A separate valid restart check, independent of any failure or cutback scenario."""
    base = _refinement_model(family, 1)
    load_path = [0.8, 0.9, 1.0]
    continuous_path = tmp_path / f"phase8-continuous-{family}.npz"
    store = NpzNonlinearCheckpointStore()
    parameters = {
        **base.analysis.parameters,
        "kinematics": "corotational_j2",
        "corotational_formulation": CORRECTED_COROTATIONAL_J2,
        "j2_corotational_tangent": "analytic_experimental",
        "adaptive_load_steps": False,
        "load_path": load_path,
        "checkpoint_path": str(continuous_path),
        "checkpoint_interval": 1,
        "checkpoint_keep_steps": True,
    }
    model = replace(
        base,
        analysis=replace(base.analysis, parameters=parameters),
        loads=[replace(load, value=load.value * 0.25) for load in base.loads],
    )
    continuous = NonlinearStaticSolver(store).solve(model)
    assert continuous.status == "PASS"
    intermediate = tmp_path / f"phase8-continuous-{family}.step00000001.npz"
    assert intermediate.is_file()

    restart_model = replace(
        model,
        analysis=replace(
            model.analysis,
            parameters={
                **model.analysis.parameters,
                "checkpoint_path": str(tmp_path / f"phase8-restarted-{family}.npz"),
                "restart_from": str(intermediate),
            },
        ),
    )
    resumed = NonlinearStaticSolver(store).solve(restart_model)
    assert resumed.status == "PASS"
    assert resumed.solver["restart_step"] == 1
    assert resumed.solver["tangent_strategy_version"] == CORRECTED_TANGENT_POLAR_ANALYTIC_VERSION
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-11, atol=1.0e-12)
    assert deterministic_state_digest(resumed.material_states) == deterministic_state_digest(continuous.material_states)
    assert resumed.solver["load_path"] == continuous.solver["load_path"]


@pytest.mark.parametrize("family", ("TET4", "HEX20"))
def test_phase8_inadmissible_guard_state_is_refused_without_retry(
    family: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """The archived guard-triggering fixed load is rejected with accepted state restored."""
    base = _refinement_model(family, 1)
    parameters = {key: value for key, value in base.analysis.parameters.items() if key != "load_path"}
    parameters.update(
        {
            "kinematics": "corotational_j2",
            "corotational_formulation": CORRECTED_COROTATIONAL_J2,
            "j2_corotational_tangent": "analytic_experimental",
            "corotational_guard_diagnostics": True,
            "adaptive_load_steps": False,
            "load_steps": 1,
            "load_path": [1.0],
            "max_iterations": 40,
            "tolerance": 1.0e-8,
        }
    )
    model = replace(
        base,
        analysis=replace(base.analysis, parameters=parameters),
    )
    rollbacks: list[dict[str, object]] = []
    original_rollback = NonlinearStateTransaction.rollback

    def record_refusal(transaction):
        before = transaction.accepted_state.digest
        original_rollback(transaction)
        rollbacks.append(
            {
                "rollback_invoked": True,
                "accepted_digest_before": before,
                "accepted_digest_after": transaction.accepted_state.digest,
                "trial_cleared": transaction.trial_state is None,
            }
        )
        return None

    monkeypatch.setattr(NonlinearStateTransaction, "rollback", record_refusal)
    caplog.set_level(logging.WARNING, logger="solveur.nonlinear.corotational_guard")
    with pytest.raises(NumericalConvergenceError) as raised:
        NonlinearStaticSolver().solve(model)

    assert raised.value.reason == NonlinearFailureReason.INVALID_ELEMENT
    assert len(rollbacks) == 1
    assert rollbacks[0]["rollback_invoked"] is True
    assert rollbacks[0]["accepted_digest_before"] == rollbacks[0]["accepted_digest_after"]
    assert rollbacks[0]["trial_cleared"] is True

    marker = "QF_COROTATIONAL_GUARD "
    records = [
        record for record in caplog.records
        if record.name == "solveur.nonlinear.corotational_guard" and marker in record.getMessage()
    ]
    assert records, "the opt-in guard refusal should emit a structured diagnostic"
    events = [json.loads(record.getMessage().split(marker, 1)[1]) for record in records]
    assert any(
        event["family"] == family
        and event["increment"] == 1
        and event["norm_u_minus_i_fro"] > event["limit_u_minus_i_fro"]
        for event in events
    ), events
