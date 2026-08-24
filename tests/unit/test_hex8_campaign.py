from solveur.verification.hex8_campaign import Hex8InternalCampaign


def test_hex8_internal_campaign_reports_open_external_gates(tmp_path) -> None:
    summary = Hex8InternalCampaign(tmp_path).run()
    assert summary["status"] == "PASS_INTERNAL"
    assert summary["h_convergence"]["levels"][-1]["relative_strain_error"] <= 0.01
    assert summary["open_gates"] == ["H8-G09", "H8-G12"]
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
