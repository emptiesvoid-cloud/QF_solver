import json

from solveur.verification.mitc3_laminate_abd_audit import (
    run_mitc3_laminate_abd_audit,
    write_mitc3_laminate_abd_audit,
)


def test_mitc3_laminate_abd_audit_passes_independent_thickness_quadrature() -> None:
    report = run_mitc3_laminate_abd_audit()

    assert report["status"] == "PASS_INDEPENDENT_ABD"
    assert all(report["checks"].values())
    assert report["symmetric_layup"]["metrics"]["B_relative_difference"] < 1.0e-9
    assert report["unsymmetric_layup"]["coupling_norm"] > 0.0


def test_mitc3_laminate_abd_audit_writes_manifest(tmp_path) -> None:
    report = write_mitc3_laminate_abd_audit(tmp_path / "abd")
    assert report["status"] == "PASS_INDEPENDENT_ABD"
    manifest = json.loads((tmp_path / "abd" / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == "VNV-MITC3-LAMINATE-ABD-001"
    assert {item["role"] for item in manifest["files"]} == {"normalized_results", "owner_review_report"}
