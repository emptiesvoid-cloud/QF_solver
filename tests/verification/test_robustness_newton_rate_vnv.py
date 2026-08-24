from solveur.verification.robustness_nonlinear_solids import run_common_global_benchmark


def test_newton_rate_evidence_records_iterations_and_residuals() -> None:
    result = run_common_global_benchmark()

    for row in result["rows"]:
        assert row["newton_iterations"] >= len(result["load_path"])
        assert 0.0 <= row["maximum_relative_residual"] < 1.0e-7
        assert row["reaction_norm"] > 0.0
