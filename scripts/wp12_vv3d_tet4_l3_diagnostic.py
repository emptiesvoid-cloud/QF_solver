"""One prospective TET4-L3 performance diagnostic; never reopens R2.

The separate diagnostic scope is preparation-only until an exact Owner
decision binds its frozen contract. The historical R1 and R2 ledgers are
read-only predecessors and remain subject to their original STOP state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

SCOPE = "wp12_vv3d_tet4_l3_optimized_diagnostic"
PREVIOUS_SCOPE = "wp12_vv3d_tet4_l3_diagnostic"
PREVIOUS_EVIDENCE_ROOT = Path(r"E:\QFSolverAgents\evidence\wp12-vv3d-tet4-l3-diagnostic")
CAMPAIGN = "WP12-VV3D-RECOVERY-20261030-R2"
CASE = "VV3D-TET4-L3"
TARGET = "tests/unit/test_wp12_vv3d_adaptive_prepared.py::test_prepared_fem_case[VV3D-TET4-L3]"
R1_PATH = Path(r"E:\QFSolverAgents\evidence\wp12-vv3d-adaptive\node-attempt-ledger-wp12-vv3d-adaptive-r1.jsonl")
R2_ROOT = Path(r"E:\QFSolverAgents\evidence\wp12-vv3d-recovery-r2")
R2_PATH = R2_ROOT / "node-attempt-ledger-wp12-vv3d-recovery-r2.jsonl"
R2_CONTRACT_PATH = R2_ROOT / "authorizations/wp12_vv3d_recovery_r2/campaign-contract.json"
R2_CONTRACT_SHA256 = "62fcb9a63ef0f5d4b557f4e4a7ec6d076ca34bb4b4fcd4f139aa6a0f1c499e16"
PREVIOUS_DIAGNOSTIC_PATH = Path(
    r"E:\QFSolverAgents\evidence\wp12-vv3d-tet4-l3-diagnostic\node-attempt-ledger-vv3d-tet4-l3-diagnostic.jsonl"
)
REGISTRATION = {
    "root": r"E:\QFSolverAgents\worktrees\vv3d-tet4-l3-optimized\qf_solver",
    "branch": "codex/vv3d-tet4-l3-optimized",
    "head": "096857b890353c8cf1c8e02007fe97c5455cb50a",
    "tree": "ca84f375e4aaf91bee3fd42bfa87406c796681bd",
    "source_fingerprint_sha256": "d2ccee34ab5aba092bcacfa98e2d3332edc7fe02c9e1c7b39de092a59635d39b",
    "field_error_draft_sha256": "77a7ce40524769c79ca30ad2bea3ce1fdcefb2e1fe1f79a34ea756cf1b93ee7d",
    "target": TARGET,
    "evidence_root": r"E:\QFSolverAgents\evidence\wp12-vv3d-tet4-l3-optimized-diagnostic",
    "ledger": "node-attempt-ledger-vv3d-tet4-l3-optimized-diagnostic.jsonl",
    "r1_sha256": "2788619d097d148c74a3e71cef456ee52bc03642d680f9090360418b61d20bf8",
    "r2_sha256": "5e090e1351578803669af37f04d161a6c4608436763f87d71e03315978446bb5",
    "predecessor_diagnostic_sha256": "3dfab79fabd3ae5986b265ecdebf6a4ed1030f3806ab25ae12f0a9d4a1f5e6c4",
    "timeout_seconds": 1200,
    "preflight_timeout_seconds": 300,
    "rss_soft_limit_mib": 4096,
    "selected_dofs": 2187,
    "max_dofs": 30000,
    "archive_size_limit_mib": 256,
    "attempts_max": 1,
    "combined_attempts_max": 24,
    "cumulative_seconds_max": 28800,
    "concurrency": 1,
    "implicit_retry": False,
    "execution_authorized": False,
}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def registration(policy: Mapping[str, Any]) -> dict[str, Any]:
    scopes = policy.get("diagnostic_scopes")
    if (not isinstance(scopes, Mapping) or set(scopes) != {PREVIOUS_SCOPE, SCOPE}
            or scopes[SCOPE] != REGISTRATION):
        raise ValueError("optimized TET4-L3 registration does not match its exact prospective envelope")
    return dict(REGISTRATION)


def controller_provenance(controller: Any) -> dict[str, Any]:
    provenance = controller._vv3d_scope_controller_provenance(controller.VV3D_R2_WORKTREE_ID)
    provenance["sha256"] = {**provenance["sha256"], "tet4_l3_optimized_diagnostic": controller._sha256(Path(__file__).resolve())}
    provenance["vv3d_tet4_l3_optimized_diagnostic_revision"] = "separate-ledger-linked-history-v1"
    return provenance


def validate_previous_diagnostic_ledger(raw: bytes, expected_sha256: str) -> dict[str, Any]:
    """Validate the immutable prior STOP ledger from bytes without writing it."""
    import math

    if digest(raw) != expected_sha256 or not raw.endswith(b"\n"):
        raise ValueError("previous diagnostic ledger digest or final newline mismatch")
    lines = raw.splitlines()
    if len(lines) != 2:
        raise ValueError("previous diagnostic ledger must contain exactly one start and one terminal record")
    records = []
    for line in lines:
        record = json.loads(line)
        if canonical(record) != line:
            raise ValueError("previous diagnostic ledger records are not canonical JSON")
        claimed = record.pop("record_sha256", None)
        if not isinstance(claimed, str) or digest(canonical(record)) != claimed:
            raise ValueError("previous diagnostic ledger record hash mismatch")
        record["record_sha256"] = claimed
        records.append(record)
    start, finish = records
    prior_elapsed = start.get("prior_elapsed_seconds")
    elapsed = finish.get("elapsed_seconds")
    combined_elapsed = finish.get("combined_elapsed_seconds")
    numeric = (prior_elapsed, elapsed, combined_elapsed)
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) for value in numeric):
        raise ValueError("previous diagnostic ledger has invalid elapsed-time values")
    if (start.get("schema") != "qf-vv3d-tet4-l3-diagnostic-ledger-v1"
            or finish.get("schema") != start.get("schema")
            or start.get("event") != "ATTEMPT_STARTED" or finish.get("event") != "ATTEMPT_FINISHED"
            or start.get("scope_id") != PREVIOUS_SCOPE or finish.get("scope_id") != PREVIOUS_SCOPE
            or start.get("case_id") != CASE or finish.get("case_id") != CASE
            or start.get("sequence") != 1 or finish.get("sequence") != 2
            or start.get("previous_record_sha256") != "0" * 64
            or finish.get("previous_record_sha256") != start["record_sha256"]
            or start.get("run_id") != finish.get("run_id")
            or start.get("attempt_id") != finish.get("attempt_id")
            or start.get("prior_attempts") != 5 or start.get("reserved_seconds") != 2400
            or start.get("r1_sha256") != REGISTRATION["r1_sha256"]
            or start.get("r2_sha256") != REGISTRATION["r2_sha256"]
            or finish.get("r1_sha256") != REGISTRATION["r1_sha256"]
            or finish.get("r2_sha256") != REGISTRATION["r2_sha256"]
            or finish.get("status") != "DIAGNOSTIC_STOP"
            or finish.get("combined_elapsed_seconds") != prior_elapsed + elapsed
            or elapsed <= 0):
        raise ValueError("previous diagnostic ledger history is inconsistent or not terminal STOP")
    return {"attempts": 1, "elapsed_seconds": elapsed, "prior_attempts": start["prior_attempts"],
            "prior_elapsed_seconds": prior_elapsed, "combined_elapsed_seconds": combined_elapsed,
            "status": finish["status"], "scope_id": PREVIOUS_SCOPE, "case_id": CASE,
            "ledger_sha256": expected_sha256}


def combined_budget(predecessor: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    """Account R1, R2 and the closed diagnostic before the proposed reservation."""
    import math

    attempts_before = (predecessor["r1_attempts"] + predecessor["r2_attempts"]
                       + predecessor["previous_diagnostic_attempts"])
    elapsed_before = predecessor["elapsed_seconds"]
    if (isinstance(attempts_before, bool) or not isinstance(attempts_before, int)
            or isinstance(elapsed_before, bool) or not isinstance(elapsed_before, (int, float))
            or not math.isfinite(elapsed_before) or elapsed_before < 0):
        raise ValueError("combined diagnostic budget inputs are invalid")
    attempts_after = attempts_before + config["attempts_max"]
    elapsed_after = elapsed_before + config["timeout_seconds"]
    if attempts_after > config["combined_attempts_max"]:
        raise ValueError("optimized diagnostic would exceed the historical combined attempt budget")
    if elapsed_after > config["cumulative_seconds_max"]:
        raise ValueError("optimized diagnostic reservation would exceed the historical combined time budget")
    return {"attempts_before": attempts_before, "attempts_after_reservation": attempts_after,
            "elapsed_seconds_before": elapsed_before, "elapsed_seconds_after_reservation": elapsed_after,
            "attempt_limit": config["combined_attempts_max"],
            "elapsed_limit_seconds": config["cumulative_seconds_max"]}


def predecessor_history(controller: Any) -> dict[str, Any]:
    """Validate the exact closed predecessor chain without writing either ledger."""
    if digest(R1_PATH.read_bytes()) != REGISTRATION["r1_sha256"]:
        raise ValueError("R1 predecessor digest mismatch")
    if digest(R2_PATH.read_bytes()) != REGISTRATION["r2_sha256"]:
        raise ValueError("R2 predecessor digest mismatch")
    ledger_class = controller._load_vv3d_r2_ledger_module().RecoveryR2Ledger
    ledger = ledger_class(R2_PATH, allowed_root=R2_ROOT, predecessor_path=R1_PATH,
                          predecessor_sha256=REGISTRATION["r1_sha256"])
    records = ledger._read_unlocked()
    starts = [record for record in records if record.get("event") == "ATTEMPT_STARTED"]
    finishes = [record for record in records if record.get("event") == "ATTEMPT_FINISHED"]
    if ([r.get("case_id") for r in starts] != ["VV3D-TET4-L1", "VV3D-TET4-L2", CASE]
            or [r.get("status") for r in finishes] != ["PASS", "PASS", "INFRA_ERROR"]
            or len(finishes) != 3 or finishes[-1].get("case_id") != CASE):
        raise ValueError("R2 predecessor must retain its exact closed PASS/PASS/STOP history")
    attempts_r1, elapsed_r1 = ledger._predecessor()
    elapsed_r2 = sum(float(record["elapsed_seconds"]) for record in finishes)
    if attempts_r1 != 2 or digest(R2_PATH.read_bytes()) != REGISTRATION["r2_sha256"]:
        raise ValueError("predecessor ledger changed during validation")
    previous_diagnostic = validate_previous_diagnostic_ledger(
        PREVIOUS_DIAGNOSTIC_PATH.read_bytes(), REGISTRATION["predecessor_diagnostic_sha256"]
    )
    if (previous_diagnostic["prior_attempts"] != attempts_r1 + len(starts)
            or previous_diagnostic["prior_elapsed_seconds"] != elapsed_r1 + elapsed_r2):
        raise ValueError("previous diagnostic ledger does not account for the exact R1/R2 history")
    result = {"r1_attempts": attempts_r1, "r2_attempts": len(starts),
            "previous_diagnostic_attempts": previous_diagnostic["attempts"],
            "elapsed_seconds": elapsed_r1 + elapsed_r2 + previous_diagnostic["elapsed_seconds"],
            "r1_sha256": REGISTRATION["r1_sha256"], "r2_sha256": REGISTRATION["r2_sha256"]}
    result["previous_diagnostic_sha256"] = previous_diagnostic["ledger_sha256"]
    return result


def inspect(controller: Any) -> dict[str, Any]:
    """Verify source, controller and frozen predecessors without launching pytest."""
    config = registration(controller.load_policy())
    if (config["branch"] is None or config["head"] is None or config["tree"] is None
            or config["source_fingerprint_sha256"] is None
            or config["field_error_draft_sha256"] is None):
        raise ValueError("optimized diagnostic is disabled until the exact scientific source identity is frozen")
    source = Path(config["root"]).resolve(strict=True)
    identity = controller._git_identity(source, expected_branch=config["branch"],
                                        baseline_commit="f882da561e868bf9b7cdbb25d6ba20634bbdffb3")
    fingerprint = controller._worktree_source_fingerprint(source, TARGET)
    if (identity["head"] != config["head"] or identity["tree"] != config["tree"]
            or identity["status_short"] or fingerprint != config["source_fingerprint_sha256"]):
        raise ValueError("optimized diagnostic source is not the exact clean frozen identity")
    if digest((source / "experiments/wp12_vv3d_adaptive/field_error_draft.py").read_bytes()) != config["field_error_draft_sha256"]:
        raise ValueError("optimized diagnostic field-error source bytes do not match their frozen digest")
    provenance = controller_provenance(controller)
    if provenance["identity"]["status_short"] or provenance["identity"]["branch"]:
        raise ValueError("diagnostic controller must be a clean detached checkout")
    predecessor = predecessor_history(controller)
    evidence = Path(config["evidence_root"])
    if (evidence / config["ledger"]).exists():
        raise ValueError("diagnostic ledger already exists; no implicit retry is permitted")
    budget = combined_budget(predecessor, config)
    if Path(config["evidence_root"]).resolve() == PREVIOUS_EVIDENCE_ROOT.resolve():
        raise ValueError("optimized diagnostic must use its distinct new evidence root")
    return {"state": "DIAGNOSTIC_PREPARED_NOT_AUTHORIZED", "scope_id": SCOPE, "target": TARGET,
            "source_identity": identity, "source_fingerprint": fingerprint,
            "controller_provenance": provenance,
            "controller_fingerprint": controller._stable_fingerprint(provenance),
            "predecessor": predecessor, "combined_budget": budget, "limits": {key: config[key] for key in (
                "timeout_seconds", "preflight_timeout_seconds", "rss_soft_limit_mib", "selected_dofs", "max_dofs",
                "archive_size_limit_mib", "attempts_max", "combined_attempts_max", "cumulative_seconds_max",
                "concurrency", "implicit_retry")},
            "ledger_exists": False, "attempt_reserved": False}


def build_contract(report: Mapping[str, Any]) -> dict[str, Any]:
    """Derive the exact contract from the measured source and predecessor state."""
    source = Path(REGISTRATION["root"])
    experiment = source / "experiments/wp12_vv3d_adaptive"
    matrix = json.loads((experiment / "prepared_20261030_r2/MATRIX_NOT_AUTHORIZED.json").read_bytes())
    case = next(item for item in matrix["cases"] if item["case_id"] == CASE)
    prior_raw = R2_CONTRACT_PATH.read_bytes()
    if digest(prior_raw) != R2_CONTRACT_SHA256:
        raise ValueError("approved R2 predecessor contract bytes changed")
    prior = json.loads(prior_raw)
    prior_case = next(item for item in prior["cases"] if item["case_id"] == CASE)
    if (prior_case["nodeid"] != TARGET or prior_case["mesh_sha256"] != case["mesh_sha256"]
            or prior_case["selected_dofs"] != case["dofs"] or case["dofs"] != REGISTRATION["selected_dofs"]
            or prior_case["criteria_path"] != case["criteria_path"]
            or prior_case["criteria_file_sha256"] != case["criteria_file_sha256"]
            or prior_case["oracle_path"] != case["oracle_path"] or prior_case["oracle_sha256"] != case["oracle_sha256"]):
        raise ValueError("diagnostic case or scientific criteria differ from the approved R2 predecessor")
    mesh = experiment / "prepared_20261030_r2" / case["mesh_file"]
    criteria = experiment / case["criteria_path"]
    oracle = experiment / case["oracle_path"]
    for path, expected in ((mesh, case["mesh_sha256"]), (criteria, case["criteria_file_sha256"]),
                           (oracle, case["oracle_sha256"])):
        if digest(path.read_bytes()) != expected:
            raise ValueError(f"frozen diagnostic artifact digest mismatch: {path.name}")
    return {"schema": "qf-vv3d-tet4-l3-optimized-diagnostic-contract-v1", "status": "PREPARED_NOT_AUTHORIZED",
                "scope_id": SCOPE, "campaign_id": CAMPAIGN, "case_id": CASE, "nodeid": TARGET,
                "source_identity": report["source_identity"], "source_fingerprint": report["source_fingerprint"],
                "field_error_draft_sha256": REGISTRATION["field_error_draft_sha256"],
                "controller_fingerprint": report["controller_fingerprint"], "predecessor": report["predecessor"],
                "combined_budget": report["combined_budget"],
                "r2_contract_sha256": R2_CONTRACT_SHA256,
                "limits": report["limits"], "mesh_sha256": case["mesh_sha256"],
                "criteria_path": case["criteria_path"], "criteria_sha256": case["criteria_file_sha256"],
                "oracle_path": case["oracle_path"], "oracle_sha256": case["oracle_sha256"],
                "trace": {"enabled": True, "sample_seconds": 5, "format": "durable-jsonl-v1"},
                "stop": {"max_attempts": 1, "implicit_retry": False,
                         "after_terminal": "STOP", "unlock_r2": False}}


def prepare_contract(controller: Any) -> dict[str, Any]:
    """Freeze a create-only diagnostic proposal; it cannot authorize execution."""
    report = inspect(controller)
    contract = build_contract(report)
    raw = canonical(contract)
    root = Path(REGISTRATION["evidence_root"])
    root.mkdir(parents=True, exist_ok=True)
    path = root / "diagnostic-contract.json"
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        import os
        os.fsync(stream.fileno())
    return {"state": contract["status"], "contract": str(path.resolve()),
            "sha256": digest(raw), "controller_fingerprint": report["controller_fingerprint"],
            "source_fingerprint": report["source_fingerprint"], "attempt_reserved": False}


def validate_authorization(contract: Mapping[str, Any], decision: Mapping[str, Any],
                           *, contract_sha256: str) -> None:
    """Validate one human-supplied decision; this does not authenticate the human."""
    import re

    fields = {"schema", "decision_id", "status", "approved_by", "scope_id", "case_id",
              "contract_sha256", "source_fingerprint", "controller_fingerprint", "limits", "created_at_utc"}
    decision_id = decision.get("decision_id")
    if (set(decision) != fields or decision.get("schema") != "qf-vv3d-tet4-l3-optimized-diagnostic-owner-v1"
            or decision.get("status") != "APPROVED" or decision.get("approved_by") != "Owner"
            or decision.get("scope_id") != SCOPE or decision.get("case_id") != CASE
            or decision.get("contract_sha256") != contract_sha256 or digest(canonical(contract)) != contract_sha256
            or decision.get("source_fingerprint") != contract.get("source_fingerprint")
            or decision.get("controller_fingerprint") != contract.get("controller_fingerprint")
            or decision.get("limits") != contract.get("limits")
            or not isinstance(decision_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}", decision_id)
            or not isinstance(decision.get("created_at_utc"), str) or not decision["created_at_utc"]):
        raise ValueError("diagnostic Owner decision does not bind the exact frozen contract and limits")


def authorized_context(controller: Any) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], str, str]:
    """Check the frozen contract and decision before any official preflight."""
    report = inspect(controller)
    root = Path(REGISTRATION["evidence_root"])
    contract_raw = (root / "diagnostic-contract.json").read_bytes()
    decision_raw = (root / "owner-decision.json").read_bytes()
    contract = json.loads(contract_raw)
    decision = json.loads(decision_raw)
    if contract_raw != canonical(contract) or decision_raw != canonical(decision):
        raise ValueError("diagnostic contract and decision require canonical JSON bytes")
    if contract != build_contract(report):
        raise ValueError("diagnostic contract differs from the current frozen identities")
    contract_sha = digest(contract_raw)
    validate_authorization(contract, decision, contract_sha256=contract_sha)
    return report, contract, decision, contract_sha, digest(decision_raw)


def preflight(controller: Any, target: str, preflight_id: str | None) -> dict[str, Any]:
    """Run one collect-only gate only after the exact Owner decision is archived."""
    import re
    import shutil
    import uuid
    from datetime import datetime, timezone

    if target != TARGET:
        raise ValueError("diagnostic accepts only the exact TET4-L3 nodeid")
    report, contract, decision, contract_sha, decision_sha = authorized_context(controller)
    root = Path(REGISTRATION["evidence_root"])
    source = Path(REGISTRATION["root"])
    if min(shutil.disk_usage(controller.ROOT).free, shutil.disk_usage(source).free,
           shutil.disk_usage(root.parent if not root.exists() else root).free) < 1024 * 1024 * 1024:
        raise ValueError("insufficient free disk for diagnostic preflight")
    preflight_id = preflight_id or f"pf-{uuid.uuid4().hex[:12]}"
    if not re.fullmatch(r"pf-[0-9a-f]{12}", preflight_id):
        raise ValueError("diagnostic preflight ID must be a fresh pf-<12 hex> identity")
    directory = root / "preflight" / preflight_id
    directory.mkdir(parents=True, exist_ok=False)
    temporary = directory / "tmp"
    output = directory / "output"
    temporary.mkdir()
    output.mkdir()
    collection_path = temporary / "collection-report.json"
    command = controller.build_pytest_command(
        "fem_exploratory", [TARGET], temporary, repository_root=source,
        source_root=source / "src", controller_root=controller.ROOT, collect_only=True,
        vv3d_tet4_l3_optimized_diagnostic_attestation=True,
    )
    environment = controller.build_child_environment(temporary, source_root=source / "src")
    environment.update({"QF_DEV_WORKTREE_ID": SCOPE,
                        "QF_DEV_SELECTED_DOFS": str(REGISTRATION["selected_dofs"]),
                        "QF_DEV_MAX_DOFS": str(REGISTRATION["max_dofs"]),
                        "QF_DEV_PREFLIGHT_COLLECTION_REPORT": str(collection_path)})
    limits = {"timeout_seconds": REGISTRATION["preflight_timeout_seconds"],
              "rss_soft_limit_mib": REGISTRATION["rss_soft_limit_mib"], "process_tree_limit": 32,
              "output_total_limit_mib": 64, "output_stream_limit_mib": 32,
              "temporary_limit_mib": 1024, "archive_size_limit_mib": 256, "minimum_free_disk_mib": 1024}
    started = datetime.now(timezone.utc).isoformat()
    result = controller.run_supervised_command(command, cwd=source, environment=environment,
                                               output_dir=output, temporary_dir=temporary,
                                               limits=limits, poll_interval=0.25)
    stdout = (output / "stdout.log").read_text(encoding="utf-8", errors="replace")
    stderr = (output / "stderr.log").read_text(encoding="utf-8", errors="replace")
    collection = json.loads(collection_path.read_bytes()) if collection_path.is_file() else None
    origin = controller._observed_solver_origin(stdout + "\n" + stderr)
    expected_origin = str((source / "src/solveur/__init__.py").resolve(strict=True))
    if (result.status != "PASS" or origin != expected_origin or not isinstance(collection, Mapping)
            or collection.get("schema") != "qfsolver-wp12-vv3d-collection-v1"
            or collection.get("scope_id") != SCOPE or collection.get("target") != TARGET
            or collection.get("collected_nodeids") != [TARGET] or collection.get("skip_markers") != []
            or collection.get("bodies_executed") is not False or collection.get("exitstatus") != 0):
        raise ValueError("diagnostic exact-node collect-only preflight failed")
    after = inspect(controller)
    if (after["source_identity"] != report["source_identity"]
            or after["source_fingerprint"] != report["source_fingerprint"]
            or after["controller_fingerprint"] != report["controller_fingerprint"]
            or after["predecessor"] != report["predecessor"] or build_contract(after) != contract):
        raise ValueError("diagnostic identity or predecessor changed during preflight")
    receipt = {"schema": "qf-vv3d-tet4-l3-optimized-diagnostic-preflight-v1", "status": "PREFLIGHT_PASS",
               "scope_id": SCOPE, "case_id": CASE, "nodeid": TARGET, "preflight_id": preflight_id,
               "contract_sha256": contract_sha, "decision_sha256": decision_sha,
               "source_fingerprint": report["source_fingerprint"],
               "controller_fingerprint": report["controller_fingerprint"],
               "solver_origin": origin, "collection_report": collection,
               "selected_nodeids": [TARGET], "skipped": 0, "bodies_executed": False,
               "reservation_created": False, "attempt_reserved": False,
               "stdout_sha256": digest((output / "stdout.log").read_bytes()),
               "stderr_sha256": digest((output / "stderr.log").read_bytes()),
               "started_at_utc": started, "finished_at_utc": datetime.now(timezone.utc).isoformat(),
               "elapsed_seconds": result.elapsed_seconds}
    path = directory / "preflight.json"
    controller._atomic_json_new(path, receipt)
    return {"state": "PREFLIGHT_PASS", "nodeid": TARGET, "preflight_id": preflight_id,
            "receipt": str(path.resolve()), "receipt_sha256": digest(path.read_bytes()),
            "attempt_reserved": False, "bodies_executed": False}


def manifest_payload(controller: Any, preflight_id: str) -> tuple[Path, dict[str, Any]]:
    """Bind one successful diagnostic preflight and the exact approved contract."""
    import re

    if not re.fullmatch(r"pf-[0-9a-f]{12}", preflight_id):
        raise ValueError("invalid diagnostic preflight ID")
    report, contract, decision, contract_sha, decision_sha = authorized_context(controller)
    root = Path(REGISTRATION["evidence_root"])
    directory = root / "preflight" / preflight_id
    path = (directory / "preflight.json").resolve(strict=True)
    raw = path.read_bytes()
    receipt = json.loads(raw)
    expected = {"schema": "qf-vv3d-tet4-l3-optimized-diagnostic-preflight-v1", "status": "PREFLIGHT_PASS",
                "scope_id": SCOPE, "case_id": CASE, "nodeid": TARGET, "preflight_id": preflight_id,
                "contract_sha256": contract_sha, "decision_sha256": decision_sha,
                "source_fingerprint": report["source_fingerprint"],
                "controller_fingerprint": report["controller_fingerprint"],
                "selected_nodeids": [TARGET], "skipped": 0, "bodies_executed": False,
                "reservation_created": False, "attempt_reserved": False}
    stdout_raw = (directory / "output/stdout.log").read_bytes()
    stderr_raw = (directory / "output/stderr.log").read_bytes()
    expected_origin = str((Path(REGISTRATION["root"]) / "src/solveur/__init__.py").resolve(strict=True))
    collection = receipt.get("collection_report") if isinstance(receipt, Mapping) else None
    if (not isinstance(receipt, Mapping) or any(receipt.get(key) != value for key, value in expected.items())
            or receipt.get("stdout_sha256") != digest(stdout_raw) or receipt.get("stderr_sha256") != digest(stderr_raw)
            or receipt.get("solver_origin") != expected_origin
            or controller._observed_solver_origin((stdout_raw + b"\n" + stderr_raw).decode("utf-8", errors="replace")) != expected_origin
            or not isinstance(collection, Mapping) or collection.get("scope_id") != SCOPE
            or collection.get("target") != TARGET or collection.get("collected_nodeids") != [TARGET]
            or collection.get("skip_markers") != [] or collection.get("bodies_executed") is not False
            or collection.get("exitstatus") != 0):
        raise ValueError("diagnostic preflight receipt is stale, altered, or outside the exact scope")
    criteria_path = Path(REGISTRATION["root"]) / "experiments/wp12_vv3d_adaptive" / contract["criteria_path"]
    criteria_raw = criteria_path.read_bytes()
    if digest(criteria_raw) != contract["criteria_sha256"]:
        raise ValueError("diagnostic frozen criteria bytes changed")
    criteria = json.loads(criteria_raw)["criteria"]
    authorization_id = "vv3d-tet4-l3-optimized-diagnostic-" + contract_sha[:12]
    manifest = {"schema": "qf-wp12-vv3d-case-manifest-v1", "campaign_id": CAMPAIGN,
                "scope_id": SCOPE, "case_id": CASE, "nodeid": TARGET,
                "state": "OWNER_AUTHORIZED", "execution_authorized": True, "do_not_execute": False,
                "mesh_sha256": contract["mesh_sha256"], "selected_dofs": REGISTRATION["selected_dofs"],
                "timeout_seconds": REGISTRATION["timeout_seconds"], "rss_soft_limit_mib": 4096,
                "archive_size_limit_mib": 256,
                "max_attempts": 1, "authorization_id": authorization_id,
                "scientific_fingerprint": report["source_fingerprint"],
                "controller_fingerprint": report["controller_fingerprint"],
                "campaign_contract_sha256": contract_sha, "frozen_criteria": criteria,
                "criteria_sha256": digest(canonical(criteria)),
                "owner_decision": {"status": "APPROVED", "approved_by": "Owner",
                                   "decision_id": decision["decision_id"], "decision_sha256": decision_sha},
                "preflight": {"preflight_id": preflight_id, "nodeid": TARGET, "status": "PREFLIGHT_PASS",
                              "receipt_path": str(path), "receipt_sha256": digest(raw)}}
    return root / "manifests" / f"{authorization_id}.json", manifest


def prepare_manifest(controller: Any, preflight_id: str) -> dict[str, Any]:
    path, manifest = manifest_payload(controller, preflight_id)
    controller._atomic_json_new(path, manifest)
    return {"state": "OWNER_AUTHORIZED", "manifest": str(path.resolve()),
            "sha256": digest(path.read_bytes()), "attempt_reserved": False}


def _append_record(path: Path, fields: dict[str, Any], *, first: bool) -> dict[str, Any]:
    """Durably append at most one start and one terminal record."""
    import os

    reserved = {"schema", "sequence", "previous_record_sha256", "scope_id", "case_id",
                "r1_sha256", "r2_sha256", "previous_diagnostic_sha256", "record_sha256"}
    if (set(fields) & reserved or fields.get("event") != ("ATTEMPT_STARTED" if first else "ATTEMPT_FINISHED")
            or not isinstance(fields.get("run_id"), str) or not fields["run_id"]):
        raise ValueError("diagnostic ledger event has invalid identity or reserved fields")
    if first:
        previous = "0" * 64
    else:
        lines = path.read_bytes().splitlines()
        if len(lines) != 1:
            raise ValueError("diagnostic ledger is not an open single-attempt ledger")
        prior = json.loads(lines[0])
        claimed = prior.pop("record_sha256", None)
        if (prior.get("event") != "ATTEMPT_STARTED" or claimed != digest(canonical(prior))
                or prior.get("scope_id") != SCOPE or prior.get("case_id") != CASE
                or prior.get("run_id") != fields["run_id"] or prior.get("r1_sha256") != REGISTRATION["r1_sha256"]
                or prior.get("r2_sha256") != REGISTRATION["r2_sha256"]
                or prior.get("previous_diagnostic_sha256") != REGISTRATION["predecessor_diagnostic_sha256"]):
            raise ValueError("diagnostic reservation record is invalid")
        previous = claimed
    body = {"schema": "qf-vv3d-tet4-l3-optimized-diagnostic-ledger-v1", "sequence": 1 if first else 2,
            "previous_record_sha256": previous, "scope_id": SCOPE, "case_id": CASE,
            "r1_sha256": REGISTRATION["r1_sha256"], "r2_sha256": REGISTRATION["r2_sha256"],
            "previous_diagnostic_sha256": REGISTRATION["predecessor_diagnostic_sha256"], **fields}
    body["record_sha256"] = digest(canonical(body))
    with path.open("xb" if first else "ab") as stream:
        stream.write(canonical(body) + b"\n")
        stream.flush()
        os.fsync(stream.fileno())
    return body


def trace_summary(raw: bytes, attempt_id: str, *, require_complete: bool,
                  expected_origin: str | None = None) -> dict[str, Any]:
    """Validate and summarize events written by the measured child process."""
    import math

    if not raw or not raw.endswith(b"\n") or len(raw) > 4 * 1024 * 1024:
        raise ValueError("diagnostic trace is empty, incomplete, or exceeds its bounded size")
    events = [json.loads(line) for line in raw.splitlines()]
    if events[0].get("stage") != "trace" or events[0].get("state") != "START":
        raise ValueError("diagnostic trace has no initial process event")
    process_id = events[0].get("process_id")
    previous = -1.0
    pending: list[str] = []
    finished: set[str] = set()
    origins: list[str] = []
    for event in events:
        elapsed = event.get("monotonic_seconds")
        if (event.get("schema") != "qf-vv3d-performance-trace-v1" or event.get("case_id") != CASE
                or event.get("attempt_id") != attempt_id or type(process_id) is not int or process_id <= 0
                or event.get("process_id") != process_id or isinstance(elapsed, bool)
                or not isinstance(elapsed, (int, float)) or not math.isfinite(elapsed) or elapsed < previous):
            raise ValueError("diagnostic trace has inconsistent process identity or monotonic time")
        previous = float(elapsed)
        stage, state = event.get("stage"), event.get("state")
        if state == "SOLVER_ORIGIN":
            origins.append(str(event.get("path", "")))
        if state == "START" and stage != "trace":
            pending.append(stage)
        elif state in {"END", "ERROR"} and stage in pending:
            pending.remove(stage)
            if state == "END":
                finished.add(stage)
    required = {"imports", "model_preparation", "body_load_order_8", "body_load_order_12",
                "finite_element_model", "solve_model", "stiffness_assembly", "constraint_reduction",
                "linear_solve", "stress_recovery", "independent_errors_order_8",
                "independent_errors_order_12", "serialize_and_archive", "acceptance"}
    if "registered_case" not in pending and "registered_case" not in finished:
        raise ValueError("diagnostic trace did not enter the registered case")
    if require_complete and not required.issubset(finished):
        raise ValueError("completed diagnostic lacks one or more required stage events")
    if len(origins) > 1 or (origins and expected_origin is not None and origins != [expected_origin]):
        raise ValueError("diagnostic trace reports an unexpected solver origin")
    if require_complete and expected_origin is not None and not origins:
        raise ValueError("completed diagnostic lacks the measured solver origin")
    return {"process_id": process_id, "events": len(events), "last_started_stage": pending[-1] if pending else None,
            "solver_origin": origins[0] if origins else None,
            "finished_stages": sorted(finished), "last_event": events[-1]}


def run(controller: Any, target: str, reason: str, preflight_id: str, manifest_path: Path) -> tuple[dict[str, Any], int]:
    """Reserve once and supervise the one approved diagnostic; never resume R2."""
    import shutil
    import uuid
    from datetime import datetime, timezone

    if target != TARGET or not reason or not reason.strip():
        raise ValueError("diagnostic requires its exact nodeid and a reason")
    # Refuse on the pending source identity before touching any lock path.
    inspect(controller)
    root = Path(REGISTRATION["evidence_root"])
    source = Path(REGISTRATION["root"])
    with controller._exclusive_file_lock(R2_ROOT / "locks/vv3d-campaign-exclusive.lock"), \
            controller._exclusive_file_lock(root / "diagnostic-exclusive.lock"):
        report, contract, decision, contract_sha, decision_sha = authorized_context(controller)
        expected_path, expected_manifest = manifest_payload(controller, preflight_id)
        if manifest_path.resolve(strict=True) != expected_path.resolve(strict=True):
            raise ValueError("diagnostic execution manifest path is not the exact registered path")
        manifest_raw = expected_path.read_bytes()
        manifest = json.loads(manifest_raw)
        if manifest != expected_manifest:
            raise ValueError("diagnostic execution manifest differs from its exact bindings")
        if controller.psutil is None:
            raise ValueError("psutil is required before diagnostic reservation")
        if min(shutil.disk_usage(controller.ROOT).free, shutil.disk_usage(source).free,
               shutil.disk_usage(root).free) < 1024 * 1024 * 1024:
            raise ValueError("insufficient free disk before diagnostic reservation")
        ledger = root / REGISTRATION["ledger"]
        if ledger.exists():
            raise ValueError("diagnostic attempt already reserved or consumed; retry is forbidden")
        run_id = "diag-" + uuid.uuid4().hex[:12]
        reservation_id = "diag-res-" + uuid.uuid4().hex[:16]
        attempt_id = run_id + "-attempt-1"
        attempt = root / "attempts" / attempt_id
        attempt.mkdir(parents=True, exist_ok=False)
        temporary = attempt / "tmp"
        output = attempt / "output"
        temporary.mkdir()
        output.mkdir()
        manifest_sha = digest(manifest_raw)
        preflight_sha = manifest["preflight"]["receipt_sha256"]
        start = _append_record(ledger, {
            "event": "ATTEMPT_STARTED", "run_id": run_id, "attempt_id": attempt_id,
            "reservation_id": reservation_id, "contract_sha256": contract_sha,
            "decision_sha256": decision_sha, "manifest_sha256": manifest_sha,
            "preflight_sha256": preflight_sha, "source_fingerprint": report["source_fingerprint"],
            "controller_fingerprint": report["controller_fingerprint"],
            "reserved_seconds": REGISTRATION["timeout_seconds"],
            "prior_attempts": report["combined_budget"]["attempts_before"],
            "prior_elapsed_seconds": report["predecessor"]["elapsed_seconds"],
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
        }, first=True)
        ledger_sha = digest(ledger.read_bytes())
        receipt = {"schema": "qf-wp12-vv3d-runner-reservation-v1", "status": "RESERVED",
                   "campaign_id": CAMPAIGN, "case_id": CASE, "nodeid": TARGET,
                   "manifest_sha256": manifest_sha, "preflight_receipt_sha256": preflight_sha,
                   "decision_id": decision["decision_id"], "decision_sha256": decision_sha,
                   "scientific_fingerprint": report["source_fingerprint"],
                   "controller_fingerprint": report["controller_fingerprint"],
                   "authorization_id": manifest["authorization_id"], "ledger_scope_id": SCOPE,
                   "selected_dofs": REGISTRATION["selected_dofs"],
                   "timeout_seconds": REGISTRATION["timeout_seconds"], "rss_soft_limit_mib": 4096,
                   "archive_size_limit_mib": 256, "attempt_number": 1, "max_attempts": 1,
                   "attempt_reserved": True, "ledger_path": str(ledger.resolve()),
                   "ledger_sha256_after_reservation": ledger_sha,
                   "campaign_attempts_used_after": start["prior_attempts"] + 1,
                   "campaign_seconds_reserved_after": start["prior_elapsed_seconds"] + REGISTRATION["timeout_seconds"],
                   "evidence_root": str(root.resolve()), "reservation_id": reservation_id,
                   "attempt_id": attempt_id}
        receipt_path = attempt / "diagnostic-reservation.json"
        controller._atomic_json_new(receipt_path, receipt)
        receipt_sha = digest(receipt_path.read_bytes())
        command = controller.build_pytest_command("fem_exploratory", [TARGET], temporary,
                                                  repository_root=source, source_root=source / "src",
                                                  controller_root=controller.ROOT)
        environment = controller.build_child_environment(temporary, source_root=source / "src")
        environment.update({"QF_DEV_WORKTREE_ID": SCOPE, "QF_DEV_CAMPAIGN_SCOPE_ID": SCOPE,
                            "QF_DEV_VV3D_CASE_ID": CASE, "QF_DEV_TARGET_NODEID": TARGET,
                            "QF_DEV_MANIFEST_PATH": str(expected_path.resolve()),
                            "QF_DEV_MANIFEST_SHA256": manifest_sha,
                            "QF_DEV_AUTHORIZATION_ID": manifest["authorization_id"],
                            "QF_DEV_VV3D_SCIENCE_FINGERPRINT": report["source_fingerprint"],
                            "QF_DEV_CONTROLLER_FINGERPRINT": report["controller_fingerprint"],
                            "QF_DEV_EVIDENCE_ROOT": str(root.resolve()),
                            "QF_DEV_VV3D_RUNNER_RECEIPT_PATH": str(receipt_path.resolve()),
                            "QF_DEV_VV3D_RUNNER_RECEIPT_SHA256": receipt_sha,
                            "QF_VV3D_PERFORMANCE_TRACE": "1"})
        limits = {"timeout_seconds": REGISTRATION["timeout_seconds"], "rss_soft_limit_mib": 4096,
                  "process_tree_limit": 32,
                  "output_total_limit_mib": 64, "output_stream_limit_mib": 32,
                  "temporary_limit_mib": 1024, "archive_size_limit_mib": 256, "minimum_free_disk_mib": 1024}
        import time
        launched = time.monotonic()
        trace_path = root / "diagnostic-timings" / CASE / attempt_id / "stages.jsonl"
        try:
            result = controller.run_supervised_command(command, cwd=source, environment=environment,
                                                       output_dir=output, temporary_dir=temporary,
                                                       limits=limits, poll_interval=0.25)
            elapsed = float(result.elapsed_seconds)
            identity = controller._git_identity(source, expected_branch=REGISTRATION["branch"])
            if (identity != report["source_identity"]
                    or controller._worktree_source_fingerprint(source, TARGET) != report["source_fingerprint"]
                    or controller._stable_fingerprint(controller_provenance(controller)) != report["controller_fingerprint"]
                    or predecessor_history(controller) != report["predecessor"] or build_contract(report) != contract):
                raise ValueError("diagnostic source, controller or predecessor changed during execution")
            trace_raw = trace_path.read_bytes()
            expected_origin = str((source / "src/solveur/__init__.py").resolve(strict=True))
            summary = trace_summary(trace_raw, attempt_id, require_complete=result.status == "PASS",
                                    expected_origin=expected_origin)
            state = "DIAGNOSTIC_COMPLETED" if result.status == "PASS" else "DIAGNOSTIC_STOP"
            details = {"state": state, "scientific_state": result.status, "stop_reason": result.stop_reason,
                       "elapsed_seconds": elapsed, "peak_rss_bytes": result.peak_rss_bytes,
                       "trace": str(trace_path.resolve()), "trace_sha256": digest(trace_raw),
                       "trace_summary": summary,
                       "stdout_sha256": digest((output / "stdout.log").read_bytes()),
                       "stderr_sha256": digest((output / "stderr.log").read_bytes())}
        except Exception as exc:
            elapsed = max(0.0, time.monotonic() - launched)
            details = {"state": "INFRA_ERROR", "elapsed_seconds": elapsed,
                       "error": f"{type(exc).__name__}: {exc}"}
            if trace_path.is_file():
                details["trace"] = str(trace_path.resolve())
                details["trace_sha256"] = digest(trace_path.read_bytes())
        finish = _append_record(ledger, {"event": "ATTEMPT_FINISHED", "run_id": run_id,
                                         "attempt_id": attempt_id, "status": details["state"],
                                         "elapsed_seconds": elapsed,
                                         "combined_elapsed_seconds": start["prior_elapsed_seconds"] + elapsed,
                                         "finished_at_utc": datetime.now(timezone.utc).isoformat()}, first=False)
        result_path = attempt / "diagnostic-result.json"
        controller._atomic_json_new(result_path, {**details, "scope_id": SCOPE, "case_id": CASE,
                                                  "ledger_sha256": digest(ledger.read_bytes()),
                                                  "terminal_record_sha256": finish["record_sha256"],
                                                  "r2_unlocked": False})
        return {**details, "record": str(result_path.resolve()), "ledger": str(ledger.resolve()),
                "r2_unlocked": False}, (0 if details["state"] == "DIAGNOSTIC_COMPLETED" else 1)
