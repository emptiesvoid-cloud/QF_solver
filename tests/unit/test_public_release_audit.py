"""Tests for public-release privacy and source-hygiene controls."""

from __future__ import annotations

from pathlib import Path

from scripts.audit_public_release import audit_public_release, public_source_files, scan_pdf_bytes
from scripts.audit_release_archive import _scan_member, audit_release_archive


def test_current_public_release_candidates_are_clean() -> None:
    report = audit_public_release()
    assert report["status"] == "PASS", report["findings"]


def test_audit_covers_public_launchers_and_release_environments() -> None:
    paths = {path.relative_to(Path(__file__).resolve().parents[2]).as_posix() for path in public_source_files()}
    assert {"qf_solver.py", "main_solveur.py", "mitc4_solver.py"} <= paths


def test_audit_reports_relative_path_for_private_workstation_marker(tmp_path) -> None:
    private_path = "C:\\Us" + "ers\\private\\model.json"
    (tmp_path / "README.md").write_text(f"path {private_path}\n", encoding="utf-8")
    report = audit_public_release(tmp_path)
    assert report["status"] == "FAIL"
    assert report["findings"] == [
        {
            "identifier": "workstation_path",
            "path": "README.md",
            "line": 1,
            "excerpt": f"path {private_path}",
        }
    ]


def test_audit_scans_generated_latex_sources(tmp_path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    private_path = "C:/Us" + "ers/private/model.png"
    (docs / "manual.tex").write_text(f"includegraphics{{{private_path}}}\n", encoding="utf-8")

    report = audit_public_release(tmp_path)

    assert report["status"] == "FAIL"
    assert report["findings"][0]["path"] == "docs/manual.tex"
    assert report["findings"][0]["identifier"] == "workstation_path"


def test_pdf_and_archive_content_scans_reject_local_file_links() -> None:
    private_uri = b"/URI (file:///C:/Us" + b"ers/private/review.pdf)"

    pdf_findings = scan_pdf_bytes("review.pdf", private_uri)
    archive_findings = _scan_member("review.pdf", private_uri)

    assert {finding.identifier for finding in pdf_findings} == {
        "workstation_path",
        "local_file_uri",
    }
    assert {finding["identifier"] for finding in archive_findings} == {
        "workstation_path",
        "local_file_uri",
    }


def test_archive_rules_exclude_local_and_working_evidence_trees() -> None:
    attributes = (Path(__file__).resolve().parents[2] / ".gitattributes").read_text(encoding="utf-8")
    for path in (
        "tmp",
        "results",
        "results_large",
        "site",
        "VNV-*",
        "qualification/vnv",
    ):
        assert f"{path} export-ignore" in attributes


def test_current_git_archive_excludes_runtime_and_private_evidence_trees() -> None:
    report = audit_release_archive()
    assert report["status"] == "PASS", report["findings"]
    assert "README.md" in report["paths"]
