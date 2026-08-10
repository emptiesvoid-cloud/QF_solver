"""Reviewable evidence for the bounded elastic-master contact study."""

import json

import pytest

from solveur.verification.contact_deformable_master import DeformableMasterContactCampaign


def test_elastic_master_contact_matches_closed_form_and_writes_evidence(tmp_path) -> None:
    summary = DeformableMasterContactCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["results"]["pressure_n"] == pytest.approx(summary["analytic"]["pressure_n"], abs=1.0e-12)
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8")) == summary
