"""Targeted WP09 robustness and external-evidence contract checks."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from solveur.verification.v2 import load_cases
from scripts.run_wp09_wedge6 import _execute_internal


ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "qualification/0_2_7/vnv_v2/wp09_cases.json"
EVIDENCE = ROOT / "qualification/0_2_7/vnv_v2/wp09_evidence.json"


def test_wp09_catalog_is_complete_and_unique() -> None:
    cases = load_cases(CATALOG)
    assert len(cases) == 22
    assert len({case.case_id for case in cases}) == len(cases)
    assert all(case.element == "WEDGE6" for case in cases)
    assert sum(case.expected_failure is not None for case in cases) == 4


def test_wp09_evidence_has_no_unexpected_internal_failures() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    assert payload["summary"]["case_count"] == 22
    assert payload["summary"]["pass"] == 18
    assert payload["summary"]["expected_failure_pass"] == 4
    assert payload["summary"]["fail"] == 0
    assert payload["summary"]["unexpected_failures"] == []
    assert payload["policy"]["post_observation_retuning"] is False


def test_wp09_external_limits_are_not_reported_as_qualification() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    calculix = payload["external"]["calculix_c3d6"]
    aster = payload["external"]["code_aster_penta6"]
    assert calculix["comparison_status"] == "NOT_FORMULATION_COMPATIBLE"
    assert calculix["verdict"] != "PASS_EXTERNAL"
    assert aster["state"] == "PASS"
    assert aster["verdict"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"
    assert aster["comparison_status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"
    assert aster["tolerance_approval_state"] == "OWNER_REVIEW_REQUIRED"
    assert payload["wp09r_external_evidence"].endswith("wp09r_code_aster_evidence.json")


def test_wp09_failure_and_invariance_fixtures_remain_fail_closed() -> None:
    with pytest.raises(RuntimeError, match="WEDGE6_JACOBIAN_CERTIFICATE_INVALID"):
        _execute_internal("WP09-INVERTED", "WEDGE6_JACOBIAN_CERTIFICATE_INVALID")
    with pytest.raises(RuntimeError, match="WEDGE6_JACOBIAN_CERTIFICATE_INVALID"):
        _execute_internal("WP09-WRONG-NODE-ORDER", "WEDGE6_JACOBIAN_CERTIFICATE_INVALID")
    with pytest.raises(RuntimeError, match="MALFORMED_GMSH_REJECTED"):
        _execute_internal("WP09-MALFORMED-GMSH", "MALFORMED_GMSH_REJECTED")
    assert _execute_internal("WP09-RIGID-TRANSFORM", None)["status"] == "PASS"
    assert _execute_internal("WP09-SCALE", None)["status"] == "PASS"
