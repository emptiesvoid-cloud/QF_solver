"""Controller VV3D registration remains closed until its runner chain is complete."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
import json

from scripts import development_autonomous as controller
from scripts import wp12_vv3d_contract


def test_policy_registers_closed_24_node_catalog_and_adaptive_runner_capability() -> None:
    policy = controller.load_policy()
    entry = policy["worktrees"][controller.VV3D_WORKTREE_ID]
    assert tuple(entry["allowed_nodeids"]) == controller.VV3D_ALL_NODEIDS
    assert tuple(entry["adaptive_fem_nodeids"]) == controller.VV3D_ADAPTIVE_FEM_NODEIDS
    assert tuple(entry["qpost_nodeids"]) == controller.VV3D_QPOST_NODEIDS
    assert len(entry["allowed_nodeids"]) == 24
    assert len(entry["qpost_nodeids"]) == 4
    assert entry["execution_authorized"] is False
    assert entry["execution_capability"] == "INITIAL_AND_CLOSED_CATALOG_ADAPTIVE_FEM_AND_QPOST_RUNNER_PATHS"
    assert entry["runner_capabilities"] == {"initial_fem": True, "adaptive_fem": True, "qpost": True}
    assert entry["attempt_limit_per_nodeid"] == 1
    assert entry["max_total_attempts"] == 24
    assert entry["max_total_seconds"] == 28_800
    assert entry["max_timeout_seconds"] == 1200
    assert entry["target_max_dofs"] == 30_000
    assert entry["rss_soft_limit_mib"] == 4096
    assert entry["per_node_selected_dofs"] == controller.VV3D_ALL_DOFS


def test_vv3d_controller_fingerprint_binds_imported_contract_and_ledger_without_changing_generic_identity() -> None:
    generic = controller._controller_provenance()
    vv3d = controller._vv3d_controller_provenance()
    assert vv3d["identity"] == generic["identity"]
    assert vv3d["sha256"]["runner"] == generic["sha256"]["runner"]
    assert vv3d["sha256"]["pytest_plugin"] == generic["sha256"]["pytest_plugin"]
    assert vv3d["sha256"]["policy"] == generic["sha256"]["policy"]
    assert "wp12_vv3d_contract" not in generic["sha256"]
    assert "wp12_vv3d_ledger" not in generic["sha256"]
    for name in ("wp12_vv3d_contract", "wp12_vv3d_ledger"):
        path = Path(controller.__file__).with_name(f"{name}.py")
        assert vv3d["sha256"][name] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert vv3d["vv3d_provenance_revision"] == "vv3d-executable-components-v1"


def test_policy_rejects_scope_budget_or_catalog_mutation(monkeypatch, tmp_path: Path) -> None:
    policy = controller.load_policy()
    policy["worktrees"][controller.VV3D_WORKTREE_ID]["max_total_seconds"] += 1
    path = tmp_path / "policy.json"
    path.write_text(__import__("json").dumps(policy), encoding="utf-8")
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    with pytest.raises(controller.PolicyError, match="VV3D"):
        controller.load_policy(path)


def test_vv3d_run_fails_before_creating_series_or_ledger(monkeypatch, tmp_path: Path) -> None:
    policy = controller.load_policy()
    run_store = tmp_path / "run-store"
    policy["run_store"] = ".codex/development-runs"
    monkeypatch.setattr(controller, "load_policy", lambda: policy)
    monkeypatch.setattr(controller, "_run_root", lambda *_args, **_kwargs: run_store)
    target = controller.VV3D_INITIAL_NODEIDS[0]
    with pytest.raises(controller.PolicyError, match="requires a reason, exact collect-only preflight"):
        controller.run_pytest(
            "fem_exploratory", target, None, worktree_id=controller.VV3D_WORKTREE_ID, reason="synthetic refusal",
        )
    assert not run_store.exists()


def test_vv3d_preflight_routes_to_official_collect_only_helper_without_reserving(monkeypatch, tmp_path: Path) -> None:
    policy = controller.load_policy()
    run_store = tmp_path / "run-store"
    monkeypatch.setattr(controller, "load_policy", lambda: policy)
    target = controller.VV3D_INITIAL_NODEIDS[0]
    calls = []

    def synthetic_collect_only(target_arg, preflight_id, *, policy):
        calls.append((target_arg, preflight_id, policy["worktrees"][controller.VV3D_WORKTREE_ID]["campaign_id"]))
        return {"state": "PREFLIGHT_PASS", "bodies_executed": False, "attempt_reserved": False}

    monkeypatch.setattr(controller, "preflight_wp12_vv3d_pytest", synthetic_collect_only)
    result = controller.preflight_pytest(controller.VV3D_WORKTREE_ID, target, "pf-000000000001")
    assert calls == [(target, "pf-000000000001", "WP12-VV3D-ADAPTIVE-20261029-R1")]
    assert result == {"state": "PREFLIGHT_PASS", "bodies_executed": False, "attempt_reserved": False}
    assert not run_store.exists()


@pytest.mark.parametrize(
    ("tamper", "expected_error"),
    [
        (None, None),
        ("manifest_fingerprint", "Owner manifest identity"),
        ("preflight_nodeid", "receipt does not attest"),
        ("owner_decision", "does not reference the exact archived campaign Owner decision"),
        ("decision_scope", "does not authorize this case or QPOST job"),
    ],
)
def test_vv3d_initial_execution_bindings_accept_exact_synthetic_package_and_refuse_mutations(
    monkeypatch, tmp_path: Path, tamper: str | None, expected_error: str | None,
) -> None:
    """Cover the strict initial manifest/preflight chain without calling a test body."""
    import sys
    import types

    target = controller.VV3D_INITIAL_NODEIDS[0]
    case_id = controller.VV3D_INITIAL_CASE_IDS[0]
    source_fp, controller_fp = "a" * 64, "b" * 64
    identity = {"head": "1" * 40, "tree": "2" * 40, "status_short": ""}
    provenance = {"identity": identity, "sha256": {"runner": "3" * 64}}
    execution_root = tmp_path / "science"
    experiment_root = execution_root / "experiments" / "wp12_vv3d_adaptive"
    mesh_root = experiment_root / "prepared_20261029"
    mesh_root.mkdir(parents=True)
    criteria_path = experiment_root / "criteria.json"
    frozen_criteria = [{"id": "finite", "classification": "CASE_GATE", "operator": "ALL_TRUE",
                        "threshold": None, "unit": "1"}]
    criteria_path.write_text(json.dumps({"criteria": frozen_criteria}), encoding="utf-8")
    criteria_sha = hashlib.sha256(json.dumps(
        frozen_criteria, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    matrix_cases = []
    for index, mesh_case_id in enumerate(controller.VV3D_INITIAL_CASE_IDS):
        mesh_name = f"mesh-{index}.json"
        mesh_path = mesh_root / mesh_name
        mesh_path.write_text(json.dumps({"case_id": mesh_case_id}), encoding="utf-8")
        matrix_cases.append({
            "case_id": mesh_case_id,
            "nodeid": controller.VV3D_INITIAL_NODEIDS[index],
            "mesh_file": mesh_name,
            "mesh_sha256": controller._sha256(mesh_path),
            "dofs": controller.VV3D_INITIAL_DOFS[mesh_case_id],
            "timeout_max_seconds": 1200,
        })
    matrix_path = mesh_root / "MATRIX_NOT_AUTHORIZED.json"
    matrix_path.write_text(json.dumps({"cases": matrix_cases}), encoding="utf-8")

    store = tmp_path / "store"
    store.mkdir()
    auth_root = store / "authorizations" / controller.VV3D_WORKTREE_ID
    auth_root.mkdir(parents=True)
    prepared_manifest_sha = "c" * 64
    contract_case = {"case_id": case_id, "nodeid": target, "manifest_sha256": prepared_manifest_sha,
                     "criteria_path": "criteria.json", "phase": "INITIAL"}
    contract = {"cases": [contract_case], "qpost_jobs": []}
    contract_path = auth_root / "campaign-contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    contract_sha = controller._sha256(contract_path)
    decision_id = "synthetic-campaign-01"
    decision_path = auth_root / "campaign-decision.json"
    decision = {"decision_id": decision_id, "status": "APPROVED",
                "case_ids": list(wp12_vv3d_contract.INITIAL_CASE_IDS)}
    if tamper == "decision_scope":
        decision["case_ids"].remove(case_id)
    decision_path.write_text(json.dumps(decision), encoding="utf-8")
    decision_sha = controller._sha256(decision_path)

    preflight_id = "pf-aaaaaaaaaaaa"
    preflight_dir = controller._preflight_directory(store, controller.VV3D_WORKTREE_ID, preflight_id)
    preflight_dir.mkdir(parents=True)
    preflight_receipt = {
        "status": "PREFLIGHT_PASS", "target": target, "nodeid": target, "preflight_id": preflight_id,
        "source_fingerprint": source_fp, "controller_provenance": provenance, "identity": identity,
        "bodies_executed": False, "attempt_reserved": False, "reservation_created": False,
        "selected_nodeids": [target], "skipped": 0,
    }
    if tamper == "preflight_nodeid":
        preflight_receipt["nodeid"] = controller.VV3D_INITIAL_NODEIDS[1]
    preflight_path = preflight_dir / "preflight.json"
    preflight_path.write_text(json.dumps(preflight_receipt), encoding="utf-8")
    preflight_sha = controller._sha256(preflight_path)
    (preflight_dir / "preflight.sha256.json").write_text(json.dumps({"sha256": preflight_sha}), encoding="utf-8")

    fake_contract = types.ModuleType("wp12_vv3d_contract")
    from scripts import wp12_vv3d_contract as vv3d_contract
    fake_contract.validate_contract = lambda *_args, **_kwargs: None
    fake_contract.validate_decision = lambda *_args, **_kwargs: None
    fake_contract.validate_decision_scope = vv3d_contract.validate_decision_scope
    fake_contract.verify_artifact_bindings = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "wp12_vv3d_contract", fake_contract)
    monkeypatch.setattr(controller, "_stable_fingerprint", lambda _value: controller_fp)
    manifest = {
        "schema": "qf-wp12-vv3d-case-manifest-v1", "campaign_id": controller.VV3D_CAMPAIGN_ID,
        "case_id": case_id, "nodeid": target, "state": "OWNER_AUTHORIZED",
        "execution_authorized": True, "do_not_execute": False,
        "mesh_sha256": matrix_cases[0]["mesh_sha256"], "selected_dofs": controller.VV3D_ALL_DOFS[target],
        "timeout_seconds": 1200, "rss_soft_limit_mib": 4096, "max_attempts": 1,
        "criteria_sha256": criteria_sha, "frozen_criteria": frozen_criteria,
        "scientific_fingerprint": source_fp, "controller_fingerprint": controller_fp,
        "campaign_contract_sha256": contract_sha, "prepared_case_manifest_sha256": prepared_manifest_sha,
        "owner_decision": {"status": "APPROVED", "approved_by": "Owner", "decision_id": decision_id,
                           "decision_sha256": decision_sha},
        "preflight": {"nodeid": target, "preflight_id": preflight_id, "status": "PREFLIGHT_PASS",
                       "receipt_path": str(preflight_path), "receipt_sha256": preflight_sha},
    }
    if tamper == "manifest_fingerprint":
        manifest["scientific_fingerprint"] = "0" * 64
    elif tamper == "owner_decision":
        manifest["owner_decision"]["decision_sha256"] = "f" * 64
    manifest_path = auth_root / "case-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    arguments = {
        "target": target, "preflight_id": preflight_id, "manifest_path": manifest_path,
        "entry": {}, "execution_root": execution_root, "identity": identity,
        "source_fingerprint": source_fp, "controller_provenance": provenance, "store": store,
    }
    if expected_error is None:
        bound_manifest, bound_preflight, manifest_sha, bound_preflight_sha, actual_decision_id, actual_decision_sha = (
            controller._vv3d_execution_bindings(**arguments)
        )
        assert bound_manifest["case_id"] == case_id
        assert bound_preflight == preflight_receipt
        assert manifest_sha == controller._sha256(manifest_path)
        assert bound_preflight_sha == preflight_sha
        assert actual_decision_id == decision_id
        assert actual_decision_sha == decision_sha
    else:
        with pytest.raises(controller.PolicyError, match=expected_error):
            controller._vv3d_execution_bindings(**arguments)
    assert not (store / "node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl").exists()


def test_vv3d_unknown_node_is_rejected_without_touching_evidence(monkeypatch, tmp_path: Path) -> None:
    policy = controller.load_policy()
    run_store = tmp_path / "run-store"
    monkeypatch.setattr(controller, "load_policy", lambda: policy)
    monkeypatch.setattr(controller, "_run_root", lambda *_args, **_kwargs: run_store)
    with pytest.raises(controller.PolicyError, match="outside the exact closed case catalogue"):
        controller.preflight_pytest(controller.VV3D_WORKTREE_ID, "tests/unit/test_anything.py::test_fem")
    assert not run_store.exists()


@pytest.mark.parametrize(
    ("target", "expected_error"),
    [
        (controller.VV3D_ADAPTIVE_FEM_NODEIDS[0], "adaptive FEM dispatch is not integrated"),
    ],
)
def test_unintegrated_adaptive_and_qpost_dispatch_refuse_before_store_creation(
    monkeypatch, tmp_path: Path, target: str, expected_error: str,
) -> None:
    policy = controller.load_policy()
    policy["worktrees"][controller.VV3D_WORKTREE_ID]["runner_capabilities"]["adaptive_fem"] = False
    store = tmp_path / "must-remain-absent"
    monkeypatch.setattr(controller, "load_policy", lambda: policy)
    monkeypatch.setattr(controller, "_run_root", lambda *_args, **_kwargs: store)
    with pytest.raises(controller.PolicyError, match=expected_error):
        controller.run_pytest(
            "fem_exploratory", target, None, worktree_id=controller.VV3D_WORKTREE_ID,
            reason="synthetic fail-closed dispatch check", preflight_id="pf-000000000001",
            execution_manifest=tmp_path / "manifest.json",
        )
    assert not store.exists()


@pytest.mark.parametrize("route", ["h1", "qload", "qpost"])
def test_initial_campaign_decision_cannot_authorize_adaptive_or_qpost_binding(
    monkeypatch, tmp_path: Path, route: str,
) -> None:
    """The approved initial tranche cannot reach H1, QLOAD, or QPOST binding paths."""
    import sys
    import types

    store = tmp_path / "store"
    auth_root = store / "authorizations" / controller.VV3D_WORKTREE_ID
    auth_root.mkdir(parents=True)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    manifest_path = auth_root / "manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    (auth_root / "campaign-contract.json").write_text("{}", encoding="utf-8")
    decision = {"case_ids": list(wp12_vv3d_contract.INITIAL_CASE_IDS)}
    (auth_root / "campaign-decision.json").write_text(json.dumps(decision), encoding="utf-8")

    fake_contract = types.ModuleType("wp12_vv3d_contract")
    fake_contract.validate_contract = lambda *_args, **_kwargs: None
    fake_contract.validate_decision = lambda *_args, **_kwargs: None
    fake_contract.validate_decision_scope = wp12_vv3d_contract.validate_decision_scope
    fake_contract.verify_artifact_bindings = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "wp12_vv3d_contract", fake_contract)
    monkeypatch.setattr(controller, "_stable_fingerprint", lambda _value: "b" * 64)

    if route in {"h1", "qload"}:
        index = 0 if route == "h1" else 1
        candidate_id = f"VV3D-ADAPT-TET4-{'H1' if route == 'h1' else 'QLOAD'}"
        target = controller.VV3D_ADAPTIVE_FEM_NODEIDS[index]
        candidate = {"candidate_id": candidate_id, "execution_kind": "FEM",
                     "kind": "uniform_h_refinement" if route == "h1" else "body_load_quadrature_escalation"}
        monkeypatch.setattr(controller, "_vv3d_adaptive_candidate_metadata",
                            lambda *_args, **_kwargs: (candidate, {}))
        with pytest.raises(controller.PolicyError, match="does not authorize this case or QPOST job"):
            controller._vv3d_adaptive_fem_launch_bindings(
                target=target, preflight_id="pf-000000000001", manifest_path=manifest_path,
                entry={}, execution_root=tmp_path, identity={}, source_fingerprint="a" * 64,
                controller_provenance={}, store=store,
            )
    else:
        target = controller.VV3D_QPOST_NODEIDS[0]
        candidate = {"candidate_id": "VV3D-ADAPT-TET4-QPOST", "execution_kind": "POSTPROCESS_ONLY"}
        monkeypatch.setattr(controller, "_vv3d_adaptive_candidate_metadata",
                            lambda *_args, **_kwargs: (candidate, {}))
        with pytest.raises(controller.PolicyError, match="does not authorize this case or QPOST job"):
            controller._vv3d_qpost_launch_bindings(
                target=target, preflight_id="pf-000000000001", manifest_path=manifest_path,
                entry={"evidence_root": str(evidence_root)}, execution_root=tmp_path,
                identity={}, source_fingerprint="a" * 64, controller_provenance={}, store=store,
            )
    assert not (store / "node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl").exists()


def test_vv3d_state_archive_is_created_once_from_exact_completed_sidecar(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    sidecar_dir = evidence_root / "VV3D-TET4-L3" / "attempt-1"
    sidecar_dir.mkdir(parents=True)
    sidecar = {
        "schema": "qf-wp12-vv3d-observables-v1", "campaign_id": controller.VV3D_CAMPAIGN_ID,
        "case_id": "VV3D-TET4-L3", "attempt_id": "attempt-1", "mesh_sha256": "1" * 64,
        "manifest_sha256": "2" * 64, "scientific_fingerprint": "3" * 64,
        "controller_fingerprint": "4" * 64, "execution": {"status": "COMPLETED_UNASSESSED"},
        "observables": {"nodal_displacements_m": {"value": [0.0, -1.25e-4, 2.5e-4]}},
    }
    (sidecar_dir / "observables.json").write_text(json.dumps(sidecar), encoding="utf-8")
    archive = controller._write_vv3d_state_archive(
        evidence_root=evidence_root, case_id="VV3D-TET4-L3", attempt_id="attempt-1",
        mesh_sha256="1" * 64, manifest_sha256="2" * 64,
        scientific_fingerprint="3" * 64, controller_fingerprint="4" * 64,
    )
    assert archive is not None
    stored = json.loads(Path(archive["path"]).read_text(encoding="utf-8"))
    assert stored["schema"] == "qf-wp12-vv3d-state-archive-v1"
    assert stored["nodal_displacements_m"] == [0.0, -1.25e-4, 2.5e-4]
    with pytest.raises(controller.PolicyError, match="already exists"):
        controller._write_vv3d_state_archive(
            evidence_root=evidence_root, case_id="VV3D-TET4-L3", attempt_id="attempt-1",
            mesh_sha256="1" * 64, manifest_sha256="2" * 64,
            scientific_fingerprint="3" * 64, controller_fingerprint="4" * 64,
        )


@pytest.mark.parametrize("tamper_receipt_binding", [False, True])
def test_vv3d_qpost_route_charges_wall_time_without_fem_attempt(
    monkeypatch, tmp_path: Path, tamper_receipt_binding: bool,
) -> None:
    from scripts.wp12_vv3d_ledger import BudgetLedger, RunBinding, RunnerCaseBinding

    policy = controller.load_policy()
    entry = policy["worktrees"][controller.VV3D_WORKTREE_ID]
    store = tmp_path / "store"
    store.mkdir()
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    entry["evidence_root"] = str(evidence_root)
    source_root = tmp_path / "science"
    source_root.mkdir()
    (store / "authorizations" / controller.VV3D_WORKTREE_ID).mkdir(parents=True)
    contract_path = store / "authorizations" / controller.VV3D_WORKTREE_ID / "campaign-contract.json"
    contract_path.write_text("{}", encoding="utf-8")
    source_manifest_sha = "1" * 64
    preflight_sha = "2" * 64
    decision_sha = "3" * 64
    contract_sha = hashlib.sha256(contract_path.read_bytes()).hexdigest()
    source_case = "VV3D-TET4-L3"
    candidate = "VV3D-ADAPT-TET4-QPOST"
    source_binding = RunBinding(contract_sha, "decision-1", decision_sha, source_manifest_sha, "4" * 64)
    ledger = BudgetLedger(store / entry["node_attempt_ledger"]["path"], allowed_root=store)
    source_id = ledger.start_runner_attempt(
        binding=source_binding,
        case=RunnerCaseBinding(source_case, controller.VV3D_INITIAL_NODEIDS[2], "attempt-seed-1",
                               "source-auth", "5" * 64, "6" * 64, 2187, 1200, 4096, 256,
                               str(evidence_root)),
        receipt_path=store / "source-receipt.json",
    )["reservation_id"]
    ledger.finish_runner_attempt(run_id=source_id, status="PASS", elapsed_seconds=5)

    archive_path = evidence_root / "state-archive.json"
    archive_path.write_text("{}", encoding="utf-8")
    archive_sha = controller._sha256(archive_path)
    manifest_sha = "7" * 64
    decision = {"status": "APPROVED", "decision_id": "decision-1", "decision_sha256": decision_sha,
                "catalog_sha256": "8" * 64}
    transition = {"status": "APPROVED", "decision_id": "decision-1", "decision_sha256": decision_sha,
                  "source_case_id": source_case, "candidate_id": candidate, "eligibility_sha256": "9" * 64}
    receipt_fields = {
        "schema": "qf-wp12-vv3d-adaptive-runner-receipt-v1", "status": "POSTPROCESS_RESERVED",
        "candidate_id": candidate, "execution_kind": "POSTPROCESS_ONLY", "seed_case": source_case,
        "catalog_sha256": decision["catalog_sha256"], "candidate_sha256": "a" * 64,
        "mesh_sha256": "b" * 64, "criteria_sha256": "c" * 64, "rule_sha256": "d" * 64,
        "source_hashes": {}, "manifest_path": str(tmp_path / "manifest.json"),
        "authorization_id": "qpost-auth-1", "preflight_receipt_sha256": preflight_sha,
        "campaign_decision": decision, "transition_decision": transition,
        "eligibility_record": {"path": str(evidence_root / "eligibility.json"), "sha256": "9" * 64},
        "eligibility": {"status": "ELIGIBLE", "sha256": "9" * 64},
        "allowed_evidence_roots": [str(evidence_root)], "evidence_root": str(evidence_root),
        "archive": {"path": str(archive_path), "sha256": archive_sha, "source_case_id": source_case,
                    "source_mesh_sha256": "b" * 64, "source_manifest_sha256": source_manifest_sha,
                    "source_attempt_id": "attempt-seed-1"},
        "source_manifest_sha256": source_manifest_sha, "postprocessing_reserved": True,
        "postprocessing_job_id": "qpost-job-1", "attempt_reserved": False,
        "postprocessing_jobs_used_before": 0, "postprocessing_jobs_used_after": 1,
        "postprocessing_jobs_max": 1,
        "frozen_criteria": [], "source_run_receipt_sha256": "e" * 64,
        "manifest_sha256": manifest_sha,
        "eligibility_threshold": 1e-4,
    }
    manifest = {"candidate_id": candidate, "seed_case": source_case, "postprocessing_job_id": "qpost-job-1",
                "timeout_seconds": 1200}
    monkeypatch.setattr(controller, "load_policy", lambda: policy)
    monkeypatch.setattr(controller, "_run_root", lambda *_args, **_kwargs: store)
    monkeypatch.setattr(controller, "_registered_worktree", lambda *_args, **_kwargs:
                        (entry, source_root, source_root, {"head": "a" * 40}, "5" * 64))
    monkeypatch.setattr(controller, "_controller_provenance", lambda: {"head": "f" * 40})
    monkeypatch.setattr(controller, "_stable_fingerprint", lambda _value: "6" * 64)
    monkeypatch.setattr(controller, "_vv3d_qpost_launch_bindings", lambda **_kwargs:
                        (manifest, {}, receipt_fields))
    monkeypatch.setattr(controller, "build_pytest_command", lambda *_args, **_kwargs: ["mock-child"])
    monkeypatch.setattr(controller, "build_child_environment", lambda *_args, **_kwargs: {})

    child_context = {}

    def monitored(*_args, output_dir: Path, environment, **_kwargs):
        child_context.update(environment)
        (output_dir / "stdout.log").write_text("qpost mock\n", encoding="utf-8")
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        qpost_dir = evidence_root / candidate / "qpost-job-1"
        qpost_dir.mkdir(parents=True)
        sidecar = {
            "schema": "qf-wp12-vv3d-observables-v1", "campaign_id": controller.VV3D_CAMPAIGN_ID,
            "case_id": candidate, "attempt_id": "qpost-job-1", "mesh_sha256": "b" * 64,
            "manifest_sha256": manifest_sha, "scientific_fingerprint": "5" * 64,
            "controller_fingerprint": "6" * 64, "archive_sha256": archive_sha,
            "case_state": "OWNER_AUTHORIZED_POSTPROCESS_ONLY",
            "runner_receipt_sha256": ("0" * 64 if tamper_receipt_binding else
                                       environment["QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256"]),
            "execution": {"status": "COMPLETED_UNASSESSED", "attempt_reserved": False,
                          "postprocessing_reserved": True, "fem_started": False},
            "observables": {"qpost": {"status": "COMPLETED_UNASSESSED", "maximum_relative_change": 2e-4}},
        }
        (qpost_dir / "observables.json").write_text(json.dumps(sidecar), encoding="utf-8")
        return SimpleNamespace(status="PASS", return_code=0, elapsed_seconds=2.5, peak_rss_bytes=1,
                               peak_process_count=1, stdout_bytes=10, stderr_bytes=0, stop_reason=None)

    monkeypatch.setattr(controller, "run_supervised_command", monitored)
    result, code = controller.run_pytest(
        "fem_exploratory", controller.VV3D_QPOST_NODEIDS[0], None,
        worktree_id=controller.VV3D_WORKTREE_ID, reason="mock qpost", preflight_id="pf-000000000001",
        execution_manifest=tmp_path / "manifest.json",
    )
    if tamper_receipt_binding:
        assert result["state"] == "PROVENANCE_MISMATCH" and code == 1, result
        postprocess_finishes = [record for record in ledger.verify()
                                if record.get("event") == "POSTPROCESS_FINISHED"]
        assert len(postprocess_finishes) == 1
        assert postprocess_finishes[0]["status"] == "INFRA_ERROR"
    else:
        assert result["state"] == "PASS" and code == 0, result
    assert child_context["QF_DEV_VV3D_ADAPTIVE_CANDIDATE_ID"] == candidate
    assert child_context["QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256"]
    assert receipt_fields["postprocessing_jobs_used_before"] == 0
    assert receipt_fields["postprocessing_jobs_used_after"] == 1
    assert receipt_fields["postprocessing_jobs_max"] == 1
    summary = ledger.summary()
    assert summary["attempts_used"] == 1
    assert summary["postprocess_jobs_used"] == 1
    assert summary["elapsed_seconds_actual"] == pytest.approx(7.5)


def test_vv3d_qpost_manifest_path_outside_campaign_auth_root_is_rejected_before_binding(
    monkeypatch, tmp_path: Path,
) -> None:
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    store = tmp_path / "store"
    auth_root = store / "authorizations" / controller.VV3D_WORKTREE_ID
    auth_root.mkdir(parents=True)
    outside_manifest = tmp_path / "manifest.json"
    outside_manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        controller, "_vv3d_adaptive_candidate_metadata",
        lambda *_args, **_kwargs: (
            {"execution_kind": "POSTPROCESS_ONLY", "candidate_id": "VV3D-ADAPT-TET4-QPOST"},
            {},
        ),
    )
    with pytest.raises(controller.PolicyError, match="campaign authorization root"):
        controller._vv3d_qpost_launch_bindings(
            target=controller.VV3D_QPOST_NODEIDS[0], preflight_id="pf-synthetic-0001",
            manifest_path=outside_manifest, entry={"evidence_root": str(evidence_root)},
            execution_root=tmp_path, identity={}, source_fingerprint="a" * 64,
            controller_provenance={}, store=store,
        )


@pytest.mark.parametrize(
    ("transition_matches_campaign", "tamper_binding"),
    [(True, None), (False, None), (True, "preflight_id"), (True, "timeout")],
)
def test_vv3d_qpost_launch_bindings_enforce_campaign_transition_binding(
    monkeypatch, tmp_path: Path, transition_matches_campaign: bool, tamper_binding: str | None,
) -> None:
    """Exercise strict QPOST bindings against temporary evidence without FEM."""
    import sys
    import types

    from scripts.wp12_vv3d_ledger import BudgetLedger, RunBinding, RunnerCaseBinding

    target = controller.VV3D_QPOST_NODEIDS[0]
    candidate_id, seed_case = "VV3D-ADAPT-TET4-QPOST", "VV3D-TET4-L3"
    source_fp, controller_fp = "a" * 64, "b" * 64
    source_manifest_sha = "c" * 64
    decision_id, source_attempt, postprocess_id = "campaign-decision-1", "seed-attempt-0001", "qpost-job-0001"
    identity = {"head": "1" * 40, "tree": "2" * 40, "status_short": ""}
    provenance = {"identity": identity, "sha256": {"runner": "3" * 64}}
    store, evidence_root, execution_root = tmp_path / "store", tmp_path / "evidence", tmp_path / "science"
    store.mkdir()
    evidence_root.mkdir()
    criteria_path = execution_root / "experiments" / "wp12_vv3d_adaptive" / "criteria.json"
    criteria_path.parent.mkdir(parents=True)
    criteria = [{"id": "observable-change", "operator": "LE", "threshold": 1e-4, "unit": "1"}]
    criteria_path.write_text(json.dumps({"criteria": criteria}), encoding="utf-8")
    auth_root = store / "authorizations" / controller.VV3D_WORKTREE_ID
    auth_root.mkdir(parents=True)

    contract = {"qpost_jobs": [{
        "job_id": candidate_id, "nodeid": target, "manifest_sha256": "d" * 64,
        "timeout_seconds": 1200, "rss_soft_limit_mib": 4096, "max_jobs": 1,
    }]}
    contract_path = auth_root / "campaign-contract.json"
    contract_path.write_text(json.dumps(contract), encoding="utf-8")
    contract_sha = controller._sha256(contract_path)
    decision = {"decision_id": decision_id, "status": "APPROVED"}
    decision_path = auth_root / "campaign-decision.json"
    decision_path.write_text(json.dumps(decision), encoding="utf-8")
    decision_sha = controller._sha256(decision_path)

    candidate = {
        "candidate_id": candidate_id, "execution_kind": "POSTPROCESS_ONLY", "family": "TET4",
        "seed_case": seed_case, "criteria_path": "criteria.json",
        "numerical_conditions": {"postprocessing_jobs_max": 1,
                                 "relative_observable_change_trigger_gt": 1e-4},
    }
    bindings = {
        "catalog_sha256": "4" * 64, "candidate_sha256": "5" * 64, "mesh_sha256": "6" * 64,
        "criteria_sha256": "7" * 64, "rule_sha256": "8" * 64,
        "source_hashes": {"experiments/wp12_vv3d_adaptive/quadrature.py": "9" * 64},
    }
    monkeypatch.setattr(controller, "_vv3d_adaptive_candidate_metadata", lambda *_args: (candidate, bindings))
    monkeypatch.setattr(controller, "_stable_fingerprint", lambda _value: controller_fp)
    fake_contract = types.ModuleType("wp12_vv3d_contract")
    fake_contract.validate_contract = lambda *_args, **_kwargs: None
    fake_contract.validate_decision = lambda *_args, **_kwargs: None
    # This fixture covers QPOST's remaining source/archive bindings after an
    # independently approved job scope; the initial-tranche denial is tested above.
    fake_contract.validate_decision_scope = lambda *_args, **_kwargs: None
    fake_contract.verify_artifact_bindings = lambda *_args, **_kwargs: None
    monkeypatch.setitem(sys.modules, "wp12_vv3d_contract", fake_contract)

    archive_path = evidence_root / "seed-state.json"
    archive_path.write_text(json.dumps({
        "schema": "qf-wp12-vv3d-state-archive-v1", "campaign_id": controller.VV3D_CAMPAIGN_ID,
        "case_id": seed_case, "mesh_sha256": bindings["mesh_sha256"],
        "case_state": "OWNER_AUTHORIZED_EXECUTION", "execution_status": "COMPLETED_UNASSESSED",
        "manifest_sha256": source_manifest_sha, "attempt_id": source_attempt,
        "nodal_displacements_m": [0.0, -1e-3],
    }), encoding="utf-8")
    archive_sha = controller._sha256(archive_path)
    ledger_path = store / "node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl"
    ledger = BudgetLedger(ledger_path, allowed_root=store)
    reservation = ledger.start_runner_attempt(
        binding=RunBinding(contract_sha, decision_id, decision_sha, source_manifest_sha, "e" * 64),
        case=RunnerCaseBinding(seed_case, controller.VV3D_INITIAL_NODEIDS[2], source_attempt,
                               "seed-auth-0001", source_fp, controller_fp, 2187, 1200, 4096, 256,
                               str(evidence_root)),
        receipt_path=store / "seed-reservation.json",
    )
    ledger.finish_runner_attempt(run_id=reservation["reservation_id"], status="PASS", elapsed_seconds=5)
    source_run_path = store / "seed-run" / "run.json"
    source_run_path.parent.mkdir()
    source_run_path.write_text(json.dumps({
        "campaign_id": controller.VV3D_CAMPAIGN_ID, "case_id": seed_case, "state": "PASS",
        "scientific_state": "PASS", "provenance_state": "VERIFIED", "source_fingerprint": source_fp,
        "controller_fingerprint": controller_fp, "manifest": {"sha256": source_manifest_sha},
        "attempt_id": source_attempt, "qpost_state_archive": {"path": str(archive_path), "sha256": archive_sha},
    }), encoding="utf-8")
    source_hash = controller._sha256(source_run_path)

    preflight_id = "pf-aaaaaaaaaaaa"
    preflight_dir = controller._preflight_directory(store, controller.VV3D_WORKTREE_ID, preflight_id)
    preflight_dir.mkdir(parents=True)
    preflight = {
        "preflight_id": preflight_id, "target": target, "nodeid": target,
        "status": "PREFLIGHT_PASS", "bodies_executed": False,
        "attempt_reserved": False, "selected_nodeids": [target], "skipped": 0,
        "reservation_created": False,
        "source_fingerprint": source_fp, "identity": identity, "controller_provenance": provenance,
    }
    if tamper_binding == "preflight_id":
        preflight["preflight_id"] = "pf-bbbbbbbbbbbb"
    preflight_path = preflight_dir / "preflight.json"
    preflight_path.write_text(json.dumps(preflight), encoding="utf-8")
    preflight_sha = controller._sha256(preflight_path)
    campaign_decision = {
        "status": "APPROVED", "decision_id": decision_id, "decision_sha256": decision_sha,
        "catalog_sha256": bindings["catalog_sha256"],
    }
    transition = {
        "status": "APPROVED",
        "decision_id": decision_id if transition_matches_campaign else "different-campaign-decision",
        "decision_sha256": decision_sha if transition_matches_campaign else "f" * 64,
        "source_case_id": seed_case,
        "candidate_id": candidate_id,
    }
    eligibility_source = {
        "campaign_id": controller.VV3D_CAMPAIGN_ID, "candidate_id": candidate_id,
        "postprocessing_job_id": postprocess_id,
        "seed_case": {"case_id": seed_case, "status": "PASS", "source_run_receipt_sha256": source_hash,
                      "manifest_sha256": source_manifest_sha, "attempt_id": source_attempt,
                      "mesh_sha256": bindings["mesh_sha256"]},
        "archive": {"status": "AVAILABLE", "path": str(archive_path.resolve()), "sha256": archive_sha,
                    "source_case_id": seed_case, "source_mesh_sha256": bindings["mesh_sha256"],
                    "source_manifest_sha256": source_manifest_sha, "source_attempt_id": source_attempt},
        "campaign_decision": {"decision_id": decision_id, "decision_sha256": decision_sha},
        "transition_decision": {"decision_id": transition["decision_id"],
                                "decision_sha256": transition["decision_sha256"]},
        "postprocessing_slot": {"postprocessing_jobs_used": 0, "postprocessing_jobs_max": 1},
    }
    transition["eligibility_sha256"] = hashlib.sha256(
        json.dumps(eligibility_source, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()
    manifest = {
        "schema": "qf-wp12-vv3d-adaptive-execution-manifest-v1", "execution_authorized": True,
        "do_not_execute": False, "campaign_id": controller.VV3D_CAMPAIGN_ID,
        "candidate_id": candidate_id, "nodeid": target, "execution_kind": "POSTPROCESS_ONLY",
        "seed_case": seed_case, "catalog_sha256": bindings["catalog_sha256"],
        "candidate_sha256": bindings["candidate_sha256"], "mesh_sha256": bindings["mesh_sha256"],
        "criteria_sha256": bindings["criteria_sha256"], "rule_sha256": bindings["rule_sha256"],
        "source_hashes": bindings["source_hashes"], "scientific_fingerprint": source_fp,
        "controller_fingerprint": controller_fp, "campaign_decision": campaign_decision,
        "transition_decision": transition, "authorization_id": "qpost-auth-0001",
        "frozen_criteria": criteria,
        "frozen_criteria_sha256": hashlib.sha256(
            json.dumps(criteria, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        ).hexdigest(),
        "preflight_receipt_sha256": preflight_sha, "evidence_root": str(evidence_root.resolve()),
        "postprocessing_job_id": postprocess_id, "job_manifest_sha256": "d" * 64,
        "timeout_seconds": 1200, "rss_soft_limit_mib": 4096,
        "postprocessing_jobs_used_before": 0, "postprocessing_jobs_used_after": 1,
        "postprocessing_jobs_max": 1, "source_run_receipt_sha256": source_hash,
    }
    if tamper_binding == "timeout":
        manifest["timeout_seconds"] = 1199
    manifest_path = auth_root / "qpost-manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    def call_bindings():
        return controller._vv3d_qpost_launch_bindings(
            target=target, preflight_id=preflight_id, manifest_path=manifest_path,
            entry={"evidence_root": str(evidence_root), "node_attempt_ledger": {"path": ledger_path.name}},
            execution_root=execution_root, identity=identity, source_fingerprint=source_fp,
            controller_provenance=provenance, store=store,
        )

    if transition_matches_campaign and tamper_binding is None:
        actual_manifest, actual_preflight, receipt_fields = call_bindings()
        assert actual_manifest == manifest
        assert actual_preflight == preflight
        assert receipt_fields["allowed_evidence_roots"] == [str(evidence_root.resolve()), str(auth_root.resolve())]
        assert receipt_fields["attempt_reserved"] is False
        assert receipt_fields["postprocessing_reserved"] is True
        assert receipt_fields["source_run_receipt_sha256"] == source_hash
        assert receipt_fields["archive"]["sha256"] == archive_sha
    else:
        expected_error = ("exact campaign-approved eligibility binding"
                          if not transition_matches_campaign else
                          "preflight receipt provenance is invalid" if tamper_binding == "preflight_id" else
                          "approved QPOST catalog row")
        with pytest.raises(controller.PolicyError, match=expected_error):
            call_bindings()


def _mock_vv3d_run(
    monkeypatch, tmp_path: Path, *, status: str = "PASS", emit_sidecar: bool = True,
    expected_state: str | None = None,
) -> Path:
    policy = controller.load_policy()
    entry = policy["worktrees"][controller.VV3D_WORKTREE_ID]
    store = tmp_path / "evidence-store"
    source = tmp_path / "science"
    (source / "src" / "solveur").mkdir(parents=True)
    (source / "src" / "solveur" / "__init__.py").write_text("", encoding="utf-8")
    evidence_root = tmp_path / "observables"
    evidence_root.mkdir()
    entry["evidence_root"] = str(evidence_root)
    entry["execution_authorized"] = False
    identity = {"root": str(source), "branch": entry["branch"], "head": "a" * 40,
                "tree": "b" * 40, "status_short": ""}
    source_fp = "c" * 64
    controller_provenance = {"synthetic": True}
    target = controller.VV3D_INITIAL_NODEIDS[0]
    case_id = "VV3D-TET4-L1"
    manifest = {
        "case_id": case_id, "selected_dofs": 81, "timeout_seconds": 1200,
        "mesh_sha256": "1" * 64,
        "rss_soft_limit_mib": 4096, "archive_size_limit_mib": 256,
        "campaign_contract_sha256": "1" * 64, "authorization_id": "synthetic-auth-1",
    }
    preflight = {}
    monkeypatch.setattr(controller, "load_policy", lambda: policy)
    monkeypatch.setattr(controller, "_run_root", lambda *_args, **_kwargs: store)
    monkeypatch.setattr(controller, "_registered_worktree", lambda *_args, **_kwargs:
                        (entry, source, source / "src", identity, source_fp))
    monkeypatch.setattr(controller, "_controller_provenance", lambda: controller_provenance)
    monkeypatch.setattr(controller, "_stable_fingerprint", lambda _value: "d" * 64)
    monkeypatch.setattr(controller, "_vv3d_execution_bindings", lambda **_kwargs:
                        (manifest, preflight, "2" * 64, "3" * 64, "synthetic-decision", "4" * 64))
    monkeypatch.setattr(controller, "build_pytest_command", lambda *_args, **_kwargs: ["synthetic-child"])
    monkeypatch.setattr(controller, "build_child_environment", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(controller, "_observed_solver_origin", lambda _value: str(source / "src" / "solveur" / "__init__.py"))

    captured_environment = {}

    def monitored(*_args, output_dir: Path, environment, **_kwargs):
        captured_environment.update(environment)
        (output_dir / "stdout.log").write_text("QF_DEV_SOLVER_ORIGIN=synthetic\n", encoding="utf-8")
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        if emit_sidecar:
            runner_receipt = json.loads(Path(environment["QF_DEV_VV3D_RUNNER_RECEIPT_PATH"]).read_text())
            case_dir = Path(environment["QF_DEV_EVIDENCE_ROOT"]) / runner_receipt["case_id"] / runner_receipt["attempt_id"]
            case_dir.mkdir(parents=True)
            sidecar = {
                "schema": "qf-wp12-vv3d-observables-v1", "campaign_id": controller.VV3D_CAMPAIGN_ID,
                "case_id": runner_receipt["case_id"], "attempt_id": runner_receipt["attempt_id"],
                "case_state": "OWNER_AUTHORIZED_EXECUTION",
                "runner_receipt_sha256": environment["QF_DEV_VV3D_RUNNER_RECEIPT_SHA256"],
                "mesh_sha256": manifest.get("mesh_sha256", "1" * 64),
                "manifest_sha256": runner_receipt["manifest_sha256"],
                "scientific_fingerprint": runner_receipt["scientific_fingerprint"],
                "controller_fingerprint": runner_receipt["controller_fingerprint"],
                "execution": {"status": "COMPLETED_UNASSESSED", "attempt_reserved": True,
                              "fem_started": True},
                "observables": {"nodal_displacements_m": {"value": [0.0, -0.1, 0.2]}},
            }
            (case_dir / "observables.json").write_text(json.dumps(sidecar), encoding="utf-8")
        return SimpleNamespace(status=status, return_code=0 if status == "PASS" else 1,
            elapsed_seconds=0.25, peak_rss_bytes=1234, peak_process_count=2,
            stdout_bytes=25, stderr_bytes=0, archive_bytes=25, temporary_bytes=30, stop_reason=None)

    monkeypatch.setattr(controller, "run_supervised_command", monitored)
    result, code = controller.run_pytest(
        "fem_exploratory", target, None, worktree_id=controller.VV3D_WORKTREE_ID,
        reason="synthetic mocked dispatch", preflight_id="pf-000000000001",
        execution_manifest=tmp_path / "manifest.json",
    )
    expected_state = expected_state or ("PASS" if status == "PASS" else "PYTEST_FAILED")
    assert result["state"] == expected_state
    assert code == (0 if expected_state == "PASS" else 1)
    for required in (
        "QF_DEV_VV3D_CASE_ID", "QF_DEV_TARGET_NODEID", "QF_DEV_MANIFEST_PATH",
        "QF_DEV_MANIFEST_SHA256", "QF_DEV_AUTHORIZATION_ID", "QF_DEV_VV3D_SCIENCE_FINGERPRINT",
        "QF_DEV_CONTROLLER_FINGERPRINT", "QF_DEV_EVIDENCE_ROOT",
        "QF_DEV_VV3D_RUNNER_RECEIPT_PATH", "QF_DEV_VV3D_RUNNER_RECEIPT_SHA256",
    ):
        assert captured_environment[required]
    receipt_path = next(store.rglob("vv3d-runner-reservation.json"))
    receipt_raw = receipt_path.read_bytes()
    receipt = json.loads(receipt_raw)
    assert controller._sha256(receipt_path) == captured_environment["QF_DEV_VV3D_RUNNER_RECEIPT_SHA256"]
    assert receipt["preflight_receipt_sha256"] == "3" * 64
    assert receipt["decision_id"] == "synthetic-decision"
    assert receipt["authorization_id"] == "synthetic-auth-1"
    assert receipt["ledger_scope_id"] == "wp12_vv3d_adaptive"
    assert receipt["attempt_reserved"] is True
    return store


def test_vv3d_monitored_dispatch_reserves_and_completes_one_mocked_attempt(monkeypatch, tmp_path: Path) -> None:
    store = _mock_vv3d_run(monkeypatch, tmp_path)
    from scripts.wp12_vv3d_ledger import BudgetLedger

    ledger = BudgetLedger(store / "node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl", allowed_root=store)
    summary = ledger.summary()
    assert summary["attempts_used"] == 1
    assert summary["seconds_reserved"] == 0
    assert summary["elapsed_seconds_actual"] == pytest.approx(0.25)
    assert summary["attempt_open"] is False


def test_vv3d_failed_mocked_body_consumes_and_stops_without_retry(monkeypatch, tmp_path: Path) -> None:
    store = _mock_vv3d_run(monkeypatch, tmp_path, status="PYTEST_FAILED")
    from scripts.wp12_vv3d_ledger import BudgetLedger, LedgerError, RunBinding, RunnerCaseBinding

    ledger = BudgetLedger(store / "node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl", allowed_root=store)
    summary = ledger.summary()
    assert summary["attempts_used"] == 1
    assert summary["seconds_reserved"] == 0
    assert summary["elapsed_seconds_actual"] == pytest.approx(0.25)
    assert summary["attempt_open"] is False
    with pytest.raises(LedgerError, match="already been attempted"):
        ledger.start_runner_attempt(
            binding=RunBinding("1" * 64, "decision-two", "2" * 64, "3" * 64, "4" * 64),
            case=RunnerCaseBinding(
                "VV3D-TET4-L1", controller.VV3D_INITIAL_NODEIDS[0], "attempt-second",
                "synthetic-auth-2", "5" * 64, "6" * 64, 81, 1200, 4096, 256, str(tmp_path),
            ),
            receipt_path=store / "second-reservation.json",
        )


def test_vv3d_initial_pass_without_sidecar_is_provenance_failure_and_not_seedable(
    monkeypatch, tmp_path: Path,
) -> None:
    store = _mock_vv3d_run(
        monkeypatch, tmp_path, status="PASS", emit_sidecar=False,
        expected_state="PROVENANCE_MISMATCH",
    )
    from scripts.wp12_vv3d_ledger import BudgetLedger

    ledger = BudgetLedger(store / "node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl", allowed_root=store)
    finished = [record for record in ledger.verify() if record.get("event") == "ATTEMPT_FINISHED"]
    assert len(finished) == 1
    assert finished[0]["status"] == "INFRA_ERROR"
    run_record = next(store.rglob("run.json"))
    result = json.loads(run_record.read_text(encoding="utf-8"))
    assert result["scientific_state"] == "PASS"
    assert result["provenance_state"] == "PROVENANCE_MISMATCH"
    assert result["qpost_state_archive"] is None


def test_vv3d_initial_pass_without_state_archive_is_provenance_failure(monkeypatch, tmp_path: Path) -> None:
    def refuse_archive(**_kwargs):
        raise OSError("synthetic archive writer failure")

    monkeypatch.setattr(controller, "_write_vv3d_state_archive", refuse_archive)
    store = _mock_vv3d_run(
        monkeypatch, tmp_path, status="PASS", expected_state="PROVENANCE_MISMATCH",
    )
    from scripts.wp12_vv3d_ledger import BudgetLedger

    ledger = BudgetLedger(store / "node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl", allowed_root=store)
    finished = [record for record in ledger.verify() if record.get("event") == "ATTEMPT_FINISHED"]
    assert len(finished) == 1
    assert finished[0]["status"] == "INFRA_ERROR"
    result = json.loads(next(store.rglob("run.json")).read_text(encoding="utf-8"))
    assert result["scientific_state"] == "PASS"
    assert result["provenance_state"] == "PROVENANCE_MISMATCH"
    assert "synthetic archive writer failure" in result["qpost_state_archive_error"]


def test_vv3d_adaptive_fem_monitored_dispatch_emits_science_receipt(monkeypatch, tmp_path: Path) -> None:
    from scripts.wp12_vv3d_ledger import BudgetLedger, RunBinding, RunnerCaseBinding

    policy = controller.load_policy()
    entry = policy["worktrees"][controller.VV3D_WORKTREE_ID]
    store, evidence, science = tmp_path / "store", tmp_path / "evidence", tmp_path / "science"
    store.mkdir()
    evidence.mkdir()
    (science / "solveur").mkdir(parents=True)
    (science / "solveur" / "__init__.py").write_text("", encoding="utf-8")
    entry["evidence_root"] = str(evidence)
    auth_root = store / "authorizations" / controller.VV3D_WORKTREE_ID
    auth_root.mkdir(parents=True)
    contract_path = auth_root / "campaign-contract.json"
    contract_path.write_text("{}", encoding="utf-8")
    contract_sha = controller._sha256(contract_path)
    ledger_path = store / entry["node_attempt_ledger"]["path"]
    ledger = BudgetLedger(ledger_path, allowed_root=store)
    source_case, candidate = "VV3D-TET4-L3", "VV3D-ADAPT-TET4-H1"
    source_id = ledger.start_runner_attempt(
        binding=RunBinding(contract_sha, "campaign-01", "1" * 64, "2" * 64, "3" * 64),
        case=RunnerCaseBinding(source_case, controller.VV3D_INITIAL_NODEIDS[2], "seed-attempt-001",
                               "seed-auth-0001", "4" * 64, "5" * 64, 2187, 1200, 4096, 256, str(evidence)),
        receipt_path=store / "seed-receipt.json",
    )["reservation_id"]
    ledger.finish_runner_attempt(run_id=source_id, status="PASS", elapsed_seconds=4.0)

    target = controller.VV3D_ADAPTIVE_FEM_NODEIDS[0]
    manifest_path = evidence / "adaptive-manifest.json"
    manifest_path.write_text("{}", encoding="utf-8")
    manifest_sha = controller._sha256(manifest_path)
    preflight_sha, eligibility_sha = "6" * 64, "7" * 64
    attempt_id, reservation_id = "adaptive-attempt-0001", "adaptive-reservation-0001"
    source_fp, controller_fp = "4" * 64, "5" * 64
    campaign_decision = {"status": "APPROVED", "decision_id": "campaign-01",
                         "decision_sha256": "1" * 64, "catalog_sha256": "8" * 64}
    transition = {"status": "APPROVED", "decision_id": "transition-01", "decision_sha256": "9" * 64,
                  "source_case_id": source_case, "candidate_id": candidate,
                  "eligibility_sha256": eligibility_sha}
    eligibility_path = evidence / "eligibility.json"
    eligibility_path.write_text("{}", encoding="utf-8")
    eligibility_sha = controller._sha256(eligibility_path)
    transition["eligibility_sha256"] = eligibility_sha
    candidate_bindings = {"catalog_sha256": "8" * 64, "candidate_sha256": "a" * 64,
                          "mesh_sha256": "b" * 64, "criteria_sha256": "c" * 64,
                          "rule_sha256": "d" * 64, "source_hashes": {}}
    manifest = {"case_id": candidate, "attempt_id": attempt_id, "reservation_id": reservation_id,
                "authorization_id": "adaptive-auth-0001", "selected_dofs": entry["per_node_selected_dofs"][target],
                "timeout_seconds": 1200, "rss_soft_limit_mib": 4096, "archive_size_limit_mib": 256,
                "mesh_sha256": candidate_bindings["mesh_sha256"], "campaign_contract_sha256": contract_sha,
                "_validated_transition_binding": {"transition_receipt_sha256": eligibility_sha,
                                                   "transition_source_case_id": source_case,
                                                   "transition_destination_case_id": candidate}}
    receipt_fields = {
        "schema": "qf-wp12-vv3d-adaptive-runner-receipt-v1", "status": "RESERVED",
        "campaign_id": controller.VV3D_CAMPAIGN_ID, "candidate_id": candidate, "nodeid": target,
        "execution_kind": "FEM", "seed_case": source_case, **candidate_bindings,
        "manifest_sha256": manifest_sha, "manifest_path": str(manifest_path),
        "authorization_id": manifest["authorization_id"], "scientific_fingerprint": source_fp,
        "controller_fingerprint": controller_fp, "preflight_receipt_sha256": preflight_sha,
        "campaign_decision": campaign_decision, "transition_decision": transition,
        "eligibility_record": {"path": str(eligibility_path), "sha256": eligibility_sha},
        "eligibility": {"status": "ELIGIBLE", "sha256": eligibility_sha},
        "allowed_evidence_roots": [str(evidence), str(auth_root)], "evidence_root": str(evidence),
        "frozen_criteria": [], "attempt_id": attempt_id, "reservation_id": reservation_id,
        "selected_dofs": manifest["selected_dofs"], "timeout_seconds": 1200,
        "attempt_number": 1, "max_attempts": 1, "attempt_reserved": True,
        "postprocessing_reserved": False,
    }
    manifest["_runner_receipt_fields"] = receipt_fields
    identity, provenance = {"head": "a" * 40}, {"controller": "candidate"}
    monkeypatch.setattr(controller, "load_policy", lambda: policy)
    monkeypatch.setattr(controller, "_run_root", lambda *_args, **_kwargs: store)
    monkeypatch.setattr(controller, "_registered_worktree", lambda *_args, **_kwargs:
                        (entry, science, science, identity, source_fp))
    monkeypatch.setattr(controller, "_controller_provenance", lambda: provenance)
    monkeypatch.setattr(controller, "_stable_fingerprint", lambda _value: controller_fp)
    monkeypatch.setattr(controller, "_vv3d_execution_bindings", lambda **_kwargs:
                        (manifest, {"status": "PREFLIGHT_PASS"}, manifest_sha, preflight_sha,
                         "campaign-01", "1" * 64))
    monkeypatch.setattr(controller, "build_pytest_command", lambda *_args, **_kwargs: ["mock-child"])
    monkeypatch.setattr(controller, "build_child_environment", lambda *_args, **_kwargs: {})
    captured = {}

    def monitored(*_args, output_dir: Path, environment, **_kwargs):
        captured.update(environment)
        (output_dir / "stdout.log").write_text("origin", encoding="utf-8")
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        sidecar_dir = evidence / candidate / attempt_id
        sidecar_dir.mkdir(parents=True)
        sidecar = {"schema": "qf-wp12-vv3d-observables-v1", "campaign_id": controller.VV3D_CAMPAIGN_ID,
                   "case_id": candidate, "attempt_id": attempt_id, "mesh_sha256": candidate_bindings["mesh_sha256"],
                   "case_state": "OWNER_AUTHORIZED_EXECUTION",
                   "runner_receipt_sha256": environment["QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256"],
                   "manifest_sha256": manifest_sha, "scientific_fingerprint": source_fp,
                   "controller_fingerprint": controller_fp,
                   "execution": {"status": "COMPLETED_UNASSESSED", "attempt_reserved": True,
                                 "fem_started": True}, "observables": {}, "criteria": {}}
        (sidecar_dir / "observables.json").write_text(json.dumps(sidecar), encoding="utf-8")
        return SimpleNamespace(status="PASS", return_code=0, elapsed_seconds=2.0, peak_rss_bytes=1,
                               peak_process_count=1, stdout_bytes=6, stderr_bytes=0, archive_bytes=1,
                               temporary_bytes=1, stop_reason=None)

    monkeypatch.setattr(controller, "run_supervised_command", monitored)
    monkeypatch.setattr(controller, "_observed_solver_origin", lambda _text: str(science / "solveur" / "__init__.py"))
    result, code = controller.run_pytest(
        "fem_exploratory", target, "dev-adaptive001", worktree_id=controller.VV3D_WORKTREE_ID,
        reason="synthetic adaptive dispatch", preflight_id="pf-adaptive-0001", execution_manifest=manifest_path,
    )
    assert result["state"] == "PASS" and code == 0, result
    assert captured["QF_DEV_VV3D_ADAPTIVE_CANDIDATE_ID"] == candidate
    assert captured["QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256"]
    receipt_path = Path(captured["QF_DEV_VV3D_ADAPTIVE_RECEIPT_PATH"])
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["schema"] == "qf-wp12-vv3d-adaptive-runner-receipt-v1"
    assert receipt["attempt_id"] == attempt_id and receipt["reservation_id"] == reservation_id
    assert receipt["allowed_evidence_roots"] == [str(evidence), str(auth_root)]
    assert ledger.summary()["attempts_used"] == 2
    assert ledger.summary()["elapsed_seconds_actual"] == pytest.approx(6.0)
