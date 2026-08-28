from __future__ import annotations

from solveur.verification.robustness_nonlinear_solids import run_multi_element_load_step_sensitivity


def test_multi_element_load_step_sensitivity_records_three_histories() -> None:
    result = run_multi_element_load_step_sensitivity(("TET4",))

    assert result["status"] == "PASS_INTERNAL_SENSITIVITY"
    row = result["rows"][0]
    assert set(row["histories"]) == {"coarse", "reference", "refined"}
    assert row["owner_acceptance_band_required"] is True
    assert all(value >= 0.0 for value in row["reference_to_refined"].values())
