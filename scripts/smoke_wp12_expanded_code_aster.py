"""Run a diagnostic four-family Code_Aster serializer smoke before WP12 R3.5 freeze.

This is preparation evidence only. It is not part of the frozen 144-case matrix
and cannot be used to claim a WP12 correlation result.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

from scripts.audit_wp12_expanded_code_aster import _audit_comm_text, _audit_mesh_text  # noqa: E402
from scripts.run_wp12_expanded_code_aster import (  # noqa: E402
    ASTER_RUNNER,
    IMAGE,
    _manifest,
    _mesh_text,
    _run_case,
    _runtime_command,
    load_json,
    sha256_file,
    write_json,
)
from scripts.wp12_expanded_models import FAMILIES, build_case  # noqa: E402


BRANCH = "codex/wp12-expanded-correlation"
BASE_SHA = "c5e842d5e589358633221ecd9f29c2ff1ef003aa"
PARENT_CONTRACT = Path("qualification/0_2_9/wp12_external_vv_r3_4_expanded_contract.json")
OUTPUT_ROOT = Path("qualification/0_2_9/wp12_external_vv_r3_5_smoke_r2_raw")
REPORT_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_5_mesh_smoke_r2.json")
MANIFEST_PATH = Path("qualification/0_2_9/wp12_external_vv_r3_5_mesh_smoke_r2_manifest.json")
SMOKE_CONTRACT_MARKER = "DIAGNOSTIC_ONLY_NO_FROZEN_144_CASE_CONTRACT"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _preflight(contract: dict[str, Any]) -> dict[str, Any]:
    if _git("branch", "--show-current") != BRANCH:
        raise RuntimeError(f"Smoke must run on isolated branch {BRANCH}.")
    if _git("status", "--porcelain"):
        raise RuntimeError("Working tree must be clean before diagnostic smoke.")
    if subprocess.run(["git", "merge-base", "--is-ancestor", BASE_SHA, "HEAD"], cwd=ROOT, check=False).returncode:
        raise RuntimeError("Smoke source does not descend from the frozen WP12 base.")
    if subprocess.run(["git", "diff", "--quiet", BASE_SHA, "HEAD", "--", "src/"], cwd=ROOT, check=False).returncode:
        raise RuntimeError("Diagnostic smoke preparation changed production source.")
    for path in (OUTPUT_ROOT, MANIFEST_PATH, REPORT_PATH):
        if (ROOT / path).exists():
            raise RuntimeError(f"Refusing to overwrite diagnostic smoke output: {path}")
    docker = shutil.which("docker")
    if docker is None:
        raise RuntimeError("Docker CLI unavailable")
    image = subprocess.run([docker, "image", "inspect", IMAGE, "--format", "{{.Id}}"], capture_output=True, text=True)
    if image.returncode != 0 or image.stdout.strip() != contract.get("code_aster_image_id"):
        raise RuntimeError("Pinned Code_Aster image ID is unavailable or mismatched")
    probe = subprocess.run(
        [docker, "run", "--rm", "--entrypoint", "/bin/bash", IMAGE, "-lc", _runtime_command(f"{ASTER_RUNNER} --version")],
        capture_output=True,
        text=True,
    )
    version = probe.stdout.strip()
    if probe.returncode != 0 or not version.startswith(f"code_aster {contract['code_aster_version']} "):
        raise RuntimeError("Pinned Code_Aster runtime/import preflight failed")
    return {
        "source_sha": _git("rev-parse", "HEAD"),
        "execution_sha": _git("rev-parse", "HEAD"),
        "runner_sha": _git("log", "-1", "--format=%H", "--", "scripts/run_wp12_expanded_code_aster.py"),
        "smoke_runner_sha": _git("log", "-1", "--format=%H", "--", "scripts/smoke_wp12_expanded_code_aster.py"),
        "code_aster_image_id": image.stdout.strip(),
        "code_aster_runtime_version": version,
        "threshold_source_contract_sha256": sha256_file(ROOT / PARENT_CONTRACT),
        "smoke_contract_sha256": SMOKE_CONTRACT_MARKER,
    }


def main() -> int:
    parent = load_json(ROOT / PARENT_CONTRACT)
    if parent.get("revision") != "R3_4_EXPANDED_144_CASE_LINEAR_STATIC_CORRELATION":
        raise RuntimeError("Expected the preserved R3.4 contract as the unchanged smoke gate source.")
    readiness = _preflight(parent)
    output_root = ROOT / OUTPUT_ROOT
    output_root.mkdir(parents=True, exist_ok=False)
    write_json(output_root / "preflight.json", readiness)
    smoke_contract = {
        "runner_sha": readiness["runner_sha"],
        "timeout_seconds": parent["timeout_seconds"],
        "memory_limit_mb": parent["memory_limit_mb"],
        "gates": parent["gates"],
    }
    results: list[dict[str, Any]] = []
    for family in FAMILIES:
        case = build_case(family, "slender_beam", "H3", "combined_xyz")
        mesh = _mesh_text(case)
        if max(map(len, mesh.splitlines())) > 80:
            errors = ["generated mesh line exceeds 80 columns"]
        else:
            smoke_case = output_root / case.case_id
            smoke_case.mkdir(parents=True, exist_ok=False)
            mesh_path = smoke_case / f"{case.case_id}.mail"
            comm_path = smoke_case / f"{case.case_id}.comm"
            mesh_path.write_text(mesh, encoding="ascii", newline="\n")
            from scripts.run_wp12_expanded_code_aster import _comm_text

            comm_path.write_text(_comm_text(case), encoding="utf-8", newline="\n")
            errors = _audit_mesh_text(mesh_path, case.family, case.model.nodes, case.connectivity)
            errors.extend(_audit_comm_text(comm_path, case.system.loads.reshape(-1, 3), parent["material"], case.case_id))
            mesh_path.unlink()
            comm_path.unlink()
            smoke_case.rmdir()
        if errors:
            results.append({"case_id": case.case_id, "family": family, "status": "FAIL_CLOSED_STATIC_INPUT", "errors": errors})
            break
        work = output_root / case.case_id
        try:
            result = _run_case(case, work, smoke_contract, readiness)
            status = "PASS_SMOKE_ONLY" if result.get("status") == "PASS_CANDIDATE" else "FAIL_CLOSED_SMOKE"
            results.append(
                {
                    "case_id": case.case_id,
                    "family": family,
                    "geometry": case.geometry,
                    "mesh": case.mesh,
                    "load_case": case.load_case,
                    "status": status,
                    "metrics": result.get("metrics"),
                    "comparisons": result.get("comparisons"),
                    "process": result.get("process"),
                    "raw_result_sha256": sha256_file(work / "result.json"),
                    "mesh_text_sha256": sha256_file(work / f"{case.case_id}.mail"),
                    "comm_text_sha256": sha256_file(work / f"{case.case_id}.comm"),
                }
            )
            if status != "PASS_SMOKE_ONLY":
                break
        except Exception as exc:
            results.append({"case_id": case.case_id, "family": family, "status": "FAIL_CLOSED_SMOKE", "error": f"{type(exc).__name__}: {exc}"})
            if work.is_dir():
                write_json(work / "smoke_failure.json", results[-1])
            break
    passed = sum(result.get("status") == "PASS_SMOKE_ONLY" for result in results)
    summary = {
        "campaign": "WP12 R3.5 four-family H3 serializer/input smoke attempt 2",
        "status": "PASS_DIAGNOSTIC_ONLY" if passed == len(FAMILIES) else "FAIL_CLOSED",
        "formal_correlation_evidence": False,
        "source_sha": readiness["source_sha"],
        "runner_sha": readiness["runner_sha"],
        "smoke_runner_sha": readiness["smoke_runner_sha"],
        "threshold_source_contract_sha256": readiness["threshold_source_contract_sha256"],
        "smoke_contract_sha256": SMOKE_CONTRACT_MARKER,
        "code_aster_image_id": readiness["code_aster_image_id"],
        "code_aster_runtime_version": readiness["code_aster_runtime_version"],
        "case_count": len(FAMILIES),
        "case_pass_count": passed,
        "attempted_case_count": len(results),
        "not_started_case_count": len(FAMILIES) - len(results),
        "families": list(FAMILIES),
        "cases": results,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "official_points_changed": False,
    }
    write_json(ROOT / REPORT_PATH, summary)
    _manifest(output_root, ROOT / MANIFEST_PATH)
    summary["manifest_sha256"] = sha256_file(ROOT / MANIFEST_PATH)
    write_json(ROOT / REPORT_PATH, summary)
    print(json.dumps(summary, indent=2, sort_keys=True, allow_nan=False))
    return 0 if summary["status"] == "PASS_DIAGNOSTIC_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
