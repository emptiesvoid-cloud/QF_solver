"""Governance and artifact checks for the G09 robustness extension."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"
DOC = ROOT / "docs" / "verification" / "0_2_6"


def _load(name: str) -> dict[str, object]:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_g09_extension_has_45_cases_and_preserves_closeout() -> None:
    evidence = _load("g09_robustness_extension_evidence.json")
    registry = _load("g09_robustness_extension_case_registry.json")
    requirements = _load("g09_robustness_extension_requirements.json")
    gates = json.loads((DATA / "gates.json").read_text(encoding="utf-8"))
    gate = next(item for item in gates["gates"] if item["id"] == "026-G09")

    assert evidence["status"] == "PASS_WITH_LIMITATIONS"
    assert evidence["official_gate_status_unchanged"] == "PASS_WITH_LIMITATIONS"
    assert evidence["source"]["sha"] == "cd5b163c59d8ed1d93bc853701d61cc58ddd61f9"
    assert evidence["source"]["dirty"] is False
    assert evidence["case_counts"] == {
        "adversarial": 6,
        "activation": 8,
        "cycles": 4,
        "geometry": 13,
        "phase_rollback": 5,
        "penalty_mesh": 15,
        "rollback": 4,
    }
    assert registry["case_count"] == 55
    assert len(registry["cases"]) == 55
    assert requirements["requirement_count"] == 18
    assert requirements["counts"] == {"BOUNDED": 11, "DEFERRED": 3, "FAIL": 0, "FULL_CANDIDATE": 4}
    assert gate["status"] == "PASS_WITH_LIMITATIONS"
    assert "g09_robustness_extension_evidence.json" in gate["evidence_ids"]
    assert "g09_robustness_extension_case_registry.json" in gate["evidence_ids"]


def test_g09_extension_has_no_unexpected_failures_or_external_overclaim() -> None:
    evidence = _load("g09_robustness_extension_evidence.json")
    external = evidence["external_extension"]

    assert evidence["unexpected_failures"] == []
    assert evidence["bugs_found"] == []
    assert evidence["functional_code_changed"] is False
    assert external["execution"] == "REUSED_CONTROLLED_ARCHIVE"
    assert external["new_external_run"] is False
    assert external["source_dirty"] is False
    assert len(external["mesh_levels"]) >= 2
    assert external["load_intensity_points"] >= 2
    assert "universal" in " ".join(evidence["limitations"])
    phases = evidence["phase_rollback"]
    assert phases["phase_coverage"] == [
        "before_activation",
        "during_activation",
        "just_after_activation",
        "during_separation",
        "during_recontact",
    ]
    assert all(row["status"] == "PASS_INTERNAL_ROLLBACK" for row in phases["rows"])
    assert phases["state_integrity"] is True
    assert len(evidence["geometry"]["rows"]) == 13
    assert all(evidence["geometry"]["coverage"].values())
    assert all(row["energy_trace_valid"] and row["work_trace_finite"] for row in evidence["cycles"]["rows"])
    assert all(row["energy_trace_valid"] and row["work_trace_finite"] for row in phases["rows"])


def test_g09_extension_manifest_digests_match_archived_artifacts() -> None:
    manifest = _load("g09_robustness_extension_manifest.json")
    expected = {
        "g09_robustness_extension_evidence.json": DATA / "g09_robustness_extension_evidence.json",
        "g09_robustness_extension_case_registry.json": DATA / "g09_robustness_extension_case_registry.json",
        "g09_robustness_extension_requirements.json": DATA / "g09_robustness_extension_requirements.json",
        "g09_robustness_extension_evidence.md": DOC / "0_2_6_g09_robustness_extension_evidence.md",
    }

    assert manifest["source_sha"] == "cd5b163c59d8ed1d93bc853701d61cc58ddd61f9"
    assert manifest["source_dirty"] is False
    for artifact, path in expected.items():
        assert manifest["artifacts"][artifact] == _sha256(path)
