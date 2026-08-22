from __future__ import annotations

from solveur.verification.mitc3_matrix_condensation_audit import (
    Mitc3MatrixCondensationAudit,
    write_mitc3_matrix_condensation_audit,
)


def test_mitc3_matrix_condensation_audit_passes() -> None:
    summary = Mitc3MatrixCondensationAudit().run()

    assert summary["status"] == "PASS_ALGEBRAIC_CONDENSATION"
    assert all(summary["checks"].values())
    assert summary["metrics"]["stiffness_projection_relative_difference"] <= 1.0e-12
    assert summary["metrics"]["mass_projection_relative_difference"] <= 1.0e-12


def test_mitc3_matrix_condensation_audit_writes_evidence(tmp_path) -> None:
    summary = write_mitc3_matrix_condensation_audit(tmp_path)

    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()
    assert summary["study_id"] in (tmp_path / "report.md").read_text(encoding="utf-8")
