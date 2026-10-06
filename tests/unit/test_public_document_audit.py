"""Tests for the controlled classification of public documentation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_public_documents import public_document_audit


ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "qualification" / "0_2_7" / "wp21_public_document_audit.json"


def test_whole_repository_document_audit_keeps_the_unresolved_public_hygiene_gate_visible() -> None:
    report = public_document_audit()

    # This is the R1 whole-repository gate, not the separately selected R3
    # package scan. Preserve the known HOLD instead of implying a clean release.
    assert report["status"] == "FAIL"
    assert report["audit_id"] == "QF-PUBLIC-DOC-AUDIT-0211-001"
    assert report["release"]["version"] == "0.2.11"
    assert report["classification"]["public_generated_documentation"]["count"] > 0
    assert report["public_release_audit"]["status"] == "FAIL"
    assert report["public_release_audit"]["finding_count"] > 0
    checks = {check["id"]: check["status"] for check in report["checks"]}
    assert checks["public_source_hygiene"] == "FAIL"


def test_controlled_public_document_audit_record_matches_current_classification() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    current = public_document_audit()

    # WP21 is an immutable 0.2.7 snapshot. Preserve its PASS and keep the
    # current whole-repository R1 failure distinct from the R3 package result.
    assert record["audit_id"] == "QF-PUBLIC-DOC-AUDIT-027-001"
    assert record["release"]["version"] == "0.2.7a0"
    assert record["status"] == "PASS"
    assert current["audit_id"] == "QF-PUBLIC-DOC-AUDIT-0211-001"
    assert current["release"]["version"] == "0.2.11"
    assert current["status"] == "FAIL"
    assert current["classification"]["public_source_documentation"]["count"] >= record["classification"]["public_source_documentation"]["count"]
    assert current["public_release_audit"]["scanned_files"] >= record["public_release_audit"]["scanned_files"]
    checks = {check["id"]: check["status"] for check in current["checks"]}
    assert checks["public_source_hygiene"] == "FAIL"
