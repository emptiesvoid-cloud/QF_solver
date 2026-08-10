import pytest

from solveur.verification.tet4_total_lagrangian import TotalLagrangianTet4Campaign


@pytest.mark.benchmark
def test_total_lagrangian_tet4_kernel_campaign_passes(tmp_path):
    summary = TotalLagrangianTet4Campaign(tmp_path).run()

    assert summary["status"] == "PASS_KERNEL"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["owner_review_required"] is True
    assert summary["integration_authorized"] is False
    assert (tmp_path / "rigid_rotation.png").stat().st_size > 10_000
    assert (tmp_path / "report.md").is_file()
