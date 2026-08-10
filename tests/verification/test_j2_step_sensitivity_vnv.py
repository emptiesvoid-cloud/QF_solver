import pytest

from solveur.verification.j2_step_sensitivity import J2StepSensitivityCampaign


@pytest.mark.benchmark
def test_j2_step_sensitivity_campaign_passes(tmp_path):
    summary = J2StepSensitivityCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert [row["increments"] for row in summary["levels"]] == [12, 24, 48]
    assert summary["maximum_state_relative_sensitivity"] < 1.0e-8
    assert summary["medium_to_fine_work_relative_sensitivity"] < 2.0e-2
    assert (tmp_path / "step_sensitivity.png").stat().st_size > 10_000
    assert (tmp_path / "report.md").is_file()
