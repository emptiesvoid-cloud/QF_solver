from solveur.verification.orthotropic_modal_dynamic import OrthotropicModalDynamicCampaign


def test_orthotropic_modal_newmark_internal_campaign_passes(tmp_path) -> None:
    summary = OrthotropicModalDynamicCampaign(tmp_path).run(run_code_aster_external=False)

    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert len(summary["modal"]["rows"]) >= 4
    assert summary["modal"]["rows"][-1]["relative_error_theory"] <= 1.0e-2
    assert len(summary["newmark"]["rows"]) >= 8
    refinement = next(check for check in summary["checks"] if check["id"] == "newmark_time_refinement")
    assert refinement["value"] <= 1.0e-2
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()
