from solveur.verification.hex8_tet_benchmark import run_multi_model_benchmark, run_tet10_hex8_benchmark


def test_tet_hex_benchmark_uses_comparable_dofs() -> None:
    summary = run_tet10_hex8_benchmark()
    assert summary["status"] == "PASS_INTERNAL"
    assert summary["dofs_match"] is True
    assert {row["element"] for row in summary["rows"]} == {"HEX8", "TET4", "TET10"}
    assert all(row["estimated_csr_bytes"] > 0 for row in summary["rows"])


def test_multi_model_tet_hex_benchmark_covers_three_cases(tmp_path) -> None:
    summary = run_multi_model_benchmark(tmp_path)
    assert summary["status"] == "PASS_INTERNAL"
    assert summary["model_count"] == 3
    assert set(summary["models"]) == {"unit_cube", "slender_beam", "distorted_cube"}
    assert len(summary["rows"]) == 9
    assert {row["element"] for row in summary["rows"]} == {"HEX8", "TET4", "TET10"}
    assert all(row["equilibrium_residual"] < 1.0e-10 for row in summary["rows"])
    assert (tmp_path / "tet_hex_multi_model_comparison.png").is_file()
