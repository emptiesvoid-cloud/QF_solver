"""Guards for the final 0.2.7 owner-review release candidate."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
R0_PATH = ROOT / "qualification/0_2_7/r0_release_readiness.json"
MANIFEST_PATH = ROOT / "qualification/0_2_7/manifest.json"
GATES_PATH = ROOT / "qualification/0_2_7/gates.json"


def test_r0_candidate_is_bounded_and_has_no_open_release_blocker() -> None:
    record = json.loads(R0_PATH.read_text(encoding="utf-8"))

    assert record["status"] == "PASS_WITH_LIMITATIONS"
    assert record["audit_start_sha"] == "5323a0996f214a3203f06b5bb468843b57c25270"
    assert record["candidate"]["tag"] == "v0.2.7a0"
    assert record["findings"]["p0_open"] == 0
    assert record["findings"]["p1_open"] == 0
    assert record["findings"]["release_blockers"] == []
    assert record["source_integrity"]["numerical_source_changed"] is False
    assert record["source_integrity"]["baseline_changed"] is False
    assert record["source_integrity"]["historical_evidence_modified"] is False


def test_r0_preserves_foreign_change_and_publication_boundary() -> None:
    record = json.loads(R0_PATH.read_text(encoding="utf-8"))
    coactivity = record["coactivity"]

    assert coactivity["classification"] == "FOREIGN_CHANGE"
    assert coactivity["stash_commit"] == "a9e64d5e03ebadfcd1292ad3c5b04460761c10aa"
    assert coactivity["release_changes_include_foreign_work"] is False
    assert record["candidate"]["tag_created"] is False
    assert record["candidate"]["github_release_created"] is False
    assert record["candidate"]["pypi_published"] is False
    assert record["ready_for_owner_decision"] is True


def test_r0_is_registered_in_active_manifest_and_gate_matrix() -> None:
    record = json.loads(R0_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    gates = json.loads(GATES_PATH.read_text(encoding="utf-8"))

    assert manifest["r0_status"] == record["status"]
    assert manifest["r0_release_readiness"] == "qualification/0_2_7/r0_release_readiness.json"
    assert gates["r0_release_readiness"]["status"] == record["status"]
    assert gates["r0_release_readiness"]["ready_for_owner_decision"] is True
    for path in record["evidence_refs"]:
        assert (ROOT / path).is_file(), path
