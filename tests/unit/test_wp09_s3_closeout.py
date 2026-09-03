"""Focused S3-to-WP09 WEDGE6 closeout contracts."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLOSEOUT = ROOT / "qualification" / "0_2_7" / "wp09_s3_closeout.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_closeout_is_bounded_and_preserves_case_accounting() -> None:
    closeout = _load(CLOSEOUT)
    accounting = closeout["case_accounting"]

    assert closeout["status"] == "PASS_WITH_LIMITATIONS"
    assert closeout["scope"] == {
        "element": "WEDGE6",
        "analysis": "linear_static",
        "material": "homogeneous_isotropic_small_strain_elastic",
        "new_physics": False,
        "heavy_benchmark_run": False,
        "historical_evidence_rewritten": False,
    }
    assert accounting["wedge6_case_count_before"] == 22
    assert accounting["new_cases_added"] == 0
    assert accounting["wedge6_case_count_after"] == 22
    assert accounting["internal_corpus"]["pass"] == 18
    assert accounting["internal_corpus"]["expected_failure_pass"] == 4
    assert accounting["external_corpus"] == {
        "total": 12,
        "pass": 12,
        "fail": 0,
        "skipped": 0,
        "source": "qualification/0_2_7/vnv_v2/wp09_final_external_evidence.json",
    }


def test_external_comparability_and_maturity_are_fail_safe() -> None:
    closeout = _load(CLOSEOUT)

    assert closeout["external_vv"]["code_aster"]["status"] == "PASS_WITH_LIMITATIONS"
    assert closeout["external_vv"]["code_aster"]["tolerance_approval_state"] == "OWNER_REVIEW_REQUIRED"
    assert closeout["external_vv"]["calculix"]["status"] == "NOT_COMPARABLE"
    assert closeout["invariants"]["stress"] == "NOT_COMPARABLE"
    assert closeout["maturity"] == {
        "current_public_maturity": "EXPERIMENTAL",
        "recommendation": "KEEP_CURRENT_MATURITY",
        "promotion": False,
        "demotion": False,
        "reason": "Evidence is convincing within the declared static-linear scope, but Owner tolerance ratification and broader claims remain separate decisions.",
    }


def test_closeout_references_existing_evidence_without_rewriting_it() -> None:
    closeout = _load(CLOSEOUT)
    refs = set(closeout["governance"]["preserved_evidence"])
    refs.update((case["source"] for case in [closeout["case_accounting"]["internal_corpus"], closeout["case_accounting"]["external_corpus"]]))
    refs.add(closeout["external_vv"]["code_aster"]["evidence"])
    refs.add(closeout["external_vv"]["calculix"]["evidence"])

    assert all((ROOT / ref).is_file() for ref in refs)
    assert closeout["governance"]["full_regression_run"] is False
    assert closeout["governance"]["pushed"] is False


def test_closeout_is_registered_in_manifest_gate_and_document_registry() -> None:
    manifest = _load(ROOT / "qualification" / "0_2_7" / "manifest.json")
    gates = _load(ROOT / "qualification" / "0_2_7" / "gates.json")
    documents = _load(ROOT / "docs" / "document_registry.json")
    document_paths = {item["path"] for item in documents["documents"]}

    assert "qualification/0_2_7/wp09_s3_closeout.json" in manifest["documents"]
    assert "tests/unit/test_wp09_s3_closeout.py" in manifest["documents"]
    assert "qualification/0_2_7/wp09_s3_closeout.json" in gates["gates"][8]["files"]
    assert "verification/0_2_7/0_2_7_wp09_s3_closeout.md" in document_paths
