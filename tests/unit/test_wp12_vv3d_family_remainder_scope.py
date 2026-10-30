"""Non-FEM checks for the closed nine-case VV3D family-remainder binding."""
from __future__ import annotations

import json

import pytest

from experiments.wp12_vv3d_adaptive import case_harness


def test_family_remainder_binding_is_exactly_the_nine_prepared_non_tet4_cases() -> None:
    matrix = json.loads(case_harness.MATRIX_PATH.read_bytes())
    prepared = {case["case_id"]: case for case in matrix["cases"]}
    assert set(case_harness.FAMILY_REMAINDER_CASE_IDS) == {
        f"VV3D-{family}-L{level}"
        for family in ("TET10", "HEX8", "HEX20")
        for level in (1, 2, 3)
    }

    for case_id in case_harness.FAMILY_REMAINDER_CASE_IDS:
        case = prepared[case_id]
        binding = case_harness._family_remainder_scope_binding(case_id, case)
        assert case["nodeid"] == case_harness._expected_nodeid(case_id)
        assert 0 < case["dofs"] <= 30_000
        assert binding == {
            "campaign_id": "WP12-VV3D-FAMILY-REMAINDER-20261030",
            "scope_id": "wp12_vv3d_family_remainder",
            "ledger_scope_id": "wp12_vv3d_family_remainder",
            "ledger_filename": "node-attempt-ledger-wp12-vv3d-family-remainder.jsonl",
            "timeout_seconds": 1_200,
            "rss_soft_limit_mib": 4_096,
            "max_attempts": 1,
        }


@pytest.mark.parametrize(
    "case_id",
    ["VV3D-TET4-L1", "VV3D-TET4-L2", "VV3D-TET4-L3", "VV3D-ADAPT-TET4-H1"],
)
def test_family_remainder_binding_rejects_tet4_and_adaptive_cases(case_id: str) -> None:
    with pytest.raises(PermissionError, match="exact nine-node family-remainder"):
        case_harness._family_remainder_scope_binding(case_id, {"case_id": case_id})


def test_family_remainder_binding_rejects_changed_nodeid_or_budget() -> None:
    matrix = json.loads(case_harness.MATRIX_PATH.read_bytes())
    case = next(case for case in matrix["cases"] if case["case_id"] == "VV3D-TET10-L1")
    wrong_node = {**case, "nodeid": case_harness._expected_nodeid("VV3D-TET10-L2")}
    wrong_timeout = {**case, "timeout_max_seconds": 2_400}
    wrong_rss = {**case, "rss_soft_limit_mib": 8_192}

    for changed in (wrong_node, wrong_timeout, wrong_rss):
        with pytest.raises(PermissionError, match="exact nine-node family-remainder"):
            case_harness._family_remainder_scope_binding("VV3D-TET10-L1", changed)
