from solveur.verification.hex20 import Hex20InternalCampaign


def test_hex20_internal_campaign_covers_analysis_j2_and_three_model_comparison(tmp_path) -> None:
    summary = Hex20InternalCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert summary["open_gates"] == ["H20-G10", "H20-G11", "H20-G12"]
    assert {row["id"] for row in summary["common_analysis_paths"]} == {
        "static",
        "modal",
        "newmark",
        "harmonic",
    }
    assert summary["j2_case"]["steps"] == 4
    benchmark = summary["tet_hex20_benchmark"]
    assert benchmark["model_count"] == 3
    assert set(benchmark["element_families"]) == {"TET4", "TET10", "HEX8", "HEX20"}
    assert len(benchmark["rows"]) == 12
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
