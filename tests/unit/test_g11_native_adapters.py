"""Focused route-native execution checks for the four 026-G11 cases."""

from __future__ import annotations

import json
from pathlib import Path

from solveur.verification.g11_native_adapters import (
    native_route_status,
    run_cross_route_g11_cases,
    run_native_g11_cases,
)


ROOT = Path(__file__).resolve().parents[2]
CASES = ROOT / "qualification" / "0_2_6" / "g11_adversarial_cases.json"
SOURCE_SHA = "1b6887c794452bb6e571bdacc3ecc0983b3bca2d"


def test_four_approved_cases_execute_on_native_routes_and_archive(tmp_path: Path) -> None:
    results = run_native_g11_cases(CASES, tmp_path, source_sha=SOURCE_SHA)

    assert len(results) == 4
    assert all(result["status"] == "PASS" for result in results.values())
    assert results["VNV026-ADV-PLN-001"]["envelope"]["ERROR_TYPE_OR_CODE"] == (
        "NumericalConvergenceError:singular"
    )
    assert results["VNV026-ADV-PLN-002"]["envelope"]["ERROR_TYPE_OR_CODE"] == (
        "MeshValidationError:UNSUPPORTED_EXPLICIT"
    )
    assert results["VNV026-ADV-PLN-003"]["envelope"]["ERROR_TYPE_OR_CODE"] == (
        "NumericalConvergenceError:MAX_ITERATIONS"
    )
    rollback = results["VNV026-ADV-PLN-004"]
    assert rollback["envelope"]["STATE_PRESERVED"] is True
    assert all(rollback["envelope"][field] is True for field in ("DETERMINISTIC", "NO_NAN_INF", "NO_SILENT_PASS"))

    for case_id in results:
        archive = tmp_path / f"{case_id}.json"
        assert archive.exists()
        record = json.loads(archive.read_text(encoding="utf-8"))
        assert record["provenance"]["source_sha"] == SOURCE_SHA
        assert record["provenance"]["runner_version"] == "026-G11-runner-1"
        assert len(record["provenance"]["case_definition_sha256"]) == 64
        assert record["provenance"]["captured_at_utc"]
        assert record["observations"]["first"]["observed_failure"] is True
        assert record["observations"]["replay"]["observed_failure"] is True

    rollback_observation = json.loads(
        (tmp_path / "VNV026-ADV-PLN-004.json").read_text(encoding="utf-8")
    )["observations"]["first"]["diagnostics"]
    assert rollback_observation["committed_digest_before_failure"] == rollback_observation["retry_state_digest"]


def test_cross_route_aggregation_is_bounded_and_complete_for_executed_cases() -> None:
    aggregation_path = ROOT / "qualification" / "0_2_6" / "g11_cross_route_aggregation.json"
    aggregation = json.loads(aggregation_path.read_text(encoding="utf-8"))

    rows = aggregation["aggregation"]
    assert len(rows) == 8
    assert aggregation["official_gate_status"] == "NOT_STARTED"
    assert all(
        row["runtime_result"] == "PASS"
        and row["deterministic"]
        and row["no_nan_inf"]
        and row["no_silent_pass"]
        and row["provenance_valid"]
        for row in rows
    )
    assert aggregation["requirements_assessment"] == {
        "G11-DIAG-002": "SATISFIED_BOUNDED",
        "G11-DIAG-004": "SATISFIED_BOUNDED",
        "G11-DIAG-005": "SATISFIED_BOUNDED",
        "G11-DIAG-008": "SATISFIED_BOUNDED",
    }

def test_cross_route_introspection_does_not_overclaim_unexecuted_routes() -> None:
    status = native_route_status()

    assert status["linear_static"] == "READY"
    assert status["nonlinear_static"] == "READY"
    assert status["geometric_nonlinear_static"] == "PARTIAL"
    assert status["modal"] == "PARTIAL"
    assert status["linear_buckling"] == "PARTIAL"
    assert status["linear_static_contact"] == "PARTIAL"


def test_partial_routes_emit_valid_deterministic_failure_envelopes(tmp_path: Path) -> None:
    cases = ROOT / "qualification" / "0_2_6" / "g11_cross_route_cases.json"
    results = run_cross_route_g11_cases(
        cases,
        tmp_path,
        source_sha="3beff93b8ad5f1455ba67097d098adacf5054e78",
    )

    assert len(results) == 4
    assert all(result["status"] == "PASS" for result in results.values())
    assert all(
        result["envelope"][field] is True
        for result in results.values()
        for field in ("DETERMINISTIC", "NO_NAN_INF", "NO_SILENT_PASS")
    )
    assert {result["envelope"]["ROUTE"] for result in results.values()} == {
        "geometric_nonlinear_static",
        "modal",
        "linear_buckling",
        "linear_static_contact",
    }
    assert all((tmp_path / f"{case_id}.json").exists() for case_id in results)

    for case_id, result in results.items():
        record = json.loads((tmp_path / f"{case_id}.json").read_text(encoding="utf-8"))
        assert result["envelope"]["EVIDENCE_ID"] == f"G11-NATIVE-{case_id}"
        assert record["provenance"]["runner_version"] == "026-G11-runner-1"
        assert len(record["provenance"]["case_definition_sha256"]) == 64
        assert record["provenance"]["captured_at_utc"]
        assert record["observations"]["first"]["error_type_or_code"] == record["observations"]["replay"]["error_type_or_code"]
        assert record["observations"]["first"]["observed_failure"] is True
        assert record["observations"]["replay"]["observed_failure"] is True
