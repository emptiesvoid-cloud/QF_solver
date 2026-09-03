"""Tests for the controlled classification of public documentation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_public_documents import public_document_audit


ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "qualification" / "0_2_7" / "wp21_public_document_audit.json"


def test_public_document_audit_passes_without_web_delivery_or_internal_paths() -> None:
    report = public_document_audit()

    assert report["status"] == "PASS"
    assert report["release"]["version"] == "0.2.7a0"
    assert report["classification"]["public_generated_documentation"]["count"] > 0
    assert report["classification"]["internal"]["tracked_count"] == 0
    assert all(check["status"] == "PASS" for check in report["checks"])


def test_controlled_public_document_audit_record_matches_current_classification() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    current = public_document_audit()

    assert record["audit_id"] == current["audit_id"]
    assert record["status"] == current["status"] == "PASS"
    # WP21 is an immutable snapshot; F3 appends public documentation afterward.
    # The current audit must still pass, but its append-only counts may be larger.
    assert current["classification"]["public_source_documentation"]["count"] >= record["classification"]["public_source_documentation"]["count"]
    assert current["public_release_audit"]["scanned_files"] >= record["public_release_audit"]["scanned_files"]
    assert all(check["status"] == "PASS" for check in current["checks"])
