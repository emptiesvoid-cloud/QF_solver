from solveur.verification.robustness_nonlinear_solids import ELEMENT_TYPES, run_common_global_benchmark


def test_common_global_benchmark_runs_same_history_on_all_elements() -> None:
    result = run_common_global_benchmark()

    assert result["status"] == "PASS"
    assert result["load_path"] == [0.25, 0.5, 0.75, 1.0]
    assert [row["element"] for row in result["rows"]] == list(ELEMENT_TYPES)
    assert all(row["maximum_relative_residual"] < 1.0e-7 for row in result["rows"])
    assert all(row["final_peeq"] > 0.0 for row in result["rows"])
