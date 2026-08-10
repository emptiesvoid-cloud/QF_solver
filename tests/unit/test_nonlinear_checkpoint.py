"""Tests for nonlinear static checkpoint persistence and restart."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace

import numpy as np
import pytest

from solveur.api import solve_model
from solveur.core.errors import InputValidationError
from solveur.core.nonlinear_checkpoint import NonlinearCheckpoint, NonlinearCheckpointSettings
from solveur.io.nonlinear_checkpoint import NpzNonlinearCheckpointStore
from tests.unit.test_analysis_features import elastoplastic_tet4_model


def test_nonlinear_checkpoint_round_trip_and_versioned_copy(tmp_path) -> None:
    checkpoint = NonlinearCheckpoint(
        model_signature="signature",
        completed_step=2,
        load_factor=0.5,
        displacement=np.array([1.0, 2.0, 3.0]),
        material_states={
            0: [{"equivalent_plastic_strain": 0.01, "plastic_strain": [0.1, -0.05, -0.05, 0, 0, 0]}]
        },
    )
    store = NpzNonlinearCheckpointStore()

    paths = store.save(tmp_path / "state.npz", checkpoint, keep_step=True)
    loaded = store.load(paths[1])

    assert [path.name for path in paths] == ["state.npz", "state.step00000002.npz"]
    assert loaded.completed_step == 2
    assert loaded.load_factor == 0.5
    assert loaded.material_states == checkpoint.material_states
    np.testing.assert_array_equal(loaded.displacement, checkpoint.displacement)


def test_corrupted_nonlinear_checkpoint_is_an_input_error(tmp_path) -> None:
    path = tmp_path / "broken.npz"
    path.write_bytes(b"not an npz")

    with pytest.raises(InputValidationError, match="corrupted"):
        NpzNonlinearCheckpointStore().load(path)


@pytest.mark.parametrize(
    "parameters",
    [
        {"checkpoint_interval": 2},
        {"checkpoint_path": "state.json"},
        {"checkpoint_path": "state.npz", "checkpoint_interval": 0},
        {"checkpoint_keep_steps": True},
    ],
)
def test_invalid_nonlinear_checkpoint_settings_are_rejected(parameters) -> None:
    with pytest.raises(InputValidationError):
        NonlinearCheckpointSettings.from_parameters(parameters, 4)


def test_nonlinear_restart_matches_continuous_cyclic_solution(tmp_path) -> None:
    continuous = elastoplastic_tet4_model()
    continuous.analysis.parameters["load_path"] = [0.5, 1.0, 0.0, -1.0, 0.0, 1.0]
    continuous.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "continuous.npz"),
            "checkpoint_interval": 2,
            "checkpoint_keep_steps": True,
        }
    )
    reference = solve_model(continuous)
    intermediate = tmp_path / "continuous.step00000002.npz"
    assert intermediate.is_file()

    restarted = deepcopy(continuous)
    restarted.analysis.parameters.update(
        {
            "checkpoint_path": str(tmp_path / "restarted.npz"),
            "restart_from": str(intermediate),
            "checkpoint_keep_steps": False,
        }
    )
    resumed = solve_model(restarted)

    np.testing.assert_allclose(resumed.displacements, reference.displacements, rtol=1.0e-12, atol=1.0e-14)
    assert resumed.material_states == reference.material_states
    assert resumed.solver["restart_step"] == 2
    assert resumed.solver["history_is_partial"] is True
    assert len(resumed.solver["steps"]) == 4
    assert resumed.solver["load_path"] == [0.5, 1.0, 0.0, -1.0, 0.0, 1.0]
    assert (tmp_path / "restarted.npz").is_file()


def test_nonlinear_restart_rejects_modified_physical_model(tmp_path) -> None:
    model = elastoplastic_tet4_model()
    model.analysis.parameters["checkpoint_path"] = str(tmp_path / "state.npz")
    solve_model(model)

    changed = deepcopy(model)
    changed.loads[0] = replace(changed.loads[0], value=1.01 * changed.loads[0].value)
    changed.analysis.parameters["restart_from"] = str(tmp_path / "state.npz")

    with pytest.raises(InputValidationError, match="does not match"):
        solve_model(changed)


def test_nonlinear_checkpoint_rejects_adaptive_continuation(tmp_path) -> None:
    model = elastoplastic_tet4_model()
    model.analysis.parameters.update(
        {"adaptive_load_steps": True, "checkpoint_path": str(tmp_path / "state.npz")}
    )

    with pytest.raises(InputValidationError, match="fixed load-control"):
        solve_model(model)
