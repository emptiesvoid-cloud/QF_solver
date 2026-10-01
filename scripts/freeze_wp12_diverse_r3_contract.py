"""Freeze WP12 R3.6-R3 and bind every preserved R3.6 attempt."""

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

from scripts import run_wp12_diverse_code_aster as runner  # noqa: E402
from scripts.wp12_diverse_models import case_catalog  # noqa: E402

BRANCH = "codex/wp12-expanded-correlation"
BASE_SHA = "b591a4c145d7139467281ab67d0b32fec68276e0"
R2_CONTRACT = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r2_contract.json")
R2_PREFLIGHT_AUDIT = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r2_preflight_audit.json")
CONTRACT_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r3_contract.json")
OUTPUT_ROOT = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r3_raw")
MANIFEST_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r3_manifest.json")
AUDIT_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_6_diverse_r3_audit.json")


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _verify_r2_preflight_block(r2_contract: dict[str, Any]) -> dict[str, Any]:
    audit = runner.engine.load_json(ROOT / R2_PREFLIGHT_AUDIT)
    contract_sha = runner.engine.sha256_file(ROOT / R2_CONTRACT)
    contract_commit = _git("log", "-1", "--format=%H", "--", R2_CONTRACT.as_posix())
    if (
        r2_contract.get("revision") != "R3_6_DIVERSE_TOPOLOGY_144_CASE_LINEAR_STATIC_CORRELATION_R2"
        or audit.get("audit_status") != "FAIL_CLOSED_PREFLIGHT"
        or audit.get("contract_sha256") != contract_sha
        or audit.get("contract_commit_sha") != contract_commit
        or audit.get("process_exit_code") != 1
        or audit.get("failure") != "CampaignError: Frozen contract_builder_sha differs from tracked source commit."
        or audit.get("execution_boundary", {}).get("cases_started") != 0
        or audit.get("execution_boundary", {}).get("code_aster_process_started") is not False
        or audit.get("execution_boundary", {}).get("docker_runtime_probe_started") is not False
        or audit.get("execution_boundary", {}).get("raw_output_created") is not False
    ):
        raise RuntimeError("R3.6 R2 preflight-block audit is missing or inconsistent.")
    if R2_CONTRACT.as_posix() != audit.get("contract_path"):
        raise RuntimeError("R3.6 R2 preflight audit references a different contract path.")
    for relative in (r2_contract["output_root"], r2_contract["manifest_path"], r2_contract["audit_path"]):
        if (ROOT / relative).exists():
            raise RuntimeError(f"R3.6 R2 preflight block unexpectedly created output: {relative}")
    return {
        "attempt_id": "r3_6_r2_preflight_builder_source_mismatch",
        "revision": r2_contract["revision"],
        "classification": "CONTRACT_BUILDER_SOURCE_PATH_MISMATCH_BEFORE_DOCKER_PREFLIGHT",
        "contract_path": R2_CONTRACT.as_posix(),
        "contract_sha256": contract_sha,
        "contract_commit_sha": contract_commit,
        "runner_sha": audit.get("runner_sha"),
        "preflight_audit_path": R2_PREFLIGHT_AUDIT.as_posix(),
        "preflight_audit_sha256": runner.engine.sha256_file(ROOT / R2_PREFLIGHT_AUDIT),
        "code_aster_process_started": False,
        "docker_runtime_probe_started": False,
        "cases_started": 0,
        "raw_output_created": False,
    }


def build_contract() -> dict[str, Any]:
    if _git("branch", "--show-current") != BRANCH:
        raise RuntimeError(f"Must freeze on isolated branch {BRANCH}.")
    if _git("status", "--porcelain"):
        raise RuntimeError("Working tree must be clean before R3.6-R3 contract freeze.")
    head = _git("rev-parse", "HEAD")
    if head != BASE_SHA and subprocess.run(
        ["git", "merge-base", "--is-ancestor", BASE_SHA, "HEAD"], cwd=ROOT, check=False
    ).returncode != 0:
        raise RuntimeError("R3.6-R3 branch does not descend from the reviewed preparation commit.")
    if subprocess.run(["git", "diff", "--quiet", BASE_SHA, "HEAD", "--", "src/"], cwd=ROOT, check=False).returncode:
        raise RuntimeError("R3.6-R3 tooling preparation changed production source.")
    for path in (CONTRACT_PATH, OUTPUT_ROOT, MANIFEST_PATH, AUDIT_PATH):
        if (ROOT / path).exists():
            raise RuntimeError(f"R3.6-R3 output already exists; refusing overwrite: {path}")

    r2_contract = runner.engine.load_json(ROOT / R2_CONTRACT)
    runner._verify_prior_attempts(r2_contract, ROOT)
    r2_block = _verify_r2_preflight_block(r2_contract)
    cases = [runner._case_record(case) for case in case_catalog()]
    if len(cases) != 144 or cases != r2_contract.get("cases"):
        raise RuntimeError("R3.6-R3 must preserve the exact frozen 144-case model matrix.")

    contract = json.loads(json.dumps(r2_contract))
    contract.update(
        {
            "revision": "R3_6_DIVERSE_TOPOLOGY_144_CASE_LINEAR_STATIC_CORRELATION_R3",
            "frozen_utc": datetime.now(timezone.utc).isoformat(),
            "branch_base_sha": BASE_SHA,
            "freeze_commit_sha": head,
            "runner_sha": _git("log", "-1", "--format=%H", "--", "scripts/run_wp12_diverse_code_aster.py"),
            "model_builder_sha": _git("log", "-1", "--format=%H", "--", "scripts/wp12_diverse_models.py"),
            "auditor_sha": _git("log", "-1", "--format=%H", "--", "scripts/audit_wp12_expanded_code_aster.py"),
            "contract_builder_sha": _git("log", "-1", "--format=%H", "--", "scripts/freeze_wp12_diverse_r3_contract.py"),
            "contract_builder_path": "scripts/freeze_wp12_diverse_r3_contract.py",
            "output_root": OUTPUT_ROOT.as_posix(),
            "manifest_path": MANIFEST_PATH.as_posix(),
            "audit_path": AUDIT_PATH.as_posix(),
            "supersedes_failed_attempts": [*r2_contract["supersedes_failed_attempts"], r2_block],
            "failure_history": {
                **r2_contract["failure_history"],
                "r2_preflight": "preserved contract-builder path guard failure before Docker or solver startup",
                "historical_attempts_overwritten": False,
            },
        }
    )
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
