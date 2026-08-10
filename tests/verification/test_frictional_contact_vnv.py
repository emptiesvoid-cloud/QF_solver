"""Acceptance checks for the internal regularized-Coulomb block campaign."""

import json

from solveur.verification.frictional_contact import FrictionalContactVerificationCampaign


def test_frictional_contact_block_matches_the_regularized_analytical_solution(tmp_path):
    summary = FrictionalContactVerificationCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert len(summary["checks"]) == 8
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert {row["state"] for row in summary["load_path"]} == {"stick", "slip"}
    assert (tmp_path / "friction_block_comparison.png").stat().st_size > 10_000
    assert (tmp_path / "vnv_manifest.json").is_file()


def test_frictional_contact_campaign_writes_a_reviewable_json_and_markdown(tmp_path):
    summary = FrictionalContactVerificationCampaign(tmp_path).run()

    stored = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert stored == summary
    assert summary["campaign_id"] in report
    assert "PASS_INTERNAL" in report
    assert "memoire incremental charge-decharge est verifiee" in report
