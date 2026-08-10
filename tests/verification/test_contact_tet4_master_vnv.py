"""V&V evidence for contact with a bounded deformable TET4 master face."""

import json

import pytest

from solveur.verification.contact_tet4_master import Tet4MasterContactCampaign


def test_tet4_master_face_contact_matches_separate_compliance_reference(tmp_path) -> None:
    summary = Tet4MasterContactCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["results"]["pressure_n"] == pytest.approx(summary["reference_solution"]["pressure_n"], abs=1.0e-10)
    assert summary["reference"]["master_normal_compliance_m_per_n"] > 0.0
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()
    figure = tmp_path / "tet4_master_deformation.png"
    assert figure.is_file()
    assert figure.stat().st_size > 1_000
    assert summary["artifacts"] == [figure.name]
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8")) == summary
