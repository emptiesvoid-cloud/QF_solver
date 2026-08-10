from solveur.verification.mitc4_newmark_operational import (
    Mitc4NewmarkOperationalStudy,
    write_mitc4_newmark_operational_evidence,
)


def test_newmark_operational_study_passes(tmp_path) -> None:
    summary = Mitc4NewmarkOperationalStudy().run(tmp_path)
    assert summary["status"] == "PASS"
    assert all(summary["checks"].values())
    assert summary["model"]["mass_formulation"] == "consistent"
    assert summary["restart"]["history_is_partial"] is True


def test_newmark_operational_evidence_is_complete(tmp_path) -> None:
    summary = write_mitc4_newmark_operational_evidence(tmp_path)
    assert summary["status"] == "PASS"
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "VNV-MITC4-NEWMARK-OPERATIONAL-006.md").is_file()
    assert (tmp_path / "VNV-MITC4-NEWMARK-OPERATIONAL-006.png").stat().st_size > 10_000
    assert (tmp_path / "vnv_manifest.json").is_file()
