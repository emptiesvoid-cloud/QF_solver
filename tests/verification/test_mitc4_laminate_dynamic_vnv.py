"""Regression coverage for the MITC4 laminate dynamic V&V campaign."""

from solveur.verification.mitc4_laminate_dynamic import (
    Mitc4LaminateDynamicStudy,
    STUDY_ID,
    write_mitc4_laminate_dynamic_evidence,
)


def test_mitc4_laminate_dynamic_campaign_proves_internal_consistency(tmp_path):
    summary = write_mitc4_laminate_dynamic_evidence(tmp_path)

    assert summary["study_id"] == STUDY_ID
    assert summary["status"] == "PASS_INTERNAL"
    assert summary["modal"]["dynamic_reduction"]["condensed_drilling_dof_count"] > 0
    assert summary["harmonic"]["ply_count_at_first_frequency"] == 4
    assert all(summary["checks"].values())
    assert (tmp_path / f"{STUDY_ID}.md").is_file()
    assert (tmp_path / f"{STUDY_ID}-newmark.png").stat().st_size > 10_000
    assert (tmp_path / f"{STUDY_ID}-harmonic.png").stat().st_size > 10_000
    assert (tmp_path / "vnv_manifest.json").is_file()


def test_mitc4_one_ply_orthotropic_case_passes_internal_dynamic_checks():
    summary = Mitc4LaminateDynamicStudy(
        mesh=(16, 4),
        layup=(45.0,),
        steps_per_period=(20, 40, 80),
    ).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert summary["model"]["layup"] == [45.0]
    assert summary["model"]["total_thickness_m"] == 0.01
    assert summary["harmonic"]["ply_count_at_first_frequency"] == 1
    assert all(summary["checks"].values())
