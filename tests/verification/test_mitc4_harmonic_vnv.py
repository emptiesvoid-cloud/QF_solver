from solveur.verification.mitc4_harmonic import Mitc4HarmonicModalStudy


def test_mitc4_harmonic_matches_modal_closed_form_and_static_limit() -> None:
    summary = Mitc4HarmonicModalStudy(
        frequency_ratios=(0.0, 0.5, 0.95, 1.0, 1.05, 1.5, 2.0),
    ).run()

    assert summary["status"] == "PASS"
    assert all(summary["checks"].values())
    assert summary["maximum_relative_error"] < 1.0e-6
    assert summary["zero_hz_static_relative_error"] < 1.0e-9
    assert summary["peak"]["frequency_ratio"] == 1.0
    assert summary["model"]["condensed_drilling_dofs"] > 0
