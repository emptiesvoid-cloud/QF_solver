"""Infrastructure tests for the route-neutral 026-G11 runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from solveur.core.errors import InputValidationError
from solveur.verification.g11_runner import (
    ENVELOPE_FIELDS,
    G11AdapterResult,
    G11CaseSpec,
    G11Runner,
    load_case_specs,
)


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "qualification" / "0_2_6" / "g11_adversarial_cases.json"


def _case(**overrides: object) -> G11CaseSpec:
    values: dict[str, object] = {
        "case_id": "TEST-G11",
        "failure_class": "unsupported_load_element_pair",
        "route": "linear_static",
        "expected_behavior": "reject explicitly",
        "adapter_id": "test",
        "expected_error_types": ("InputValidationError",),
    }
    values.update(overrides)
    return G11CaseSpec(**values)


def test_g11_runner_loads_four_planned_cases_without_executing_them() -> None:
    cases = load_case_specs(CASES)
    assert [case.case_id for case in cases] == [
        "VNV026-ADV-PLN-001",
        "VNV026-ADV-PLN-002",
        "VNV026-ADV-PLN-003",
        "VNV026-ADV-PLN-004",
    ]
    assert all(case.expected_failure for case in cases)


def test_g11_case_schema_rejects_missing_required_fields() -> None:
    with pytest.raises(ValueError, match="failure_class"):
        G11CaseSpec.from_mapping({"case_id": "missing"})


def test_g11_runner_emits_complete_envelope_for_route_native_exception() -> None:
    runner = G11Runner(
        {"test": lambda case: (_ for _ in ()).throw(InputValidationError("unsupported combination"))},
        source_sha="test-sha",
    )
    result = runner.run_case(_case(), evidence_id="EVIDENCE-001")
    assert result["status"] == "PASS"
    assert tuple(result["envelope"]) == ENVELOPE_FIELDS
    assert result["envelope"]["ERROR_TYPE_OR_CODE"] == "InputValidationError"
    assert result["envelope"]["NO_NAN_INF"] is True
    assert result["envelope"]["NO_SILENT_PASS"] is True
    assert result["envelope"]["DETERMINISTIC"] is True
    assert result["envelope"]["EVIDENCE_ID"] == "EVIDENCE-001"


def test_g11_runner_rejects_nan_inf_in_a_failure_payload() -> None:
    runner = G11Runner(
        {"test": lambda case: G11AdapterResult(False, "controlled failure", payload={"value": float("nan")})},
        source_sha="test-sha",
    )
    result = runner.run_case(_case())
    assert result["status"] == "FAIL"
    assert result["envelope"]["NO_NAN_INF"] is False


def test_g11_runner_detects_silent_pass() -> None:
    runner = G11Runner({"test": lambda case: G11AdapterResult(True, payload={"value": 1.0})}, source_sha="test-sha")
    result = runner.run_case(_case())
    assert result["status"] == "FAIL"
    assert result["envelope"]["NO_SILENT_PASS"] is False


def test_g11_runner_detects_nondeterministic_adapter_results() -> None:
    calls = 0

    def adapter(case: G11CaseSpec) -> G11AdapterResult:
        nonlocal calls
        calls += 1
        return G11AdapterResult(False, f"InputValidationError:code-{calls}")

    result = G11Runner({"test": adapter}, source_sha="test-sha").run_case(_case())
    assert result["status"] == "FAIL"
    assert result["envelope"]["DETERMINISTIC"] is False


def test_g11_runner_checks_state_preservation_and_archives_result(tmp_path: Path) -> None:
    case = _case(
        case_id="TEST-STATE",
        failure_class="rejected_increment",
        route="geometric_nonlinear_static",
        expected_behavior="rollback then retry",
        stateful=True,
        expected_error_types=("NumericalConvergenceError",),
    )
    runner = G11Runner(
        {"test": lambda spec: G11AdapterResult(False, "NumericalConvergenceError:MAX_ITERATIONS", state_preserved=True)},
        source_sha="test-sha",
        provenance={"runner": "unit-test"},
    )
    result = runner.run_case(case)
    assert result["status"] == "PASS"
    assert result["envelope"]["STATE_PRESERVED"] is True
    target = runner.archive_result(result, tmp_path / "g11-result.json")
    archived = json.loads(target.read_text(encoding="utf-8"))
    assert set(archived["envelope"]) == set(ENVELOPE_FIELDS)
    assert archived["provenance"]["source_sha"] == "test-sha"


def test_g11_runner_rejects_unsupported_success_as_silent_pass() -> None:
    runner = G11Runner({"test": lambda case: {"route": "linear_static"}}, source_sha="test-sha")
    result = runner.run_case(_case())
    assert result["status"] == "FAIL"
    assert result["checks"]["expected_failure_observed"] is False
