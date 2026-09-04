"""F4 release guards for unit-test quality and bounded public claims."""

from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "qualification/0_2_7/f4_unit_test_quality_audit.json"
DOC_PATH = ROOT / "docs/verification/0_2_7/0_2_7_f4_unit_test_quality_audit.md"


def _audit() -> dict[str, object]:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_f4_record_is_complete_and_bounded() -> None:
    audit = _audit()
    assert audit["schema_version"] == 1
    assert audit["record_type"] == "f4_unit_test_quality_audit"
    assert audit["audit_start_sha"] == "6ddb581851754a5e701c35e97be565cc0f95ef60"
    assert audit["worktree_clean_at_start"] is True
    summary = audit["summary"]
    assert summary["p0_found"] == 0
    assert summary["p1_found"] == 0
    assert summary["p2_found"] == 3
    assert summary["p2_deferred"] == 2
    assert summary["release_blockers_remaining"] == 0
    controls = audit["controls"]
    assert controls["numerical_source_changed"] is False
    assert controls["historical_evidence_modified"] is False
    assert controls["maturity_promoted"] is False
    assert controls["f5_started"] is False
    assert audit["validation"]["full_test_suite"].startswith("2142 passed, 3 failed")


def test_f4_critical_negative_assertions_use_specific_contract_types() -> None:
    broad_catches: list[str] = []
    for path in sorted((ROOT / "tests").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "raises" or not node.args:
                continue
            expected = node.args[0]
            if isinstance(expected, ast.Name) and expected.id in {"Exception", "BaseException"}:
                broad_catches.append(f"{path}:{node.lineno}")
    assert broad_catches == []
    assert _audit()["quality_audit"]["negative_testing"]["broad_exception_catches_remaining"] == 0


def test_f4_behavior_matrix_preserves_public_maturity_boundaries() -> None:
    matrix = {entry["surface"]: entry for entry in _audit()["behavior_matrix"]}
    assert matrix["WEDGE6 static"]["maturity"] == "EXPERIMENTAL"
    assert matrix["WEDGE6 modal"]["maturity"] == "QUALIFIED_BOUNDED_FIRST_THREE_MODES"
    assert matrix["nonlinear static and J2 small-strain"]["maturity"] == "QUALIFIED_BOUNDED_SMALL_STRAIN_J2"
    assert "Finite-kinematic J2 remains experimental" in matrix["nonlinear static and J2 small-strain"]["gap"]


def test_f4_skip_and_xfail_policy_is_explicit() -> None:
    skip_policy = _audit()["quality_audit"]["skip_policy"]
    assert skip_policy["xfail_sites_reviewed"] == 0
    assert skip_policy["xfail_markers_present"] is False
    assert skip_policy["skip_sites_reviewed"] == 26
    assert "not converted into PASS" in skip_policy["policy"]


def test_f4_evidence_and_document_paths_exist() -> None:
    audit = _audit()
    assert DOC_PATH.is_file()
    for path in audit["evidence_refs"]:
        assert (ROOT / path).is_file(), path
    for path in audit["files"]["created"]:
        assert (ROOT / path).is_file(), path
