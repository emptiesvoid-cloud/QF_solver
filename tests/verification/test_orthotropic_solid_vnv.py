from solveur.verification.orthotropic_solid import OrthotropicSolidKernelCampaign


def test_orthotropic_solid_kernel_campaign_passes(tmp_path) -> None:
    summary = OrthotropicSolidKernelCampaign(tmp_path).run()
    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert summary["covered_specifications"] == [
        "SPEC-COMP-SOLID-001",
        "SPEC-COMP-SOLID-002",
        "SPEC-COMP-SOLID-003",
        "SPEC-COMP-SOLID-004",
        "SPEC-COMP-SOLID-005",
    ]
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()
