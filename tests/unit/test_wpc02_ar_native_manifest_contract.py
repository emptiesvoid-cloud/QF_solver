"""Static integrity and authorization checks for the WP-C02-AR native candidate."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = Path(os.environ.get(
    "WPC02_AR_NATIVE_MANIFEST_PATH",
    ROOT / "qualification/0_2_12/wp_c02_ar_native_execution_manifest.json",
))


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aggregate(files: dict[str, str]) -> str:
    payload = "\n".join(f"{path}  {files[path]}" for path in sorted(files))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def test_manifest_source_hash_contract_and_all_files() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    runner = _load_module("wpc02_ar_candidate_runner_contract", ROOT / "scripts/run_wpc02_ar_native_pytest.py")
    assert manifest["source_set_contract"] == runner.SOURCE_SET_CONTRACT
    files = manifest["source_files_sha256"]
    assert manifest["source_file_count"] == len(files)
    assert manifest["source_set_sha256"] == _aggregate(files)
    assert runner._source_set_sha256(files) == _aggregate(files)
    assert "qualification/0_2_12/wp_c02_ar_native_preparation_report.md" not in files
    assert "qualification/0_2_12/wp_c02_ar_native_execution_manifest.json" not in files
    for relative, expected in files.items():
        path = ROOT / relative
        assert path.is_file(), f"missing frozen source: {relative}"
        assert _sha256(path) == expected, f"source hash mismatch: {relative}"
    runner._verify_source_set(manifest)


def test_runner_rejects_aggregate_tampering() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    runner = _load_module("wpc02_ar_candidate_runner_tamper", ROOT / "scripts/run_wpc02_ar_native_pytest.py")
    manifest["source_set_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="source-set hash mismatch"):
        runner._verify_source_set(manifest)


def test_runner_rejects_wrong_git_identity() -> None:
    runner = _load_module("wpc02_ar_candidate_runner_git_identity", ROOT / "scripts/run_wpc02_ar_native_pytest.py")
    with pytest.raises(RuntimeError, match="Frozen Git HEAD mismatch"):
        runner._verify_git_identity({"identity": {"git_head": "0" * 40, "git_tree_oid": "0" * 40}})


def test_runner_accepts_current_git_identity() -> None:
    runner = _load_module("wpc02_ar_candidate_runner_git_identity_valid", ROOT / "scripts/run_wpc02_ar_native_pytest.py")
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    tree = subprocess.run(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    runner._verify_git_identity({"identity": {"git_head": head, "git_tree_oid": tree}})


def test_runner_rejects_source_path_escape() -> None:
    runner = _load_module("wpc02_ar_candidate_runner_path", ROOT / "scripts/run_wpc02_ar_native_pytest.py")
    manifest = {
        "source_set_contract": runner.SOURCE_SET_CONTRACT,
        "source_files_sha256": {"../outside": "0" * 64},
        "source_file_count": 1,
        "source_set_sha256": _aggregate({"../outside": "0" * 64}),
    }
    with pytest.raises(RuntimeError, match="repository-relative POSIX"):
        runner._verify_source_set(manifest)


def test_runner_rejects_source_missing_from_identified_commit(tmp_path: Path) -> None:
    runner = _load_module("wpc02_ar_candidate_runner_commit_membership", ROOT / "scripts/run_wpc02_ar_native_pytest.py")
    source = tmp_path / "candidate.py"
    source.write_text("value = 1\n", encoding="utf-8")
    files = {"candidate.py": _sha256(source)}
    manifest = {
        "source_set_contract": runner.SOURCE_SET_CONTRACT,
        "source_files_sha256": files,
        "source_file_count": 1,
        "source_set_sha256": _aggregate(files),
    }
    with pytest.raises(RuntimeError, match="not present in the identified Git commit"):
        runner._verify_source_set(manifest, root=ROOT, require_committed=True)


def test_runner_rejects_changed_source_file(tmp_path: Path) -> None:
    runner = _load_module("wpc02_ar_candidate_runner_changed_source", ROOT / "scripts/run_wpc02_ar_native_pytest.py")
    (tmp_path / "source.py").write_text("changed\n", encoding="utf-8")
    files = {"source.py": "0" * 64}
    manifest = {
        "source_set_contract": runner.SOURCE_SET_CONTRACT,
        "source_files_sha256": files,
        "source_file_count": 1,
        "source_set_sha256": _aggregate(files),
    }
    with pytest.raises(RuntimeError, match="Frozen source hash mismatch"):
        runner._verify_source_set(manifest, root=tmp_path)


def test_runner_refuses_wrong_manifest_digest_before_pytest() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/run_wpc02_ar_native_pytest.py"),
            "--owner-go",
            "GO-RUN-FEM-NATIF",
            "--owner-manifest-sha256",
            "0" * 64,
            "--manifest",
            str(MANIFEST_PATH),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "Manifest digest does not match" in result.stderr


def test_prospective_owner_approval_matches_frozen_ar_contract() -> None:
    approval = json.loads((ROOT / "qualification/0_2_12/wp_c02_n03_ar_prospective_criteria_approval.json").read_text(encoding="utf-8"))
    plan_path = ROOT / "qualification/0_2_12/wp_c02_ar_mesh_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    protocol_path = ROOT / "qualification/0_2_12/wp_c02_ar_spatial_convergence_protocol_report.md"
    assert approval["plan_sha256"] == _sha256(plan_path)
    assert approval["protocol_sha256"] == _sha256(protocol_path)
    assert approval["decision_id"] == "WP-C02-N03-OWNER-CRITERIA-20261023"
    assert len(approval["criteria"]) == 6

    endpoint = plan["proposed_ar_endpoint_gates_require_owner_approval"]
    assert endpoint["relative_displacement_error_ratio_M5_over_M1_strictly_less_than"] == 0.9
    assert endpoint["relative_pressure_error_ratio_M5_over_M1_strictly_less_than"] == 0.9
    assert endpoint["energy_error_norm_M5_strictly_less_than_M1"] is True
    front = plan["proposed_ar_front_gate_requires_owner_approval"]
    assert front["eligible_levels"] == ["M2", "M3", "M4", "M5"]
    assert front["physical_resolution_gate"] == "D_front,max/hx <= 1 at each eligible level"
    assert front["spatial_locality_gate"] == "every false-positive or false-negative node is within hx of x=0.5 m"
    assert front["coverage_gate"] == "every y row has interpretable active and open states and a front bracket; no row may be silently excluded"
    gates = plan["frozen_aj_acceptance_gates"]
    assert gates["complementarity_tolerance_nm"] == 1e-10
    assert gates["production_stationarity_inf_residual_n"] == 1e-6
    assert gates["production_normalized_force_balance"] == 1e-9
    assert gates["production_normalized_moment_balance"] == 1e-9


@pytest.mark.parametrize("level", ["M4", "M5"])
def test_pytest_scenario_is_disabled_without_owner_token(monkeypatch: pytest.MonkeyPatch, level: str) -> None:
    monkeypatch.delenv("WPC02_AR_NATIVE_OWNER_GO_TOKEN", raising=False)
    monkeypatch.delenv("WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256", raising=False)
    scenario = _load_module(
        f"wpc02_ar_candidate_scenario_gate_{level.lower()}",
        ROOT / "tests/verification/test_wpc02_ar_native_contact_convergence.py",
    )
    with pytest.raises(pytest.skip.Exception, match="GO-RUN-FEM-NATIF"):
        scenario._require_owner_go(level)


@pytest.mark.parametrize("level", ["M4", "M5"])
def test_pytest_scenario_is_disabled_for_wrong_manifest_digest(
    monkeypatch: pytest.MonkeyPatch, level: str
) -> None:
    monkeypatch.setenv("WPC02_AR_NATIVE_OWNER_GO_TOKEN", "GO-RUN-FEM-NATIF")
    monkeypatch.setenv("WPC02_AR_NATIVE_OWNER_GO_MANIFEST_SHA256", "0" * 64)
    scenario = _load_module(
        f"wpc02_ar_candidate_scenario_digest_gate_{level.lower()}",
        ROOT / "tests/verification/test_wpc02_ar_native_contact_convergence.py",
    )
    with pytest.raises(pytest.skip.Exception, match="exact execution-manifest SHA-256"):
        scenario._require_owner_go(level)
