"""Public API and CLI contract for the aggregated V1 contact evidence suite."""

import json

from solveur.api import run_contact_verification
from tests.helpers.cli import run_solver_cli


def test_contact_verification_api_and_cli_write_reviewable_evidence(tmp_path) -> None:
    api_dir = tmp_path / "api"
    summary = run_contact_verification(api_dir)
    assert summary["status"] == "PASS_INTERNAL"
    assert len(summary["studies"]) == 6
    assert any(study["campaign_id"] == "VNV-CONTACT-DEFORMABLE-MASTER-003" for study in summary["studies"])
    assert any(study["campaign_id"] == "VNV-CONTACT-TET4-MASTER-FACE-004" for study in summary["studies"])
    assert any(study["campaign_id"] == "VNV-CONTACT-MASTER-SURFACE-005" for study in summary["studies"])
    assert (api_dir / "contact_campaign_report.md").is_file()
    assert (api_dir / "vnv_manifest.json").is_file()

    cli_dir = tmp_path / "cli"
    json_report = tmp_path / "contact.json"
    completed = run_solver_cli("verify-contact", "--output", cli_dir, "--json-report", json_report)
    assert completed.returncode == 0, completed.stderr
    assert "GLOBAL STATUS: PASS_INTERNAL" in completed.stdout
    saved = json.loads(json_report.read_text(encoding="utf-8"))
    assert saved["campaign_id"] == "VNV-CONTACT-V1-001"
