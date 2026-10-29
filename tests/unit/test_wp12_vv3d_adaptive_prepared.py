"""WP12 VV3D prepared nodes; FEM entries remain controller-gated."""
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
    """Controller-gated adaptive FEM identities; no local authorization is inferred."""
    case_harness.run_registered_adaptive_fem_candidate(case_id)


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20"])
def test_prepared_archived_postprocess_case(family: str) -> None:
    """Controller-bound QPOST reads an archived displacement field only."""
    case_harness.run_registered_qpost_candidate(family)


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


@pytest.mark.parametrize(
    ("field", "replacement"),
    [("timeout_seconds", 1201), ("decision_sha256", "f" * 64)],
)
def test_synthetic_runner_receipt_budget_or_decision_mismatch_is_refused(
    tmp_path, monkeypatch, field, replacement,
) -> None:
    _manifest, env = _synthetic_runner_manifest(tmp_path)
    receipt_path = Path(env["QF_DEV_VV3D_RUNNER_RECEIPT_PATH"])
    receipt = json.loads(receipt_path.read_bytes())
    receipt[field] = replacement
    receipt_raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":")) + "\n").encode()
    receipt_path.write_bytes(receipt_raw)
    env["QF_DEV_VV3D_RUNNER_RECEIPT_SHA256"] = hashlib.sha256(receipt_raw).hexdigest()
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    with pytest.raises(PermissionError, match="runner receipt"):
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


def _synthetic_campaign_seed_cases(
    *, family: str = "TET4", displacement_errors: tuple[float, float, float] = (0.08, 0.034, 0.014),
    energy_errors: tuple[float, float, float] = (0.16, 0.09, 0.05),
) -> dict[str, dict]:
    cases: dict[str, dict] = {}
    for level, (displacement_error, energy_error) in enumerate(
        zip(displacement_errors, energy_errors, strict=True), start=1,
    ):
        case_id = f"VV3D-{family}-L{level}"
        cases[case_id] = {
            "case_id": case_id, "state": "PASS", "provenance_state": "VERIFIED",
            "sidecar_valid": True, "sidecar_sha256": f"{level:x}" * 64,
            "manifest_sha256": f"{level + 1:x}" * 64, "mesh_sha256": f"{level + 2:x}" * 64,
            "scientific_fingerprint": "a" * 64, "controller_fingerprint": "b" * 64,
            "h_m": 1.0 / (2 ** level),
            "observables": {
                "displacement_l2_m_5_2": {"status": "DIAGNOSTIC_UNQUALIFIED",
                                           "relative_error": displacement_error},
                "energy_error_norm_sqrt_j": {"status": "DIAGNOSTIC_UNQUALIFIED",
                                              "relative_error": energy_error},
                "stress_l2_pa": {"status": "DIAGNOSTIC_UNQUALIFIED", "relative_error": 0.2},
                "scalar_energy_relative_error": {"status": "AVAILABLE", "value": 0.04},
            },
            "criteria": {name: {"status": "PASS", "classification": "CASE_GATE"} for name in (
                "finite", "det_j_positive", "free_residual", "energy_identity", "force_closure",
                "moment_closure", "load_quadrature", "post_quadrature",
            )},
        }
    return cases


def _campaign_rules(family: str = "TET4") -> list[dict]:
    criteria_path = case_harness._safe_catalog_file(
        f"criteria_proposals_20261029/criteria_{family.lower()}_draft.json",
    )
    return json.loads(criteria_path.read_bytes())["criteria"]


def test_synthetic_campaign_gates_pass_and_preserve_all_refinement_metrics() -> None:
    seeds = _synthetic_campaign_seed_cases()
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "PASS"
    assert assessment["decision"] == "CONTINUE"
    assert {value["status"] for value in assessment["criteria"].values()} == {"PASS"}
    assert set(assessment["level_metrics"]) == {f"VV3D-TET4-L{level}" for level in (1, 2, 3)}
    assert assessment["criteria"]["displacement_order"]["intervals"] == ["L1-L2", "L2-L3"]


@pytest.mark.parametrize("state", ["PYTEST_FAILED", "SCIENTIFIC_DEVIATION", "INCONCLUSIVE"])
def test_synthetic_campaign_rejects_nonpass_case_state_even_with_finite_observables(state: str) -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET4-L3"]["state"] = state
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["decision"] == "STOP_INCONCLUSIVE"
    assert {item["status"] for item in assessment["criteria"].values()} == {"INCONCLUSIVE"}


def test_synthetic_campaign_rejects_case_gate_failure_hidden_in_a_pass_state() -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET4-L1"]["criteria"]["force_closure"]["status"] = "FAIL"
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["decision"] == "STOP_INCONCLUSIVE"
    assert all(item["status"] != "PASS" for item in assessment["criteria"].values())


def test_synthetic_campaign_partial_pytest_failure_is_not_downgraded_to_not_assessed() -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET4-L1"]["state"] = "PYTEST_FAILED"
    del seeds["VV3D-TET4-L2"]
    del seeds["VV3D-TET4-L3"]
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["criteria"]["displacement_order"]["status"] == "INCONCLUSIVE"
    assert assessment["criteria"]["energy_order"]["status"] == "INCONCLUSIVE"


def test_synthetic_campaign_gate_failure_is_scientific_deviation_stop() -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET4-L3"]["observables"]["displacement_l2_m_5_2"]["relative_error"] = 0.2
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "FAIL"
    assert assessment["decision"] == "SCIENTIFIC_DEVIATION_STOP"
    assert assessment["criteria"]["displacement_error_L3"]["status"] == "FAIL"
    assert "displacement_error_L3" in assessment["blocking_failures"]


def test_synthetic_campaign_missing_refinement_is_not_assessed_not_pass() -> None:
    seeds = _synthetic_campaign_seed_cases()
    del seeds["VV3D-TET4-L2"]
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "NOT_ASSESSED"
    assert assessment["criteria"]["displacement_order"]["status"] == "NOT_ASSESSED"
    assert assessment["criteria"]["energy_order"]["status"] == "NOT_ASSESSED"
    assert assessment["criteria"]["displacement_error_L3"]["status"] == "PASS"


def test_synthetic_campaign_missing_l3_metric_is_inconclusive() -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET4-L3"]["observables"].pop("stress_l2_pa")
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["criteria"]["stress_error_L3"]["status"] == "INCONCLUSIVE"
    assert assessment["criteria"]["stress_error_L3"]["status"] != "PASS"


def test_synthetic_campaign_unavailable_level_metric_never_passes_order_gate() -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET4-L2"]["observables"]["displacement_l2_m_5_2"]["status"] = "NOT_AVAILABLE"
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["criteria"]["displacement_order"]["status"] == "INCONCLUSIVE"
    assert assessment["status"] == "INCONCLUSIVE"


def test_synthetic_campaign_nonfinite_metric_is_inconclusive() -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET4-L3"]["observables"]["energy_error_norm_sqrt_j"]["relative_error"] = float("nan")
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["criteria"]["energy_error_L3"]["status"] == "INCONCLUSIVE"


def test_synthetic_campaign_interrupted_refinement_is_inconclusive() -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET4-L2"].update({"state": "INTERRUPTED", "sidecar_valid": False})
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["criteria"]["displacement_order"]["status"] == "INCONCLUSIVE"
    assert assessment["criteria"]["energy_order"]["status"] == "INCONCLUSIVE"


def test_synthetic_campaign_interruption_is_not_downgraded_to_missing_data() -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET4-L1"].update({"state": "TIMEOUT", "sidecar_valid": False})
    del seeds["VV3D-TET4-L2"]
    del seeds["VV3D-TET4-L3"]
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["criteria"]["displacement_order"]["status"] == "INCONCLUSIVE"
    assert "MISSING_LEVELS" in assessment["criteria"]["energy_order"]["reason"]


def test_synthetic_campaign_missing_run_state_is_inconclusive() -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET4-L3"].pop("state")
    assessment = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())

    assert assessment["status"] == "INCONCLUSIVE"
    assert assessment["criteria"]["displacement_error_L3"]["status"] == "INCONCLUSIVE"
    assert assessment["criteria"]["displacement_order"]["status"] == "INCONCLUSIVE"


def test_synthetic_campaign_invalid_seed_or_frozen_rules_are_explicitly_inconclusive() -> None:
    seeds = _synthetic_campaign_seed_cases()
    seeds["VV3D-TET10-L1"] = seeds.pop("VV3D-TET4-L1")
    identity_failure = case_harness.evaluate_campaign_criteria("TET4", seeds, _campaign_rules())
    assert identity_failure["status"] == "INCONCLUSIVE"
    assert {result["status"] for result in identity_failure["criteria"].values()} == {"INCONCLUSIVE"}

    rules = _campaign_rules()
    malformed = [rule for rule in rules if rule["id"] != "energy_order"]
    criteria_failure = case_harness.evaluate_campaign_criteria(
        "TET4", _synthetic_campaign_seed_cases(), malformed,
    )
    assert criteria_failure["status"] == "INCONCLUSIVE"
    assert {result["status"] for result in criteria_failure["criteria"].values()} == {"INCONCLUSIVE"}


def _synthetic_adaptive_receipt(
    tmp_path: Path, candidate_id: str, *, qpost_archive: dict | None = None,
) -> dict:
    _, candidates, catalog_sha = case_harness._adaptive_inventory()
    candidate = candidates[candidate_id]
    binding = case_harness._adaptive_bindings(candidate)
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir(exist_ok=True)
    campaign_decision = {"status": "APPROVED", "decision_id": "SYNTHETIC-CAMPAIGN-01",
                         "decision_sha256": "f" * 64, "catalog_sha256": catalog_sha}
    transition = {
        "status": "APPROVED", "decision_id": "SYNTHETIC-TRANSITION-01",
        "decision_sha256": "d" * 64, "source_case_id": candidate["seed_case"],
        "candidate_id": candidate_id,
    }
    archive_meta = None
    if candidate["execution_kind"] == "POSTPROCESS_ONLY":
        archive_document = qpost_archive or {
            "schema": "qf-wp12-vv3d-state-archive-v1",
            "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
            "case_id": candidate["seed_case"],
            "mesh_sha256": candidate["prepared_mesh"]["sha256"],
            "case_state": "OWNER_AUTHORIZED_EXECUTION", "execution_status": "COMPLETED_UNASSESSED",
            "manifest_sha256": "9" * 64, "attempt_id": "SYNTHETIC-SEED-ATTEMPT-01",
            "nodal_displacements_m": [],
        }
        archive_raw = (json.dumps(archive_document, sort_keys=True, separators=(",", ":"),
                                      allow_nan=False) + "\n").encode()
        archive_path = evidence_root / f"archive-{candidate_id}.json"
        archive_path.write_bytes(archive_raw)
        archive_meta = {
            "status": "AVAILABLE", "path": str(archive_path), "sha256": hashlib.sha256(archive_raw).hexdigest(),
            "source_case_id": archive_document["case_id"],
            "source_mesh_sha256": archive_document["mesh_sha256"],
            "source_manifest_sha256": archive_document["manifest_sha256"],
            "source_attempt_id": archive_document["attempt_id"],
        }
        source = {
            "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1", "candidate_id": candidate_id,
            "postprocessing_job_id": "SYNTHETIC-QPOST-JOB-01",
            "seed_case": {
                "case_id": candidate["seed_case"], "status": "PASS",
                "source_run_receipt_sha256": "7" * 64,
                "manifest_sha256": archive_meta["source_manifest_sha256"],
                "attempt_id": archive_meta["source_attempt_id"],
                "mesh_sha256": archive_meta["source_mesh_sha256"],
            },
            "archive": archive_meta,
            "campaign_decision": {"decision_id": campaign_decision["decision_id"],
                                  "decision_sha256": campaign_decision["decision_sha256"]},
            "postprocessing_slot": {"postprocessing_jobs_used": 0,
                                    "postprocessing_jobs_max": candidate["numerical_conditions"]["postprocessing_jobs_max"]},
        }
        transition_source_sha = hashlib.sha256(json.dumps(
            source, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8")).hexdigest()
        transition["eligibility_source_sha256"] = transition_source_sha
    elif candidate["kind"] == "uniform_h_refinement":
        source = {"seed_cases": {f"VV3D-{candidate['family']}-L{level}": {
            "observables": {
                "displacement_l2_m_5_2": {"status": "AVAILABLE", "relative_error": 0.9 / (level ** 0.8)},
                "energy_error_norm_sqrt_j": {"status": "AVAILABLE", "relative_error": 0.8 / (level ** 0.2)},
            },
            "criteria": {name: {"status": "PASS"} for name in (
                "finite", "det_j_positive", "free_residual", "energy_identity", "force_closure",
                "moment_closure", "load_quadrature", "post_quadrature")},
        } for level in (1, 2, 3)}}
    else:
        source = {"load_quadrature_8_12": {
            "order_8": {"force_closure_n": [0, 0, 1.1], "moment_closure_nm": [0.5, 0, 0]},
            "order_12": {"force_closure_n": [0, 0, 1.0], "moment_closure_nm": [0.4, 0, 0]},
        }}
    eligibility_result = case_harness.evaluate_adaptive_eligibility(candidate_id, source)
    eligibility_record = {"schema": "qf-wp12-vv3d-adaptive-eligibility-v1",
                          "candidate_id": candidate_id, "source": source,
                          "result": eligibility_result}
    if candidate["execution_kind"] == "POSTPROCESS_ONLY":
        eligibility_record["transition_decision"] = transition
    eligibility_raw = (json.dumps(eligibility_record, sort_keys=True, separators=(",", ":"),
                                   allow_nan=False) + "\n").encode()
    eligibility_path = evidence_root / f"eligibility-{candidate_id}.json"
    eligibility_path.write_bytes(eligibility_raw)
    eligibility_sha = hashlib.sha256(eligibility_raw).hexdigest()
    if candidate["execution_kind"] == "FEM":
        transition["eligibility_sha256"] = eligibility_sha
    receipt = {
        "schema": case_harness.ADAPTIVE_RECEIPT_SCHEMA,
        "status": "RESERVED" if candidate["execution_kind"] == "FEM" else "POSTPROCESS_RESERVED",
        "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1", "candidate_id": candidate_id,
        "nodeid": candidate["nodeid"], "execution_kind": candidate["execution_kind"],
        "seed_case": candidate["seed_case"], **binding,
        "manifest_sha256": "a" * 64, "scientific_fingerprint": "b" * 64,
        "controller_fingerprint": "c" * 64, "authorization_id": "SYNTHETIC-ADAPT-AUTH-01",
        "campaign_decision": campaign_decision, "transition_decision": transition,
        "eligibility_record": {"path": str(eligibility_path), "sha256": eligibility_sha},
        "eligibility": {"status": "ELIGIBLE", "sha256": eligibility_sha},
        "evidence_root": str(evidence_root), "allowed_evidence_roots": [str(evidence_root)],
        "preflight_receipt_sha256": "e" * 64,
        "frozen_criteria": json.loads(
            case_harness._safe_catalog_file(candidate["criteria_path"]).read_bytes(),
        )["criteria"],
    }
    if candidate["execution_kind"] == "FEM":
        receipt.update({"attempt_reserved": True, "postprocessing_reserved": False,
                        "attempt_id": "SYNTHETIC-ADAPT-ATTEMPT-01",
                        "reservation_id": "SYNTHETIC-ADAPT-RESERVATION-01",
                        "selected_dofs": candidate["prepared_mesh"]["selected_dofs"],
                        "timeout_seconds": candidate["numerical_conditions"]["timeout_seconds_max"],
                        "attempt_number": 1, "max_attempts": 1})
    else:
        receipt.update({
            "attempt_reserved": False, "postprocessing_reserved": True,
            "postprocessing_job_id": source["postprocessing_job_id"],
            "source_manifest_sha256": archive_meta["source_manifest_sha256"],
            "source_run_receipt_sha256": source["seed_case"]["source_run_receipt_sha256"],
            "postprocessing_jobs_used_before": 0, "postprocessing_jobs_used_after": 1,
            "postprocessing_jobs_max": candidate["numerical_conditions"]["postprocessing_jobs_max"],
            "archive": {key: value for key, value in archive_meta.items() if key != "status"},
        })
    manifest = {
        "schema": "qf-wp12-vv3d-adaptive-execution-manifest-v1",
        **{key: receipt[key] for key in (
            "campaign_id", "candidate_id", "nodeid", "execution_kind", "seed_case",
            "catalog_sha256", "candidate_sha256", "mesh_sha256", "criteria_sha256",
            "rule_sha256", "source_hashes",
        )},
        "authorization_id": receipt["authorization_id"],
        "scientific_fingerprint": receipt["scientific_fingerprint"],
        "controller_fingerprint": receipt["controller_fingerprint"],
        "campaign_decision": receipt["campaign_decision"],
        "transition_decision": receipt["transition_decision"],
        "execution_authorized": True, "do_not_execute": False,
        "frozen_criteria": receipt["frozen_criteria"],
        "frozen_criteria_sha256": hashlib.sha256(json.dumps(
            receipt["frozen_criteria"], sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode()).hexdigest(),
        "preflight_receipt_sha256": receipt["preflight_receipt_sha256"],
        "evidence_root": receipt["evidence_root"],
    }
    if candidate["execution_kind"] == "FEM":
        manifest.update({"attempt_id": receipt["attempt_id"], "reservation_id": receipt["reservation_id"],
                         "selected_dofs": receipt["selected_dofs"], "timeout_seconds": receipt["timeout_seconds"],
                         "attempt_number": receipt["attempt_number"], "max_attempts": receipt["max_attempts"]})
    else:
        manifest.update({
            "postprocessing_job_id": receipt["postprocessing_job_id"],
            "source_run_receipt_sha256": receipt["source_run_receipt_sha256"],
            "postprocessing_jobs_used_before": receipt["postprocessing_jobs_used_before"],
            "postprocessing_jobs_used_after": receipt["postprocessing_jobs_used_after"],
            "postprocessing_jobs_max": receipt["postprocessing_jobs_max"],
        })
    manifest_raw = (json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    manifest_path = evidence_root / f"manifest-{candidate_id}.json"
    manifest_path.write_bytes(manifest_raw)
    receipt["manifest_path"] = str(manifest_path)
    receipt["manifest_sha256"] = hashlib.sha256(manifest_raw).hexdigest()
    return receipt


def _synthetic_qpost_wrapper_context(tmp_path: Path, *, archive_changes: dict | None = None) -> tuple[dict, Path]:
    candidate_id = "VV3D-ADAPT-TET4-QPOST"
    (tmp_path / "evidence").mkdir(exist_ok=True)
    _, candidates, _ = case_harness._adaptive_inventory()
    candidate = candidates[candidate_id]
    mesh = json.loads(case_harness._safe_catalog_file(candidate["prepared_mesh"]["path"]).read_bytes())
    archive = {
        "schema": "qf-wp12-vv3d-state-archive-v1",
        "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
        "case_id": candidate["seed_case"],
        "mesh_sha256": candidate["prepared_mesh"]["sha256"],
        "case_state": "OWNER_AUTHORIZED_EXECUTION",
        "execution_status": "COMPLETED_UNASSESSED",
        "manifest_sha256": "9" * 64,
        "attempt_id": "SYNTHETIC-SEED-ATTEMPT-01",
        "nodal_displacements_m": [0.0] * (3 * len(mesh["nodes_integer"])),
    }
    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id, qpost_archive=archive)
    archive_path = tmp_path / "evidence" / f"archive-{candidate_id}.json"
    if archive_changes:
        archive.update(archive_changes)
        archive_raw = (json.dumps(archive, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
        archive_path.write_bytes(archive_raw)
    receipt_path = tmp_path / "synthetic-adaptive-runner-receipt.json"
    receipt_raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    receipt_path.write_bytes(receipt_raw)
    return ({
        "QF_DEV_VV3D_ADAPTIVE_CANDIDATE_ID": candidate_id,
        "QF_DEV_TARGET_NODEID": candidate["nodeid"],
        "QF_DEV_VV3D_ADAPTIVE_RECEIPT_PATH": str(receipt_path),
        "QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256": hashlib.sha256(receipt_raw).hexdigest(),
        "QF_DEV_EVIDENCE_ROOT": str(tmp_path / "evidence"),
    }, archive_path)


def _mock_qpost_quadrature(monkeypatch) -> None:
    from experiments.wp12_vv3d_adaptive import field_error_draft

    monkeypatch.setattr(field_error_draft, "integrated_errors", lambda prepared, displacement, *, order: {
        "displacement_relative_l2": 0.20 if order == 8 else 0.21,
        "energy_error_relative": 0.30 if order == 8 else 0.32,
        "stress_error_relative": 0.40 if order == 8 else 0.44,
        "scalar_energy_j": 0.8 if order == 8 else 0.9,
    })


def _set_synthetic_qpost_env(monkeypatch, context: dict[str, str]) -> None:
    for name, value in context.items():
        monkeypatch.setenv(name, value)


def _set_synthetic_adaptive_env(monkeypatch, candidate_id: str, receipt_path: Path, receipt_raw: bytes) -> None:
    _, candidates, _ = case_harness._adaptive_inventory()
    receipt = json.loads(receipt_raw)
    monkeypatch.setenv("QF_DEV_VV3D_ADAPTIVE_CANDIDATE_ID", candidate_id)
    monkeypatch.setenv("QF_DEV_TARGET_NODEID", candidates[candidate_id]["nodeid"])
    monkeypatch.setenv("QF_DEV_VV3D_ADAPTIVE_RECEIPT_PATH", str(receipt_path))
    monkeypatch.setenv("QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256", hashlib.sha256(receipt_raw).hexdigest())
    monkeypatch.setenv("QF_DEV_EVIDENCE_ROOT", receipt["evidence_root"])


def _synthetic_qpost_sidecar(tmp_path: Path) -> Path:
    return (tmp_path / "evidence" / "VV3D-ADAPT-TET4-QPOST" / "SYNTHETIC-QPOST-JOB-01"
            / "observables.json")


def test_synthetic_adaptive_catalog_has_exact_twelve_candidate_nodeids() -> None:
    candidates, by_id, _ = case_harness._adaptive_inventory()
    catalog = json.loads(case_harness.ADAPTIVE_CATALOG_PATH.read_text(encoding="utf-8"))
    assert len(candidates) == len(by_id) == 12
    assert catalog["execution_authorized"] is False
    assert catalog["execution_state"] == "PREPARED_NOT_AUTHORIZED"
    for candidate in candidates:
        assert case_harness._adaptive_candidate_nodeid(candidate) == candidate["nodeid"]
        assert candidate["nodeid_status"] == "REGISTERED_PREPARED_NOT_AUTHORIZED"
        assert candidate["status"] == "PREPARED_NOT_AUTHORIZED"
        assert case_harness._adaptive_bindings(candidate)["mesh_sha256"] == candidate["prepared_mesh"]["sha256"]


def test_synthetic_adaptive_receipt_binds_candidate_rule_decisions_and_sources(tmp_path) -> None:
    candidate_id = "VV3D-ADAPT-TET4-QPOST"
    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id)
    verified = case_harness.validate_adaptive_runner_receipt(candidate_id, receipt)
    assert verified["candidate_id"] == candidate_id
    assert verified["transition_decision"]["candidate_id"] == candidate_id
    assert verified["campaign_decision"]["catalog_sha256"] == receipt["catalog_sha256"]

    receipt["rule_sha256"] = "0" * 64
    with pytest.raises(PermissionError, match="candidate/nodeid/mesh/rule/sources"):
        case_harness.validate_adaptive_runner_receipt(candidate_id, receipt)


def test_synthetic_adaptive_receipt_requires_authorization_and_raw_manifest_binding(tmp_path) -> None:
    candidate_id = "VV3D-ADAPT-TET4-QPOST"
    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id)
    missing_auth = dict(receipt)
    missing_auth.pop("authorization_id")
    with pytest.raises(PermissionError, match="authorization_id"):
        case_harness.validate_adaptive_runner_receipt(candidate_id, missing_auth)

    manifest_path = Path(receipt["manifest_path"])
    manifest_path.write_bytes(manifest_path.read_bytes() + b"tampered")
    with pytest.raises(PermissionError, match="raw manifest SHA-256"):
        case_harness.validate_adaptive_runner_receipt(candidate_id, receipt)


@pytest.mark.parametrize("path_kind", ["eligibility", "archive", "manifest"])
def test_synthetic_adaptive_receipt_rejects_evidence_paths_outside_allowed_roots(tmp_path, path_kind) -> None:
    candidate_id = "VV3D-ADAPT-TET4-QPOST"
    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id)
    outside = tmp_path / f"outside-{path_kind}.json"
    if path_kind == "eligibility":
        outside.write_bytes(Path(receipt["eligibility_record"]["path"]).read_bytes())
        receipt["eligibility_record"]["path"] = str(outside)
        reason = "eligibility record path is outside"
    elif path_kind == "archive":
        outside.write_bytes(b"synthetic archived-state placeholder")
        receipt["archive"]["path"] = str(outside)
        reason = "QPOST archive path is outside"
    else:
        outside.write_bytes(Path(receipt["manifest_path"]).read_bytes())
        receipt["manifest_path"] = str(outside)
        reason = "manifest path is outside"
    with pytest.raises(PermissionError, match=reason):
        case_harness.validate_adaptive_runner_receipt(candidate_id, receipt)


@pytest.mark.parametrize("field", ["source_attempt_id", "source_mesh_sha256"])
def test_synthetic_qpost_receipt_rejects_archive_source_mismatch(tmp_path, field) -> None:
    candidate_id = "VV3D-ADAPT-TET4-QPOST"
    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id)
    receipt["archive"][field] = (
        "SYNTHETIC-OTHER-ATTEMPT" if field == "source_attempt_id" else "0" * 64
    )
    with pytest.raises(PermissionError, match="QPOST receipt does not bind an archived state"):
        case_harness.validate_adaptive_runner_receipt(candidate_id, receipt)


def test_synthetic_adaptive_receipt_rejects_evidence_root_outside_allowlist(tmp_path) -> None:
    candidate_id = "VV3D-ADAPT-TET4-QPOST"
    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id)
    outside_root = tmp_path / "outside-root"
    outside_root.mkdir()
    receipt["evidence_root"] = str(outside_root)
    with pytest.raises(PermissionError, match="evidence root is not an allowed"):
        case_harness.validate_adaptive_runner_receipt(candidate_id, receipt)


def test_synthetic_adaptive_runner_rejects_controller_evidence_root_mismatch(tmp_path, monkeypatch) -> None:
    context, _archive_path = _synthetic_qpost_wrapper_context(tmp_path)
    _set_synthetic_qpost_env(monkeypatch, context)
    outside_root = tmp_path / "wrong-controller-root"
    outside_root.mkdir()
    monkeypatch.setenv("QF_DEV_EVIDENCE_ROOT", str(outside_root))
    with pytest.raises(PermissionError, match="differs from the controller assignment"):
        case_harness.require_adaptive_runner_receipt("VV3D-ADAPT-TET4-QPOST")


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20"])
@pytest.mark.parametrize("kind", ["H1", "QLOAD"])
def test_synthetic_adaptive_fem_entrypoint_refuses_missing_receipt_before_worker(
    tmp_path, monkeypatch, family, kind,
) -> None:
    from experiments.wp12_vv3d_adaptive import load_assembly_draft

    candidate_id = f"VV3D-ADAPT-{family}-{kind}"
    _, candidates, _ = case_harness._adaptive_inventory()
    monkeypatch.setenv("QF_DEV_VV3D_ADAPTIVE_CANDIDATE_ID", candidate_id)
    monkeypatch.setenv("QF_DEV_TARGET_NODEID", candidates[candidate_id]["nodeid"])
    monkeypatch.delenv("QF_DEV_VV3D_ADAPTIVE_RECEIPT_PATH", raising=False)
    monkeypatch.delenv("QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256", raising=False)
    monkeypatch.setattr(case_harness, "_run_prospective_case_with_context",
                        lambda *args, **kwargs: pytest.fail("common FEM worker reached without a receipt"))
    monkeypatch.setattr(load_assembly_draft, "assemble_body_load",
                        lambda *args, **kwargs: pytest.fail("load adapter reached without a receipt"))
    with pytest.raises(PermissionError, match="receipt context is missing"):
        case_harness.run_registered_adaptive_fem_candidate(candidate_id)


@pytest.mark.parametrize("family", ["TET4", "TET10", "HEX8", "HEX20"])
@pytest.mark.parametrize("kind", ["H1", "QLOAD"])
def test_synthetic_adaptive_fem_entrypoint_rejects_tampered_receipt_before_worker(
    tmp_path, monkeypatch, family, kind,
) -> None:
    from experiments.wp12_vv3d_adaptive import load_assembly_draft

    candidate_id = f"VV3D-ADAPT-{family}-{kind}"
    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id)
    receipt_path = tmp_path / "adaptive-runner-receipt.json"
    receipt_raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    receipt_path.write_bytes(receipt_raw + b"tampered")
    _set_synthetic_adaptive_env(monkeypatch, candidate_id, receipt_path, receipt_raw)
    monkeypatch.setattr(case_harness, "_run_prospective_case_with_context",
                        lambda *args, **kwargs: pytest.fail("common FEM worker reached with a tampered receipt"))
    monkeypatch.setattr(load_assembly_draft, "assemble_body_load",
                        lambda *args, **kwargs: pytest.fail("load adapter reached with a tampered receipt"))
    with pytest.raises(PermissionError, match="raw SHA-256 mismatch"):
        case_harness.run_registered_adaptive_fem_candidate(candidate_id)


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [("selected_dofs", 1), ("timeout_seconds", 1), ("attempt_number", 2)],
)
def test_synthetic_adaptive_fem_entrypoint_rejects_budget_mismatch_before_worker(
    tmp_path, monkeypatch, field, wrong_value,
) -> None:
    from experiments.wp12_vv3d_adaptive import load_assembly_draft

    candidate_id = "VV3D-ADAPT-TET4-QLOAD"
    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id)
    receipt[field] = wrong_value
    receipt_path = tmp_path / "adaptive-runner-receipt.json"
    receipt_raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    receipt_path.write_bytes(receipt_raw)
    _set_synthetic_adaptive_env(monkeypatch, candidate_id, receipt_path, receipt_raw)
    monkeypatch.setattr(case_harness, "_run_prospective_case_with_context",
                        lambda *args, **kwargs: pytest.fail("common FEM worker reached with a budget mismatch"))
    monkeypatch.setattr(load_assembly_draft, "assemble_body_load",
                        lambda *args, **kwargs: pytest.fail("load adapter reached with a budget mismatch"))
    with pytest.raises(PermissionError, match="reserved exact attempt"):
        case_harness.run_registered_adaptive_fem_candidate(candidate_id)


def test_synthetic_adaptive_worker_persists_sidecar_with_faked_solver_and_load_hooks(
    tmp_path, monkeypatch,
) -> None:
    import solveur.api.public as public_api
    from experiments.wp12_vv3d_adaptive import field_error_draft, load_assembly_draft, metrics, oracle

    candidate_id = "VV3D-ADAPT-TET4-QLOAD"
    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id)
    receipt_path = tmp_path / "adaptive-runner-receipt.json"
    receipt_raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    receipt_path.write_bytes(receipt_raw)
    _set_synthetic_adaptive_env(monkeypatch, candidate_id, receipt_path, receipt_raw)
    calls = {"load_adapter": 0, "model_factory": 0, "solver": 0}

    class SyntheticVector(list):
        def tolist(self):
            return list(self)

    class SyntheticDofs:
        @staticmethod
        def index(node, dof):
            return 3 * node + {"UX": 0, "UY": 1, "UZ": 2}[dof]

    class SyntheticModel:
        @classmethod
        def from_raw(cls, **kwargs):
            calls["model_factory"] += 1
            instance = cls()
            instance.nodes = kwargs["nodes"]
            return instance

    class SyntheticResult:
        status = "SYNTHETIC_ONLY"
        audit = None

        def __init__(self, node_count):
            self.displacements = SyntheticVector([0.0] * (3 * node_count))
            self.dofs = SyntheticDofs()

    def fake_load_adapter(prepared, *, order, execution_context, permit_validator):
        assert order in (8, 12)
        assert permit_validator(execution_context) is True
        calls["load_adapter"] += 1
        return [0.0] * (3 * len(prepared["nodes_integer"]))

    def fake_solver(model):
        calls["solver"] += 1
        return SyntheticResult(len(model.nodes))

    monkeypatch.setattr(load_assembly_draft, "assemble_body_load", fake_load_adapter)
    monkeypatch.setattr(public_api, "FiniteElementModel", SyntheticModel)
    monkeypatch.setattr(public_api, "solve_model", fake_solver)
    monkeypatch.setattr(public_api, "recover_solid_stress_field", lambda model, displacements: {"elements": []})
    monkeypatch.setattr(metrics, "force_moment_balance", lambda coordinates, loads, reactions: {
        "force_closure_n": (0.0, 0.0, 0.0), "moment_closure_nm": (0.0, 0.0, 0.0),
    })
    monkeypatch.setattr(oracle, "exact_global_balance", lambda: {
        "body_force_n": (0.0, 0.0, 0.0), "body_moment_origin_nm": (0.0, 0.0, 0.0),
    })
    monkeypatch.setattr(oracle, "exact_energy_j", lambda: 1.0)
    monkeypatch.setattr(field_error_draft, "integrated_errors", lambda prepared, displacement, *, order: {
        "displacement_l2_m_5_2": 0.0, "displacement_relative_l2": 0.2,
        "energy_error_norm_sqrt_j": 0.0, "energy_error_relative": 0.3,
        "strain_error_l2_m_3_2": 0.0, "strain_error_relative": 0.4,
        "stress_error_l2_pa_m_3_2": 0.0, "stress_error_relative": 0.4,
        "scalar_energy_j": 1.0,
    })
    monkeypatch.setattr(case_harness, "evaluate_case_criteria", lambda payload, rules: {
        rule["id"]: {"status": "PASS", "classification": rule["classification"]}
        if rule["classification"] == "CASE_GATE"
        else {"status": "NOT_ASSESSED", "classification": rule["classification"]}
        for rule in rules
    })

    outcome = case_harness.run_registered_adaptive_fem_candidate(candidate_id)
    sidecar = Path(receipt["evidence_root"]) / candidate_id / receipt["attempt_id"] / "observables.json"
    saved = json.loads(sidecar.read_bytes())
    assert calls == {"load_adapter": 2, "model_factory": 1, "solver": 1}
    assert outcome["payload"]["execution"]["status"] == "COMPLETED_UNASSESSED"
    assert outcome["payload"]["execution"]["fem_started"] is True
    assert saved["mesh_sha256"] == receipt["mesh_sha256"]
    assert saved["runner_receipt_sha256"] == hashlib.sha256(receipt_raw).hexdigest()


def test_synthetic_adaptive_eligibility_uses_closed_transition_conditions() -> None:
    seed_cases = _synthetic_campaign_seed_cases()
    h1 = case_harness.evaluate_adaptive_eligibility(
        "VV3D-ADAPT-TET4-H1", {"seed_cases": seed_cases},
    )
    assert h1["status"] == "INELIGIBLE"
    assert h1["trigger"] == "NO_SLOPE_TRIGGER"

    below_floor = _synthetic_campaign_seed_cases(
        displacement_errors=(0.9, 0.5, 0.1), energy_errors=(0.8, 0.7, 0.6),
    )
    stopped = case_harness.evaluate_adaptive_eligibility(
        "VV3D-ADAPT-TET4-H1", {"seed_cases": below_floor},
    )
    assert stopped["status"] == "INELIGIBLE"
    assert stopped["reason"] == "CAMPAIGN_GATES_NOT_PASS"
    assert stopped["campaign_assessment"]["status"] == "FAIL"

    qload = case_harness.evaluate_adaptive_eligibility("VV3D-ADAPT-TET4-QLOAD", {
        "load_quadrature_8_12": {
            "order_8": {"force_closure_n": [0, 0, 1.1], "moment_closure_nm": [0.5, 0, 0]},
            "order_12": {"force_closure_n": [0, 0, 1.0], "moment_closure_nm": [0.4, 0, 0]},
        },
    })
    assert qload["status"] == "ELIGIBLE"
    missing = case_harness.evaluate_adaptive_eligibility("VV3D-ADAPT-TET4-QPOST", {})
    assert missing["status"] == "NOT_ASSESSABLE"
def test_synthetic_qpost_launch_eligibility_is_seed_archive_and_slot_only(tmp_path) -> None:
    candidate_id = "VV3D-ADAPT-TET4-QPOST"
    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id)
    record = json.loads(Path(receipt["eligibility_record"]["path"]).read_bytes())
    launch = case_harness.evaluate_adaptive_eligibility(candidate_id, record["source"])
    assert launch == record["result"]
    assert launch["status"] == "ELIGIBLE"
    assert launch["trigger"] == "SEED_PASS_ARCHIVE_BOUND_SLOT_UNUSED"
    assert "maximum_relative_change" not in launch
    _, candidates, _ = case_harness._adaptive_inventory()
    for candidate in candidates.values():
        if candidate["execution_kind"] == "POSTPROCESS_ONLY":
            condition = candidate["eligibility_condition"]
            assert "exact L3 seed PASS" in condition
            assert "evaluated only after the job" in condition
            assert "does not trigger launch or another case" in condition
            assert "changes by more than 1e-4" not in condition

    missing_archive = dict(record["source"])
    missing_archive.pop("archive")
    assert case_harness.evaluate_adaptive_eligibility(candidate_id, missing_archive)["status"] == "NOT_ASSESSABLE"
    spent_slot = dict(record["source"])
    spent_slot["postprocessing_slot"] = {"postprocessing_jobs_used": 1,
                                         "postprocessing_jobs_max": 1}
    assert case_harness.evaluate_adaptive_eligibility(candidate_id, spent_slot)["status"] == "INELIGIBLE"


def test_synthetic_qpost_processes_only_fabricated_archived_state(monkeypatch) -> None:
    from experiments.wp12_vv3d_adaptive import field_error_draft

    candidate_id = "VV3D-ADAPT-TET4-QPOST"
    candidate = case_harness._adaptive_inventory()[1][candidate_id]
    mesh = json.loads(case_harness._safe_catalog_file(candidate["prepared_mesh"]["path"]).read_bytes())
    archive = {
        "schema": "qf-wp12-vv3d-state-archive-v1",
        "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1",
        "case_id": candidate["seed_case"], "mesh_sha256": candidate["prepared_mesh"]["sha256"],
        "case_state": "OWNER_AUTHORIZED_EXECUTION", "execution_status": "COMPLETED_UNASSESSED",
        "manifest_sha256": "9" * 64, "attempt_id": "SYNTHETIC-SEED-ATTEMPT-01",
        "nodal_displacements_m": [0.0] * (3 * len(mesh["nodes_integer"])),
    }
    monkeypatch.setattr(field_error_draft, "integrated_errors", lambda prepared, displacement, *, order: {
        "displacement_relative_l2": 0.20 if order == 8 else 0.21,
        "energy_error_relative": 0.30 if order == 8 else 0.32,
        "stress_error_relative": 0.40 if order == 8 else 0.44,
        "scalar_energy_j": 0.8 if order == 8 else 0.9,
    })
    outcome = case_harness.process_archived_qpost(candidate_id, archive)
    assert outcome["status"] == "COMPLETED_UNASSESSED"
    assert outcome["criteria_status"] == "DIAGNOSTIC_UNQUALIFIED"
    assert outcome["triggered"] is True
    assert set(outcome["relative_changes"]) == {
        "displacement_relative_l2", "energy_error_relative", "stress_error_relative",
        "scalar_energy_relative_error",
    }


def test_synthetic_qpost_wrapper_accepts_exact_receipt_and_writes_sidecar(tmp_path, monkeypatch) -> None:
    context, _archive_path = _synthetic_qpost_wrapper_context(tmp_path)
    _set_synthetic_qpost_env(monkeypatch, context)
    _mock_qpost_quadrature(monkeypatch)

    bound = case_harness.require_adaptive_runner_receipt("VV3D-ADAPT-TET4-QPOST")
    assert bound["nodeid"] == context["QF_DEV_TARGET_NODEID"]
    result = case_harness.run_registered_qpost_candidate("TET4")
    sidecar = _synthetic_qpost_sidecar(tmp_path)
    saved = json.loads(sidecar.read_bytes())
    assert result["outcome"]["status"] == "COMPLETED_UNASSESSED"
    assert saved["execution"] == {
        "status": "COMPLETED_UNASSESSED", "attempt_reserved": False,
        "postprocessing_reserved": True, "fem_started": False,
    }
    assert saved["archive_sha256"] == bound["archive"]["sha256"]


def test_synthetic_qpost_wrapper_rejects_tampered_archive_and_preserves_error_sidecar(
    tmp_path, monkeypatch,
) -> None:
    context, archive_path = _synthetic_qpost_wrapper_context(tmp_path)
    _set_synthetic_qpost_env(monkeypatch, context)
    archive_path.write_bytes(archive_path.read_bytes() + b"tampered")

    with pytest.raises(PermissionError, match="archived-state SHA-256"):
        case_harness.run_registered_qpost_candidate("TET4")
    saved = json.loads(_synthetic_qpost_sidecar(tmp_path).read_bytes())
    assert saved["execution"]["status"] == "FAILED_OR_INCOMPLETE"
    assert saved["execution"]["fem_started"] is False
    assert saved["observables"]["qpost"]["status"] == "FAILED_OR_INCOMPLETE"


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [("attempt_id", "SYNTHETIC-OTHER-ATTEMPT"), ("mesh_sha256", "0" * 64)],
)
def test_synthetic_qpost_wrapper_rejects_wrong_archive_source_and_preserves_sidecar(
    tmp_path, monkeypatch, field, wrong_value,
) -> None:
    context, _archive_path = _synthetic_qpost_wrapper_context(
        tmp_path, archive_changes={field: wrong_value},
    )
    _set_synthetic_qpost_env(monkeypatch, context)

    with pytest.raises(PermissionError, match="archived-state SHA-256 mismatch"):
        case_harness.run_registered_qpost_candidate("TET4")
    saved = json.loads(_synthetic_qpost_sidecar(tmp_path).read_bytes())
    assert saved["execution"]["status"] == "FAILED_OR_INCOMPLETE"
    assert saved["observables"]["qpost"]["error_type"] == "PermissionError"


def test_synthetic_qpost_wrapper_refuses_duplicate_sidecar_without_overwrite(tmp_path, monkeypatch) -> None:
    context, _archive_path = _synthetic_qpost_wrapper_context(tmp_path)
    _set_synthetic_qpost_env(monkeypatch, context)
    _mock_qpost_quadrature(monkeypatch)
    case_harness.run_registered_qpost_candidate("TET4")
    sidecar = _synthetic_qpost_sidecar(tmp_path)
    original = sidecar.read_bytes()

    with pytest.raises(FileExistsError):
        case_harness.run_registered_qpost_candidate("TET4")
    assert sidecar.read_bytes() == original
