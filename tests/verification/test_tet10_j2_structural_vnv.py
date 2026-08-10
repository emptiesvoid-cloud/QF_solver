import pytest

from solveur.verification.j2_structural import J2StructuralCyclicCampaign


@pytest.mark.benchmark
def test_tet10_j2_structural_cyclic_campaign_uses_committed_hammer_states(tmp_path):
    summary = J2StructuralCyclicCampaign(tmp_path, element_type="TET10").run()

    assert summary["campaign_id"] == "VNV-J2-TET10-CYCLIC-001"
    assert summary["status"] == "PASS_INTERNAL"
    assert summary["mesh"]["element_type"] == "TET10"
    assert summary["mesh"]["integration_points_per_element"] == 4
    assert summary["mesh"]["elements"] > 100
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert (tmp_path / "cyclic_response.png").stat().st_size > 20_000
    assert (tmp_path / "deformation.vtu").is_file()
