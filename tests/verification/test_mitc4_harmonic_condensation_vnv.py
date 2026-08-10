from solveur.verification.mitc4_harmonic_condensation import Mitc4HarmonicCondensationStudy


def test_harmonic_condensation_matches_full_complex_system() -> None:
    summary = Mitc4HarmonicCondensationStudy(
        frequency_ratios=(0.0, 0.5, 1.5),
        rayleigh_betas=(0.0, 1.0e-3, 1.0e-2),
    ).run()

    assert summary["status"] == "PASS"
    assert all(summary["checks"].values())
    assert summary["maxima"]["schur_relative_error"] < 1.0e-11
    assert summary["maxima"]["load_relative_error"] < 1.0e-11
    assert summary["maxima"]["response_relative_error"] < 1.0e-9
    assert summary["maxima"]["full_relative_residual"] < 1.0e-8
