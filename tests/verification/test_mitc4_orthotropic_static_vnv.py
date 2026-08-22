"""Verification checks for the one-ply MITC4 orthotropic static campaign."""

from solveur.verification.mitc4_orthotropic_static import Mitc4OrthotropicStaticCampaign


def test_one_ply_orthotropic_static_campaign_passes(tmp_path):
    summary = Mitc4OrthotropicStaticCampaign(tmp_path, mesh=(8, 2)).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert len(summary["rows"]) == 3
    assert all(row["status"] == "PASS" for row in summary["rows"])
    assert (tmp_path / "summary.json").is_file()
