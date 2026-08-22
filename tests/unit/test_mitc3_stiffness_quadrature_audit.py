from __future__ import annotations

from solveur.verification.mitc3_stiffness_quadrature_audit import (
    Mitc3StiffnessQuadratureAudit,
    write_mitc3_stiffness_quadrature_audit,
)


def test_mitc3_stiffness_quadrature_audit_passes() -> None:
    summary = Mitc3StiffnessQuadratureAudit().run()

    assert summary["status"] == "PASS_INDEPENDENT_QUADRATURE"
    assert all(summary["checks"].values())
    assert summary["metrics"]["expanded_total_relative_difference"] <= 2.0e-7


def test_mitc3_stiffness_quadrature_audit_writes_evidence(tmp_path) -> None:
    summary = write_mitc3_stiffness_quadrature_audit(tmp_path)

    assert (tmp_path / "summary.json").is_file()
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()
    assert summary["study_id"] in (tmp_path / "report.md").read_text(encoding="utf-8")
