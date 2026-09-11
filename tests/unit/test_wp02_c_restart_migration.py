"""Focused fixed/adaptive schema-v2 restart migration checks."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.nonlinear.checkpoint import (
    NonlinearCheckpoint,
    NonlinearCheckpointV2,
    NonlinearCheckpointSession,
    NonlinearCheckpointSettings,
    _signature_payload,
    migrate_v1_checkpoint,
)
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.material_state import initial_material_states
from solveur.core.nonlinear.state import NonlinearState, deterministic_state_digest
from solveur.core.model import FiniteElementModel
from solveur.contact.entities import FrictionlessContact
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from solveur.verification.robustness_nonlinear_solids import _refinement_model
from tests.unit.test_analysis_features import elastoplastic_tet4_model
from tests.unit.test_geometric_nonlinear_public import _model as geometric_tet4_model


def _fixed_model(method: str = "newton_raphson") -> FiniteElementModel:
    model = elastoplastic_tet4_model()
    model.analysis = replace(model.analysis, method=method)
    return model


def _adaptive_model() -> FiniteElementModel:
    model = _fixed_model("newton_line_search")
    model.analysis.parameters.update(
        {
            "adaptive_load_steps": True,
            "load_steps": 2,
            "initial_load_increment": 0.25,
            "min_load_increment": 0.05,
            "max_load_increment": 0.5,
            "max_cutbacks": 8,
        }
    )
    return model


def _geometric_hex8_model() -> FiniteElementModel:
    nodes = np.asarray(
        [
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
            [0.0, 1.0, 1.0],
        ]
    )
    fixed = np.flatnonzero(np.isclose(nodes[:, 0], 0.0))
    loaded = np.flatnonzero(np.isclose(nodes[:, 0], 1.0))
    return FiniteElementModel.from_raw(
        nodes=nodes.tolist(),
        elements=[{"type": "HEX8", "nodes": list(range(8)), "material": "solid"}],
        materials={"solid": {"type": "isotropic_3d", "E": 1.0e6, "nu": 0.3}},
        fixed_dofs=[{"node": int(node), "dofs": ["UX", "UY", "UZ"]} for node in fixed],
        loads=[{"node": int(node), "dof": "UX", "value": 1.0 / len(loaded)} for node in loaded],
        analysis={
            "type": "geometric_nonlinear_static",
            "method": "newton_raphson",
            "parameters": {"load_increments": 6},
        },
    )


def _configure_checkpoint(model: FiniteElementModel, path: Path, *, interval: int = 1) -> None:
    model.analysis.parameters.update(
        {
            "checkpoint_path": str(path),
            "checkpoint_interval": interval,
            "checkpoint_keep_steps": True,
        }
    )


def _fixed_restart_pair(tmp_path: Path, method: str = "newton_raphson"):
    model = _fixed_model(method)
    _configure_checkpoint(model, tmp_path / "continuous.npz", interval=2)
    continuous = solve_model(model)
    intermediate = tmp_path / "continuous.step00000002.npz"
    assert intermediate.is_file()
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "restarted.npz"),
            "restart_from": str(intermediate),
            "checkpoint_keep_steps": False,
        }
    )
    resumed = solve_model(restarted)
    return continuous, resumed, intermediate


def _adaptive_restart_pair(tmp_path: Path):
    model = _adaptive_model()
    _configure_checkpoint(model, tmp_path / "adaptive.npz")
    continuous = solve_model(model)
    intermediate = tmp_path / "adaptive.step00000002.npz"
    assert intermediate.is_file()
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "adaptive-restarted.npz"),
            "restart_from": str(intermediate),
            "checkpoint_keep_steps": False,
        }
    )
    resumed = solve_model(restarted)
    return continuous, resumed, intermediate


def _write_v1(path: Path, model: FiniteElementModel, checkpoint: NonlinearCheckpoint) -> None:
    metadata = {
        "schema_version": 1,
        "model_signature": NpzNonlinearCheckpointStore().signature(_signature_payload(model)),
        "completed_step": checkpoint.completed_step,
        "load_factor": checkpoint.load_factor,
        "material_states": checkpoint.material_states,
        "continuation_state": checkpoint.continuation_state,
    }
    np.savez_compressed(
        path,
        metadata_json=json.dumps(metadata, sort_keys=True),
        displacement=np.asarray(checkpoint.displacement),
    )


def _tamper_v2(path: Path, mutate) -> None:
    with np.load(path, allow_pickle=False) as data:
        metadata = json.loads(str(data["metadata_json"].item()))
    mutate(metadata)
    np.savez_compressed(path, metadata_json=json.dumps(metadata, sort_keys=True))


def test_t02c_01_fixed_v2_restart_restores_exact_composite_digest(tmp_path: Path) -> None:
    _, _, intermediate = _fixed_restart_pair(tmp_path)
    checkpoint = NpzNonlinearCheckpointStore().load(intermediate)
    assert checkpoint.composite_digest == checkpoint.accepted_state.digest
    assert checkpoint.component_digests == checkpoint.accepted_state.component_digests


def test_t02c_02_fixed_j2_continuous_vs_restart_equivalence(tmp_path: Path) -> None:
    continuous, resumed, _ = _fixed_restart_pair(tmp_path)
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-9, atol=1.0e-12)
    assert resumed.material_states == continuous.material_states


def test_t02c_03_fixed_modified_newton_continuous_vs_restart_equivalence(tmp_path: Path) -> None:
    continuous, resumed, _ = _fixed_restart_pair(tmp_path, method="modified_newton")
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-9, atol=1.0e-12)
    assert resumed.material_states == continuous.material_states


def test_t02c_04_fixed_geometric_tet4_continuous_vs_restart_equivalence(tmp_path: Path) -> None:
    model = geometric_tet4_model(increments=6)
    _configure_checkpoint(model, tmp_path / "tet4.npz", interval=2)
    continuous = solve_model(model, enforce_policy=False)
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {"checkpoint_path": str(tmp_path / "tet4-r.npz"), "restart_from": str(tmp_path / "tet4.step00000002.npz")}
    )
    resumed = solve_model(restarted, enforce_policy=False)
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-9, atol=1.0e-12)


def test_t02c_05_fixed_geometric_hex8_continuous_vs_restart_equivalence(tmp_path: Path) -> None:
    model = _geometric_hex8_model()
    _configure_checkpoint(model, tmp_path / "hex8.npz", interval=2)
    continuous = solve_model(model, enforce_policy=False)
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {"checkpoint_path": str(tmp_path / "hex8-r.npz"), "restart_from": str(tmp_path / "hex8.step00000002.npz")}
    )
    resumed = solve_model(restarted, enforce_policy=False)
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-9, atol=1.0e-12)


def test_t02c_06_fixed_penalty_contact_checkpoint_route_preserves_result(tmp_path: Path) -> None:
    model = _refinement_model("TET4", 1)
    model.contacts.append(FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4)))
    model.analysis.parameters.update({"contact_mode": "penalty", "contact_penalty": 1.0e6, "load_steps": 2})
    _configure_checkpoint(model, tmp_path / "contact.npz", interval=1)
    continuous = solve_model(model, enforce_policy=False)
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {"checkpoint_path": str(tmp_path / "contact-r.npz"), "restart_from": str(tmp_path / "contact.step00000001.npz")}
    )
    resumed = solve_model(restarted, enforce_policy=False)
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-9, atol=1.0e-12)


def test_t02c_07_adaptive_j2_continuous_vs_restart_equivalence(tmp_path: Path) -> None:
    continuous, resumed, _ = _adaptive_restart_pair(tmp_path)
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-9, atol=1.0e-12)
    assert resumed.material_states == continuous.material_states


def test_t02c_08_adaptive_geometric_tet4_continuous_vs_restart_equivalence(tmp_path: Path) -> None:
    model = geometric_tet4_model(increments=6)
    model.analysis.parameters.update(
        {"adaptive_load_steps": True, "initial_load_increment": 0.5, "min_load_increment": 0.05, "max_load_increment": 0.5}
    )
    _configure_checkpoint(model, tmp_path / "adaptive-tet4.npz")
    continuous = solve_model(model, enforce_policy=False)
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "adaptive-tet4-r.npz"),
            "restart_from": str(tmp_path / "adaptive-tet4.step00000001.npz"),
        }
    )
    resumed = solve_model(restarted, enforce_policy=False)
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-9, atol=1.0e-12)


def test_t02c_09_adaptive_geometric_hex8_continuous_vs_restart_equivalence(tmp_path: Path) -> None:
    model = _geometric_hex8_model()
    model.analysis.parameters.update(
        {"adaptive_load_steps": True, "initial_load_increment": 0.5, "min_load_increment": 0.05, "max_load_increment": 0.5}
    )
    _configure_checkpoint(model, tmp_path / "adaptive-hex8.npz")
    continuous = solve_model(model, enforce_policy=False)
    restarted = deepcopy(model)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "adaptive-hex8-r.npz"),
            "restart_from": str(tmp_path / "adaptive-hex8.step00000001.npz"),
        }
    )
    resumed = solve_model(restarted, enforce_policy=False)
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-9, atol=1.0e-12)


def test_t02c_10_restart_installs_load_factor(tmp_path: Path) -> None:
    _, _, intermediate = _fixed_restart_pair(tmp_path)
    checkpoint = NpzNonlinearCheckpointStore().load(intermediate)
    assert checkpoint.accepted_state.load_factor == pytest.approx(0.4)


def test_t02c_11_restart_installs_material_state_exactly(tmp_path: Path) -> None:
    _, _, intermediate = _fixed_restart_pair(tmp_path)
    checkpoint = NpzNonlinearCheckpointStore().load(intermediate)
    assert deterministic_state_digest(checkpoint.accepted_state.material_state) == checkpoint.component_digests[
        "material_state"
    ]


def test_t02c_12_restart_installs_contact_state_exactly(tmp_path: Path) -> None:
    state = NonlinearState(np.zeros(2), contact_state={"pair": {"active": True, "slip": np.array([1, 2])}})
    checkpoint = NonlinearCheckpointV2.from_state(
        model_signature="synthetic",
        completed_step=1,
        state=state,
    )
    path = tmp_path / "contact-state.npz"
    NpzNonlinearCheckpointStore().save(path, checkpoint)
    restored = NpzNonlinearCheckpointStore().load(path).accepted_state
    assert restored.contact_state["pair"]["active"] is True
    np.testing.assert_array_equal(restored.contact_state["pair"]["slip"], np.array([1, 2]))


def test_t02c_13_failed_restore_leaves_existing_state_unchanged(tmp_path: Path) -> None:
    model = _fixed_model()
    _configure_checkpoint(model, tmp_path / "state.npz")
    solve_model(model)
    initial = NonlinearState(np.ones(model.dof_manager().ndof), material_state=initial_material_states(model))
    before = initial.digest
    changed = deepcopy(model)
    changed.loads[0] = replace(changed.loads[0], value=changed.loads[0].value * 1.01)
    changed.analysis.parameters["restart_from"] = str(tmp_path / "state.npz")
    with pytest.raises(InputValidationError):
        solve_model(changed)
    assert initial.digest == before


def test_t02c_14_wrong_signature_rejected_before_installation(tmp_path: Path) -> None:
    model = _fixed_model()
    _configure_checkpoint(model, tmp_path / "state.npz")
    solve_model(model)
    changed = deepcopy(model)
    changed.loads[0] = replace(changed.loads[0], value=changed.loads[0].value * 1.01)
    changed.analysis.parameters["restart_from"] = str(tmp_path / "state.npz")
    with pytest.raises(InputValidationError, match="model signature"):
        solve_model(changed)


def test_t02c_15_wrong_material_topology_rejected_before_installation(tmp_path: Path) -> None:
    _, _, intermediate = _fixed_restart_pair(tmp_path)
    store = NpzNonlinearCheckpointStore()
    checkpoint = store.load(intermediate)
    session = NonlinearCheckpointSession(
        settings=NonlinearCheckpointSettings(None, 5, False, str(intermediate)),
        store=store,
        signature=checkpoint.model_signature,
        total_steps=5,
    )
    with pytest.raises(InputValidationError, match="material-state topology"):
        session.restore_state(NonlinearState(np.zeros(checkpoint.displacement.size), material_state={999: []}), load_factors=[0.2, 0.4, 0.6, 0.8, 1.0])


def test_t02c_16_digest_mismatch_rejected_before_installation(tmp_path: Path) -> None:
    _, _, intermediate = _fixed_restart_pair(tmp_path)
    _tamper_v2(intermediate, lambda metadata: metadata["component_digests"].update({"load_factor": "0" * 64}))
    with pytest.raises(NumericalConvergenceError) as error:
        NpzNonlinearCheckpointStore().load(intermediate)
    assert error.value.reason is NonlinearFailureReason.STATE_CORRUPTION


def test_t02c_17_supported_v1_restart_succeeds(tmp_path: Path) -> None:
    model = _fixed_model()
    _configure_checkpoint(model, tmp_path / "source.npz", interval=2)
    continuous = solve_model(model)
    source = NpzNonlinearCheckpointStore().load(tmp_path / "source.step00000002.npz")
    v1_path = tmp_path / "legacy.npz"
    _write_v1(
        v1_path,
        model,
        NonlinearCheckpoint(
            model_signature="legacy-placeholder",
            completed_step=source.completed_step,
            load_factor=source.load_factor,
            displacement=source.displacement,
            material_states=source.material_states,
        ),
    )
    restarted = deepcopy(model)
    restarted.analysis.parameters.update({"checkpoint_path": str(tmp_path / "v1-r.npz"), "restart_from": str(v1_path)})
    resumed = solve_model(restarted)
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-9, atol=1.0e-12)


def test_t02c_18_v1_resumed_analysis_writes_v2(tmp_path: Path) -> None:
    model = _fixed_model()
    _configure_checkpoint(model, tmp_path / "source.npz", interval=2)
    solve_model(model)
    source = NpzNonlinearCheckpointStore().load(tmp_path / "source.step00000002.npz")
    v1_path = tmp_path / "legacy.npz"
    _write_v1(v1_path, model, NonlinearCheckpoint("legacy-placeholder", source.completed_step, source.load_factor, source.displacement, source.material_states))
    restarted = deepcopy(model)
    restarted.analysis.parameters.update({"checkpoint_path": str(tmp_path / "v2.npz"), "restart_from": str(v1_path)})
    solve_model(restarted)
    assert NpzNonlinearCheckpointStore().load(tmp_path / "v2.npz").schema_version == 2


def test_t02c_19_ambiguous_contact_v1_restart_is_rejected() -> None:
    model = _refinement_model("TET4", 1)
    model.contacts.append(
        FrictionlessContact(slave_node=1, master_nodes=(0, 3, 4), friction_coefficient=0.2, tangential_stiffness=10.0)
    )
    legacy = NonlinearCheckpoint("legacy", 1, 1.0, np.zeros(model.dof_manager().ndof), {0: []})
    with pytest.raises(InputValidationError, match="stateful contact"):
        migrate_v1_checkpoint(legacy, model=model)


def test_t02c_20_checkpoint_written_only_after_accepted_increment(tmp_path: Path) -> None:
    model = _fixed_model()
    _configure_checkpoint(model, tmp_path / "accepted.npz", interval=1)
    solve_model(model)
    checkpoints = [NpzNonlinearCheckpointStore().load(path) for path in sorted(tmp_path.glob("accepted.step*.npz"))]
    assert checkpoints
    assert all(item.completed_step >= 1 for item in checkpoints)


def test_t02c_21_rejected_adaptive_increment_is_never_persisted(tmp_path: Path) -> None:
    model = _adaptive_model()
    _configure_checkpoint(model, tmp_path / "retry.npz", interval=1)
    from solveur.core.nonlinear.solver import NonlinearStaticSolver

    class RejectFirst(NonlinearStaticSolver):
        attempts = 0

        def _solve_load_step(self, *args, **kwargs):
            if self.attempts == 0:
                self.attempts += 1
                raise NumericalConvergenceError("synthetic retry", reason=NonlinearFailureReason.MAX_ITERATIONS)
            return super()._solve_load_step(*args, **kwargs)

    result = RejectFirst(checkpoint_store=NpzNonlinearCheckpointStore()).solve(model)
    assert result.solver["rejected_increments"] >= 1
    checkpoints = [NpzNonlinearCheckpointStore().load(path) for path in sorted(tmp_path.glob("retry.step*.npz"))]
    assert checkpoints and all(item.completed_step >= 1 for item in checkpoints)


def test_t02c_22_adaptive_retry_after_restart_begins_from_last_accepted_state(tmp_path: Path) -> None:
    continuous, resumed, intermediate = _adaptive_restart_pair(tmp_path)
    checkpoint = NpzNonlinearCheckpointStore().load(intermediate)
    assert resumed.solver["restart_step"] == checkpoint.completed_step
    np.testing.assert_allclose(resumed.displacements, continuous.displacements, rtol=1.0e-12, atol=1.0e-14)


def test_t02c_23_checkpoint_save_failure_does_not_alter_accepted_state(tmp_path: Path) -> None:
    class FailingStore(NpzNonlinearCheckpointStore):
        def save(self, *args, **kwargs):
            raise NumericalConvergenceError("save failed", reason=NonlinearFailureReason.CHECKPOINT_FAILURE)

    model = _fixed_model()
    model.analysis.parameters.update({"checkpoint_path": str(tmp_path / "state.npz"), "checkpoint_interval": 1})
    session = NonlinearCheckpointSession.create(model, 5, FailingStore())
    state = NonlinearState(np.zeros(model.dof_manager().ndof), material_state=initial_material_states(model))
    before = state.digest
    with pytest.raises(NumericalConvergenceError) as error:
        session.save_state(1, state)
    assert error.value.reason is NonlinearFailureReason.CHECKPOINT_FAILURE
    assert state.digest == before


def test_t02c_24_checkpoint_failure_does_not_trigger_physical_cutback(tmp_path: Path) -> None:
    class FailingStore(NpzNonlinearCheckpointStore):
        def save(self, *args, **kwargs):
            raise NumericalConvergenceError("save failed", reason=NonlinearFailureReason.CHECKPOINT_FAILURE)

    model = _adaptive_model()
    model.analysis.parameters["checkpoint_path"] = str(tmp_path / "state.npz")
    from solveur.core.nonlinear.solver import NonlinearStaticSolver

    with pytest.raises(NumericalConvergenceError) as error:
        NonlinearStaticSolver(checkpoint_store=FailingStore()).solve(model)
    assert error.value.reason is NonlinearFailureReason.CHECKPOINT_FAILURE
    assert error.value.reason is not NonlinearFailureReason.MIN_INCREMENT_REACHED


def test_t02c_25_identical_interrupted_restarted_runs_have_deterministic_terminal_digest(tmp_path: Path) -> None:
    first, resumed, intermediate = _fixed_restart_pair(tmp_path / "one")
    second, resumed_again, intermediate_again = _fixed_restart_pair(tmp_path / "two")
    assert NpzNonlinearCheckpointStore().load(intermediate).accepted_state.digest == NpzNonlinearCheckpointStore().load(
        intermediate_again
    ).accepted_state.digest
    np.testing.assert_allclose(first.displacements, second.displacements, rtol=1.0e-12, atol=1.0e-14)
    np.testing.assert_allclose(resumed.displacements, resumed_again.displacements, rtol=1.0e-12, atol=1.0e-14)
