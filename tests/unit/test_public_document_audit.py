"""Tests for the controlled classification of public documentation."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import scripts.audit_public_documents as public_document_audit_module
from scripts.audit_public_documents import public_document_audit


ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "qualification" / "0_2_7" / "wp21_public_document_audit.json"


@pytest.fixture(scope="module")
def current_public_document_report(current_public_release_scan) -> dict[str, object]:
    """Share the real source scan while classifying its public-document report."""
    if current_public_release_scan is None:
        return public_document_audit()

    current_public_release_scan.assert_current()
    original_audit = public_document_audit_module.audit_public_release

    def reuse_identical_source_scan(root: str | Path) -> dict[str, object]:
        if Path(root).resolve() != ROOT.resolve():
            raise AssertionError("The shared report is valid only for the current repository root.")
        current_public_release_scan.assert_current()
        return copy.deepcopy(current_public_release_scan.report)

    public_document_audit_module.audit_public_release = reuse_identical_source_scan
    try:
        report = public_document_audit()
    finally:
        public_document_audit_module.audit_public_release = original_audit
    current_public_release_scan.assert_current()
    return report


def test_whole_repository_document_audit_keeps_the_unresolved_public_hygiene_gate_visible(
    current_public_document_report: dict[str, object],
) -> None:
    report = current_public_document_report

    # This is the R1 whole-repository gate, not the separately selected R3
    # package scan. Preserve the known HOLD instead of implying a clean release.
    assert report["status"] == "FAIL"
    assert report["audit_id"] == "QF-PUBLIC-DOC-AUDIT-0212-001"
    assert report["release"]["version"] == "0.2.12"
    assert report["classification"]["public_generated_documentation"]["count"] > 0
    assert report["public_release_audit"]["status"] == "FAIL"
    assert report["public_release_audit"]["finding_count"] > 0
    checks = {check["id"]: check["status"] for check in report["checks"]}
    assert checks["public_source_hygiene"] == "FAIL"


def test_controlled_public_document_audit_record_matches_current_classification(
    current_public_document_report: dict[str, object],
) -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    current = current_public_document_report

    # WP21 is an immutable 0.2.7 snapshot. Preserve its PASS and keep the
    # current whole-repository R1 failure distinct from the R3 package result.
    assert record["audit_id"] == "QF-PUBLIC-DOC-AUDIT-027-001"
    assert record["release"]["version"] == "0.2.7a0"
    assert record["status"] == "PASS"
    assert current["audit_id"] == "QF-PUBLIC-DOC-AUDIT-0212-001"
    assert current["release"]["version"] == "0.2.12"
    assert current["status"] == "FAIL"
    assert current["classification"]["public_source_documentation"]["count"] >= record["classification"]["public_source_documentation"]["count"]
    assert current["public_release_audit"]["scanned_files"] >= record["public_release_audit"]["scanned_files"]
    checks = {check["id"]: check["status"] for check in current["checks"]}
    assert checks["public_source_hygiene"] == "FAIL"
