"""Targeted tests for the experimental WP08 area-supported M2/M3 runner."""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pytest
from numpy.typing import NDArray

from scripts.run_wp08_area_supported_m2_m3_diagnostic import (
    _all_finite,
    _binding_digest,
    _common_coordinate_displacement_delta,
    _diagnostic_gates,
    _failure_payload,
    _json_safe,
    _case_skip_reason,
    _load_case_metrics,
    _relative_delta,
)
from scripts.run_wp08_area_supported_m2_m3_diagnostic_r1_9 import (
    ARTIFACT_ID as R1_9_ARTIFACT_ID,
    CONTRACT_REL as R1_9_CONTRACT_REL,
    FREEZE_BINDING_REL as R1_9_FREEZE_BINDING_REL,
    M1_CONTRACT_DOCUMENT_REL as R1_9_M1_CONTRACT_DOCUMENT_REL,
    R1_8_EVIDENCE_REL as R1_8_EVIDENCE_REL,
    R1_8_EXPECTED_FILE_HASHES as R1_8_EXPECTED_FILE_HASHES,
    _manifest_preserved_files as r1_9_manifest_preserved_files,
    _source_inventory as r1_9_m2_source_inventory,
    prepare_r1_9_amendment as r1_9_prepare_amendment,
)
from scripts.run_wp08_area_supported_m1_diagnostic_r1_9 import _source_inventory as r1_9_m1_source_inventory
from solveur.core.errors import NumericalConvergenceError


def test_r1_9_m2_m3_binding_uses_its_own_prospective_m1_root_and_document() -> None:
    assert R1_9_ARTIFACT_ID.endswith("R1.9")
    assert "area_supported_r1_9_20260926" in R1_9_CONTRACT_REL.as_posix()
    assert "area_supported_r1_9_20260926" in R1_9_FREEZE_BINDING_REL.as_posix()
    assert R1_9_M1_CONTRACT_DOCUMENT_REL.as_posix().endswith(
        "wp08-area-supported-contact-requalification-r1-9.md"
    )


def test_r1_9_historical_file_manifest_records_path_size_and_hash(tmp_path) -> None:
    historical = tmp_path / "historical" / "result.json"
    historical.parent.mkdir()
    historical.write_bytes(b'{"status":"FAIL_CLOSED"}\n')

    records = r1_9_manifest_preserved_files(tmp_path, (historical,))

    assert records == [
        {
            "path": "historical/result.json",
            "sha256": hashlib.sha256(historical.read_bytes()).hexdigest(),
            "size_bytes": historical.stat().st_size,
        }
    ]


def test_r1_9_m2_m3_amendment_requires_explicit_owner_authorization(tmp_path) -> None:
    with pytest.raises(PermissionError, match="explicit Owner authorization"):
        r1_9_prepare_amendment(tmp_path / "not-authorized")


def test_r1_9_m1_and_m2_m3_freeze_the_same_source_inventory() -> None:
    assert r1_9_m1_source_inventory() == r1_9_m2_source_inventory()


def test_r1_9_preserves_the_exact_r1_8_failure_and_parent_records() -> None:
    assert R1_8_EVIDENCE_REL.as_posix().endswith("area_supported_r1_8_20260926")
    assert R1_8_EXPECTED_FILE_HASHES["M2_M3/final.json"] == (
        "0e39832b0ec6df63d49a74bc69fdd552ea29fd05482af903faa53dc7e271786a"
    )
    assert R1_8_EXPECTED_FILE_HASHES["M2_M3/M3/slip_target/failure.json"] == (
        "f2eb4698778bf01e002425cbed873a078e122bba0dbcbe4bccb5577a493446b0"
    )
    assert R1_8_EXPECTED_FILE_HASHES["freeze_binding_r1_8_contact_requalification.json"] == (
        "a8215839e20d92857b0f88f3e0ff69ba691ce69766d8ea3bd079ffba9c7fd47f"
    )


def test_execution_binding_digest_uses_canonical_object_not_pretty_json_bytes() -> None:
    binding: dict[str, object] = {
        "schema": "test.execution_binding.v1",
        "owner_authorized": True,
        "execution_binding_sha256": None,
    }
    binding["execution_binding_sha256"] = _binding_digest(binding)
    expected = str(binding["execution_binding_sha256"])
    pretty_json_bytes = json.dumps(binding, indent=2, sort_keys=True).encode("utf-8")

    assert _binding_digest(binding) == expected
    assert hashlib.sha256(pretty_json_bytes).hexdigest() != expected


def test_failure_payload_preserves_structured_contact_diagnostics_and_provenance() -> None:
    error = NumericalConvergenceError(
        "contact root failed",
        diagnostics={"contact": 7, "residual_vector": np.asarray([1.0e-8, -2.0e-8])},
    )
    payload = _json_safe(
        _failure_payload(
            error,
            mesh="M3",
            case="slip_target",
            contract_sha256="contract",
            execution_binding_sha256="binding",
            binding={
                "source_bundle_sha256": "source",
                "runner_sha256": "runner",
                "git": {"head": "head"},
            },
        )
    )

    assert payload["diagnostics"] == {"contact": 7, "residual_vector": [1.0e-8, -2.0e-8]}
    assert payload["contract_sha256"] == "contract"
    assert payload["execution_binding_sha256"] == "binding"
    assert payload["source_bundle_sha256"] == "source"
    assert payload["source_head"] == "head"
    assert payload["runner_sha256"] == "runner"


def test_relative_delta_handles_identical_zero_vectors() -> None:
    result = _relative_delta(np.zeros(3), np.zeros(3))

    assert result == {"absolute_l2": 0.0, "relative_l2": 0.0}


def test_common_coordinate_displacement_uses_shared_body_nodes() -> None:
    coarse = {
        "coordinates": np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]]),
        "body_node_count": 2,
        "displacement": np.asarray([[0.0, 0.0, 0.0], [0.0, 0.01, 0.0]]),
    }
    fine = {
        "coordinates": np.asarray(
            [[0.0, 0.0, 0.0], [0.5, 0.0, 0.0], [1.0, 0.0, 0.0]]
        ),
        "body_node_count": 3,
        "displacement": np.asarray(
            [[0.0, 0.0, 0.0], [0.0, 0.005, 0.0], [0.0, 0.01, 0.0]]
        ),
    }

    result = _common_coordinate_displacement_delta(coarse, fine)

    assert result["common_node_count"] == 2
    assert result["absolute_l2_m"] == 0.0
    assert result["relative_l2"] == 0.0


def test_diagnostic_gates_pass_for_two_dimensional_all_stick_patch() -> None:
    body: NDArray[np.float64] = np.zeros((12, 3), dtype=float)
    body[2] = [2.0, 0.0, 0.0]
    body[5] = [2.0, 1.0, 0.0]
    body[8] = [2.0, 0.0, 0.5]
    body[11] = [2.0, 1.0, 0.5]
    slave_nodes = (2, 5, 8, 11)
    area_by_node = {node: 0.125 for node in slave_nodes}
    rows = [
        {"active": True, "slave_node": node, "tangential_state": "stick"}
        for node in slave_nodes
    ]
    payload = {
        "solver": {
            "converged": True,
            "residual_norm": 1.0e-12,
            "contact": {"contacts": rows, "load_steps": [{} for _ in range(8)]},
        }
    }

    diagnostic, _ = _diagnostic_gates(
        payload, "M2", "stick_target", body, slave_nodes, area_by_node
    )

    assert diagnostic["status"] == "PASS_DIAGNOSTIC_GATES"
    assert diagnostic["active_support_affine_rank"] == 2
    assert diagnostic["active_area_fraction"] == 1.0
    assert diagnostic["terminal_active_states"] == ["stick"]
    assert diagnostic["fallback_count"] is None


def test_diagnostic_gates_fail_closed_on_wrong_terminal_state() -> None:
    body = np.asarray(
        [[2.0, 0.0, 0.0], [2.0, 1.0, 0.0], [2.0, 0.0, 0.5]], dtype=float
    )
    slave_nodes = (0, 1, 2)
    rows = [
        {"active": True, "slave_node": node, "tangential_state": "slip"}
        for node in slave_nodes
    ]
    payload = {
        "solver": {
            "converged": True,
            "contact": {"contacts": rows, "load_steps": [{} for _ in range(8)]},
        }
    }

    diagnostic, _ = _diagnostic_gates(
        payload, "M2", "stick_target", body, slave_nodes, {0: 0.2, 1: 0.2, 2: 0.1}
    )

    assert diagnostic["gates"]["expected_terminal_tangential_state"] is False
    assert diagnostic["status"] == "FAIL_CLOSED_DIAGNOSTIC_GATE"


def test_nonfinite_nested_observable_is_detected() -> None:
    assert _all_finite({"values": [1.0, np.float64(2.0)]})
    assert not _all_finite({"values": [1.0, float("inf")]})


@pytest.mark.parametrize(
    ("mesh", "case", "statuses", "expected"),
    [
        ("M2", "slip_target", {"M2/stick_target": "FAIL"}, "NOT_RUN_PREVIOUS_M2_CASE_FAILED"),
        ("M2", "slip_target", {"M2/stick_target": "PASS_DIAGNOSTIC_GATES"}, None),
        ("M3", "stick_target", {"M2/stick_target": "PASS_DIAGNOSTIC_GATES"}, "NOT_RUN_M2_GATE_FAILED"),
        (
            "M3",
            "slip_target",
            {
                "M2/stick_target": "PASS_DIAGNOSTIC_GATES",
                "M2/slip_target": "PASS_DIAGNOSTIC_GATES",
                "M3/stick_target": "FAIL",
            },
            "NOT_RUN_PREVIOUS_M3_CASE_FAILED",
        ),
        (
            "M3",
            "slip_target",
            {
                "M2/stick_target": "PASS_DIAGNOSTIC_GATES",
                "M2/slip_target": "PASS_DIAGNOSTIC_GATES",
                "M3/stick_target": "PASS_DIAGNOSTIC_GATES",
            },
            None,
        ),
    ],
)
def test_sequential_campaign_dependencies_fail_closed(
    mesh: str, case: str, statuses: dict[str, str], expected: str | None
) -> None:
    assert _case_skip_reason(mesh, case, statuses) == expected


def test_m1_refinement_metrics_load_requires_complete_raw_schema(tmp_path) -> None:
    case_dir = tmp_path / "M1" / "stick_target"
    case_dir.mkdir(parents=True)
    (case_dir / "result.json").write_text(
        json.dumps(
            {
                "audit": {
                    "equilibrium": {
                        "reaction_resultant": [1.0, 0.0, 0.0],
                        "reaction_moment_about_origin": [0.0, 1.0, 0.0],
                        "force_balance_relative_error": 0.0,
                        "moment_balance_relative_error": 0.0,
                    }
                },
                "solver": {"contact": {"contacts": []}, "residual_norm": 1.0e-12},
                "diagnostic": {
                    "active_area_m2": 1.0,
                    "active_area_fraction": 1.0,
                    "active_slave_node_count": 3,
                    "active_support_affine_rank": 2,
                },
            }
        ),
        encoding="utf-8",
    )
    np.savez_compressed(
        case_dir / "raw.npz",
        node_coordinates=np.zeros((3, 3)),
        body_node_count=np.asarray([3]),
        displacement=np.zeros(9),
        contact_normal_force=np.asarray([[1.0, 0.0, 0.0]]),
        contact_tangential_force_global=np.asarray([[0.0, 2.0, 0.0]]),
    )

    metrics = _load_case_metrics(tmp_path, "M1", "stick_target")

    assert metrics["normal_resultant"].tolist() == [1.0, 0.0, 0.0]
    assert metrics["tangential_resultant"].tolist() == [0.0, 2.0, 0.0]


def test_m1_refinement_metrics_reject_missing_raw_arrays(tmp_path) -> None:
    case_dir = tmp_path / "M1" / "stick_target"
    case_dir.mkdir(parents=True)
    (case_dir / "result.json").write_text("{}", encoding="utf-8")
    np.savez_compressed(case_dir / "raw.npz", displacement=np.zeros(3))

    with pytest.raises(ValueError, match="missing required comparison arrays"):
        _load_case_metrics(tmp_path, "M1", "stick_target")
