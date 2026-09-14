"""Lightweight WP06-D remediation tooling tests; no structural solves."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.prepare_wp06d_requalification import build_requalification_plan, require_owner_authorization
from scripts.wp06_premerge_tools import (
    CROWN_NODE_SET,
    archive_accepted_state,
    mean_crown_uz,
    reconstruct_balance,
)
from solveur.core.errors import InputValidationError
from solveur.core.model import FiniteElementModel
from solveur.core.nonlinear.state import NonlinearState


def _model() -> FiniteElementModel:
    return FiniteElementModel.from_raw(
        nodes=[[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, -0.05, 0.20], [0.0, 0.05, 0.20], [0.0, 0.0, 0.25]],
        elements=[
            {"type": "TET4", "nodes": [0, 2, 3, 4], "material": "solid"},
            {"type": "TET4", "nodes": [1, 3, 2, 4], "material": "solid"},
        ],
        materials={"solid": {"type": "isotropic_3d", "E": 100.0, "nu": 0.3}},
        fixed_dofs=[
            {"node": 0, "dofs": ["UX", "UY", "UZ"]},
            {"node": 1, "dofs": ["UX", "UY", "UZ"]},
            {"node": 2, "dofs": ["UY"]},
            {"node": 3, "dofs": ["UY"]},
            {"node": 4, "dofs": ["UY"]},
        ],
        loads=[{"node": 4, "dof": "UZ", "value": -1.0}],
    )


def test_mean_crown_uz_is_frozen_deterministic_and_not_node4_only() -> None:
    model = _model()
    displacement = np.zeros(model.dof_manager().ndof)
    dofs = model.dof_manager()
    displacement[dofs.index(2, "UZ")] = -0.2
    displacement[dofs.index(3, "UZ")] = -0.4
    displacement[dofs.index(4, "UZ")] = -0.8
    assert CROWN_NODE_SET == (2, 3, 4)
    assert mean_crown_uz(displacement, model) == pytest.approx(0.4666666666666667)
    assert mean_crown_uz(displacement, model) != pytest.approx(0.8)
    with pytest.raises(InputValidationError):
        mean_crown_uz(displacement, model, crown_nodes=(4,))


def test_archive_contains_lossless_state_and_explicit_missing_metrics(tmp_path) -> None:
    model = _model()
    state = NonlinearState(displacement=np.zeros(model.dof_manager().ndof), load_factor=0.25)
    class Checkpoint:
        schema_version = 2
        state_schema_version = 1
        completed_step = 3
        accepted_state = state
        composite_digest = state.digest
        model_signature = "model"

    from scripts.wp06_premerge_tools import read_checkpoint  # local import keeps the test no-solve

    class Store:
        def load(self, path, **kwargs):
            return Checkpoint()

    checkpoint_path = tmp_path / "checkpoint.npz"
    checkpoint_path.write_bytes(b"test-double")
    snapshot = read_checkpoint(checkpoint_path, model=model, expected_dofs=state.displacement.size, store=Store())
    record = archive_accepted_state(snapshot, model, metrics={"newton_iterations": 4})
    assert record["accepted_displacement"] == [0.0] * state.displacement.size
    assert record["mean_crown_uz"] == 0.0
    assert record["metrics"]["newton_iterations"] == 4
    assert record["metrics"]["residual_norm"]["reason"] == "NOT_AVAILABLE_IN_ACCEPTED_STATE"


def test_archive_rejects_nonfinite_metric() -> None:
    model = _model()
    state = NonlinearState(displacement=np.zeros(model.dof_manager().ndof))
    from scripts.wp06_premerge_tools import CheckpointSnapshot

    snapshot = CheckpointSnapshot(2, 0, 0.0, state.displacement, {}, {}, {}, {}, state.digest, "model")
    with pytest.raises(InputValidationError):
        archive_accepted_state(snapshot, model, metrics={"residual_norm": float("inf")})


def test_checkpoint_reader_retries_only_legacy_keyword_mismatch(tmp_path) -> None:
    model = _model()
    state = NonlinearState(displacement=np.zeros(model.dof_manager().ndof))
    checkpoint_path = tmp_path / "checkpoint.npz"
    checkpoint_path.write_bytes(b"test-double")

    class Checkpoint:
        schema_version = 2
        state_schema_version = 1
        completed_step = 0
        accepted_state = state
        composite_digest = state.digest
        model_signature = "model"

    class LegacyStore:
        def load(self, path):
            return Checkpoint()

    from scripts.wp06_premerge_tools import read_checkpoint

    snapshot = read_checkpoint(checkpoint_path, model=model, store=LegacyStore())
    assert snapshot.schema_version == 2
    assert snapshot.displacement.flags.writeable is True


def test_independent_balance_reconstructs_force_and_moment_vectors() -> None:
    coordinates = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]], dtype=float)
    external = np.asarray([0.0, 0.0, -1.0, 0.0, 0.0, 0.0])
    internal = np.asarray([0.0, 0.0, 1.0, 0.0, 0.0, 0.0])
    result = reconstruct_balance(
        coordinates=coordinates,
        internal_force=internal,
        external_force=external,
        fixed_dof_indices=(0, 1, 2, 3, 4, 5),
    )
    assert result.external_resultant.tolist() == [0.0, 0.0, -1.0]
    assert result.reaction_resultant.tolist() == [0.0, 0.0, 2.0]
    assert result.force_pass is False
    assert result.moment_pass is True


def test_requalification_plan_is_guarded_and_m3_is_gated() -> None:
    plan = build_requalification_plan()
    assert plan["execution"] == "PREPARED_NOT_EXECUTED"
    assert plan["levels"] == ["M1", "M2", "M3"]
    assert "M1 and M2 pass" in plan["m3_gate"]
    with pytest.raises(PermissionError):
        require_owner_authorization(False)
