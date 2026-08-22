import json

from solveur.api import run_linear_solver_verification
from solveur.verification.linear_solver_comparison import (
    run_linear_solver_comparison,
    write_linear_solver_comparison,
)


def test_controlled_linear_method_comparison_covers_spd_and_nonsymmetric_contracts():
    report = run_linear_solver_comparison()

    assert report["status"] == "PASS"
    cases = {row["case"]: row for row in report["cases"]}
    assert cases["symmetric_positive_definite"]["recommended_method"] == "cg"
    assert {row["method"] for row in cases["symmetric_positive_definite"]["methods"]} == {
        "direct",
        "cg",
        "minres",
        "gmres",
        "bicgstab",
    }
    assert cases["nonsymmetric"]["recommended_method"] == "gmres"
    assert {row["method"] for row in cases["nonsymmetric"]["methods"]} == {"direct", "gmres", "bicgstab"}
    assert {row["method"] for row in cases["nonsymmetric"]["excluded_methods"]} == {"cg", "minres"}
    assert {row["case"] for row in report["cases"]} == {
        "symmetric_positive_definite",
        "nonsymmetric",
        "symmetric_positive_definite_32",
        "nonsymmetric_32",
    }
    assert all(row["dimension"] <= 32 for row in report["cases"])
    assert all(row["condition_number_2"] > 1.0 for row in report["cases"])
    for case in report["cases"]:
        assert all(row["status"] == "PASS" for row in case["methods"])
        assert all(row["relative_residual"] <= 1.0e-10 for row in case["methods"])
        assert all(row["solve_time_seconds"] >= 0.0 for row in case["methods"])


def test_controlled_linear_method_comparison_writes_portable_evidence(tmp_path):
    report = write_linear_solver_comparison(tmp_path / "evidence")

    assert report["status"] == "PASS"
    assert json.loads((tmp_path / "evidence" / "summary.json").read_text(encoding="utf-8"))["status"] == "PASS"
    manifest = json.loads((tmp_path / "evidence" / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == "VNV-LINEAR-SOLVERS-001"
    assert {entry["role"] for entry in manifest["files"]} == {"normalized_results", "owner_review_report"}
    markdown = (tmp_path / "evidence" / "report.md").read_text(encoding="utf-8")
    assert "nonsymmetric" in markdown
    assert "conditionnement 2-norme" in markdown
    assert "`cg` exclu" in markdown


def test_linear_method_comparison_is_available_through_public_api(tmp_path):
    report = run_linear_solver_verification(tmp_path / "api_evidence")

    assert report["status"] == "PASS"
    assert (tmp_path / "api_evidence" / "summary.json").is_file()
