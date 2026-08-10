import pytest

from solveur.verification.j2_structural import J2StructuralCyclicCampaign


@pytest.mark.benchmark
def test_j2_structural_cyclic_campaign_passes(tmp_path):
    summary = J2StructuralCyclicCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert summary["mesh"]["elements"] > 100
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert (tmp_path / "cyclic_response.png").stat().st_size > 20_000
    assert (tmp_path / "deformation.vtu").is_file()
    assert "rolls_back" in summary["rollback_test"]
