from __future__ import annotations

import json
from dataclasses import replace

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.checkpoint import (
    NonlinearCheckpointSession,
    _checkpoint_identity_metadata,
    _signature_payload,
    model_signature_v2,
)
from solveur.core.nonlinear.state import (
    NonlinearState,
    NonlinearStateTransaction,
    checkpoint_acceptance_status,
    mark_checkpoint_state_accepted,
)
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.elements.discrete import ConcentratedMass, SpringDefinition
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from tests.unit.test_analysis_features import elastoplastic_tet4_model


def _v1_file(path, model: FiniteElementModel, store: NpzNonlinearCheckpointStore) -> str:
    legacy_signature = store.signature(_signature_payload(model))
    metadata = {
        "schema_version": 1,
        "model_signature": legacy_signature,
        "completed_step": 1,
        "load_factor": 0.5,
        "material_states": {"0": [{"equivalent_plastic_strain": 0.0}]},
        "continuation_state": {},
    }
    np.savez_compressed(
        path,
        metadata_json=json.dumps(metadata, sort_keys=True),
        displacement=np.zeros(model.dof_manager().ndof),
    )
    return legacy_signature


def _accepted_state(model: FiniteElementModel, step: int = 1) -> NonlinearState:
    state = NonlinearState(
        displacement=np.zeros(model.dof_manager().ndof),
        load_factor=0.5,
        material_state={},
        continuation_state={"accepted_step": step},
        accepted_increment_metadata={"step": step},
    )
    mark_checkpoint_state_accepted(state)
    return state


@pytest.mark.parametrize("mutation", ["mass", "spring"])
def test_v1_identity_omission_never_authorizes_restart_after_discrete_mutation(tmp_path, mutation: str) -> None:
    model = elastoplastic_tet4_model()
    store = NpzNonlinearCheckpointStore()
    path = tmp_path / f"legacy-{mutation}.npz"
    legacy_signature = _v1_file(path, model, store)

    if mutation == "mass":
        model.concentrated_masses.append(ConcentratedMass(node=0, mass=2.0))
    else:
        model.springs.append(SpringDefinition(node_a=0, dofs=("UX",), stiffness=((250.0,),)))

    # This reproduces why comparing only the old signature is insufficient.
    assert store.signature(_signature_payload(model)) == legacy_signature
    with pytest.raises(InputValidationError, match="UNPROVEN.*FAIL_CLOSED"):
        store.load(
            path,
            model=model,
            expected_legacy_model_signature=store.signature(_signature_payload(model)),
        )
    assert store.read_legacy_v1(path).schema_version == 1


@pytest.mark.parametrize("mutation", ["mass", "spring"])
def test_v2_model_identity_changes_for_discrete_physics(mutation: str) -> None:
    model = elastoplastic_tet4_model()
    original = model_signature_v2(model)
    if mutation == "mass":
        model.concentrated_masses.append(ConcentratedMass(node=0, mass=2.0))
    else:
        model.springs.append(SpringDefinition(node_a=0, dofs=("UX",), stiffness=((250.0,),)))
    assert model_signature_v2(model) != original


@pytest.mark.parametrize("mutation", ["material", "boundary", "mesh", "load"])
def test_v2_model_identity_changes_for_core_physical_inputs(mutation: str) -> None:
    model = elastoplastic_tet4_model()
    original = model_signature_v2(model)
    if mutation == "material":
        material_name = model.elements[0].material
        model.materials[material_name]["E"] *= 1.01
    elif mutation == "boundary":
        model.fixed_dofs.append(type(model.fixed_dofs[0])(node=0, dofs=("RX",)))
    elif mutation == "mesh":
        model.nodes[0, 0] += 0.01
    else:
        model.loads[0] = replace(model.loads[0], value=1.01 * model.loads[0].value)
    assert model_signature_v2(model) != original


def test_load_identity_is_separate_from_operator_identity() -> None:
    model = elastoplastic_tet4_model()
    original = _checkpoint_identity_metadata(model)["identity_digests"]
    model.loads[0] = replace(model.loads[0], value=1.01 * model.loads[0].value)
    changed = _checkpoint_identity_metadata(model)["identity_digests"]
    assert changed["operator_identity"] == original["operator_identity"]
    assert changed["load_identity"] != original["load_identity"]


def test_trial_state_cannot_be_checkpointed_and_commit_attests_atomically(tmp_path) -> None:
    model = elastoplastic_tet4_model()
    path = tmp_path / "accepted.npz"
    model.analysis.parameters.update({"checkpoint_path": str(path), "checkpoint_interval": 1})
    store = NpzNonlinearCheckpointStore()
    session = NonlinearCheckpointSession.create(model, 1, store)
    transaction = NonlinearStateTransaction(_accepted_state(model, step=0))

    trial = transaction.begin_trial()
    trial.accepted_increment_metadata["step"] = 1
    trial.continuation_state["accepted_step"] = 1
    assert checkpoint_acceptance_status(trial) == "TRIAL"
    before = transaction.accepted_digest
    with pytest.raises(InputValidationError, match="not transaction-attested as ACCEPTED"):
        session.save_state(1, trial, final=True)
    assert transaction.accepted_digest == before
    assert not path.exists()

    accepted = transaction.commit()
    assert checkpoint_acceptance_status(accepted) == "ACCEPTED"
    session.save_state(1, accepted, final=True)
    loaded = store.load(path, model=model)
    assert checkpoint_acceptance_status(loaded.accepted_state) == "ACCEPTED"
    assert loaded.completed_step == 1


def test_scalar_checkpoint_writer_cannot_forge_accepted_state(tmp_path) -> None:
    model = elastoplastic_tet4_model()
    path = tmp_path / "unattested.npz"
    model.analysis.parameters["checkpoint_path"] = str(path)
    session = NonlinearCheckpointSession.create(model, 1, NpzNonlinearCheckpointStore())
    with pytest.raises(InputValidationError, match="cannot prove transaction acceptance"):
        session.save(1, 0.5, np.zeros(model.dof_manager().ndof), {}, {})
    assert not path.exists()


@pytest.mark.parametrize(
    ("metadata", "continuation", "expected_message"),
    [
        ({}, {}, "missing its accepted-step counter"),
        ({"step": 2}, {"accepted_step": 1}, "counters disagree"),
    ],
)
def test_accepted_checkpoint_counters_must_be_present_and_consistent(
    tmp_path, metadata, continuation, expected_message: str
) -> None:
    model = elastoplastic_tet4_model()
    path = tmp_path / "counter-check.npz"
    model.analysis.parameters["checkpoint_path"] = str(path)
    session = NonlinearCheckpointSession.create(model, 2, NpzNonlinearCheckpointStore())
    state = NonlinearState(
        displacement=np.zeros(model.dof_manager().ndof),
        load_factor=0.0,
        material_state={},
        continuation_state=continuation,
        accepted_increment_metadata=metadata,
    )
    mark_checkpoint_state_accepted(state)
    with pytest.raises(InputValidationError, match=expected_message):
        session.save_state(2, state, final=True)
    assert not path.exists()


def test_rollback_keeps_accepted_composite_and_retry_is_a_new_trial() -> None:
    initial = _accepted_state(elastoplastic_tet4_model(), step=1)
    transaction = NonlinearStateTransaction(initial)
    accepted_digest = transaction.accepted_digest
    first = transaction.begin_trial()
    first.material_state[0] = [{"plastic_strain": [0.1]}]
    transaction.rollback()
    assert transaction.accepted_digest == accepted_digest

    retry = transaction.begin_trial()
    assert checkpoint_acceptance_status(retry) == "TRIAL"
    assert retry.material_state == initial.material_state
    assert transaction.accepted_digest == accepted_digest
    transaction.rollback()


@pytest.mark.parametrize("mutation", ["mass", "spring", "material", "boundary", "mesh", "load"])
def test_v2_checkpoint_identity_bundle_binds_execution_and_model(tmp_path, mutation: str) -> None:
    model = elastoplastic_tet4_model()
    path = tmp_path / "identity.npz"
    model.analysis.parameters.update({"checkpoint_path": str(path), "checkpoint_interval": 1})
    store = NpzNonlinearCheckpointStore()
    session = NonlinearCheckpointSession.create(model, 1, store)
    session.save_state(1, _accepted_state(model), final=True)
    checkpoint = store.load(path, model=model)
    identities = checkpoint.migration_metadata["identity_digests"]
    assert checkpoint.migration_metadata["identity_status"] == "VERIFIED"
    assert set(identities) == {
        "physical_identity",
        "operator_identity",
        "constitutive_identity",
        "load_identity",
        "execution_identity",
        "checkpoint_schema_identity",
    }

    changed = elastoplastic_tet4_model()
    if mutation == "mass":
        changed.concentrated_masses.append(ConcentratedMass(node=0, mass=2.0))
    elif mutation == "spring":
        changed.springs.append(SpringDefinition(node_a=0, dofs=("UX",), stiffness=((250.0,),)))
    elif mutation == "material":
        material_name = changed.elements[0].material
        changed.materials[material_name]["E"] *= 1.01
    elif mutation == "boundary":
        changed.fixed_dofs.append(type(changed.fixed_dofs[0])(node=0, dofs=("RX",)))
    elif mutation == "mesh":
        changed.nodes[0, 0] += 0.01
    else:
        changed.loads[0] = replace(changed.loads[0], value=1.01 * changed.loads[0].value)
    with pytest.raises(InputValidationError, match="does not match"):
        store.load(path, model=changed)


def test_v2_checkpoint_metadata_identity_tampering_fails_integrity(tmp_path) -> None:
    model = elastoplastic_tet4_model()
    path = tmp_path / "tampered.npz"
    model.analysis.parameters.update({"checkpoint_path": str(path), "checkpoint_interval": 1})
    store = NpzNonlinearCheckpointStore()
    session = NonlinearCheckpointSession.create(model, 1, store)
    session.save_state(1, _accepted_state(model), final=True)
    with np.load(path, allow_pickle=False) as data:
        metadata = json.loads(str(data["metadata_json"].item()))
    metadata["migration_metadata"]["identity_status"] = "UNPROVEN"
    np.savez_compressed(path, metadata_json=json.dumps(metadata, sort_keys=True, allow_nan=False))
    with pytest.raises(NumericalConvergenceError, match="metadata integrity check failed"):
        store.load(path, model=model)


def test_zero_load_residual_uses_finite_absolute_floor_and_commits(tmp_path) -> None:
    model = elastoplastic_tet4_model()
    model.loads = [replace(load, value=0.0) for load in model.loads]
    model.analysis.parameters["load_steps"] = 1
    result = solve_model(model, enforce_policy=False)
    first_step = result.solver["steps"][0]
    assert first_step["residual_norm"] == pytest.approx(0.0)
    assert first_step["relative_residual"] == pytest.approx(0.0)
    assert first_step["state_committed"] is True


def test_max_iterations_is_reported_as_nonconvergence_not_acceptance() -> None:
    model = elastoplastic_tet4_model()
    model.analysis.parameters.update({"load_steps": 1, "max_iterations": 1})
    with pytest.raises(NumericalConvergenceError) as caught:
        solve_model(model, enforce_policy=False)
    assert caught.value.reason is NonlinearFailureReason.MAX_ITERATIONS
    assert caught.value.to_dict()["converged"] is False
