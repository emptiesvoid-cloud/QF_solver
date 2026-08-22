"""Tests for the controlled classification of public documentation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_public_documents import public_document_audit


ROOT = Path(__file__).resolve().parents[2]
RECORD = ROOT / "qualification" / "publication_audit_0_2_1.json"


def test_public_document_audit_passes_without_web_delivery_or_internal_paths() -> None:
    report = public_document_audit()

    assert report["status"] == "PASS"
    assert report["classification"]["public_generated_documentation"]["count"] > 0
    assert report["classification"]["internal"]["tracked_count"] == 0
    assert all(check["status"] == "PASS" for check in report["checks"])


def test_controlled_public_document_audit_record_matches_current_classification() -> None:
    record = json.loads(RECORD.read_text(encoding="utf-8"))
    current = public_document_audit()

    assert record["audit_id"] == current["audit_id"]
    assert record["status"] == current["status"] == "PASS"
    assert record["classification"] == current["classification"]
    assert record["checks"] == current["checks"]
