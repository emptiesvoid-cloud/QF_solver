"""F6 guards for numerical/performance baseline integrity and bounded claims."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
AUDIT_PATH = ROOT / "qualification/0_2_7/f6_numerical_performance_regression_audit.json"
DOC_PATH = ROOT / "docs/verification/0_2_7/0_2_7_f6_numerical_performance_regression_audit.md"


def _audit() -> dict[str, object]:
    return json.loads(AUDIT_PATH.read_text(encoding="utf-8"))


def test_f6_record_is_bounded_and_has_no_release_blocker() -> None:
    audit = _audit()
    assert audit["schema_version"] == 1
    assert audit["record_type"] == "f6_numerical_performance_regression_audit"
    assert audit["audit_start_sha"] == "f6cfde036f5866c15e688bce70be5ed21b493ff1"
    summary = audit["summary"]
    assert summary["p0_found"] == 0
    assert summary["p1_found"] == 0
    assert summary["release_blockers_remaining"] == 0
    controls = audit["controls"]
    assert controls["numerical_source_changed"] is False
    assert controls["baseline_changed"] is False
    assert controls["requalification_required"] is False
    assert controls["historical_evidence_modified"] is False
    assert controls["maturity_promoted"] is False
    assert controls["r0_started"] is False


def test_f6_full_suite_failures_are_the_known_f4_set() -> None:
    full_suite = _audit()["execution"]["full_test_suite"]
    assert full_suite["same_failures_as_f4"] is True
    assert full_suite["result"].startswith("2147 passed, 3 failed, 184 skipped")
    assert set(full_suite["failures"]) == {
        "tests/unit/test_contact_finite_sliding.py::test_finite_sliding_diagnostics_reach_common_newton_result",
        "tests/unit/test_geometric_nonlinear_public.py::test_public_geometric_nonlinear_rejects_distributed_loads",
        "tests/unit/test_nonlinear_benchmark.py::test_nonlinear_benchmark_paths_execute_bounded_profiles[finite_sliding]",
    }


def test_f6_heavy_replay_decision_preserves_active_evidence() -> None:
    audit = _audit()
    decision = audit["heavy_benchmark_decision"]
    assert decision["five_million_replay_required"] is False
    assert decision["ten_million_replay_required"] is False
    baseline = audit["active_baselines"]
    assert baseline["five_million_silver"]["status"] == "PASS"
    assert baseline["five_million_silver"]["replays"] == 2
    assert baseline["one_million"]["status"] == "PASS"
    assert baseline["three_million_silver"]["replays"] == 2
    assert baseline["ten_million_c3"]["record_status"] == "PASS"


def test_f6_record_and_document_are_registered() -> None:
    audit = _audit()
    assert DOC_PATH.is_file()
    for path in audit["evidence_refs"]:
        assert (ROOT / path).is_file(), path
    manifest = json.loads((ROOT / "qualification/0_2_7/manifest.json").read_text(encoding="utf-8"))
    assert manifest["f6_status"] == "PASS_WITH_LIMITATIONS"
    assert manifest["f6_numerical_performance_audit"] == "qualification/0_2_7/f6_numerical_performance_regression_audit.json"
    registry = json.loads((ROOT / "docs/document_registry.json").read_text(encoding="utf-8"))
    entries = [entry for entry in registry["documents"] if entry["id"] == "DOC-027-F6-REGRESSION-001"]
    assert len(entries) == 1
    assert entries[0]["examples"] == [
        "qualification/0_2_7/f6_numerical_performance_regression_audit.json",
        "tests/unit/test_f6_numerical_performance_regression.py",
    ]


def test_f6_does_not_promote_or_expand_public_scope() -> None:
    verdict = _audit()["verdict"]
    assert verdict["status"] == "PASS_WITH_LIMITATIONS"
    assert "universal" in verdict["performance_claim_boundary"]
    assert _audit()["controls"]["maturity_promoted"] is False
