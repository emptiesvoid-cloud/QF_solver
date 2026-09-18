"""Lightweight WP06-D remediation tooling tests; no structural solves."""

from __future__ import annotations

import numpy as np
import pytest

from scripts.prepare_wp06d_requalification import (
    build_requalification_plan,
    require_owner_authorization,
    validate_phase1_authorization,
)
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
    assert plan["current_r1_execution_contract"] == "PHASE_0_PREPARATION_ONLY"
    assert plan["legacy_r1_runner"] == "QUARANTINED_STALE_MONITOR_AND_SHARED_OUTPUT_PATHS"
    assert plan["levels"] == ["M1", "M2", "M3"]
    assert "M1 and M2 pass" in plan["m3_gate"]
    with pytest.raises(PermissionError):
        require_owner_authorization(False)


def test_phase1_guard_rejects_missing_r2_contract_before_execution(tmp_path) -> None:
    with pytest.raises(PermissionError, match="No frozen WP06-D Phase-1 R2 execution contract"):
        validate_phase1_authorization(
            contract_path=tmp_path / "missing-contract.json",
            authorization_path=tmp_path / "missing-owner-grant.json",
            output_root=tmp_path / "new-run",
            source_sha="a" * 40,
            branch="codex/wp06-score-requalification",
            working_tree_clean=True,
        )
    assert not (tmp_path / "new-run").exists()


def test_phase1_guard_binds_owner_grant_and_refuses_existing_output(tmp_path) -> None:
    import hashlib
    import json

    contract_path = tmp_path / "contract.json"
    authorization_path = tmp_path / "owner.json"
    output_root = tmp_path / "run"
    source_sha = "a" * 40
    branch = "codex/wp06-score-requalification"
    contract = {
        "phase": "PHASE_1_EXECUTION",
        "status": "FROZEN_FOR_EXECUTION",
        "solver_policy_digest": "b" * 64,
        "execution_guard": {"structural_solves_enabled": True},
    }
    contract_bytes = (json.dumps(contract, sort_keys=True) + "\n").encode("utf-8")
    contract_path.write_bytes(contract_bytes)
    authorization = {
        "status": "AUTHORIZED",
        "owner_authorized": True,
        "branch": branch,
        "source_sha": source_sha,
        "contract_sha256": hashlib.sha256(contract_bytes).hexdigest(),
        "solver_policy_digest": contract["solver_policy_digest"],
        "authorized_levels": ["M1", "M2", "M3"],
        "m3_conditional_on_m1_m2_reference_replay": True,
    }
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")

    result = validate_phase1_authorization(
        contract_path=contract_path,
        authorization_path=authorization_path,
        output_root=output_root,
        source_sha=source_sha,
        branch=branch,
        working_tree_clean=True,
    )
    assert result["status"] == "AUTHORIZED_PREFLIGHT_PASS"
    assert result["authorized_levels"] == ["M1", "M2", "M3"]
    assert not output_root.exists()

    output_root.mkdir()
    with pytest.raises(FileExistsError, match="Refusing to reuse or overwrite"):
        validate_phase1_authorization(
            contract_path=contract_path,
            authorization_path=authorization_path,
            output_root=output_root,
            source_sha=source_sha,
            branch=branch,
            working_tree_clean=True,
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("dirty", "clean working tree"),
        ("sha", "source_sha"),
        ("branch", "branch"),
        ("digest", "contract_sha256"),
    ],
)
def test_phase1_guard_rejects_provenance_drift(tmp_path, mutation: str, message: str) -> None:
    import hashlib
    import json

    contract_path = tmp_path / "contract.json"
    authorization_path = tmp_path / "owner.json"
    source_sha = "a" * 40
    branch = "codex/wp06-score-requalification"
    contract = {
        "phase": "PHASE_1_EXECUTION",
        "status": "FROZEN_FOR_EXECUTION",
        "solver_policy_digest": "c" * 64,
        "execution_guard": {"structural_solves_enabled": True},
    }
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    authorization = {
        "status": "AUTHORIZED",
        "owner_authorized": True,
        "branch": branch,
        "source_sha": source_sha,
        "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
        "solver_policy_digest": contract["solver_policy_digest"],
        "authorized_levels": ["M1", "M2", "M3"],
        "m3_conditional_on_m1_m2_reference_replay": True,
    }
    if mutation == "sha":
        authorization["source_sha"] = "d" * 40
    elif mutation == "branch":
        authorization["branch"] = "wrong-branch"
    elif mutation == "digest":
        authorization["contract_sha256"] = "e" * 64
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")

    with pytest.raises(PermissionError, match=message):
        validate_phase1_authorization(
            contract_path=contract_path,
            authorization_path=authorization_path,
            output_root=tmp_path / "new-run",
            source_sha=source_sha,
            branch=branch,
            working_tree_clean=(mutation != "dirty"),
        )


def test_legacy_r1_runner_entrypoint_is_quarantined(monkeypatch, capsys) -> None:
    from scripts import run_wp06d_phase1

    def forbidden_solve(*args, **kwargs):
        raise AssertionError("quarantined runner must not reach a structural solve")

    monkeypatch.setattr(run_wp06d_phase1, "_run_level", forbidden_solve)
    assert run_wp06d_phase1.main() == 2
    assert '"status": "BLOCKED_STALE_R1_RUNNER"' in capsys.readouterr().out
