from solveur.verification.j2_performance import J2NonlinearPerformanceCampaign


def test_nonlinear_performance_campaign_archives_bounded_scope(monkeypatch, tmp_path):
    def fake_case(_self, _family):
        return {
            "element_type": "TET4",
            "status": "PASS",
            "node_count": 4,
            "element_count": 1,
            "dof_count": 12,
            "integration_point_state_count": 1,
            "elapsed_seconds": 0.01,
            "peak_python_memory_bytes": 128,
            "increments": 2,
            "total_newton_iterations": 3,
            "maximum_relative_residual": 1.0e-8,
            "final_relative_residual": 1.0e-9,
            "residual_samples": 3,
            "notes": [],
        }

    monkeypatch.setattr(J2NonlinearPerformanceCampaign, "_run_case", fake_case)
    summary = J2NonlinearPerformanceCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert summary["scope"]["scalability_claim"] is False
    assert len(summary["cases"]) == 2
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
