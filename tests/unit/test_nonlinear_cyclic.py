from __future__ import annotations

from solveur.verification.robustness_nonlinear_solids import run_cyclic_load_benchmark


def test_cyclic_j2_path_records_reversal_without_state_regression() -> None:
    result = run_cyclic_load_benchmark(("TET4",))

    assert result["status"] == "PASS_INTERNAL_CYCLIC"
    row = result["rows"][0]
    assert min(row["load_path"]) < 0.0 < max(row["load_path"])
    assert row["monotonic_peeq"] is True
    assert row["monotonic_dissipation"] is True
    assert row["maximum_relative_residual"] < 1.0e-6
