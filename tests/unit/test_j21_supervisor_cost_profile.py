from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from research.j21.supervised_exact import run_supervised_exact, sha256_file


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "research" / "j21" / "contracts" / "cost_profile_001.json"
OUTPUT = ROOT / "research" / "j21" / "results" / "cost_profile_001"
CONTRACT_002 = ROOT / "research" / "j21" / "contracts" / "cost_profile_002.json"
OUTPUT_002 = ROOT / "research" / "j21" / "results" / "cost_profile_002"


def _write_manifest(directory: Path, contract_sha256: str, contract_id: str) -> None:
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != "artifact_manifest.json":
            relative = path.relative_to(directory).as_posix()
            files[relative] = {"sha256": sha256_file(path), "bytes": path.stat().st_size}
    manifest = {
        "schema": "qfsolver-j21-supervisor-cost-artifact-manifest-v1",
        "contract_id": contract_id,
        "contract_sha256": contract_sha256,
        "files": files,
        "limitations": [
            "Synthetic exact-system work only; no FEM assembly, harmonic solve, or NAFEMS archive.",
            "RSS is sampled per worker process tree and may overshoot between samples; it is not a hard quota.",
            "Measurements are observations from one Windows host and do not imply worst-case cost.",
        ],
    }
    manifest_path = directory / "artifact_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def test_j21_supervisor_cost_profile() -> None:
    if OUTPUT.exists() and any(OUTPUT.iterdir()):
        raise RuntimeError("J21 cost output already exists; refusing to overwrite the frozen run")
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if contract.get("state") != "FROZEN_BEFORE_EXECUTION":
        raise RuntimeError("J21 cost contract must be frozen before execution")
    contract_sha256 = hashlib.sha256(CONTRACT.read_bytes()).hexdigest()
    journal = run_supervised_exact(CONTRACT, OUTPUT / "run")
    expected = {case["case_id"]: case for case in contract["cases"]}
    for result in journal["cases"]:
        case = expected[result["case_id"]]
        if journal["run_status"] != "COMPLETE" or result["supervisor_status"] != "COMPLETE":
            raise AssertionError(result)
        if result["exact_status"] != "PASS":
            raise AssertionError(result)
        if result["exact_result"]["stored_entries"] != case["expected_stored_entries"]:
            raise AssertionError(result)
        if result["exact_result"]["dimension"] != case["dimension"]:
            raise AssertionError(result)
        if result["peak_rss_bytes_sampled"] is None:
            raise AssertionError("sampled process-tree RSS is required by the frozen contract")
    _write_manifest(OUTPUT, contract_sha256, contract["contract_id"])


def test_j21_supervisor_cost_profile_002() -> None:
    if OUTPUT_002.exists() and any(OUTPUT_002.iterdir()):
        raise RuntimeError("J21 cost output already exists; refusing to overwrite the frozen run")
    contract = json.loads(CONTRACT_002.read_text(encoding="utf-8"))
    if contract.get("state") != "FROZEN_BEFORE_EXECUTION":
        raise RuntimeError("J21 cost contract must be frozen before execution")
    contract_sha256 = hashlib.sha256(CONTRACT_002.read_bytes()).hexdigest()
    journal = run_supervised_exact(CONTRACT_002, OUTPUT_002 / "run")
    expected = {case["case_id"]: case for case in contract["cases"]}
    for result in journal["cases"]:
        case = expected[result["case_id"]]
        if journal["run_status"] != "COMPLETE" or result["supervisor_status"] != "COMPLETE":
            raise AssertionError(result)
        if result["exact_status"] != "PASS":
            raise AssertionError(result)
        if result["exact_result"]["stored_entries"] != case["expected_stored_entries"]:
            raise AssertionError(result)
        if result["exact_result"]["dimension"] != case["dimension"]:
            raise AssertionError(result)
        if result["peak_rss_bytes_sampled"] is None:
            raise AssertionError("sampled process-tree RSS is required by the frozen contract")
    _write_manifest(OUTPUT_002, contract_sha256, contract["contract_id"])


def test_j21_cost_artifact_manifest_uses_contract_id(tmp_path: Path) -> None:
    _write_manifest(tmp_path, "a" * 64, "J21-SYNTHETIC-TEST-CONTRACT")
    manifest = json.loads((tmp_path / "artifact_manifest.json").read_text(encoding="utf-8"))
    assert manifest["contract_id"] == "J21-SYNTHETIC-TEST-CONTRACT"
