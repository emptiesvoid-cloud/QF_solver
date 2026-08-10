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
    for case in cases.values():
        assert all(row["status"] == "PASS" for row in case["methods"])


def test_controlled_linear_method_comparison_writes_portable_evidence(tmp_path):
    report = write_linear_solver_comparison(tmp_path / "evidence")

    assert report["status"] == "PASS"
    assert json.loads((tmp_path / "evidence" / "summary.json").read_text(encoding="utf-8"))["status"] == "PASS"
    markdown = (tmp_path / "evidence" / "report.md").read_text(encoding="utf-8")
    assert "nonsymmetric" in markdown
    assert "`cg` exclu" in markdown


def test_linear_method_comparison_is_available_through_public_api(tmp_path):
    report = run_linear_solver_verification(tmp_path / "api_evidence")

    assert report["status"] == "PASS"
    assert (tmp_path / "api_evidence" / "summary.json").is_file()
