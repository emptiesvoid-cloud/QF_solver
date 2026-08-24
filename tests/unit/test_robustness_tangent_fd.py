from solveur.verification.robustness_nonlinear_solids import tangent_finite_difference


def test_consistent_tangent_is_stable_over_finite_difference_steps() -> None:
    result = tangent_finite_difference()

    assert result["status"] == "PASS"
    assert len(result["relative_errors"]) == 3
    assert result["maximum_relative_error"] < result["limit"]
