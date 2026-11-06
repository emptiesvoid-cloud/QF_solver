from solveur.verification.hex20 import Hex20InternalCampaign


def test_hex20_internal_campaign_covers_analysis_j2_and_three_model_comparison(tmp_path) -> None:
    summary = Hex20InternalCampaign(tmp_path).run()

    assert summary["status"] == "INCONCLUSIVE"
    assert summary["modal_certification"] == "INCONCLUSIVE"
    assert summary["modal_certification_reason"] == "aggregate_work_budget"
    assert summary["open_gates"] == ["H20-G10", "H20-G11", "H20-G12"]
    assert {row["id"] for row in summary["common_analysis_paths"]} == {
        "static",
        "modal",
        "newmark",
        "harmonic",
    }
    paths = {row["id"]: row for row in summary["common_analysis_paths"]}
    assert paths["modal"]["status"] == "INCONCLUSIVE"
    assert paths["modal"]["calculation_status"] == "COMPUTED"
    assert all(paths[name]["status"] == "PASS" for name in ("static", "newmark", "harmonic"))
    assert summary["kernel_verification"]["status"] == "PASS"
    assert summary["load_cases"]["status"] == "PASS"
    assert summary["j2_case"]["status"] == "PASS"
    assert summary["j2_case"]["steps"] == 4
    benchmark = summary["tet_hex20_benchmark"]
    assert benchmark["model_count"] == 3
    assert set(benchmark["element_families"]) == {"TET4", "TET10", "HEX8", "HEX20"}
    assert len(benchmark["rows"]) == 12
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()


def test_hex20_aggregate_keeps_physical_failures_separate_from_modal_uncertainty() -> None:
    campaign = Hex20InternalCampaign()
    kernel = {"status": "PASS"}
    analyses = [
        {"id": "static", "status": "PASS"},
        {
            "id": "modal",
            "status": "INCONCLUSIVE",
            "solver_status": "INCONCLUSIVE",
            "modal_validation_status": "INCONCLUSIVE",
            "modal_validation_reason": "aggregate_work_budget",
            "calculation_status": "COMPUTED",
        },
        {"id": "newmark", "status": "PASS"},
        {"id": "harmonic", "status": "PASS"},
    ]
    loads = {"status": "PASS"}
    j2 = {"status": "PASS"}
    benchmark = {"status": "PASS_INTERNAL"}

    assert campaign._internal_status(kernel, analyses, loads, j2, benchmark) == "INCONCLUSIVE"
    failing_analyses = [*analyses, {"id": "physical-check", "status": "FAIL"}]
    assert campaign._internal_status(kernel, failing_analyses, loads, j2, benchmark) == "FAIL"
    actual_modal_failure = [
        {
            **row,
            "status": "FAIL",
            "solver_status": "FAIL",
            "modal_validation_status": "FAIL",
        }
        if row["id"] == "modal"
        else row
        for row in analyses
    ]
    assert campaign._internal_status(kernel, actual_modal_failure, loads, j2, benchmark) == "FAIL"
    uncertified_claim = [
        {**row, "status": "PASS", "solver_status": "PASS"} if row["id"] == "modal" else row
        for row in analyses
    ]
    assert campaign._internal_status(kernel, uncertified_claim, loads, j2, benchmark) == "FAIL"
