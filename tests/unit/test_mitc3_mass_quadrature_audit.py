"""Tests for the independent MITC3+ mass quadrature audit."""

from __future__ import annotations

from solveur.verification.mitc3_mass_quadrature_audit import (
    STUDY_ID,
    Mitc3MassQuadratureAudit,
    write_mitc3_mass_quadrature_audit,
)


def test_mitc3_mass_quadrature_audit_passes() -> None:
    summary = Mitc3MassQuadratureAudit().run()

    assert summary["study_id"] == STUDY_ID
    assert summary["status"] == "PASS_INDEPENDENT_QUADRATURE"
    assert all(summary["checks"].values())
    assert summary["metrics"]["condensed_relative_difference"] < 2.0e-5


def test_mitc3_mass_quadrature_audit_writes_bundle(tmp_path) -> None:
    summary = write_mitc3_mass_quadrature_audit(tmp_path)

    assert summary["status"] == "PASS_INDEPENDENT_QUADRATURE"
    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()

