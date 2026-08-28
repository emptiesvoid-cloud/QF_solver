from solveur.verification.robustness_nonlinear_solids import run_common_global_benchmark


def test_newton_rate_evidence_records_iterations_and_residuals() -> None:
    result = run_common_global_benchmark()

    for row in result["rows"]:
        assert row["newton_iterations"] >= len(result["load_path"])
        assert 0.0 <= row["maximum_relative_residual"] < 1.0e-7
        assert row["reaction_norm"] > 0.0
        assert row["residual_histories"]
        metrics = row["rate_metrics"]
        assert metrics["history_count"] == len(row["residual_histories"])
        assert metrics["finite_histories"] is True
        assert len(metrics["residual_reduction_ratios"]) == len(row["residual_histories"])

    for row in result["newton_rate_study"]["rows"]:
        assert row["full_newton"]["residual_histories"]
        assert row["full_newton"]["rate_metrics"]["finite_histories"] is True
        assert row["modified_newton"]["status"] in {"PASS", "NON_CONVERGED"}
