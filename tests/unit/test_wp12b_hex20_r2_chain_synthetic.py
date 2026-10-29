"""Synthetic R2 contract chain; no scientific test body is executed."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from scripts import development_autonomous as c


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    store = tmp_path / "evidence"
    science = tmp_path / "science"
    science.mkdir()
    predecessor = tmp_path / "r1.json"
    r1key = f"{c.WP12B_HEX20_R1_MANDATE_ID}:{c.WP12B_HEX20_DIAGNOSTIC_WORKTREE_ID}:{c.WP12B_HEX20_DIAGNOSTIC_NODEID}"
    _write(predecessor, {"schema": "qfsolver-development-node-ledger-v1", "mandate_id": c.WP12B_HEX20_R1_MANDATE_ID,
                         "entries": {r1key: [{"attempt": 1, "state": "PROVENANCE_MISMATCH"}]}})
    monkeypatch.setattr(c, "WP12B_HEX20_R1_LEDGER_PATH", predecessor)
    monkeypatch.setattr(c, "WP12B_HEX20_R1_LEDGER_SHA256", c._sha256(predecessor))
    binding = {"path": str(predecessor.resolve()), "sha256": c.WP12B_HEX20_R1_LEDGER_SHA256,
               "mandate_id": c.WP12B_HEX20_R1_MANDATE_ID}
    entry = {"root": str(science), "source_root": "src", "evidence_root": str(store),
             "development_mandate_id": c.WP12B_HEX20_R2_MANDATE_ID,
             "campaign_id": "R2-SYNTHETIC", "target_max_dofs": 60, "attempt_limit_per_nodeid": 1,
             "max_fem_cases_per_attempt": 1,
             "max_total_attempts": 1, "budgets": {"timeout_seconds": 300, **c.WP12_RUN_BUDGETS},
             "node_attempt_ledger": {"path": "node-attempt-ledger-r2.json", "predecessor": binding}}
    policy = {"worktrees": {c.WP12B_HEX20_R2_WORKTREE_ID: entry}}
    target = c.WP12B_HEX20_DIAGNOSTIC_NODEID
    identity = {"head": "a" * 40, "tree": "b" * 40, "branch": "synthetic", "status_short": ""}
    fp = "c" * 64
    prov = {"synthetic": "controller"}
    registration = {"target": target, "source_fingerprint": fp, "timeout_seconds": 300,
                    "selected_dofs": 60, "selection_basis": "synthetic", "timeout_reason": None}
    monkeypatch.setattr(c, "_wp12_active_registration", lambda *a, **k: registration)
    lid = "pf-012345abcdef"
    ledger, lock, mandate, _ = c._node_ledger_context(policy, store, c.WP12B_HEX20_R2_WORKTREE_ID)
    origin = str((science / "src" / "solveur" / "__init__.py").resolve())
    receipt = {"schema": "qfsolver-development-wp12b-hex20-r2-preflight-v1", "state": "PREFLIGHT_PASS",
               "mode": "DEVELOPMENT_AUTONOMOUS", "mandate_id": mandate, "worktree_id": c.WP12B_HEX20_R2_WORKTREE_ID,
               "target": target, "preflight_id": lid, "phase": "PYTEST_COLLECT_ONLY", "bodies_executed": False,
               "attempt_reserved": False, "ledger_touched": False, "identity": identity, "identity_after": identity,
               "source_fingerprint": fp, "source_fingerprint_after": fp, "controller_provenance": prov,
               "controller_provenance_after": prov, "solver_origin_expected": origin, "solver_origin_observed": origin,
               "collected_nodeids": [target], "skip_markers": [], "return_code": 0, "registration": registration,
               "budgets": entry["budgets"], "attempt_ledger": {"path": str(ledger), "touched": False,
               "sha256_before": None, "sha256_after": None, "predecessor": binding,
               "predecessor_sha256_before": binding["sha256"], "predecessor_sha256_after": binding["sha256"]}}
    path = c._preflight_directory(store, c.WP12B_HEX20_R2_WORKTREE_ID, lid) / "preflight.json"
    output = path.parent / "output"
    output.mkdir(parents=True)
    attestation = {"schema": c.WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_SCHEMA,
        "worktree_id": c.WP12B_HEX20_R2_WORKTREE_ID, "expected_nodeid": target, "collected_nodeids": [target],
        "solver_origin": origin, "skip_markers": [], "bodies_executed": False,
        "selected_dofs_expected": 60, "selected_dofs": "60", "max_dofs_expected": 60, "max_dofs": "60",
        "exitstatus": 0}
    (output / "stdout.log").write_text("QF_DEV_SOLVER_ORIGIN=" + origin + "\n"
        + c.WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_MARKER + json.dumps(attestation), encoding="utf-8")
    (output / "stderr.log").write_text("", encoding="utf-8")
    receipt["stdout_sha256"] = c._sha256(output / "stdout.log")
    receipt["stderr_sha256"] = c._sha256(output / "stderr.log")
    _write(path, receipt)
    _write(path.with_name("preflight.sha256.json"), {"sha256": c._sha256(path)})
    return locals()


def test_r2_synthetic_preflight_manifest_reservation_and_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    f = _fixture(tmp_path, monkeypatch)
    path, digest = c._validate_wp12b_hex20_r2_preflight_receipt(f["store"], f["lid"], target=f["target"],
        identity=f["identity"], source_fingerprint=f["fp"], controller_provenance=f["prov"], policy=f["policy"])
    manifest = {"schema": "qfsolver-wp12-development-execution-v1", "state": "OWNER_AUTHORIZED",
        "execution_authorized": True, "do_not_execute": False, "authorization_id": "synthetic-auth-1",
        "worktree_id": c.WP12B_HEX20_R2_WORKTREE_ID, "mandate_id": f["mandate"], "campaign_id": "R2-SYNTHETIC",
        "target": f["target"], "identity": f["identity"], "source_fingerprint": f["fp"],
        "controller_fingerprint": "d" * 64, "limits": c._wp12_manifest_limits(f["entry"], f["registration"]),
        "scientific_criteria": c.WP12B_HEX20_R2_CRITERIA,
        "owner_decision": {"status": "APPROVED", "approved_by": "Owner", "approved_at_utc": "2026-10-29T10:00:00+00:00",
                           "reason": "Synthetic decision for contract test only", "decision_id": "synthetic-decision-1"},
        "preflight": {"preflight_id": f["lid"], "receipt_path": str(path), "receipt_sha256": digest}}
    manifest_path = f["store"] / "authorizations" / c.WP12B_HEX20_R2_WORKTREE_ID / "synthetic.json"
    _write(manifest_path, manifest)
    receipt = c._validate_wp12_execution_manifest(manifest_path, worktree_id=c.WP12B_HEX20_R2_WORKTREE_ID,
        target=f["target"], entry=f["entry"], identity=f["identity"], source_fingerprint=f["fp"],
        controller_fingerprint="d" * 64, selection=f["registration"], preflight_id=f["lid"], preflight_receipt=(path, digest))
    c._validate_wp12b_decision_receipt(receipt)
    key, number = c._reserve_node_attempt(f["ledger"], f["lock"], mandate_id=f["mandate"],
        worktree_id=c.WP12B_HEX20_R2_WORKTREE_ID, target=f["target"], series_id="dev-synthetic",
        source_fingerprint=f["fp"], controller_fingerprint="d" * 64, reason="synthetic only", maximum=1, total_maximum=1,
        authorization_id=receipt["authorization_id"], owner_decision_id=receipt["decision_id"], predecessor=f["binding"],
        require_ledger_snapshot=True)
    with pytest.raises(c.PolicyError, match="already been consumed"):
        c._validate_wp12b_hex20_r2_preflight_receipt(f["store"], f["lid"], target=f["target"],
            identity=f["identity"], source_fingerprint=f["fp"], controller_provenance=f["prov"], policy=f["policy"])
    run_path = f["store"] / "run.json"
    attempt_id = "dev-synthetic-attempt-1"
    _write(run_path, {"controller_attempt_id": attempt_id, "worktree_id": c.WP12B_HEX20_R2_WORKTREE_ID,
        "target": f["target"], "series_id": "dev-synthetic", "attempt": number, "execution_manifest": receipt,
        "wp12_case_selection": {"selected_dofs": 60}})
    sidecar = f["store"] / "wp12b_hex20_affine_diagnostic" / f"{attempt_id}.json"
    _write(sidecar, {"schema": "qfsolver-wp12b-hex20-affine-diagnostic-v2", "identity": {"nodeid": f["target"]},
        "diagnostic_criteria": {"r2_face_nodal_gate": {"rtol": 1e-12, "atol_N": 1e-6,
            "status": "PROPOSED_FOR_OWNER; ASSERTED_AFTER_PRE_ASSERTION_ARCHIVE"}},
        "controller": {"worktree_id": c.WP12B_HEX20_R2_WORKTREE_ID, "selected_dofs": 60,
        "controller_attempt_id": attempt_id, "manifest_id": receipt["authorization_id"],
        "manifest_sha256": receipt["sha256"], "run_json_path": str(run_path.resolve())}})
    result = c._wp12b_hex20_diagnostic_sidecar(worktree_id=c.WP12B_HEX20_R2_WORKTREE_ID, target=f["target"],
        evidence_root=str(f["store"]), attempt_id=attempt_id, manifest_receipt=receipt, selected_dofs=60,
        run_json_path=run_path, sidecar_limit_bytes=100000)
    assert result["status"] == "VERIFIED"
    sidecar_payload = json.loads(sidecar.read_text(encoding="utf-8"))
    sidecar_payload["schema"] = "qfsolver-wp12b-hex20-affine-diagnostic-v3"
    _write(sidecar, sidecar_payload)
    rejected = c._wp12b_hex20_diagnostic_sidecar(worktree_id=c.WP12B_HEX20_R2_WORKTREE_ID, target=f["target"],
        evidence_root=str(f["store"]), attempt_id=attempt_id, manifest_receipt=receipt, selected_dofs=60,
        run_json_path=run_path, sidecar_limit_bytes=100000)
    assert rejected["status"] == "PROVENANCE_MISMATCH"
    sidecar_payload["schema"] = "qfsolver-wp12b-hex20-affine-diagnostic-v2"
    _write(sidecar, sidecar_payload)
    c._complete_node_attempt(f["ledger"], f["lock"], key=key, attempt_number=number, state="PASS",
        finished_at_utc="2026-10-29T10:00:01+00:00", post_fingerprint=f["fp"],
        worktree_id=c.WP12B_HEX20_R2_WORKTREE_ID, expected_ledger_sha256=c._sha256(f["ledger"]))
    assert json.loads(f["ledger"].read_text())["entries"][key][0]["state"] == "PASS"
    assert hashlib.sha256(f["predecessor"].read_bytes()).hexdigest() == f["binding"]["sha256"]


def test_r2_preflight_writer_emits_receipt_accepted_by_validator(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    f = _fixture(tmp_path, monkeypatch)
    monkeypatch.setattr(c, "resolve_targets", lambda *a, **k: [f["target"]])
    monkeypatch.setattr(c, "_registered_worktree", lambda *a, **k: (
        f["entry"], f["science"], f["science"] / "src", f["identity"], f["fp"]
    ))
    f["policy"].update(minimum_free_disk_mib=1, poll_interval_seconds=0.01)
    monkeypatch.setattr(c, "load_policy", lambda *a: f["policy"])
    monkeypatch.setattr(c, "_run_root", lambda *a: f["store"])
    monkeypatch.setattr(c, "_controller_provenance", lambda: f["prov"])
    monkeypatch.setattr(c, "build_child_environment", lambda *a, **k: {})
    monkeypatch.setattr(c, "psutil", object())
    monkeypatch.setattr(c.shutil, "disk_usage", lambda *a: SimpleNamespace(free=10**12))
    origin = f["receipt"]["solver_origin_expected"]
    payload = {"schema": c.WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_SCHEMA,
        "worktree_id": c.WP12B_HEX20_R2_WORKTREE_ID, "expected_nodeid": f["target"],
        "collected_nodeids": [f["target"]], "solver_origin": origin, "skip_markers": [],
        "bodies_executed": False, "selected_dofs_expected": 60, "selected_dofs": "60",
        "max_dofs_expected": 60, "max_dofs": "60", "exitstatus": 0}
    def supervised(command, *, output_dir, **kwargs):
        assert "--collect-only" in command and command[-1] == f["target"]
        (output_dir / "stdout.log").write_text("QF_DEV_SOLVER_ORIGIN=" + origin + "\n"
            + c.WP12B_HEX20_DIAGNOSTIC_PREFLIGHT_MARKER + json.dumps(payload), encoding="utf-8")
        (output_dir / "stderr.log").write_text("", encoding="utf-8")
        return SimpleNamespace(status="PASS", return_code=0, elapsed_seconds=0.01, peak_rss_bytes=1,
            peak_process_count=1, stdout_bytes=1, stderr_bytes=0)
    monkeypatch.setattr(c, "run_supervised_command", supervised)
    result = c.preflight_wp12b_hex20_diagnostic_pytest(
        f["target"], "pf-abcdef012345", policy=f["policy"], worktree_id=c.WP12B_HEX20_R2_WORKTREE_ID
    )
    assert result["state"] == "PREFLIGHT_PASS"
    validated = c._validate_wp12b_hex20_r2_preflight_receipt(f["store"], result["preflight_id"],
        target=f["target"], identity=f["identity"], source_fingerprint=f["fp"],
        controller_provenance=f["prov"], policy=f["policy"])
    assert validated == (Path(result["receipt"]), result["receipt_sha256"])
    assert not f["ledger"].exists()


@pytest.mark.parametrize("mutation", ["decision", "nodeid", "fingerprint", "budget", "preflight", "prepared", "criteria"])
def test_r2_manifest_refuses_inconsistent_authorization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation):
    f = _fixture(tmp_path, monkeypatch)
    path, digest = c._validate_wp12b_hex20_r2_preflight_receipt(f["store"], f["lid"], target=f["target"],
        identity=f["identity"], source_fingerprint=f["fp"], controller_provenance=f["prov"], policy=f["policy"])
    manifest = {"schema": "qfsolver-wp12-development-execution-v1", "state": "OWNER_AUTHORIZED",
        "execution_authorized": True, "do_not_execute": False, "authorization_id": "synthetic-auth-1",
        "worktree_id": c.WP12B_HEX20_R2_WORKTREE_ID, "mandate_id": f["mandate"], "campaign_id": "R2-SYNTHETIC",
        "target": f["target"], "identity": f["identity"], "source_fingerprint": f["fp"],
        "controller_fingerprint": "d" * 64, "limits": c._wp12_manifest_limits(f["entry"], f["registration"]),
        "scientific_criteria": dict(c.WP12B_HEX20_R2_CRITERIA),
        "owner_decision": {"status": "APPROVED", "approved_by": "Owner", "approved_at_utc": "2026-10-29T10:00:00+00:00",
            "reason": "Synthetic decision for contract test only", "decision_id": "synthetic-decision-1"},
        "preflight": {"preflight_id": f["lid"], "receipt_path": str(path), "receipt_sha256": digest}}
    if mutation == "decision":
        manifest["owner_decision"] = None
    elif mutation == "nodeid":
        manifest["target"] = "unknown"
    elif mutation == "fingerprint":
        manifest["source_fingerprint"] = "f" * 64
    elif mutation == "budget":
        manifest["limits"]["timeout_seconds"] = 301
    elif mutation == "preflight":
        manifest["preflight"]["receipt_sha256"] = "0" * 64
    elif mutation == "criteria":
        manifest["scientific_criteria"]["moment_balance_max"] = 1e-6
    else:
        manifest["state"] = "PREPARED_NOT_AUTHORIZED"
    manifest_path = f["store"] / "authorizations" / c.WP12B_HEX20_R2_WORKTREE_ID / "synthetic.json"
    _write(manifest_path, manifest)
    with pytest.raises(c.PolicyError):
        c._validate_wp12_execution_manifest(manifest_path, worktree_id=c.WP12B_HEX20_R2_WORKTREE_ID,
            target=f["target"], entry=f["entry"], identity=f["identity"], source_fingerprint=f["fp"],
            controller_fingerprint="d" * 64, selection=f["registration"], preflight_id=f["lid"],
            preflight_receipt=(path, digest))
    assert not f["ledger"].exists()


@pytest.mark.parametrize("field,value", [("target", "wrong"), ("source_fingerprint", "wrong"),
    ("skip_markers", ["skip"]), ("bodies_executed", True), ("attempt_reserved", True), ("budgets", {})])
def test_r2_synthetic_preflight_refuses_tampering(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field, value):
    f = _fixture(tmp_path, monkeypatch)
    f["receipt"][field] = value
    _write(f["path"], f["receipt"])
    _write(f["path"].with_name("preflight.sha256.json"), {"sha256": c._sha256(f["path"])})
    with pytest.raises(c.PolicyError):
        c._validate_wp12b_hex20_r2_preflight_receipt(f["store"], f["lid"], target=f["target"],
            identity=f["identity"], source_fingerprint=f["fp"], controller_provenance=f["prov"], policy=f["policy"])
    assert not f["ledger"].exists()
