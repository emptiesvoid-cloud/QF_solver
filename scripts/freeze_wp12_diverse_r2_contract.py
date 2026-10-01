"""Freeze WP12 R3.6-R2 with immutable links to both failed attempts."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts import freeze_wp12_diverse_contract as prior_freezer  # noqa: E402
from scripts import run_wp12_diverse_code_aster as runner  # noqa: E402
from scripts.wp12_diverse_models import case_catalog  # noqa: E402

BRANCH = "codex/wp12-expanded-correlation"
BASE_SHA = "b591a4c145d7139467281ab67d0b32fec68276e0"
R1_CONTRACT = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r1_contract.json")
R1_MANIFEST = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r1_manifest.json")
R1_AUDIT = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r1_audit.json")
R1_RAW = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r1_raw")
R1_SUMMARY = R1_RAW / "wp12_expanded_summary.json"

CONTRACT_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r2_contract.json")
OUTPUT_ROOT = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r2_raw")
MANIFEST_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r2_manifest.json")
AUDIT_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r2_audit.json")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _manifest_record(raw_root: Path, manifest_path: Path) -> dict[str, Any]:
    manifest = runner.engine.load_json(ROOT / manifest_path)
    entries = manifest.get("files")
    if not isinstance(entries, dict) or not entries:
        raise RuntimeError(f"Attempt manifest is empty or invalid: {manifest_path}")
    actual = {
        path.relative_to(ROOT / raw_root).as_posix()
        for path in (ROOT / raw_root).rglob("*")
        if path.is_file()
    }
    if actual != set(entries):
        raise RuntimeError(f"Attempt raw file set differs from manifest: {raw_root}")
    for relative, record in entries.items():
        path = ROOT / raw_root / relative
        if (
            not path.is_file()
            or path.stat().st_size != record.get("size_bytes")
            or runner.engine.sha256_file(path) != record.get("sha256")
        ):
            raise RuntimeError(f"Attempt raw hash mismatch: {relative}")
    return {
        "raw_root": raw_root.as_posix(),
        "manifest_path": manifest_path.as_posix(),
        "manifest_sha256": runner.engine.sha256_file(ROOT / manifest_path),
        "raw_file_count": len(entries),
    }


def _verify_r1_failure() -> dict[str, Any]:
    contract = runner.engine.load_json(ROOT / R1_CONTRACT)
    summary = runner.engine.load_json(ROOT / R1_SUMMARY)
    audit = runner.engine.load_json(ROOT / R1_AUDIT)
    process_path = R1_RAW / "tet4_l_section_beam_h1_axial_x" / "process.json"
    process = runner.engine.load_json(ROOT / process_path)
    case = summary.get("cases", {}).get("tet4_l_section_beam_h1_axial_x", {})
    contract_sha = runner.engine.sha256_file(ROOT / R1_CONTRACT)
    manifest_sha = runner.engine.sha256_file(ROOT / R1_MANIFEST)
    if contract.get("revision") != "R3_6_DIVERSE_TOPOLOGY_144_CASE_LINEAR_STATIC_CORRELATION_R1":
        raise RuntimeError("R3.6 R1 contract identity mismatch.")
    if (
        summary.get("status") != "FAIL_CLOSED"
        or summary.get("attempted_case_count") != 1
        or summary.get("candidate_cases_passed") != 0
        or summary.get("not_started_case_count") != 143
        or summary.get("execution_aborted_on_error") is not True
        or summary.get("contract_sha256") != contract_sha
        or case.get("status") != "FAIL_CLOSED_EXECUTION"
        or process.get("exit_code") != 2
        or (ROOT / R1_RAW / "tet4_l_section_beam_h1_axial_x" / "aster_raw.json").exists()
    ):
        raise RuntimeError("R3.6 R1 does not show the preserved fail-fast Code_Aster input failure.")
    if (
        audit.get("audit_status") != "FAIL_CLOSED"
        or audit.get("case_count") != 144
        or audit.get("case_pass_count") != 0
        or audit.get("contract_sha256") != contract_sha
        or audit.get("manifest_sha256") != manifest_sha
    ):
        raise RuntimeError("R3.6 R1 independent audit is inconsistent with its contract or manifest.")
    manifest_data = _manifest_record(R1_RAW, R1_MANIFEST)
    if manifest_data["raw_file_count"] != 20:
        raise RuntimeError("R3.6 R1 expected exactly the 20 manifested raw files.")

    attempt1 = prior_freezer._verify_failed_r3_6_attempt1()
    attempt1_contract = Path(attempt1["contract_path"])
    attempt1_manifest = Path(attempt1["manifest_path"])
    attempt1_audit = Path(attempt1["audit_path"])
    attempt1_summary = Path(attempt1["summary_path"])
    attempt1_record = {
        "attempt_id": "r3_6_attempt1_serializer_recursion",
        "revision": attempt1["revision"],
        "classification": attempt1["classification"],
        "contract_path": attempt1_contract.as_posix(),
        "contract_sha256": runner.engine.sha256_file(ROOT / attempt1_contract),
        "manifest_path": attempt1_manifest.as_posix(),
        "manifest_sha256": runner.engine.sha256_file(ROOT / attempt1_manifest),
        "audit_path": attempt1_audit.as_posix(),
        "audit_sha256": runner.engine.sha256_file(ROOT / attempt1_audit),
        "summary_path": attempt1_summary.as_posix(),
        "summary_sha256": runner.engine.sha256_file(ROOT / attempt1_summary),
        "raw_root": attempt1_summary.parent.as_posix(),
        "code_aster_process_started": False,
        "numerical_result_produced": False,
    }
    r1_record = {
        "attempt_id": "r3_6_r1_force_node_label",
        "revision": contract["revision"],
        "classification": "CODE_ASTER_FORCE_NODALE_COMPACT_NODE_LABEL_PARSE_FAILURE",
        "contract_path": R1_CONTRACT.as_posix(),
        "contract_sha256": contract_sha,
        "manifest_path": R1_MANIFEST.as_posix(),
        "manifest_sha256": manifest_sha,
        "audit_path": R1_AUDIT.as_posix(),
        "audit_sha256": runner.engine.sha256_file(ROOT / R1_AUDIT),
        "summary_path": R1_SUMMARY.as_posix(),
        "summary_sha256": runner.engine.sha256_file(ROOT / R1_SUMMARY),
        "raw_root": R1_RAW.as_posix(),
        "first_case_process_path": process_path.as_posix(),
        "first_case_process_sha256": runner.engine.sha256_file(ROOT / process_path),
        "first_case_exit_code": 2,
        "first_case_aster_raw_present": False,
        "manifested_raw_file_count": manifest_data["raw_file_count"],
        "code_aster_process_started": True,
        "numerical_result_produced": False,
    }
    return {"attempt1": attempt1_record, "r1": r1_record}


def build_contract() -> dict[str, Any]:
    if _git("branch", "--show-current") != BRANCH:
        raise RuntimeError(f"Must freeze on isolated branch {BRANCH}.")
    if _git("status", "--porcelain"):
        raise RuntimeError("Working tree must be clean before R3.6-R2 contract freeze.")
    head = _git("rev-parse", "HEAD")
    if head != BASE_SHA and subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_SHA, "HEAD"], cwd=ROOT, check=False
    ).returncode != 0:
        raise RuntimeError("R3.6-R2 branch does not descend from the reviewed R3.6 preparation commit.")
    if subprocess.run(["git", "diff", "--quiet", BASE_SHA, "HEAD", "--", "src/"], cwd=ROOT, check=False).returncode:
        raise RuntimeError("R3.6-R2 tooling preparation changed production source.")
    for path in (CONTRACT_PATH, OUTPUT_ROOT, MANIFEST_PATH, AUDIT_PATH):
        if (ROOT / path).exists():
            raise RuntimeError(f"R3.6-R2 output already exists; refusing overwrite: {path}")

    prior_attempts = _verify_r1_failure()
    template = runner.engine.load_json(ROOT / R1_CONTRACT)
    cases = [runner._case_record(case) for case in case_catalog()]
    if len(cases) != 144 or cases != template.get("cases"):
        raise RuntimeError("R3.6-R2 must preserve the exact frozen 144-case model matrix.")

    contract = json.loads(json.dumps(template))
    contract.update(
        {
            "revision": "R3_6_DIVERSE_TOPOLOGY_144_CASE_LINEAR_STATIC_CORRELATION_R2",
            "frozen_utc": datetime.now(timezone.utc).isoformat(),
            "branch_base_sha": BASE_SHA,
            "freeze_commit_sha": head,
            "runner_sha": prior_freezer._source_commit("scripts/run_wp12_diverse_code_aster.py"),
            "model_builder_sha": prior_freezer._source_commit("scripts/wp12_diverse_models.py"),
            "auditor_sha": prior_freezer._source_commit("scripts/audit_wp12_expanded_code_aster.py"),
            "contract_builder_sha": prior_freezer._source_commit("scripts/freeze_wp12_diverse_r2_contract.py"),
            "output_root": OUTPUT_ROOT.as_posix(),
            "manifest_path": MANIFEST_PATH.as_posix(),
            "audit_path": AUDIT_PATH.as_posix(),
            "supersedes_failed_attempts": [prior_attempts["attempt1"], prior_attempts["r1"]],
            "exporter_policy": {
                "force_nodal_addressing": "FORCE_NODALE GROUP_NO=QF%05d singleton groups",
                "load_vector_change": False,
                "geometry_or_mesh_change": False,
            },
            "failure_history": {
                "attempt1": "preserved pre-solver serializer RecursionError; no Code_Aster process",
                "r1": "preserved Code_Aster 18.1 NOEUD compact-label parse failure before MECA_STATIQUE",
                "historical_attempts_overwritten": False,
            },
        }
    )
    contract.pop("supersedes_failed_attempt", None)
    return contract


def main() -> int:
    if (ROOT / CONTRACT_PATH).exists():
        raise SystemExit(f"Refusing to overwrite existing contract: {CONTRACT_PATH}")
    contract = build_contract()
    target = ROOT / CONTRACT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(contract, indent=2, sort_keys=True, allow_nan=False) + "\n")
    print(json.dumps(
        {
            "status": contract["status"],
            "revision": contract["revision"],
            "case_count": contract["case_count"],
            "freeze_commit_sha": contract["freeze_commit_sha"],
            "contract_path": CONTRACT_PATH.as_posix(),
        },
        indent=2,
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
