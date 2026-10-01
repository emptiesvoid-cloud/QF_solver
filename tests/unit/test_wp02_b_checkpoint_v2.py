"""Focused schema-v2 checkpoint and serialization foundation tests."""

from __future__ import annotations

import json
from copy import deepcopy

import numpy as np
import pytest

from solveur.core.errors import InputValidationError, NumericalConvergenceError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.checkpoint import (
    NonlinearCheckpointV2,
    build_state_topology,
    model_signature_v2,
)
from solveur.core.nonlinear.contracts import NonlinearFailureReason
from solveur.core.nonlinear.state import NonlinearState, deterministic_state_digest
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore


def _state(*, ordered: bool = True, contact: dict | None = None) -> NonlinearState:
    material = {
        3: [
            {
                "plastic_strain": np.array([0.1, -0.05, -0.05], dtype=np.float32),
                "nested": ("ip", np.array([[1, 2]], dtype=np.int16)),
            }
        ],
        1: [{"equivalent_plastic_strain": np.float64(0.01)}],
    }
    continuation = {
        "radius": np.float32(0.25),
        "previous_du": np.array([0.1, 0.2], dtype=np.float32),
        "previous_dlambda": np.float64(0.05),
    }
    if not ordered:
        material = {key: material[key] for key in reversed(list(material))}
        continuation = {key: continuation[key] for key in reversed(list(continuation))}
    return NonlinearState(
        displacement=np.array([1.0, 2.0, 3.0], dtype=np.float32),
        load_factor=np.float64(0.5),
        material_state=material,
        contact_state=contact or {},
        continuation_state=continuation,
        accepted_increment_metadata={"accepted_step": 2, "attempt": 0},
    )


def _checkpoint(state: NonlinearState | None = None) -> NonlinearCheckpointV2:
    state = state or _state()
    return NonlinearCheckpointV2.from_state(
        model_signature="v2-test-model",
        completed_step=2,
        state=state,
        state_topology=build_state_topology(None, state),
    )


def _write_v1(path, *, continuation: dict | None = None) -> None:
    metadata = {
        "schema_version": 1,
        "model_signature": "legacy-model",
        "completed_step": 2,
        "load_factor": 0.5,
        "material_states": {"0": [{"equivalent_plastic_strain": 0.01}]},
        "continuation_state": continuation or {},
    }
    np.savez_compressed(
        path,
        metadata_json=json.dumps(metadata, sort_keys=True),
        displacement=np.array([1.0, 2.0, 3.0]),
    )


def _rewrite_metadata(path, mutate) -> None:
    with np.load(path, allow_pickle=False) as data:
        metadata = json.loads(str(data["metadata_json"].item()))
    mutate(metadata)
    np.savez_compressed(path, metadata_json=json.dumps(metadata, sort_keys=True, allow_nan=False))


def _accepted_state_entry(metadata: dict, name: str) -> dict:
    for key, value in metadata["accepted_state"]["entries"]:
        if key["type"] == "str" and key["value"] == name:
            return value
    raise AssertionError(name)


def _contact_model(friction: float) -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        elements=[],
        materials={},
        contacts=[
            {
                "name": "support",
                "slave_node": 3,
                "master_nodes": [0, 1, 2],
                "friction_coefficient": friction,
                "tangential_stiffness": 1.0 if friction else None,
            }
        ],
    )


def test_t02b_01_v2_simple_accepted_state_round_trip(tmp_path) -> None:
    path = tmp_path / "state.npz"
    store = NpzNonlinearCheckpointStore()
    store.save(path, _checkpoint())
    loaded = store.load(path)
    assert loaded.schema_version == 2
    assert loaded.completed_step == 2
    np.testing.assert_array_equal(loaded.displacement, _state().displacement)


def test_t02b_02_displacement_dtype_and_shape_preserved(tmp_path) -> None:
    path = tmp_path / "state.npz"
    state = _state()
    NpzNonlinearCheckpointStore().save(path, _checkpoint(state))
    loaded = NpzNonlinearCheckpointStore().load(path).accepted_state
    assert loaded.displacement.dtype == np.dtype(np.float32)
    assert loaded.displacement.shape == (3,)


def test_t02b_03_nested_material_numpy_state_preserved(tmp_path) -> None:
    path = tmp_path / "state.npz"
    NpzNonlinearCheckpointStore().save(path, _checkpoint())
    value = NpzNonlinearCheckpointStore().load(path).accepted_state.material_state[3][0]
    assert value["plastic_strain"].dtype == np.dtype(np.float32)
    assert value["nested"][1].dtype == np.dtype(np.int16)


def test_t02b_04_empty_contact_state_round_trip(tmp_path) -> None:
    path = tmp_path / "state.npz"
    NpzNonlinearCheckpointStore().save(path, _checkpoint())
    assert NpzNonlinearCheckpointStore().load(path).contact_state == {}


def test_t02b_05_non_empty_synthetic_contact_state_round_trip(tmp_path) -> None:
    path = tmp_path / "state.npz"
    state = _state(contact={"pair-1": {"active": True, "gap": np.float32(-0.01)}})
    NpzNonlinearCheckpointStore().save(path, _checkpoint(state))
    loaded = NpzNonlinearCheckpointStore().load(path).contact_state
    assert loaded["pair-1"]["active"] is True
    assert loaded["pair-1"]["gap"] == pytest.approx(-0.01)


def test_t02b_06_continuation_state_round_trip(tmp_path) -> None:
    path = tmp_path / "state.npz"
    NpzNonlinearCheckpointStore().save(path, _checkpoint())
    loaded = NpzNonlinearCheckpointStore().load(path).continuation_state
    assert loaded["previous_du"].dtype == np.dtype(np.float32)
    assert loaded["previous_dlambda"] == np.float64(0.05)


def test_t02b_07_accepted_metadata_round_trip(tmp_path) -> None:
    path = tmp_path / "state.npz"
    NpzNonlinearCheckpointStore().save(path, _checkpoint())
    assert NpzNonlinearCheckpointStore().load(path).accepted_increment_metadata == {
        "accepted_step": 2,
        "attempt": 0,
    }


def test_t02b_08_component_digests_identical_after_round_trip(tmp_path) -> None:
    path = tmp_path / "state.npz"
    checkpoint = _checkpoint()
    NpzNonlinearCheckpointStore().save(path, checkpoint)
    assert NpzNonlinearCheckpointStore().load(path).component_digests == checkpoint.component_digests


def test_t02b_09_composite_digest_identical_after_round_trip(tmp_path) -> None:
    path = tmp_path / "state.npz"
    checkpoint = _checkpoint()
    NpzNonlinearCheckpointStore().save(path, checkpoint)
    assert NpzNonlinearCheckpointStore().load(path).composite_digest == checkpoint.composite_digest


def test_t02b_10_changed_persisted_component_is_state_corruption(tmp_path) -> None:
    path = tmp_path / "state.npz"
    NpzNonlinearCheckpointStore().save(path, _checkpoint())

    def mutate(metadata):
        metadata["component_digests"]["load_factor"] = "0" * 64

    _rewrite_metadata(path, mutate)
    with pytest.raises(NumericalConvergenceError) as caught:
        NpzNonlinearCheckpointStore().load(path)
    assert caught.value.reason is NonlinearFailureReason.STATE_CORRUPTION


def test_t02b_11_corrupt_truncated_npz_is_rejected(tmp_path) -> None:
    path = tmp_path / "broken.npz"
    path.write_bytes(b"truncated")
    with pytest.raises(InputValidationError, match="corrupted"):
        NpzNonlinearCheckpointStore().load(path)


def test_t02b_12_unsupported_schema_is_rejected(tmp_path) -> None:
    path = tmp_path / "unsupported.npz"
    np.savez_compressed(path, metadata_json=json.dumps({"schema_version": 99}))
    with pytest.raises(InputValidationError, match="Unsupported"):
        NpzNonlinearCheckpointStore().load(path)


def test_t02b_13_non_finite_persisted_state_is_state_corruption(tmp_path) -> None:
    path = tmp_path / "nonfinite.npz"
    NpzNonlinearCheckpointStore().save(path, _checkpoint())

    def mutate(metadata):
        _accepted_state_entry(metadata, "load_factor").update(type="float", value="nan")

    _rewrite_metadata(path, mutate)
    with pytest.raises(NumericalConvergenceError) as caught:
        NpzNonlinearCheckpointStore().load(path)
    assert caught.value.reason is NonlinearFailureReason.STATE_CORRUPTION


def test_t02b_14_wrong_model_signature_is_rejected(tmp_path) -> None:
    path = tmp_path / "state.npz"
    NpzNonlinearCheckpointStore().save(path, _checkpoint())
    with pytest.raises(InputValidationError, match="signature"):
        NpzNonlinearCheckpointStore().load(path, expected_model_signature="other")


def test_t02b_15_wrong_dof_topology_is_rejected(tmp_path) -> None:
    path = tmp_path / "state.npz"
    NpzNonlinearCheckpointStore().save(path, _checkpoint())
    with pytest.raises(InputValidationError, match="dofs|DOF"):
        NpzNonlinearCheckpointStore().load(path, expected_dofs=4)


def test_t02b_16_wrong_material_topology_is_rejected(tmp_path) -> None:
    path = tmp_path / "state.npz"
    checkpoint = _checkpoint()
    NpzNonlinearCheckpointStore().save(path, checkpoint)
    expected = deepcopy(checkpoint.state_topology)
    expected["material"]["entries"].append(
        {"key_type": "int", "element_id": 99, "integration_point_count": 1}
    )
    with pytest.raises(InputValidationError, match="topology"):
        NpzNonlinearCheckpointStore().load(path, expected_topology=expected)


def test_t02b_17_safe_contact_free_v1_loads_successfully(tmp_path) -> None:
    path = tmp_path / "legacy.npz"
    _write_v1(path)
    loaded = NpzNonlinearCheckpointStore().load(path)
    assert loaded.schema_version == 2
    assert loaded.migration_metadata["source_schema_version"] == 1
    assert loaded.contact_state == {}


def test_t02b_18_v1_migration_has_explicit_metadata(tmp_path) -> None:
    path = tmp_path / "legacy.npz"
    _write_v1(path, continuation={"radius": 0.25})
    loaded = NpzNonlinearCheckpointStore().load(path)
    assert loaded.migration_metadata == {
        "source_schema_version": 1,
        "bounded_contact_policy": "contact-free-or-stateless-only",
    }
    assert loaded.accepted_increment_metadata["historical_metadata_available"] is False


def test_t02b_19_stateful_contact_v1_is_rejected(tmp_path) -> None:
    path = tmp_path / "legacy.npz"
    _write_v1(path)
    with pytest.raises(InputValidationError, match="stateful contact"):
        NpzNonlinearCheckpointStore().load(path, model=_contact_model(0.3))


def test_t02b_20_v1_loaded_state_writes_as_v2(tmp_path) -> None:
    source = tmp_path / "legacy.npz"
    target = tmp_path / "v2.npz"
    _write_v1(source)
    store = NpzNonlinearCheckpointStore()
    store.save(target, store.load(source))
    with np.load(target, allow_pickle=False) as data:
        metadata = json.loads(str(data["metadata_json"].item()))
    assert metadata["schema_version"] == 2


def test_t02b_21_failed_temp_write_preserves_previous_canonical(tmp_path, monkeypatch) -> None:
    path = tmp_path / "state.npz"
    store = NpzNonlinearCheckpointStore()
    store.save(path, _checkpoint())
    original = path.read_bytes()

    def fail(*args, **kwargs):
        raise OSError("injected write failure")

    monkeypatch.setattr(np, "savez_compressed", fail)
    with pytest.raises(NumericalConvergenceError) as caught:
        store.save(path, _checkpoint(_state(contact={"new": 1})))
    assert caught.value.reason is NonlinearFailureReason.CHECKPOINT_FAILURE
    assert path.read_bytes() == original


def test_t02b_22_successful_save_leaves_no_temp_artifact(tmp_path) -> None:
    path = tmp_path / "state.npz"
    NpzNonlinearCheckpointStore().save(path, _checkpoint())
    assert not (tmp_path / ".state.npz.tmp.npz").exists()


def test_t02b_23_keep_step_canonical_and_retained_files_are_valid(tmp_path) -> None:
    store = NpzNonlinearCheckpointStore()
    paths = store.save(tmp_path / "state.npz", _checkpoint(), keep_step=True)
    assert len(paths) == 2
    for path in paths:
        assert store.load(path).composite_digest == store.load(paths[0]).composite_digest


def test_t02b_24_identical_writes_have_identical_metadata(tmp_path) -> None:
    store = NpzNonlinearCheckpointStore()
    first = tmp_path / "first.npz"
    second = tmp_path / "second.npz"
    checkpoint = _checkpoint()
    store.save(first, checkpoint)
    store.save(second, checkpoint)
    with np.load(first, allow_pickle=False) as data:
        first_metadata = str(data["metadata_json"].item())
    with np.load(second, allow_pickle=False) as data:
        second_metadata = str(data["metadata_json"].item())
    assert first_metadata == second_metadata


def test_t02b_25_pickle_object_array_is_rejected() -> None:
    with pytest.raises(TypeError, match="numeric dtype"):
        NonlinearState(np.zeros(3), material_state={0: [{"object": np.array([object()], dtype=object)}]})


def test_t02b_adversarial_mapping_order_does_not_change_digest() -> None:
    first = _state(ordered=True)
    second = _state(ordered=False)
    assert deterministic_state_digest(first.material_state) == deterministic_state_digest(second.material_state)
    assert first.digest == second.digest


def test_t02b_adversarial_int_and_string_keys_remain_distinct() -> None:
    assert deterministic_state_digest({1: "one"}) != deterministic_state_digest({"1": "one"})


def test_t02b_model_signature_excludes_storage_paths_but_includes_physical_contact() -> None:
    model = _contact_model(0.0)
    model.analysis.parameters.update(
        {
            "checkpoint_path": "one.npz",
            "checkpoint_interval": 1,
            "checkpoint_keep_steps": False,
            "restart_from": "old.npz",
        }
    )
    first = model_signature_v2(model)
    model.analysis.parameters["checkpoint_path"] = "two.npz"
    assert model_signature_v2(model) == first
    model.contacts[0] = type(model.contacts[0])(
        slave_node=model.contacts[0].slave_node,
        master_nodes=model.contacts[0].master_nodes,
        name=model.contacts[0].name,
        gap_tolerance=model.contacts[0].gap_tolerance,
        friction_coefficient=0.2,
        tangential_stiffness=1.0,
    )
    assert model_signature_v2(model) != first
