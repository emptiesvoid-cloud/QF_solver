from scripts.benchmark_newmark_factorization import run_campaign


def test_newmark_factorization_campaign_reports_reuse_metrics(tmp_path):
    report = run_campaign([8], tmp_path / "newmark.json", steps=2)

    assert report["campaign"] == "qf-solver-newmark-factorization-reuse-0.2.2-alpha"
    row = report["sizes"][0]
    assert row["factorization_reused"] is True
    assert row["factorization_count"] == 1
    assert row["solve_count"] == 2
    assert row["reuse_count_ratio"] == 2.0
    assert row["factorization_seconds"] >= 0.0
    assert row["solve_seconds_total"] >= 0.0
    assert row["status"] == "PASS"
    assert (tmp_path / "newmark.json").is_file()
