from scripts.benchmark_sparse_scaling import run_campaign


def test_sparse_scaling_campaign_is_reproducible_and_reports_resources(tmp_path):
    report = run_campaign([8, 32], tmp_path / "scaling.json")

    assert report["campaign"] == "qf-solver-sparse-scaling-0.2.2-alpha"
    assert [row["dofs"] for row in report["sizes"]] == [8, 32]
    for row in report["sizes"]:
        assert row["nnz"] > 0
        assert row["backend"] == "scipy"
        assert row["relative_residual_norm"] < 1.0e-7
        assert row["dense_memory_estimate_bytes"] > row["sparse_memory_bytes"]
    assert (tmp_path / "scaling.json").is_file()
