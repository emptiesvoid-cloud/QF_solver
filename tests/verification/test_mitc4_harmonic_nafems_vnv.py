from solveur.verification.mitc4_harmonic_nafems import (
    Mitc4Nafems13HStudy,
    write_mitc4_nafems_13h_evidence,
)


def test_nafems_13h_external_harmonic_correlation_passes() -> None:
    summary = Mitc4Nafems13HStudy().run()
    comparison = summary["external_correlation"]

    assert summary["status"] == "PASS"
    assert all(summary["checks"].values())
    assert all(comparison["checks"].values())
    assert comparison["relative_differences"]["abaqus_displacement"] < 0.05
    assert comparison["relative_differences"]["abaqus_frequency"] < 0.03
    assert comparison["relative_differences"]["abaqus_stress"] < 0.05
    assert comparison["relative_differences"]["abaqus_s4_stress"] < 0.05
    assert comparison["relative_differences"]["nafems_stress"] < 0.05
    assert summary["classical_plate_theory"]["qf_relative_differences"]["stress"] < 0.05
    assert summary["peak"]["max_relative_residual"] < 1.0e-8


def test_nafems_13h_evidence_contains_model_setup_figure(tmp_path) -> None:
    write_mitc4_nafems_13h_evidence(tmp_path)
    assert (tmp_path / "VNV-MITC4-HARMONIC-NAFEMS13H-004-model-setup.png").is_file()
