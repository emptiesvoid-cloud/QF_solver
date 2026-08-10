import json
import subprocess
import sys
from pathlib import Path

from solveur.api import run_qualification_campaign


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = PROJECT_ROOT / "qualification" / "campaign.json"


def test_public_api_runs_official_qualification_campaign(tmp_path: Path):
    output = tmp_path / "campaign"
    summary = run_qualification_campaign(MANIFEST, output)
    assert summary["status"] == "PASS"
    assert summary["case_count"] >= 13
    assert summary["failed_count"] == 0
    assert summary["replacement_candidate_count"] == 3
    assert summary["replacement_ready_count"] == 3
    assert summary["reference_check_count"] >= 24
    assert summary["independent_reference_check_count"] >= 20
    assert "analytic" in summary["reference_types"]
    assert "equilibrium_closed_form" in summary["reference_types"]
    assert "non_regression" in summary["reference_types"]
    assert "REQ-SOL-001" in summary["requirement_coverage"]
    assert "SOV-TET4-PRESSURE-001" in summary["requirement_coverage"]["REQ-LOAD-001"]
    assert "SOV-TET4-BODY-FORCE-001" in summary["requirement_coverage"]["REQ-LOAD-001"]
    assert "SOV-TET4-COMPRESSION-001" in summary["requirement_coverage"]["REQ-SOL-001"]
    assert "REQ-MOD-001" in summary["requirement_coverage"]
    assert "SOV-DYN-SDOF-001" in summary["requirement_coverage"]["REQ-DYN-001"]
    assert "SOV-HAR-SDOF-001" in summary["requirement_coverage"]["REQ-HAR-001"]
    assert sum(case["check_count"] for case in summary["cases"]) >= 20
    assert sum(case["failed_check_count"] for case in summary["cases"]) == 0
    solved_cases = [case for case in summary["cases"] if case["mode"] == "solve"]
    assert summary["evidence_manifest_schema_version"] == 2
    assert summary["evidence_bundle_count"] == len(solved_cases)
    assert summary["evidence_verified_count"] == len(solved_cases)
    assert all(case["evidence_verification"]["status"] == "PASS" for case in solved_cases)
    assert all(case["infrastructure_errors"] == [] for case in solved_cases)
    for case in solved_cases:
        case_dir = Path(case["evidence_dir"])
        evidence_manifest = json.loads((case_dir / "evidence_manifest.json").read_text(encoding="utf-8"))
        assert evidence_manifest["manifest_schema_version"] == 2
        assert evidence_manifest["file_count"] == len(evidence_manifest["files"])
        assert {entry["role"] for entry in evidence_manifest["files"]} >= {
            "input",
            "results",
            "audit",
            "mesh_report",
            "solver_settings",
            "qualification_summary",
        }
    assert (output / "qualification_campaign_summary.json").exists()
    assert (output / "qualification_campaign_summary.md").exists()
    tet4_case = output / "SOV-TET4-STATIC-001"
    assert (tet4_case / "results.json").exists()
    assert (tet4_case / "qualification_summary.json").exists()
    mesh_case = output / "SOV-MESH-REJECT-001"
    mesh_report = json.loads((mesh_case / "mesh_report.json").read_text(encoding="utf-8"))
    assert mesh_report["status"] == "FAIL"


def test_cli_runs_qualification_campaign(tmp_path: Path):
    output = tmp_path / "cli_campaign"
    completed = subprocess.run(
        [
            sys.executable,
            "main_solveur.py",
            "qualify",
            "--manifest",
            str(MANIFEST),
            "--output",
            str(output),
        ],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0
    assert "QUALIFICATION CAMPAIGN STATUS: PASS" in completed.stdout
    data = json.loads((output / "qualification_campaign_summary.json").read_text(encoding="utf-8"))
    assert data["passed_count"] == data["case_count"]
    assert data["replacement_ready_count"] == 3
    assert data["reference_check_count"] >= 24
    assert data["independent_reference_check_count"] >= 20
    assert data["evidence_manifest_schema_version"] == 2
    assert data["evidence_verified_count"] == data["evidence_bundle_count"]
    assert "analytic" in data["reference_types"]


def test_qualification_campaign_fails_when_numeric_criterion_fails(tmp_path: Path):
    manifest = tmp_path / "bad_campaign.json"
    manifest.write_text(
        json.dumps(
            {
                "campaign": "bad_threshold",
                "cases": [
                    {
                        "id": "BAD-STATIC",
                        "requirement": "REQ-SOL-001",
                        "input": str(PROJECT_ROOT / "examples" / "tet4_static.json"),
                        "mode": "solve",
                        "expected_status": "PASS",
                        "checks": [
                            {
                                "path": "result.audit.equilibrium.free_relative_residual",
                                "op": "less_equal",
                                "expected": -1.0,
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    summary = run_qualification_campaign(manifest, tmp_path / "bad_output")
    assert summary["status"] == "FAIL"
    assert summary["cases"][0]["passed"] is False
    assert summary["cases"][0]["failed_check_count"] == 1


def test_qualification_campaign_fails_when_reference_comparison_fails(tmp_path: Path):
    manifest = tmp_path / "bad_reference.json"
    manifest.write_text(
        json.dumps(
            {
                "campaign": "bad_reference",
                "cases": [
                    {
                        "id": "BAD-REFERENCE",
                        "requirement": "REQ-SOL-001",
                        "input": str(PROJECT_ROOT / "examples" / "tet4_static.json"),
                        "mode": "solve",
                        "expected_status": "PASS",
                        "checks": [
                            {
                                "path": "result.max_displacement",
                                "op": "relative_error",
                                "expected": 1.0,
                                "tolerance": 1.0e-12,
                                "reference_type": "non_regression",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    summary = run_qualification_campaign(manifest, tmp_path / "bad_reference_output")
    assert summary["status"] == "FAIL"
    assert summary["reference_check_count"] == 1
    assert summary["cases"][0]["checks"][0]["status"] == "FAIL"


def test_qualification_campaign_blocks_experimental_replacement_candidate(tmp_path: Path):
    manifest = tmp_path / "bad_readiness.json"
    manifest.write_text(
        json.dumps(
            {
                "campaign": "bad_readiness",
                "cases": [
                    {
                        "id": "BAD-TET10-CANDIDATE",
                        "requirement": "REQ-SOL-001",
                        "input": str(PROJECT_ROOT / "examples" / "tet10_static.json"),
                        "mode": "solve",
                        "profile": "strict",
                        "expected_status": "PASS",
                        "replacement_candidate": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    summary = run_qualification_campaign(manifest, tmp_path / "bad_readiness_output")
    assert summary["status"] == "FAIL"
    assert summary["replacement_candidate_count"] == 1
    assert summary["replacement_ready_count"] == 0
    case = summary["cases"][0]
    assert case["replacement_ready"] is False
    assert any("maturity" in blocker for blocker in case["readiness_blockers"])


def test_qualification_campaign_blocks_candidate_without_independent_reference(tmp_path: Path):
    manifest = tmp_path / "no_independent_reference.json"
    manifest.write_text(
        json.dumps(
            {
                "campaign": "no_independent_reference",
                "cases": [
                    {
                        "id": "NO-INDEPENDENT-REF",
                        "requirement": "REQ-SOL-001",
                        "input": str(PROJECT_ROOT / "examples" / "tet4_static.json"),
                        "mode": "solve",
                        "profile": "strict",
                        "expected_status": "PASS",
                        "replacement_candidate": True,
                        "checks": [
                            {
                                "path": "result.max_displacement",
                                "op": "relative_error",
                                "expected": 2.122448979591837e-08,
                                "tolerance": 1.0e-12,
                                "reference_type": "non_regression",
                            }
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    summary = run_qualification_campaign(manifest, tmp_path / "no_independent_reference_output")
    assert summary["status"] == "FAIL"
    assert summary["replacement_candidate_count"] == 1
    assert summary["replacement_ready_count"] == 0
    assert summary["independent_reference_check_count"] == 0
    case = summary["cases"][0]
    assert case["failed_check_count"] == 0
    assert any("independent reference" in blocker for blocker in case["readiness_blockers"])
