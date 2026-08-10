from solveur.verification.mitc4_harmonic_broadband import Mitc4HarmonicBroadbandStudy


def test_mitc4_broadband_response_matches_complete_modal_oracle() -> None:
    summary = Mitc4HarmonicBroadbandStudy(frequency_count=400).run()

    assert summary["status"] == "PASS"
    assert all(summary["checks"].values())
    assert len(summary["peaks"]) == 4
    assert summary["metrics"]["maximum_complex_response_relative_error"] < 1.0e-6
    assert summary["metrics"]["maximum_relative_residual"] < 1.0e-8
    assert summary["oracle"]["mode_count"] == summary["oracle"]["reduced_dof_count"]
