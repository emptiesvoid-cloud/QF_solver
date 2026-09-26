"""No-solve tests for the WP07-D R2.5 evidence status normalization."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOL_PATH = (
    ROOT
    / "qualification/0_2_9/wp07d_contact_requalification_r2/continue_r2_5_replays.py"
)
SPEC = importlib.util.spec_from_file_location("wp07d_r2_5_replay_resume", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
TOOL = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(TOOL)


def _gate(raw_penalty_status: str = "success") -> dict[str, object]:
    cases: dict[str, object] = {}
    process_keys: list[str] = []
    for route in ("ACTIVE_SET", "PENALTY"):
        route_cases: dict[str, object] = {}
        for level in ("M1", "M2", "M3"):
            key = f"{route}/{level}"
            process_keys.append(key)
            production_status = "PASS" if route == "ACTIVE_SET" else raw_penalty_status
            route_cases[level] = {
                "status": "PASS",
                "problems": [],
                "production_status": production_status,
                "production_run_status": "COMPLETED",
                "reference_status": "PASS",
                "reference_run_status": "COMPLETED",
                "production_telemetry_status": "HEALTHY",
                "reference_telemetry_status": "PASS",
                "production_result_sha256": "a" * 64,
                "production_run_sha256": "b" * 64,
                "reference_result_sha256": "c" * 64,
                "reference_run_sha256": "d" * 64,
                "production_metrics": {"sentinel": 1.25},
            }
        cases[route] = {
            "status": "PASS_READY_FOR_REPLAY",
            "replay_level": "M2" if route == "ACTIVE_SET" else "M1",
            "production_and_reference_cases_pass": True,
            "convergence_gates_pass": True,
            "cases": route_cases,
        }
    manifest_map = {key: {"path": key, "sha256": "e" * 64} for key in process_keys}
    order = [f"{route}/{level}/PRIMARY_PRODUCTION" for route in ("ACTIVE_SET", "PENALTY") for level in ("M1", "M2", "M3")]
    order += [f"{route}/{level}/INDEPENDENT_REFERENCE" for route in ("ACTIVE_SET", "PENALTY") for level in ("M1", "M2", "M3")]
    return {
        "status": "PASS_REPLAY_GATES_EVALUATED",
        "replay_run": False,
        "replay_authorizations_created": False,
        "routes": cases,
        "production_process_manifests": manifest_map,
        "reference_process_manifests": manifest_map,
        "sequential_process_order": order,
    }


def test_success_is_normalized_only_after_case_gate_passes() -> None:
    source = _gate()
    normalized = TOOL.normalize_pre_replay_gate(
        source,
        expected_replay_levels={"ACTIVE_SET": "M2", "PENALTY": "M1"},
        postprocessor_path="normalizer.py",
        postprocessor_sha256="f" * 64,
        source_gate_path="old.json",
        source_gate_sha256="1" * 64,
    )

    penalty = normalized["routes"]["PENALTY"]["cases"]["M1"]
    assert penalty["production_status_raw"] == "success"
    assert penalty["production_status"] == "PASS"
    assert penalty["production_metrics"] == {"sentinel": 1.25}
    assert source["routes"]["PENALTY"]["cases"]["M1"]["production_status"] == "success"
    assert normalized["status_normalization"]["normalized_cases"] == [
        {"case": "PENALTY/M1", "from": "success", "to": "PASS"},
        {"case": "PENALTY/M2", "from": "success", "to": "PASS"},
        {"case": "PENALTY/M3", "from": "success", "to": "PASS"},
    ]


@pytest.mark.parametrize(
    ("raw_status", "case_pass", "result_present", "expected"),
    [
        ("success", True, True, "PASS"),
        ("PASS", True, True, "PASS"),
        ("success", False, True, "FAIL_CLOSED"),
        ("not-a-pass", True, True, "FAIL_CLOSED"),
        (None, False, False, "MISSING"),
    ],
)
def test_primary_status_mapping_is_fail_closed(
    raw_status: object, case_pass: bool, result_present: bool, expected: str
) -> None:
    assert TOOL.canonical_primary_status(raw_status, case_pass=case_pass, result_present=result_present) == expected


def test_normalizer_rejects_a_failed_case_instead_of_promoting_it() -> None:
    source = _gate()
    source["routes"]["PENALTY"]["cases"]["M2"]["status"] = "FAIL_CLOSED"

    with pytest.raises(ValueError, match="complete passing"):
        TOOL.normalize_pre_replay_gate(
            source,
            expected_replay_levels={"ACTIVE_SET": "M2", "PENALTY": "M1"},
            postprocessor_path="normalizer.py",
            postprocessor_sha256="f" * 64,
            source_gate_path="old.json",
            source_gate_sha256="1" * 64,
        )
