"""Freeze and execute one prospective R1.12 M4 slip diagnostic.

The run tests the already-frozen R1.11 optimizer change at M4. It runs only
M4/slip_target, once, with the historical M4 inputs and physical gates. It
does not retry, tune, rerun M1/M2/M3, or claim formal WP08 qualification.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from time import perf_counter
from typing import Any

import numpy as np
import scipy

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from scripts import run_wp08_area_supported_m4_diagnostic_r1_10 as m4  # noqa: E402
from scripts import run_wp08_area_supported_m4_slip_forensic_r2 as forensic  # noqa: E402

ARTIFACT_ID = "QF-029-WP08-AREA-SUPPORTED-CONTACT-M4-SLIP-R1.12"
OUTPUT_REL = Path(
    "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_12_m4_slip_20260927"
)
DOC_REL = Path("docs/verification/0_2_9/wp08-area-supported-contact-m4-slip-r1-12.md")
R1_11_ROOT_REL = Path(
    "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_11_optimizer_20260926"
)
OLD_FORENSIC_ROOT_REL = Path(
    "qualification/0_2_9/wp08_surface_stiffness_remediation/area_supported_r1_10_m4_slip_forensic_r2_20260926"
)
R1_11_CONTRACT_SHA256 = "95146b015cc4a76ee413593e1dc40a9cc0d4de2c7f01f1c7fc15cbc6ff4a6ca9"
R1_11_M2_M3_CONTRACT_SHA256 = "55c7d48b35f3fdaabad1e3460182de8b67a9c85fd777780f7efce5eae21803bf"
R1_11_BINDING_SHA256 = "4b900be6c08178eb53ef721f161b045cb7ecacb0b011049d11ea96b7fb62b5b0"
OLD_M4_CONTRACT_SHA256 = "79073a5199a2832a3c546f77c5e3a98d48d7fd38b6f69c1fb3a237a40fffa0dd"
SOURCE_TESTS = (
    "tests/unit/test_wp08_area_supported_m4_r1_10_runner.py",
    "tests/unit/test_wp08_area_supported_m4_slip_forensic_r2_runner.py",
    "tests/unit/test_wp08_area_supported_r1_11_optimizer_runner.py",
    "tests/unit/test_wp08_area_supported_m4_slip_r1_12_runner.py",
)


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha(value: object) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _binding_sha(binding: Mapping[str, Any]) -> str:
    normalized = dict(binding)
    normalized["execution_binding_sha256"] = None
    return _canonical_sha(normalized)


def _write_json(path: Path, value: object, *, exclusive: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x" if exclusive else "w", encoding="utf-8", newline="\n") as stream:
        json.dump(value, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _source_inventory() -> dict[str, str]:
    files = {
        path
        for folder in (ROOT / "src", ROOT / "scripts")
        for path in folder.rglob("*.py")
        if "__pycache__" not in path.parts
    }
    files.update(ROOT / relative for relative in SOURCE_TESTS)
    missing = [path for path in files if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing bound source/test file: {missing[0]}")
    return {
        path.relative_to(ROOT).as_posix(): _sha(path)
        for path in sorted(files, key=lambda item: item.relative_to(ROOT).as_posix())
    }


def _require_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(f"Required read-only evidence is missing: {path}")
    return path


def _artifact_record(root: Path, relative: str) -> dict[str, Any]:
    path = _require_file(root / relative)
    return {"path": (root / relative).relative_to(ROOT).as_posix(), "sha256": _sha(path), "size_bytes": path.stat().st_size}


def _verify_process_logs(root: Path, record: dict[str, Any]) -> dict[str, Any]:
    if record.get("exit_code") != 0 or not isinstance(record.get("pid"), int):
        raise RuntimeError("An R1.11 parent process did not exit successfully with a recorded PID.")
    if not record.get("started_utc") or not record.get("ended_utc"):
        raise RuntimeError("An R1.11 process record lacks UTC start/end timestamps.")
    verified: dict[str, Any] = {"pid": record["pid"], "exit_code": record["exit_code"]}
    for kind in ("stdout", "stderr"):
        relative = record.get(f"{kind}_path")
        if not isinstance(relative, str):
            raise RuntimeError(f"R1.11 process record lacks {kind} path.")
        path = _require_file(root / relative)
        observed = _sha(path)
        if observed != record.get(f"{kind}_sha256"):
            raise RuntimeError(f"R1.11 {kind} log hash mismatch: {relative}")
        verified[kind] = {"path": (root / relative).relative_to(ROOT).as_posix(), "sha256": observed, "size_bytes": path.stat().st_size}
    return verified


def _r1_11_parent_evidence() -> dict[str, Any]:
    root = ROOT / R1_11_ROOT_REL
    contract_path = _require_file(root / "contract.json")
    contract = _json(contract_path)
    if _sha(contract_path) != R1_11_CONTRACT_SHA256:
        raise RuntimeError("R1.11 M1 contract digest differs from the expected frozen contract.")
    m1_final_path = _require_file(root / "final.json")
    m23_final_path = _require_file(root / "M2_M3" / "final.json")
    m1_final, m23_final = _json(m1_final_path), _json(m23_final_path)
    if m1_final.get("status") != "M1_DIAGNOSTIC_PASS_M2_M3_READY":
        raise RuntimeError("R1.11 M1 is not in its recorded pass state.")
    if m23_final.get("status") != "M2_M3_DIAGNOSTIC_CASES_PASS_REFINEMENT_UNCLASSIFIED":
        raise RuntimeError("R1.11 M2/M3 is not in its recorded pass state.")
    if m23_final.get("execution_binding_sha256") != R1_11_BINDING_SHA256:
        raise RuntimeError("R1.11 M2/M3 binding digest mismatch.")
    if m23_final.get("parent_contract_sha256") != R1_11_CONTRACT_SHA256:
        raise RuntimeError("R1.11 M2/M3 is not bound to the frozen M1 contract.")
    if not m23_final.get("m2_all_case_gates_pass") or not m23_final.get("m3_all_case_gates_pass"):
        raise RuntimeError("R1.11 M2/M3 aggregate gates are not all passing.")
    m1_source_manifest_path = _require_file(root / "source_file_manifest.json")
    m23_source_manifest_path = _require_file(root / "execution_source_manifest.json")
    m1_source_manifest = _json(m1_source_manifest_path)
    m23_source_manifest = _json(m23_source_manifest_path)
    source_bundle_sha = _canonical_sha(m1_source_manifest)
    if m1_source_manifest != m23_source_manifest or source_bundle_sha != m1_final.get("source_bundle_sha256") or source_bundle_sha != m23_final.get("source_bundle_sha256"):
        raise RuntimeError("R1.11 M1/M2/M3 source manifests or source-bundle digests disagree.")
    if m1_final.get("contract_sha256") != R1_11_CONTRACT_SHA256:
        raise RuntimeError("R1.11 M1 final record is not bound to its frozen contract.")
    m23_contract_path = _require_file(root / "contract_r1_11_optimizer_contact_requalification.json")
    if _sha(m23_contract_path) != R1_11_M2_M3_CONTRACT_SHA256:
        raise RuntimeError("R1.11 M2/M3 amendment contract bytes do not match the expected digest.")

    records: dict[str, Any] = {}
    for mesh, final, case_records in (
        ("M1", m1_final, {item["case"]: item for item in m1_final.get("processes", [])}),
        ("M2", m23_final, {item["case"]: item for item in m23_final.get("processes", []) if item.get("mesh") == "M2"}),
        ("M3", m23_final, {item["case"]: item for item in m23_final.get("processes", []) if item.get("mesh") == "M3"}),
    ):
        for case in ("stick_target", "slip_target"):
            key = f"{mesh}/{case}"
            declared = final.get("cases", {}).get(case) if mesh == "M1" else final.get("case_status", {}).get(key)
            if declared != "PASS_DIAGNOSTIC_GATES":
                raise RuntimeError(f"R1.11 parent case is not PASS_DIAGNOSTIC_GATES: {key}")
            process = case_records.get(case)
            if process is None:
                raise RuntimeError(f"R1.11 final record has no process for {key}.")
            process_rel = f"_process_logs/{mesh}_{case}.process.json" if mesh != "M1" else f"_process_logs/{case}.process.json"
            process_path = _require_file(root / process_rel)
            process_file = _json(process_path)
            if process_file.get("exit_code") != 0 or process_file.get("pid") != process.get("pid"):
                raise RuntimeError(f"R1.11 process manifest conflicts with final record: {key}")
            logs = _verify_process_logs(root, process_file)
            case_root = root / mesh / case if mesh == "M1" else root / "M2_M3" / mesh / case
            case_artifacts: dict[str, Any] = {}
            for filename in ("result.json", "raw.npz", "telemetry.jsonl", "progress.json"):
                artifact = _artifact_record(root, case_root.relative_to(root).as_posix() + "/" + filename)
                case_artifacts[filename] = artifact
            result_path = ROOT / case_artifacts["result.json"]["path"]
            result = _json(result_path)
            if result.get("contract_sha256") != (R1_11_CONTRACT_SHA256 if mesh == "M1" else R1_11_M2_M3_CONTRACT_SHA256):
                raise RuntimeError(f"R1.11 result contract binding mismatch: {key}")
            if result.get("source_bundle_sha256") != source_bundle_sha:
                raise RuntimeError(f"R1.11 result source-bundle binding mismatch: {key}")
            if mesh != "M1" and result.get("execution_binding_sha256") != R1_11_BINDING_SHA256:
                raise RuntimeError(f"R1.11 result execution-binding mismatch: {key}")
            if result.get("diagnostic", {}).get("status") != "PASS_DIAGNOSTIC_GATES":
                raise RuntimeError(f"R1.11 result-level diagnostic is not pass: {key}")
            for field, filename in (("result", "result.json"), ("raw", "raw.npz"), ("telemetry", "telemetry.jsonl")):
                declared_path = process_file.get(f"{field}_path")
                declared_hash = process_file.get(f"{field}_sha256")
                if declared_path is not None or declared_hash is not None:
                    expected_local = case_artifacts[filename]["path"].removeprefix(
                        R1_11_ROOT_REL.as_posix() + "/"
                    )
                    if declared_path != expected_local or declared_hash != case_artifacts[filename]["sha256"]:
                        raise RuntimeError(f"R1.11 process artifact binding mismatch: {key}/{filename}")
            records[key] = {
                "status": declared,
                "process_manifest": _artifact_record(root, process_rel),
                "process": {"pid": process_file["pid"], "exit_code": process_file["exit_code"], "started_utc": process_file["started_utc"], "ended_utc": process_file["ended_utc"], "logs": logs},
                "artifacts": case_artifacts,
            }

    refs = {
        "contract": _artifact_record(root, "contract.json"),
        "m1_contract_amendment": _artifact_record(root, "contract_r1_11_optimizer_contact_requalification.json"),
        "m1_freeze_binding": _artifact_record(root, "freeze_binding.json"),
        "m1_r1_11_freeze_binding": _artifact_record(root, "freeze_binding_r1_11_optimizer_contact_requalification.json"),
        "m1_source_manifest": _artifact_record(root, "source_file_manifest.json"),
        "m1_final": _artifact_record(root, "final.json"),
        "m2_m3_contract_amendment": _artifact_record(root, "contract_r1_11_optimizer_contact_requalification.json"),
        "m2_m3_execution_binding": _artifact_record(root, "execution_binding.json"),
        "m2_m3_source_manifest": _artifact_record(root, "execution_source_manifest.json"),
        "m2_m3_final": _artifact_record(root, "M2_M3/final.json"),
    }
    m23_binding = _json(_require_file(root / "execution_binding.json"))
    if _binding_sha(m23_binding) != R1_11_BINDING_SHA256:
        raise RuntimeError("R1.11 M2/M3 execution binding bytes do not match the expected SHA-256.")
    return {"contract_sha256": R1_11_CONTRACT_SHA256, "m2_m3_contract_sha256": R1_11_M2_M3_CONTRACT_SHA256, "binding_sha256": R1_11_BINDING_SHA256, "references": refs, "cases": records}


def _expected_untracked_roots() -> set[str]:
    return {R1_11_ROOT_REL.as_posix(), OUTPUT_REL.as_posix()}


def _check_git_state(*, before_freeze: bool) -> dict[str, Any]:
    if _git("diff", "--quiet", "HEAD", "--") != "":
        raise RuntimeError("Tracked worktree changes are not permitted for R1.12 freeze or execution.")
    if _git("diff", "--cached", "--quiet") != "":
        raise RuntimeError("Staged changes are not permitted for R1.12 freeze or execution.")
    lines = _git("status", "--porcelain", "--untracked-files=normal").splitlines()
    observed: set[str] = set()
    for line in lines:
        if not line.startswith("?? "):
            raise RuntimeError(f"Unexpected tracked or staged Git status at R1.12 boundary: {line}")
        observed.add(line[3:].replace("\\", "/").rstrip("/"))
    allowed = {R1_11_ROOT_REL.as_posix()} if before_freeze else _expected_untracked_roots()
    if observed != allowed:
        raise RuntimeError(f"Unexpected untracked paths; expected {sorted(allowed)}, observed {sorted(observed)}")
    return {"branch": _git("branch", "--show-current"), "head": _git("rev-parse", "HEAD"), "status_porcelain": lines}


def _contract_payload(inventory: dict[str, str], parent: dict[str, Any], old_failure: dict[str, Any], preflight: dict[str, Any]) -> dict[str, Any]:
    prior_path = ROOT / m4.OUTPUT_REL / "contract.json"
    prior_contract = _json(_require_file(prior_path))
    if _sha(prior_path) != OLD_M4_CONTRACT_SHA256:
        raise RuntimeError("Frozen M4 physical-input contract hash mismatch.")
    r1_11_doc = _json(ROOT / R1_11_ROOT_REL / "contract_r1_11_optimizer_contact_requalification.json")
    return {
        "schema": "qf.wp08.area_supported_contact_m4_slip_r1_12_contract.r1",
        "artifact_id": ARTIFACT_ID,
        "status": "FROZEN_PROSPECTIVE_SINGLE_ATTEMPT",
        "frozen_utc": _utc(),
        "contract_document": DOC_REL.as_posix(),
        "contract_document_sha256": _sha(ROOT / DOC_REL),
        "execution": {"output_root": OUTPUT_REL.as_posix(), "attempts": 1, "overwrite_or_retry": False, "sequence": ["M4/slip_target"], "one_solver_process_at_a_time": True, "rerun_M1_M2_M3": False, "rerun_stick": False, "reference_or_replay": False},
        "purpose": "Prospectively test whether the frozen R1.11 optimizer stopping correction resolves the previously observed M4 active-slip failure, without changing physical inputs or acceptance criteria.",
        "source": {"branch": _git("branch", "--show-current"), "execution_sha": _git("rev-parse", "HEAD"), "source_bundle_sha256": _canonical_sha(inventory), "runner_sha256": _sha(Path(__file__).resolve()), "optimizer_implementation_sha": "0a56da58aafc257c05d7399eb7ec7323e52b7f0c", "optimizer_runner_binding_sha": _sha(Path(__file__).resolve())},
        "frozen_physical_inputs": {"parent_m4_contract_sha256": OLD_M4_CONTRACT_SHA256, "parent_m4_contract_artifact_id": prior_contract.get("artifact_id"), "mesh": prior_contract.get("mesh"), "benchmark": prior_contract.get("benchmark"), "diagnostic_gates": prior_contract.get("diagnostic_gates"), "preflight": preflight, "r1_11_optimizer_policy": r1_11_doc.get("optimizer_stopping_policy"), "r1_11_physical_contact_residual_tolerance": 1e-9, "r1_11_max_nfev": 500, "r1_11_semismooth_iteration_budget": 30, "active_set_iteration_cap": 25, "enumeration_guard": "unchanged", "r1_11_m1_m2_m3_read_only_evidence": parent, "historical_m4_slip_failure_read_only": old_failure},
        "acceptance": {"required": ["solver_converged", "all serialized observables finite", "exactly 8 load steps recorded", "active support affine rank 2", "terminal active tangential state is slip"], "physical_active_slip_root_tolerance": 1e-9, "optimizer_success_alone_is_never_acceptance": True, "mesh_refinement_threshold": None},
        "change_policy": {"production_mechanics_changed_for_this_campaign": False, "r1_11_optimizer_change_is_part_of_executed_source": True, "thresholds_changed": False, "mesh_load_material_friction_or_stiffness_changed": False, "iteration_or_fallback_policy_changed": False, "historical_evidence_overwritten": False},
        "policy_digest_context_only": m4.POLICY_DIGEST_CONTEXT,
        "source_manifest_sha256": _canonical_sha(inventory),
        "parent_evidence_sha256": _canonical_sha(parent),
        "historical_failure_evidence_sha256": _canonical_sha(old_failure),
        "owner_authorization": {"authorized": True, "recorded_from": "Owner instruction: freeze the runner and launch execution; explicit green light.", "scope": "Exactly one prospective M4/slip_target run under the R1.11 optimizer source; preserve previous failures; no retry, parameter change, M1/M2/M3 rerun, reference, replay, formal claim, or points."},
        "limitations": {"formal_wp08_qualification": False, "independent_global_fem_reference": False, "formal_replay": False, "points_awarded": False, "mesh_convergence_claim": False},
    }


def freeze() -> dict[str, Any]:
    output = ROOT / OUTPUT_REL
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite R1.12 output root: {output}")
    git_state = _check_git_state(before_freeze=True)
    parent = _r1_11_parent_evidence()
    old_failure = forensic._old_m4_evidence()
    inventory = _source_inventory()
    preflight = m4.generate_preflight(m4.M4_LEVEL)
    contract = _contract_payload(inventory, parent, old_failure, preflight)
    output.mkdir(parents=True, exist_ok=False)
    _write_json(output / "contract.json", contract)
    _write_json(output / "source_manifest.json", inventory)
    _write_json(output / "parent_evidence.json", parent)
    binding: dict[str, Any] = {
        "schema": "qf.wp08.area_supported_contact_m4_slip_r1_12_binding.r1",
        "artifact_id": ARTIFACT_ID,
        "frozen_utc": contract["frozen_utc"],
        "contract_sha256": _sha(output / "contract.json"),
        "source_bundle_sha256": _canonical_sha(inventory),
        "runner_sha256": _sha(Path(__file__).resolve()),
        "contract_document_sha256": _sha(ROOT / DOC_REL),
        "source_head": git_state["head"],
        "git": git_state,
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "parent_evidence_sha256": _canonical_sha(parent),
        "historical_failure_evidence_sha256": _canonical_sha(old_failure),
        "owner_authorization": contract["owner_authorization"],
        "execution_binding_sha256": None,
    }
    binding["execution_binding_sha256"] = _binding_sha(binding)
    _write_json(output / "execution_binding.json", binding)
    record = {"status": "FROZEN_READY_TO_EXECUTE", "artifact_id": ARTIFACT_ID, "contract_sha256": binding["contract_sha256"], "runner_sha256": binding["runner_sha256"], "source_bundle_sha256": binding["source_bundle_sha256"], "execution_binding_sha256": binding["execution_binding_sha256"], "source_head": binding["source_head"], "owner_authorization": binding["owner_authorization"]}
    _write_json(output / "freeze_record.json", record)
    return record


def _verify_frozen(output: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if output.resolve() != (ROOT / OUTPUT_REL).resolve():
        raise PermissionError("R1.12 output root differs from its frozen dedicated path.")
    contract_path, binding_path = output / "contract.json", output / "execution_binding.json"
    contract, binding = _json(contract_path), _json(binding_path)
    manifest = _json(output / "source_manifest.json")
    if contract.get("status") != "FROZEN_PROSPECTIVE_SINGLE_ATTEMPT" or contract.get("execution", {}).get("sequence") != ["M4/slip_target"]:
        raise RuntimeError("R1.12 contract is not frozen for exactly one M4 slip attempt.")
    if _sha(contract_path) != binding.get("contract_sha256") or binding.get("execution_binding_sha256") != _binding_sha(binding):
        raise RuntimeError("R1.12 contract or execution binding hash mismatch.")
    if manifest != _source_inventory() or _canonical_sha(manifest) != binding.get("source_bundle_sha256"):
        raise RuntimeError("R1.12 source inventory changed after freeze.")
    if _sha(Path(__file__).resolve()) != binding.get("runner_sha256") or _sha(ROOT / DOC_REL) != binding.get("contract_document_sha256"):
        raise RuntimeError("R1.12 runner or frozen document changed after freeze.")
    if _git("rev-parse", "HEAD") != binding.get("source_head") or _git("branch", "--show-current") != binding.get("git", {}).get("branch"):
        raise RuntimeError("R1.12 source branch/HEAD changed after freeze.")
    _check_git_state(before_freeze=False)
    parent = _r1_11_parent_evidence()
    old_failure = forensic._old_m4_evidence()
    if _canonical_sha(parent) != binding.get("parent_evidence_sha256") or _canonical_sha(old_failure) != binding.get("historical_failure_evidence_sha256"):
        raise RuntimeError("R1.12 parent or historical failure evidence changed after freeze.")
    if _canonical_sha(parent) != _canonical_sha(_json(output / "parent_evidence.json")):
        raise RuntimeError("R1.12 parent evidence record differs from the frozen record.")
    if contract.get("owner_authorization", {}).get("authorized") is not True:
        raise PermissionError("R1.12 execution is not Owner-authorized in its frozen contract.")
    return contract, binding


def _worker(output: Path, binding_sha: str) -> int:
    _, binding = _verify_frozen(output.resolve())
    if binding.get("execution_binding_sha256") != binding_sha:
        raise RuntimeError("R1.12 worker execution-binding argument mismatch.")
    case_dir = output / "M4" / "slip_target"
    case_dir.mkdir(parents=True, exist_ok=False)
    from solveur.api.public import solve_model
    from solveur.core.telemetry.jsonl import JsonlSink
    from solveur.core.telemetry.observer import TelemetryEmitter

    model, body, slave_nodes, area_by_node = m4._build_model("slip_target")
    telemetry_path = case_dir / "telemetry.jsonl"
    sink = JsonlSink(telemetry_path, fsync=True, sink_identifier="wp08_area_m4_slip_r1_12")
    telemetry = TelemetryEmitter(analysis_id=f"{ARTIFACT_ID}-M4-slip_target", analysis_type="linear_static", route="linear_static", sinks=(sink,), metadata={"contract_sha256": binding["contract_sha256"], "execution_binding_sha256": binding_sha, "source_bundle_sha256": binding["source_bundle_sha256"], "mesh": "M4", "case": "slip_target"})
    started = perf_counter()
    try:
        result = solve_model(model, enforce_policy=False, telemetry=telemetry)
        payload = result.to_dict()
        diagnostic = m4._case_gates(payload, "slip_target", body, slave_nodes, area_by_node)
        payload.update({"artifact_id": ARTIFACT_ID, "execution_kind": "PROSPECTIVE_R1_12_M4_SLIP_DIAGNOSTIC", "mesh": "M4", "case": "slip_target", "contract_sha256": binding["contract_sha256"], "execution_binding_sha256": binding_sha, "source_bundle_sha256": binding["source_bundle_sha256"], "diagnostic": {**diagnostic, "elapsed_seconds": perf_counter() - started}, "formal_wp08_qualification": False, "points_awarded": False})
        _write_json(case_dir / "result.json", payload)
        body_count = len(body)
        master_nodes = np.asarray([[m4.LENGTH_M + m4.INITIAL_GAP_M, 0.0, 0.0], [m4.LENGTH_M + m4.INITIAL_GAP_M, 0.0, m4.HEIGHT_M], [m4.LENGTH_M + m4.INITIAL_GAP_M, m4.WIDTH_M, m4.HEIGHT_M], [m4.LENGTH_M + m4.INITIAL_GAP_M, m4.WIDTH_M, 0.0]], dtype=float)
        coordinates = np.vstack((body, master_nodes))
        eq = payload.get("audit", {}).get("equilibrium", {})
        rows = payload.get("solver", {}).get("contact", {}).get("contacts", [])
        normals = np.asarray([row.get("normal", [0.0, 0.0, 0.0]) for row in rows], dtype=float).reshape((-1, 3))
        pressure = np.asarray([row.get("pressure", 0.0) for row in rows], dtype=float)
        normal_force = -pressure[:, None] * normals
        tangential_force = []
        for row in rows:
            components = np.asarray(row.get("tangential_force", [0.0, 0.0]), dtype=float)
            tangential_force.append(components[0] * np.asarray(row.get("tangent_one", [0.0, 0.0, 0.0]), dtype=float) + components[1] * np.asarray(row.get("tangent_two", [0.0, 0.0, 0.0]), dtype=float))
        np.savez_compressed(case_dir / "raw.npz", displacement=np.asarray(result.displacements, dtype=float), node_coordinates=coordinates, body_node_count=np.asarray([body_count], dtype=np.int64), slave_nodes=np.asarray(slave_nodes, dtype=np.int64), reference_slave_area=np.asarray([area_by_node[node] for node in slave_nodes], dtype=float), contact_slave_nodes=np.asarray([row.get("slave_node", -1) for row in rows], dtype=np.int64), contact_active=np.asarray([row.get("active", False) for row in rows], dtype=bool), contact_pressure=pressure, contact_normal=normals, contact_normal_force=normal_force, contact_gap=np.asarray([row.get("gap", np.nan) for row in rows], dtype=float), contact_states=np.asarray([row.get("tangential_state", "unknown") for row in rows], dtype=str), contact_tangential_force_global=np.asarray(tangential_force, dtype=float).reshape((-1, 3)), contact_reference_area=np.asarray([row.get("reference_slave_area", 0.0) for row in rows], dtype=float), reaction_resultant=np.asarray(eq.get("reaction_resultant", [0.0, 0.0, 0.0]), dtype=float), reaction_moment=np.asarray(eq.get("reaction_moment_about_origin", [0.0, 0.0, 0.0]), dtype=float), force_balance_relative_error=np.asarray([eq.get("force_balance_relative_error", np.nan)], dtype=float), moment_balance_relative_error=np.asarray([eq.get("moment_balance_relative_error", np.nan)], dtype=float), active_slave_nodes=np.asarray(diagnostic["active_slave_nodes"], dtype=np.int64))
        _write_json(case_dir / "progress.json", {"status": diagnostic["status"], **diagnostic})
        return 0 if all(diagnostic["gates"].values()) else 3
    except BaseException as error:
        _write_json(case_dir / "failure.json", {"artifact_id": ARTIFACT_ID, "execution_kind": "PROSPECTIVE_R1_12_M4_SLIP_DIAGNOSTIC", "mesh": "M4", "case": "slip_target", "contract_sha256": binding["contract_sha256"], "execution_binding_sha256": binding_sha, "error": forensic._exception_record(error), "failed_utc": _utc(), "elapsed_seconds": perf_counter() - started})
        raise
    finally:
        telemetry.close()


def _invoke(output: Path, binding: dict[str, Any]) -> dict[str, Any]:
    logs = output / "_process_logs"
    logs.mkdir(exist_ok=True)
    stdout_path, stderr_path = logs / "M4_slip_target.stdout.log", logs / "M4_slip_target.stderr.log"
    command = [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", "--output-root", str(output), "--execution-binding-sha256", str(binding["execution_binding_sha256"])]
    start = _utc()
    timer = perf_counter()
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        exit_code = process.wait()
    record: dict[str, Any] = {"artifact_id": ARTIFACT_ID, "mesh": "M4", "case": "slip_target", "execution_kind": "PROSPECTIVE_R1_12_M4_SLIP_DIAGNOSTIC", "pid": process.pid, "command": command, "started_utc": start, "ended_utc": _utc(), "elapsed_seconds": perf_counter() - timer, "exit_code": exit_code, "contract_sha256": binding["contract_sha256"], "execution_binding_sha256": binding["execution_binding_sha256"], "source_bundle_sha256": binding["source_bundle_sha256"], "stdout_path": stdout_path.relative_to(output).as_posix(), "stdout_sha256": _sha(stdout_path), "stderr_path": stderr_path.relative_to(output).as_posix(), "stderr_sha256": _sha(stderr_path)}
    case_dir = output / "M4" / "slip_target"
    for filename, key in (("result.json", "result"), ("raw.npz", "raw"), ("failure.json", "failure"), ("telemetry.jsonl", "telemetry")):
        path = case_dir / filename
        if path.is_file():
            record[f"{key}_path"] = path.relative_to(output).as_posix()
            record[f"{key}_sha256"] = _sha(path)
    _write_json(logs / "M4_slip_target.process.json", record)
    return record


def execute() -> int:
    output = ROOT / OUTPUT_REL
    _, binding = _verify_frozen(output)
    run_root = output / "M4"
    if run_root.exists():
        raise FileExistsError("R1.12 M4 directory already exists; no retry/overwrite is permitted.")
    run_root.mkdir(parents=True, exist_ok=False)
    _write_json(run_root / "progress.json", {"status": "RUNNING", "started_utc": _utc()}, exclusive=False)
    process = _invoke(output, binding)
    case_dir = run_root / "slip_target"
    result_path, failure_path = case_dir / "result.json", case_dir / "failure.json"
    if process["exit_code"] == 0 and result_path.is_file():
        result = _json(result_path)
        status = result.get("diagnostic", {}).get("status", "UNKNOWN")
    elif failure_path.is_file():
        status = "FAIL_CLOSED_NUMERICAL_OR_RUNTIME"
    else:
        status = "FAIL_CLOSED_INCOMPLETE_PROCESS_ARTIFACTS"
    final = {"artifact_id": ARTIFACT_ID, "status": "M4_SLIP_DIAGNOSTIC_PASS" if status == "PASS_DIAGNOSTIC_GATES" else status, "case_status": status, "contract_sha256": binding["contract_sha256"], "execution_binding_sha256": binding["execution_binding_sha256"], "source_bundle_sha256": binding["source_bundle_sha256"], "source_head": binding["source_head"], "execution_process": process, "result_path": result_path.relative_to(output).as_posix() if result_path.is_file() else None, "result_sha256": _sha(result_path) if result_path.is_file() else None, "raw_path": (case_dir / "raw.npz").relative_to(output).as_posix() if (case_dir / "raw.npz").is_file() else None, "raw_sha256": _sha(case_dir / "raw.npz") if (case_dir / "raw.npz").is_file() else None, "failure_path": failure_path.relative_to(output).as_posix() if failure_path.is_file() else None, "failure_sha256": _sha(failure_path) if failure_path.is_file() else None, "telemetry_path": (case_dir / "telemetry.jsonl").relative_to(output).as_posix() if (case_dir / "telemetry.jsonl").is_file() else None, "telemetry_sha256": _sha(case_dir / "telemetry.jsonl") if (case_dir / "telemetry.jsonl").is_file() else None, "m1_m2_m3_rerun": False, "stick_case_rerun": False, "retry_count": 0, "reference_or_replay_run": False, "production_mechanics_changed_by_this_campaign": False, "thresholds_changed": False, "formal_wp08_qualification": False, "points_awarded": False}
    _write_json(run_root / "final.json", final)
    _write_json(run_root / "progress.json", {"status": "COMPLETED", "completed_utc": _utc(), **final}, exclusive=False)
    print(json.dumps(final, indent=2, sort_keys=True))
    return 0 if final["status"] == "M4_SLIP_DIAGNOSTIC_PASS" else 3


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--output-root", type=Path, default=ROOT / OUTPUT_REL)
    parser.add_argument("--execution-binding-sha256")
    args = parser.parse_args()
    if args.freeze:
        print(json.dumps(freeze(), indent=2, sort_keys=True))
        return 0
    if args.execute:
        return execute()
    if args.worker and args.execution_binding_sha256:
        return _worker(args.output_root.resolve(), args.execution_binding_sha256)
    parser.error("Choose --freeze, --execute, or worker with an execution-binding SHA.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
