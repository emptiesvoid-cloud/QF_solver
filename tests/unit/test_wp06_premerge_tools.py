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


def _phase1_git_fixture(tmp_path):
    import hashlib
    import json
    import subprocess

    repo = tmp_path / "repository"
    repo.mkdir()
    subprocess.run(["git", "init", "--quiet"], cwd=repo, check=True)
    subprocess.run(["git", "checkout", "--quiet", "-b", "wp06d-r2-test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "WP06 test"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "wp06-test@example.invalid"], cwd=repo, check=True)

    policy_path = repo / "src" / "solver_policy.py"
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text("POLICY = 'frozen'\n", encoding="utf-8")
    parent_contract_path = repo / "qualification" / "0_2_9" / "wp06d_structural_limit_point_contract.json"
    parent_contract_path.parent.mkdir(parents=True)
    parent_contract_path.write_text('{"contract_revision":"WP06D-R1"}\n', encoding="utf-8")
    subprocess.run(
        ["git", "add", "src/solver_policy.py", "qualification/0_2_9/wp06d_structural_limit_point_contract.json"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "commit", "--quiet", "-m", "freeze test policy source"], cwd=repo, check=True)
    policy_source_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    policy_file_hashes = {
        "src/solver_policy.py": hashlib.sha256(
            subprocess.check_output(
                ["git", "show", f"{policy_source_sha}:src/solver_policy.py"], cwd=repo
            )
        ).hexdigest()
    }
    policy_digest = hashlib.sha256(
        json.dumps(policy_file_hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    parent_contract_blob = subprocess.check_output(
        ["git", "show", f"{policy_source_sha}:qualification/0_2_9/wp06d_structural_limit_point_contract.json"],
        cwd=repo,
    )
    parent_contract_oid = subprocess.run(
        ["git", "rev-parse", f"{policy_source_sha}:qualification/0_2_9/wp06d_structural_limit_point_contract.json"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    contract_path = repo / "qualification" / "0_2_9" / "wp06d_r2_execution_contract.json"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract = {
        "contract_revision": "WP06D-R2",
        "phase": "PHASE_1_EXECUTION",
        "status": "FROZEN_FOR_EXECUTION",
        "provenance": {"governing_policy_source_sha": policy_source_sha},
        "parent_r1": {
            "contract_path": "qualification/0_2_9/wp06d_structural_limit_point_contract.json",
            "contract_sha256_at_execution": hashlib.sha256(parent_contract_blob).hexdigest(),
            "contract_git_blob_at_governing_source": parent_contract_oid,
        },
        "solver_policy_binding": {
            "source_sha": policy_source_sha,
            "source_file_sha256": policy_file_hashes,
            "policy_digest": policy_digest,
        },
        "execution_guard": {"structural_solves_enabled": True},
    }
    contract_bytes = (json.dumps(contract, sort_keys=True) + "\n").encode("utf-8")
    contract_path.write_bytes(contract_bytes)
    subprocess.run(["git", "add", str(contract_path.relative_to(repo))], cwd=repo, check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "freeze WP06-D R2 test contract"], cwd=repo, check=True)

    source_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    contract_blob = subprocess.check_output(
        ["git", "show", f"{source_sha}:qualification/0_2_9/wp06d_r2_execution_contract.json"],
        cwd=repo,
    )
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    authorization_path = tmp_path / "owner-grant.json"
    authorization = {
        "status": "AUTHORIZED",
        "owner_authorized": True,
        "contract_revision": "WP06D-R2",
        "branch": branch,
        "source_sha": source_sha,
        "contract_sha256": hashlib.sha256(contract_blob).hexdigest(),
        "policy_source_sha": policy_source_sha,
        "solver_policy_digest": policy_digest,
        "authorized_operations": ["PRODUCTION_STRUCTURAL", "INDEPENDENT_REFERENCE", "REPLAY"],
        "authorized_levels": ["M1", "M2", "M3"],
        "m3_conditional_on_m1_m2_reference_replay": True,
    }
    authorization_path.write_text(json.dumps(authorization), encoding="utf-8")
    return {
        "repo": repo,
        "contract_path": contract_path,
        "authorization_path": authorization_path,
        "output_root": repo / "qualification" / "0_2_9" / "wp06d_r2_runs" / "test-run",
        "source_sha": source_sha,
        "branch": branch,
        "authorization": authorization,
    }


def test_phase1_guard_binds_owner_grant_and_refuses_existing_output(tmp_path) -> None:
    fixture = _phase1_git_fixture(tmp_path)
    result = validate_phase1_authorization(
        contract_path=fixture["contract_path"],
        authorization_path=fixture["authorization_path"],
        output_root=fixture["output_root"],
        source_sha=fixture["source_sha"],
        branch=fixture["branch"],
        working_tree_clean=True,
    )
    assert result["status"] == "AUTHORIZED_PREFLIGHT_PASS"
    assert result["source_sha"] == fixture["source_sha"]
    assert result["branch"] == fixture["branch"]
    assert result["authorized_levels"] == ["M1", "M2", "M3"]
    assert not fixture["output_root"].exists()

    fixture["output_root"].mkdir(parents=True)
    with pytest.raises(FileExistsError, match="Refusing to reuse or overwrite"):
        validate_phase1_authorization(
            contract_path=fixture["contract_path"],
            authorization_path=fixture["authorization_path"],
            output_root=fixture["output_root"],
            source_sha=fixture["source_sha"],
            branch=fixture["branch"],
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
    import json

    fixture = _phase1_git_fixture(tmp_path)
    authorization = fixture["authorization"]
    if mutation == "sha":
        authorization["source_sha"] = "d" * 40
    elif mutation == "branch":
        authorization["branch"] = "wrong-branch"
    elif mutation == "digest":
        authorization["contract_sha256"] = "e" * 64
    elif mutation == "dirty":
        (fixture["repo"] / "untracked.txt").write_text("dirty", encoding="utf-8")
    fixture["authorization_path"].write_text(json.dumps(authorization), encoding="utf-8")

    with pytest.raises(PermissionError, match=message):
        validate_phase1_authorization(
            contract_path=fixture["contract_path"],
            authorization_path=fixture["authorization_path"],
            output_root=fixture["output_root"],
            source_sha=fixture["source_sha"],
            branch=fixture["branch"],
            working_tree_clean=True,
        )


def test_phase1_guard_rejects_caller_supplied_git_state_that_disagrees_with_repository(tmp_path) -> None:
    fixture = _phase1_git_fixture(tmp_path)
    with pytest.raises(PermissionError, match="supplied source_sha does not match Git HEAD"):
        validate_phase1_authorization(
            contract_path=fixture["contract_path"],
            authorization_path=fixture["authorization_path"],
            output_root=fixture["output_root"],
            source_sha="f" * 40,
            branch=fixture["branch"],
            working_tree_clean=True,
        )


def test_phase1_guard_rejects_owner_grant_inside_repository(tmp_path) -> None:
    fixture = _phase1_git_fixture(tmp_path)
    in_repo_grant = fixture["repo"] / "owner-grant.json"
    in_repo_grant.write_text("{}", encoding="utf-8")
    with pytest.raises(PermissionError, match="outside the repository"):
        validate_phase1_authorization(
            contract_path=fixture["contract_path"],
            authorization_path=in_repo_grant,
            output_root=fixture["output_root"],
            source_sha=fixture["source_sha"],
            branch=fixture["branch"],
            working_tree_clean=True,
        )


def test_phase1_guard_rejects_solver_policy_change_after_frozen_source(tmp_path) -> None:
    import json
    import subprocess

    fixture = _phase1_git_fixture(tmp_path)
    policy_path = fixture["repo"] / "src" / "solver_policy.py"
    policy_path.write_text("POLICY = 'changed after freeze'\n", encoding="utf-8")
    subprocess.run(["git", "add", "src/solver_policy.py"], cwd=fixture["repo"], check=True)
    subprocess.run(["git", "commit", "--quiet", "-m", "change frozen policy file"], cwd=fixture["repo"], check=True)
    current_head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=fixture["repo"], check=True, capture_output=True, text=True
    ).stdout.strip()
    authorization = fixture["authorization"]
    authorization["source_sha"] = current_head
    fixture["authorization_path"].write_text(json.dumps(authorization), encoding="utf-8")

    with pytest.raises(PermissionError, match="execution source differs from frozen policy"):
        validate_phase1_authorization(
            contract_path=fixture["contract_path"],
            authorization_path=fixture["authorization_path"],
            output_root=fixture["output_root"],
            source_sha=current_head,
            branch=fixture["branch"],
            working_tree_clean=True,
        )


def test_phase1_guard_rejects_output_outside_dedicated_wp06d_root(tmp_path) -> None:
    fixture = _phase1_git_fixture(tmp_path)
    with pytest.raises(PermissionError, match="new child of qualification"):
        validate_phase1_authorization(
            contract_path=fixture["contract_path"],
            authorization_path=fixture["authorization_path"],
            output_root=tmp_path / "outside-run",
            source_sha=fixture["source_sha"],
            branch=fixture["branch"],
            working_tree_clean=True,
        )


def test_legacy_r1_runner_entrypoint_is_quarantined(monkeypatch, capsys) -> None:
    from scripts import run_wp06d_phase1

    def forbidden_solve(*args, **kwargs):
        raise AssertionError("quarantined runner must not reach a structural solve")

    monkeypatch.setattr(run_wp06d_phase1, "_run_level", forbidden_solve)
    assert run_wp06d_phase1.main() == 2
    assert '"status": "BLOCKED_STALE_R1_RUNNER"' in capsys.readouterr().out
