"""Tests for transient checkpoint persistence and restart controls."""

from __future__ import annotations

import numpy as np
import pytest

from solveur.core.dynamic_checkpoint import DynamicCheckpoint, DynamicCheckpointSettings
from solveur.core.errors import InputValidationError
from solveur.io.dynamic_checkpoint import NpzDynamicCheckpointStore


def test_npz_checkpoint_round_trip_and_versioned_copy(tmp_path) -> None:
    store = NpzDynamicCheckpointStore()
    checkpoint = DynamicCheckpoint(
        model_signature="abc",
        completed_step=2,
        time=0.2,
        time_step=0.1,
        beta=0.25,
        gamma=0.5,
        initial_energy=3.0,
        displacement=np.array([1.0, 2.0]),
        velocity=np.array([3.0, 4.0]),
        acceleration=np.array([5.0, 6.0]),
    )
    paths = store.save(tmp_path / "state.npz", checkpoint, keep_step=True)
    assert [path.name for path in paths] == ["state.npz", "state.step00000002.npz"]
    loaded = store.load(paths[1])
    assert loaded.model_signature == "abc"
    assert loaded.completed_step == 2
    np.testing.assert_array_equal(loaded.displacement, checkpoint.displacement)


def test_corrupted_checkpoint_is_an_input_error(tmp_path) -> None:
    path = tmp_path / "broken.npz"
    path.write_bytes(b"not-an-npz")
    with pytest.raises(InputValidationError, match="corrupted"):
        NpzDynamicCheckpointStore().load(path)


@pytest.mark.parametrize(
    "parameters",
    [
        {"checkpoint_interval": 2},
        {"checkpoint_path": "state.json"},
        {"checkpoint_path": "state.npz", "checkpoint_interval": 0},
        {"checkpoint_keep_steps": True},
    ],
)
def test_invalid_checkpoint_settings_are_rejected(parameters) -> None:
    with pytest.raises(InputValidationError):
        DynamicCheckpointSettings.from_parameters(parameters, 4)
