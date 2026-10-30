"""Synthetic fail-closed checks; never run or collect a scientific test body."""
from __future__ import annotations

import copy
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import development_autonomous as controller
from scripts import wp12_vv3d_tet4_l3_diagnostic as diagnostic


def test_registration_accepts_only_exact_single_case_envelope() -> None:
    policy = {"diagnostic_scopes": {diagnostic.SCOPE: copy.deepcopy(diagnostic.REGISTRATION)}}
    assert diagnostic.registration(policy)["target"] == diagnostic.TARGET
    for key, value in (("target", diagnostic.TARGET.replace("L3", "L2")), ("attempts_max", 2),
                       ("timeout_seconds", 2401), ("execution_authorized", True)):
        changed = copy.deepcopy(policy)
        changed["diagnostic_scopes"][diagnostic.SCOPE][key] = value
        with pytest.raises(ValueError, match="registration"):
            diagnostic.registration(changed)


def test_exact_owner_decision_rejects_mutation() -> None:
    contract = {"source_fingerprint": "a" * 64, "controller_fingerprint": "b" * 64,
                "limits": {"timeout_seconds": 2400, "attempts_max": 1}}
    contract_sha = diagnostic.digest(diagnostic.canonical(contract))
    decision = {"schema": "qf-vv3d-tet4-l3-diagnostic-owner-v1", "decision_id": "synthetic-owner-01",
                "status": "APPROVED", "approved_by": "Owner", "scope_id": diagnostic.SCOPE,
                "case_id": diagnostic.CASE, "contract_sha256": contract_sha,
                "source_fingerprint": "a" * 64, "controller_fingerprint": "b" * 64,
                "limits": contract["limits"], "created_at_utc": "2026-10-30T00:00:00Z"}
    diagnostic.validate_authorization(contract, decision, contract_sha256=contract_sha)
    for field, value in (("case_id", "VV3D-TET4-L2"), ("status", "DRAFT"),
                         ("contract_sha256", "f" * 64), ("controller_fingerprint", "c" * 64)):
        changed = {**decision, field: value}
        with pytest.raises(ValueError, match="Owner decision"):
            diagnostic.validate_authorization(contract, changed, contract_sha256=contract_sha)


def test_one_attempt_ledger_is_append_only_and_refuses_retry(tmp_path: Path) -> None:
    ledger = tmp_path / "diagnostic.jsonl"
    start = diagnostic._append_record(ledger, {"event": "ATTEMPT_STARTED", "run_id": "synthetic"}, first=True)
    with pytest.raises(FileExistsError):
        diagnostic._append_record(ledger, {"event": "ATTEMPT_STARTED", "run_id": "retry"}, first=True)
    with pytest.raises(ValueError, match="reservation record"):
        diagnostic._append_record(ledger, {"event": "ATTEMPT_FINISHED", "run_id": "other"}, first=False)
    finish = diagnostic._append_record(ledger, {"event": "ATTEMPT_FINISHED", "run_id": "synthetic",
                                                "status": "DIAGNOSTIC_STOP"}, first=False)
    assert finish["previous_record_sha256"] == start["record_sha256"]
    raw = ledger.read_bytes()
    with pytest.raises(ValueError, match="single-attempt"):
        diagnostic._append_record(ledger, {"event": "ATTEMPT_FINISHED", "run_id": "retry"}, first=False)
    assert ledger.read_bytes() == raw


def test_trace_requires_one_measured_process_and_monotonic_events() -> None:
    common = {"schema": "qf-vv3d-performance-trace-v1", "case_id": diagnostic.CASE,
              "attempt_id": "synthetic", "process_id": 42}
    events = [{**common, "stage": "trace", "state": "START", "monotonic_seconds": 0.0},
              {**common, "stage": "registered_case", "state": "START", "monotonic_seconds": 1.0},
              {**common, "stage": "body_load_order_12", "state": "START", "monotonic_seconds": 2.0}]
    def encode(values):
        return b"".join(diagnostic.canonical(item) + b"\n" for item in values)
    assert diagnostic.trace_summary(encode(events), "synthetic", require_complete=False)["last_started_stage"] == "body_load_order_12"
    bad = copy.deepcopy(events)
    bad[-1]["process_id"] = 43
    with pytest.raises(ValueError, match="process identity"):
        diagnostic.trace_summary(encode(bad), "synthetic", require_complete=False)
    bad = copy.deepcopy(events)
    bad[-1]["monotonic_seconds"] = 0.5
    with pytest.raises(ValueError, match="monotonic"):
        diagnostic.trace_summary(encode(bad), "synthetic", require_complete=False)
    bad = [*events, {**common, "stage": "imports", "state": "SOLVER_ORIGIN",
                     "monotonic_seconds": 3.0, "path": "wrong-source"}]
    with pytest.raises(ValueError, match="solver origin"):
        diagnostic.trace_summary(encode(bad), "synthetic", require_complete=False, expected_origin="expected-source")
    with pytest.raises(ValueError, match="required stage"):
        diagnostic.trace_summary(encode(events), "synthetic", require_complete=True)


def test_diagnostic_preflight_requires_approved_decision_before_any_output(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(diagnostic, "REGISTRATION", {**diagnostic.REGISTRATION, "evidence_root": str(tmp_path)})
    monkeypatch.setattr(diagnostic, "inspect", lambda _: {"state": "synthetic"})
    (tmp_path / "diagnostic-contract.json").write_bytes(diagnostic.canonical({"synthetic": True}))
    with pytest.raises(FileNotFoundError):
        diagnostic.preflight(SimpleNamespace(), diagnostic.TARGET, None)
    assert not (tmp_path / "preflight").exists()
    assert not (tmp_path / diagnostic.REGISTRATION["ledger"]).exists()


def test_collect_attestor_refuses_other_node_or_execution(tmp_path: Path) -> None:
    source = tmp_path / "src"
    good = controller.build_pytest_command("fem_exploratory", [diagnostic.TARGET], tmp_path,
                                           repository_root=tmp_path, source_root=source,
                                           collect_only=True, vv3d_tet4_l3_diagnostic_attestation=True)
    assert "vv3d-tet4-l3-diagnostic-preflight" in good
    with pytest.raises(controller.PolicyError):
        controller.build_pytest_command("fem_exploratory", [diagnostic.TARGET.replace("L3", "L2")], tmp_path,
                                        repository_root=tmp_path, source_root=source,
                                        collect_only=True, vv3d_tet4_l3_diagnostic_attestation=True)
    with pytest.raises(controller.PolicyError):
        controller.build_pytest_command("fem_exploratory", [diagnostic.TARGET], tmp_path,
                                        repository_root=tmp_path, source_root=source,
                                        collect_only=False, vv3d_tet4_l3_diagnostic_attestation=True)


def test_fake_preflight_and_manifest_bind_exact_receipt_without_reservation(tmp_path: Path, monkeypatch) -> None:
    import json

    source = tmp_path / "source"
    origin = source / "src/solveur/__init__.py"
    origin.parent.mkdir(parents=True)
    origin.write_text("# synthetic", encoding="utf-8")
    criteria = source / "experiments/wp12_vv3d_adaptive/criteria.json"
    criteria.parent.mkdir(parents=True)
    criteria_raw = diagnostic.canonical({"criteria": [{"id": "finite", "threshold": None}]})
    criteria.write_bytes(criteria_raw)
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    monkeypatch.setattr(diagnostic, "REGISTRATION", {**diagnostic.REGISTRATION, "root": str(source),
                                                       "evidence_root": str(evidence)})
    report = {"source_identity": {"head": "synthetic"}, "source_fingerprint": "a" * 64,
              "controller_fingerprint": "b" * 64, "predecessor": {"r1_attempts": 2, "r2_attempts": 3}}
    contract = {"criteria_path": "criteria.json", "criteria_sha256": diagnostic.digest(criteria_raw),
                "mesh_sha256": "c" * 64}
    decision = {"decision_id": "synthetic-owner"}
    monkeypatch.setattr(diagnostic, "authorized_context", lambda _: (report, contract, decision, "d" * 64, "e" * 64))
    monkeypatch.setattr(diagnostic, "inspect", lambda _: report)
    monkeypatch.setattr(diagnostic, "build_contract", lambda _: contract)
    monkeypatch.setattr(controller, "build_pytest_command", lambda *args, **kwargs: ["fake-collection"])
    monkeypatch.setattr(controller, "build_child_environment", lambda *args, **kwargs: {})

    def fake_supervisor(command, *, cwd, environment, output_dir, temporary_dir, limits, poll_interval):
        assert command == ["fake-collection"] and limits["timeout_seconds"] == 300
        report_path = Path(environment["QF_DEV_PREFLIGHT_COLLECTION_REPORT"])
        report_path.write_bytes(diagnostic.canonical({"schema": "qfsolver-wp12-vv3d-collection-v1",
            "scope_id": diagnostic.SCOPE, "target": diagnostic.TARGET,
            "collected_nodeids": [diagnostic.TARGET], "skip_markers": [],
            "bodies_executed": False, "exitstatus": 0}))
        (output_dir / "stdout.log").write_text(f"QF_DEV_SOLVER_ORIGIN={origin.resolve()}\n", encoding="utf-8")
        (output_dir / "stderr.log").write_bytes(b"")
        return SimpleNamespace(status="PASS", elapsed_seconds=0.1)

    monkeypatch.setattr(controller, "run_supervised_command", fake_supervisor)
    result = diagnostic.preflight(controller, diagnostic.TARGET, "pf-123456789abc")
    assert result["state"] == "PREFLIGHT_PASS" and result["attempt_reserved"] is False
    prepared = diagnostic.prepare_manifest(controller, result["preflight_id"])
    manifest = json.loads(Path(prepared["manifest"]).read_bytes())
    assert manifest["scope_id"] == diagnostic.SCOPE and manifest["timeout_seconds"] == 2400
    assert manifest["preflight"]["receipt_sha256"] == result["receipt_sha256"]
    assert not (evidence / diagnostic.REGISTRATION["ledger"]).exists()


def test_fake_diagnostic_timeout_preserves_trace_and_refuses_retry(tmp_path: Path, monkeypatch) -> None:
    """A simulated process tests reservation/STOP without executing a FEM body."""
    import json

    evidence = tmp_path / "diagnostic"
    source = tmp_path / "source"
    source.mkdir()
    origin = source / "src/solveur/__init__.py"
    origin.parent.mkdir(parents=True)
    origin.write_text("# synthetic", encoding="utf-8")
    r1 = tmp_path / "r1.jsonl"
    r2 = tmp_path / "r2.jsonl"
    r1.write_bytes(b"immutable-r1")
    r2.write_bytes(b"immutable-r2")
    originals = (r1.read_bytes(), r2.read_bytes())
    config = {**diagnostic.REGISTRATION, "root": str(source), "evidence_root": str(evidence)}
    monkeypatch.setattr(diagnostic, "REGISTRATION", config)
    monkeypatch.setattr(diagnostic, "R2_ROOT", tmp_path / "r2-root")
    prior = {"r1_attempts": 2, "r2_attempts": 3, "elapsed_seconds": 1355.0,
             "r1_sha256": config["r1_sha256"], "r2_sha256": config["r2_sha256"]}
    report = {"source_identity": {"head": "fake"}, "source_fingerprint": "a" * 64,
              "controller_fingerprint": "b" * 64, "predecessor": prior}
    contract = {"synthetic": True}
    decision = {"decision_id": "synthetic-owner"}
    contract_sha, decision_sha = "c" * 64, "d" * 64
    monkeypatch.setattr(diagnostic, "authorized_context", lambda _: (report, contract, decision, contract_sha, decision_sha))
    monkeypatch.setattr(diagnostic, "predecessor_history", lambda _: prior)
    monkeypatch.setattr(diagnostic, "controller_provenance", lambda _: {})
    monkeypatch.setattr(diagnostic, "build_contract", lambda _: contract)
    manifest_path = evidence / "manifests" / "synthetic.json"
    manifest_path.parent.mkdir(parents=True)
    manifest = {"authorization_id": "synthetic-auth", "preflight": {"receipt_sha256": "e" * 64}}
    manifest_path.write_bytes(diagnostic.canonical(manifest))
    monkeypatch.setattr(diagnostic, "manifest_payload", lambda *_: (manifest_path, manifest))
    monkeypatch.setattr(controller, "_exclusive_file_lock", lambda _: nullcontext())
    monkeypatch.setattr(controller, "build_pytest_command", lambda *args, **kwargs: ["fake-child"])
    monkeypatch.setattr(controller, "build_child_environment", lambda *args, **kwargs: {})
    monkeypatch.setattr(controller, "_git_identity", lambda *args, **kwargs: report["source_identity"])
    monkeypatch.setattr(controller, "_worktree_source_fingerprint", lambda *args, **kwargs: report["source_fingerprint"])
    monkeypatch.setattr(controller, "_stable_fingerprint", lambda _: report["controller_fingerprint"])

    def fake_supervisor(command, *, cwd, environment, output_dir, temporary_dir, limits, poll_interval):
        assert command == ["fake-child"] and environment["QF_VV3D_PERFORMANCE_TRACE"] == "1"
        assert limits["timeout_seconds"] == 2400 and cwd == source
        receipt = json.loads(Path(environment["QF_DEV_VV3D_RUNNER_RECEIPT_PATH"]).read_bytes())
        trace = evidence / "diagnostic-timings" / diagnostic.CASE / receipt["attempt_id"] / "stages.jsonl"
        trace.parent.mkdir(parents=True)
        common = {"schema": "qf-vv3d-performance-trace-v1", "case_id": diagnostic.CASE,
                  "attempt_id": receipt["attempt_id"], "process_id": 123}
        trace.write_bytes(diagnostic.canonical({**common, "stage": "trace", "state": "START",
                                                "monotonic_seconds": 0.0}) + b"\n" +
                          diagnostic.canonical({**common, "stage": "registered_case", "state": "START",
                                                "monotonic_seconds": 0.1}) + b"\n")
        (output_dir / "stdout.log").write_bytes(b"")
        (output_dir / "stderr.log").write_bytes(b"")
        return SimpleNamespace(status="WALL_TIMEOUT_EXCEEDED", stop_reason="WALL_TIMEOUT_EXCEEDED",
                               elapsed_seconds=2400.1, peak_rss_bytes=123)

    monkeypatch.setattr(controller, "run_supervised_command", fake_supervisor)
    result, exit_code = diagnostic.run(controller, diagnostic.TARGET, "synthetic", "pf-123456789abc", manifest_path)
    assert exit_code == 1 and result["state"] == "DIAGNOSTIC_STOP"
    assert Path(result["trace"]).is_file() and result["r2_unlocked"] is False
    assert result["trace_summary"]["process_id"] == 123
    assert result["trace_summary"]["last_started_stage"] == "registered_case"
    ledger = evidence / config["ledger"]
    assert [json.loads(line)["event"] for line in ledger.read_bytes().splitlines()] == ["ATTEMPT_STARTED", "ATTEMPT_FINISHED"]
    with pytest.raises(ValueError, match="retry is forbidden"):
        diagnostic.run(controller, diagnostic.TARGET, "synthetic", "pf-123456789abc", manifest_path)
    assert (r1.read_bytes(), r2.read_bytes()) == originals
