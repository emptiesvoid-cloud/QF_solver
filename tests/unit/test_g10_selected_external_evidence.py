"""Contract checks for the selected G10 external evidence pack."""

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).parents[2]
EVIDENCE = ROOT / "qualification" / "0_2_6" / "g10_selected_external_evidence.json"
MANIFEST = ROOT / "qualification" / "0_2_6" / "g10_selected_external_manifest.json"
GATES = ROOT / "qualification" / "0_2_6" / "gates.json"
SOURCE_SHA = "efed8c3e1bcf173d335b3b9a605febd0fa1084cb"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_selected_external_evidence_is_bounded_and_provenanced() -> None:
    evidence = _load(EVIDENCE)

    assert evidence["gate"] == "026-G10"
    assert evidence["status"] == "PARTIAL"
    assert evidence["execution_source_sha"] == SOURCE_SHA
    assert evidence["execution_worktree_dirty"] is False
    assert evidence["functional_source_changed"] is False
    assert evidence["numerical_regression_detected"] is False
    assert evidence["scope_guard"]["other_g10_routes_extended"] is False
    assert evidence["scope_guard"]["full_regression"] == "SKIPPED_BY_POLICY"
    assert evidence["decision"]["g10_status_unchanged"] == "IN_PROGRESS"
    assert all(
        route["comparison_class"] == "PASS_WITH_LIMITATIONS"
        for route in evidence["routes"].values()
    )


def test_selected_external_manifest_matches_committed_artifacts() -> None:
    manifest = _load(MANIFEST)

    assert manifest["execution_source_sha"] == SOURCE_SHA
    assert manifest["execution_worktree_dirty"] is False
    assert manifest["g10_closeout"] is False
    for artifact in manifest["artifacts"]:
        path = ROOT / artifact["path"]
        assert path.is_file(), artifact["path"]
        assert _sha256(path) == artifact["sha256"], artifact["path"]


def test_gate_registry_links_selected_external_pack_without_closing_g10() -> None:
    gates = _load(GATES)
    gate = next(item for item in gates["gates"] if item["id"] == "026-G10")

    assert gate["status"] == "IN_PROGRESS"
    assert "g10_selected_external_evidence.json" in gate["evidence_ids"]
    assert "g10_selected_external_manifest.json" in gate["evidence_ids"]
    assert "0_2_6_g10_selected_external_campaign.md" in gate["evidence_ids"]
