"""WP12 VV3D prepared case nodes; all FEM entries remain disabled."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from experiments.wp12_vv3d_adaptive import case_harness


@pytest.mark.parametrize(
    "case_id",
    [
        "VV3D-TET4-L1", "VV3D-TET4-L2", "VV3D-TET4-L3",
        "VV3D-TET10-L1", "VV3D-TET10-L2", "VV3D-TET10-L3",
        "VV3D-HEX8-L1", "VV3D-HEX8-L2", "VV3D-HEX8-L3",
        "VV3D-HEX20-L1", "VV3D-HEX20-L2", "VV3D-HEX20-L3",
    ],
)
def test_prepared_fem_case(case_id: str) -> None:
    """Exact future runner node; its first action is a strict manifest gate."""
    case_harness.run_registered_case(case_id)


@pytest.mark.parametrize(
    "case_id",
    [f"VV3D-ADAPT-{family}-{kind}" for family in ("TET4", "TET10", "HEX8", "HEX20")
     for kind in ("H1", "QLOAD")],
)
def test_prepared_adaptive_fem_case(case_id: str) -> None:
    """Prospective adaptive FEM identities; no execution before official registration."""
    pytest.skip(f"{case_id}: PREPARED_NOT_AUTHORIZED; adaptive execution is not integrated")


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20"])
def test_prepared_archived_postprocess_case(family: str) -> None:
    """Prospective archived-field postprocessing only; never performs an FEM solve."""
    pytest.skip(f"VV3D-ADAPT-{family}-QPOST: PREPARED_NOT_AUTHORIZED; archived-state path is not integrated")


def test_synthetic_inventory_hashes_and_execution_gate(monkeypatch) -> None:
    cases = case_harness.load_prepared_cases()
    assert len(cases) == 12
    for case in cases:
        assert case["execution_authorized"] is False
        assert case["nodeid_status"] == "PREPARED_NOT_AUTHORIZED"
        assert case["nodeid"] == case_harness._expected_nodeid(case["case_id"])
        monkeypatch.delenv("QF_DEV_VV3D_CASE_ID", raising=False)
        monkeypatch.delenv("QF_DEV_TARGET_NODEID", raising=False)
        monkeypatch.delenv("QF_DEV_MANIFEST_PATH", raising=False)
        monkeypatch.delenv("QF_DEV_MANIFEST_SHA256", raising=False)
        monkeypatch.delenv("QF_DEV_AUTHORIZATION_ID", raising=False)
        monkeypatch.delenv("QF_DEV_VV3D_SCIENCE_FINGERPRINT", raising=False)
        monkeypatch.delenv("QF_DEV_CONTROLLER_FINGERPRINT", raising=False)
        monkeypatch.delenv("QF_DEV_EVIDENCE_ROOT", raising=False)
        monkeypatch.delenv("QF_DEV_VV3D_RUNNER_RECEIPT_PATH", raising=False)
        monkeypatch.delenv("QF_DEV_VV3D_RUNNER_RECEIPT_SHA256", raising=False)
        with pytest.raises(PermissionError, match="runner context"):
            case_harness.require_authorized_execution(case["case_id"])


def test_registered_entry_refuses_without_runner_permit(monkeypatch) -> None:
    for name in (
        "QF_DEV_VV3D_CASE_ID", "QF_DEV_TARGET_NODEID", "QF_DEV_MANIFEST_PATH",
        "QF_DEV_MANIFEST_SHA256", "QF_DEV_AUTHORIZATION_ID",
        "QF_DEV_VV3D_SCIENCE_FINGERPRINT", "QF_DEV_CONTROLLER_FINGERPRINT",
        "QF_DEV_EVIDENCE_ROOT", "QF_DEV_VV3D_RUNNER_RECEIPT_PATH",
        "QF_DEV_VV3D_RUNNER_RECEIPT_SHA256",
    ):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(PermissionError, match="runner context"):
        case_harness.run_registered_case("VV3D-TET4-L1")


def _synthetic_runner_manifest(tmp_path: Path, case_id: str = "VV3D-TET4-L1") -> tuple[dict, dict[str, str]]:
    case = next(item for item in case_harness.load_prepared_cases() if item["case_id"] == case_id)
    nodeid = case_harness._expected_nodeid(case_id)
    receipt_path = tmp_path / "synthetic-preflight.json"
    receipt = {
        "nodeid": nodeid, "status": "PREFLIGHT_PASS", "bodies_executed": False,
        "reservation_created": False, "selected_nodeids": [nodeid], "skipped": 0,
    }
    receipt_raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    receipt_path.write_bytes(receipt_raw)
    rules_path = case_harness.CAMPAIGN_DIR.parent / "criteria_proposals_20261029" / "criteria_tet4_draft.json"
    rules = json.loads(rules_path.read_bytes())["criteria"]
    criteria_sha256 = hashlib.sha256(json.dumps(
        rules, sort_keys=True, separators=(",", ":"), allow_nan=False,
    ).encode()).hexdigest()
    identities = {
        "scientific_fingerprint": "a" * 64,
        "controller_fingerprint": "b" * 64,
    }
    manifest = {
        "schema": "qf-wp12-vv3d-case-manifest-v1", "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
        "case_id": case_id, "nodeid": nodeid, "state": "OWNER_AUTHORIZED",
        "execution_authorized": True, "do_not_execute": False, "mesh_sha256": case["mesh_sha256"],
        "selected_dofs": case["dofs"], "timeout_seconds": case["timeout_max_seconds"],
        "rss_soft_limit_mib": case["rss_soft_limit_mib"], "max_attempts": case["attempts_max"],
        "authorization_id": "SYNTHETIC-AUTH-01", **identities,
        "owner_decision": {"status": "APPROVED", "approved_by": "Owner", "decision_id": "SYNTHETIC-OWNER-01",
                           "decision_sha256": "d" * 64},
        "preflight": {"nodeid": nodeid, "status": "PREFLIGHT_PASS",
                      "receipt_sha256": hashlib.sha256(receipt_raw).hexdigest(),
                      "receipt_path": str(receipt_path)},
        "frozen_criteria": rules, "criteria_sha256": criteria_sha256,
    }
    manifest_path = tmp_path / "synthetic-manifest.json"
    manifest_raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    manifest_path.write_bytes(manifest_raw)
    runner_receipt = {
        "schema": "qf-wp12-vv3d-runner-reservation-v1", "status": "RESERVED",
        "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1", "case_id": case_id, "nodeid": nodeid,
        "manifest_sha256": hashlib.sha256(manifest_raw).hexdigest(),
        "preflight_receipt_sha256": manifest["preflight"]["receipt_sha256"],
        "decision_id": manifest["owner_decision"]["decision_id"],
        "decision_sha256": manifest["owner_decision"]["decision_sha256"], **identities,
        "authorization_id": manifest["authorization_id"],
        "ledger_scope_id": "wp12_vv3d_adaptive",
        "selected_dofs": case["dofs"], "timeout_seconds": case["timeout_max_seconds"],
        "rss_soft_limit_mib": case["rss_soft_limit_mib"], "archive_size_limit_mib": 256,
        "attempt_number": 1, "max_attempts": 1, "attempt_reserved": True,
        "ledger_path": str(tmp_path / case_harness.VV3D_LEDGER_FILENAME),
        "ledger_sha256_after_reservation": "e" * 64,
        "campaign_attempts_used_after": 1, "campaign_seconds_reserved_after": 1200,
        "evidence_root": str(tmp_path / "evidence"),
        "reservation_id": "SYNTHETIC-RESERVATION-01", "attempt_id": "SYNTHETIC-ATTEMPT-01",
    }
    runner_receipt_path = tmp_path / "synthetic-runner-reservation.json"
    runner_receipt_raw = (json.dumps(runner_receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    runner_receipt_path.write_bytes(runner_receipt_raw)
    env = {
        "QF_DEV_VV3D_CASE_ID": case_id, "QF_DEV_TARGET_NODEID": nodeid,
        "QF_DEV_MANIFEST_PATH": str(manifest_path), "QF_DEV_MANIFEST_SHA256": hashlib.sha256(manifest_raw).hexdigest(),
        "QF_DEV_AUTHORIZATION_ID": manifest["authorization_id"],
        "QF_DEV_VV3D_SCIENCE_FINGERPRINT": identities["scientific_fingerprint"],
        "QF_DEV_CONTROLLER_FINGERPRINT": identities["controller_fingerprint"],
        "QF_DEV_EVIDENCE_ROOT": str(tmp_path / "evidence"),
        "QF_DEV_VV3D_RUNNER_RECEIPT_PATH": str(runner_receipt_path),
        "QF_DEV_VV3D_RUNNER_RECEIPT_SHA256": hashlib.sha256(runner_receipt_raw).hexdigest(),
    }
    return manifest, env


def test_synthetic_manifest_and_preflight_shape_is_accepted_without_running_case(tmp_path, monkeypatch) -> None:
    # This tests only the child-side envelope parser. It does not authenticate Owner
    # identity or call any element assembly / solver path.
    _manifest, env = _synthetic_runner_manifest(tmp_path)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    context = case_harness.require_authorized_execution("VV3D-TET4-L1")
    assert context["nodeid"] == env["QF_DEV_TARGET_NODEID"]
    assert context["criteria_sha256"] == _manifest["criteria_sha256"]


def test_synthetic_preflight_skip_or_manifest_mutation_is_refused(tmp_path, monkeypatch) -> None:
    manifest, env = _synthetic_runner_manifest(tmp_path)
    receipt_path = Path(manifest["preflight"]["receipt_path"])
    receipt = json.loads(receipt_path.read_bytes())
    receipt["skipped"] = 1
    receipt_raw = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    receipt_path.write_bytes(receipt_raw)
    manifest["preflight"]["receipt_sha256"] = hashlib.sha256(receipt_raw).hexdigest()
    manifest_path = Path(env["QF_DEV_MANIFEST_PATH"])
    manifest_raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    manifest_path.write_bytes(manifest_raw)
    env["QF_DEV_MANIFEST_SHA256"] = hashlib.sha256(manifest_raw).hexdigest()
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(PermissionError, match="collect-only"):
        case_harness.require_authorized_execution("VV3D-TET4-L1")


def test_synthetic_sidecar_is_written_before_observable_assertions(tmp_path) -> None:
    case_id = "VV3D-TET4-L1"
    receipt = case_harness.write_synthetic_sidecar(tmp_path / "evidence", case_id, "SYNTHETIC-001")
    sidecar = Path(receipt["path"])
    saved = json.loads(sidecar.read_bytes())

    # This comparison runs only after persistence; actual measurements remain absent.
    assert hashlib.sha256(sidecar.read_bytes()).hexdigest() == receipt["sha256"]
    assert saved["case_state"] == "PREPARED_NOT_AUTHORIZED"
    assert saved["execution"] == {"status": "NOT_AUTHORIZED", "attempt_reserved": False, "fem_started": False}
    assert all(value == {"status": "NOT_EXPOSED"} for value in saved["observables"].values())
    assert all(value == {"status": "NOT_ASSESSED"} for value in saved["criteria"].values())


def test_synthetic_nonfinite_values_are_explicitly_preserved() -> None:
    result = case_harness.sanitize_for_evidence({"u": [1.0, float("nan"), float("inf")]})
    assert result["u"][0] == 1.0
    assert result["u"][1] == {"status": "NONFINITE", "representation": "nan"}
    assert result["u"][2] == {"status": "NONFINITE", "representation": "inf"}
    assert json.loads(json.dumps(result, allow_nan=False)) == result


def test_synthetic_load_quadrature_metric_compares_nodal_load_vectors() -> None:
    exact = case_harness._relative_vector_difference((1.0, 2.0, 3.0), (1.0, 2.0, 3.0))
    changed = case_harness._relative_vector_difference((1.0, 0.0, 0.0), (3.0, 0.0, 0.0))
    assert exact == 0.0
    assert changed == pytest.approx(2.0 / 3.0)


def test_synthetic_load_quadrature_gate_checks_independent_force_and_moment_oracle() -> None:
    low = {"force_closure_n": (0.0, 0.0, 1.1), "moment_closure_nm": (0.0, 0.0, 0.0)}
    high = {"force_closure_n": (0.0, 0.0, 1.1), "moment_closure_nm": (0.0, 0.0, 0.0)}
    exact = {"body_force_n": (0.0, 0.0, 1.0), "body_moment_origin_nm": (0.0, 0.0, 0.0)}
    diagnostic = case_harness._load_quadrature_relative_diagnostics(
        (0.0, 0.0, 0.5), (0.0, 0.0, 0.5), low, high, exact,
    )
    assert diagnostic["nodal_load_vector_relative_l2"] == 0.0
    assert diagnostic["maximum_relative_difference"] == pytest.approx(0.1)


def test_synthetic_campaign_criteria_remain_unassessed() -> None:
    payload = {"case_level": 3, "observables": {}}
    mandatory = [
        {"id": "finite", "classification": "CASE_GATE", "operator": "ALL_TRUE", "threshold": None, "unit": "1"},
        {"id": "det_j_positive", "classification": "CASE_GATE", "operator": "GT", "threshold": 0, "unit": "m3"},
        {"id": "free_residual", "classification": "CASE_GATE", "operator": "LE", "threshold": 1e-8, "unit": "1"},
        {"id": "energy_identity", "classification": "CASE_GATE", "operator": "LE", "threshold": 1e-6, "unit": "1"},
        {"id": "force_closure", "classification": "CASE_GATE", "operator": "LE", "threshold": 1e-8, "unit": "1"},
        {"id": "moment_closure", "classification": "CASE_GATE", "operator": "LE", "threshold": 1e-8, "unit": "1"},
        {"id": "load_quadrature", "classification": "CASE_GATE", "operator": "LE", "threshold": 1e-6, "unit": "1"},
        {"id": "post_quadrature", "classification": "CASE_GATE", "operator": "LE", "threshold": 1e-4, "unit": "1"},
    ]
    deferred = {
        "id": "displacement_order", "classification": "CAMPAIGN_GATE_DEFERRED",
        "operator": "GE", "threshold": 1.2, "unit": "1",
    }
    outcome = case_harness.evaluate_case_criteria(payload, [*mandatory, deferred])
    assert outcome["displacement_order"]["status"] == "NOT_ASSESSED"
    assert outcome["displacement_order"]["classification"] == "CAMPAIGN_GATE_DEFERRED"
