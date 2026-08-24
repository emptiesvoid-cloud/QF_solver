from solveur.verification.robustness_nonlinear_solids import ELEMENT_TYPES, run_element_matrix


def test_common_j2_element_matrix_covers_all_four_solid_families() -> None:
    result = run_element_matrix()

    assert result["status"] == "PASS"
    assert [row["element"] for row in result["rows"]] == list(ELEMENT_TYPES)
    assert all(row["integration_points"] > 0 for row in result["rows"])
    assert all(any(item["peeq_max"] > 0.0 for item in row["history"]) for row in result["rows"])
