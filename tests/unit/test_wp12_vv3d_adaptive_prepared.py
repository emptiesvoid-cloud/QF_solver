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


def _synthetic_adaptive_receipt(tmp_path: Path, candidate_id: str) -> dict:
    _, candidates, catalog_sha = case_harness._adaptive_inventory()
    candidate = candidates[candidate_id]
    binding = case_harness._adaptive_bindings(candidate)
    if candidate["kind"] == "uniform_h_refinement":
        source = {"seed_cases": {f"VV3D-{candidate['family']}-L{level}": {
            "observables": {
                "displacement_l2_m_5_2": {"status": "AVAILABLE", "relative_error": 0.9 / (level ** 0.8)},
                "energy_error_norm_sqrt_j": {"status": "AVAILABLE", "relative_error": 0.8 / (level ** 0.2)},
            },
            "criteria": {name: {"status": "PASS"} for name in (
                "finite", "det_j_positive", "free_residual", "energy_identity", "force_closure",
                "moment_closure", "load_quadrature", "post_quadrature")},
        } for level in (1, 2, 3)}}
    elif candidate["kind"] == "body_load_quadrature_escalation":
        source = {"load_quadrature_8_12": {
            "order_8": {"force_closure_n": [0, 0, 1.1], "moment_closure_nm": [0.5, 0, 0]},
            "order_12": {"force_closure_n": [0, 0, 1.0], "moment_closure_nm": [0.4, 0, 0]},
        }}
    else:
        source = {"quadrature_relative_difference": {"value": {
            "displacement_relative_l2": 0.2, "energy_error_relative": 0.2,
            "stress_error_relative": 0.2, "scalar_energy_relative_error": 0.2,
        }}}
    eligibility_result = case_harness.evaluate_adaptive_eligibility(candidate_id, source)
    eligibility_raw = (json.dumps({"schema": "qf-wp12-vv3d-adaptive-eligibility-v1",
                                   "candidate_id": candidate_id, "source": source,
                                   "result": eligibility_result}, sort_keys=True, separators=(",", ":"),
                                  allow_nan=False) + "\n").encode()
    eligibility_path = tmp_path / f"eligibility-{candidate_id}.json"
    eligibility_path.write_bytes(eligibility_raw)
    eligibility_sha = hashlib.sha256(eligibility_raw).hexdigest()
    transition = {
        "status": "APPROVED", "decision_id": "SYNTHETIC-TRANSITION-01",
        "decision_sha256": "d" * 64, "source_case_id": candidate["seed_case"],
        "candidate_id": candidate_id, "eligibility_sha256": eligibility_sha,
    }
    receipt = {
        "schema": case_harness.ADAPTIVE_RECEIPT_SCHEMA,
        "status": "RESERVED" if candidate["execution_kind"] == "FEM" else "POSTPROCESS_RESERVED",
        "campaign_id": "WP12-VV3D-ADAPTIVE-20261029-R1", "candidate_id": candidate_id,
        "nodeid": candidate["nodeid"], "execution_kind": candidate["execution_kind"],
        "seed_case": candidate["seed_case"], **binding,
        "manifest_sha256": "a" * 64, "scientific_fingerprint": "b" * 64,
        "controller_fingerprint": "c" * 64, "authorization_id": "SYNTHETIC-ADAPT-AUTH-01",
        "campaign_decision": {"status": "APPROVED", "decision_id": "SYNTHETIC-CAMPAIGN-01",
                              "decision_sha256": "f" * 64, "catalog_sha256": catalog_sha},
        "transition_decision": transition,
        "eligibility_record": {"path": str(eligibility_path), "sha256": eligibility_sha},
        "eligibility": {"status": "ELIGIBLE", "sha256": eligibility_sha},
        "evidence_root": "synthetic/evidence",
    }
    if candidate["execution_kind"] == "FEM":
        receipt.update({"attempt_reserved": True, "postprocessing_reserved": False,
                        "attempt_id": "SYNTHETIC-ADAPT-ATTEMPT-01"})
    else:
        receipt.update({
            "attempt_reserved": False, "postprocessing_reserved": True,
            "postprocessing_job_id": "SYNTHETIC-QPOST-JOB-01", "source_manifest_sha256": "9" * 64,
            "archive": {"path": "synthetic/archive.json", "sha256": "8" * 64,
                        "source_case_id": candidate["seed_case"],
                        "source_mesh_sha256": candidate["prepared_mesh"]["sha256"],
                        "source_manifest_sha256": "9" * 64, "source_attempt_id": "SYNTHETIC-SEED-ATTEMPT-01"},
        })
    return receipt


def _synthetic_qpost_wrapper_context(tmp_path: Path, *, archive_changes: dict | None = None) -> tuple[dict, Path]:
    candidate_id = "VV3D-ADAPT-TET4-QPOST"
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
    archive.update(archive_changes or {})
    archive_path = tmp_path / "synthetic-state-archive.json"
    archive_raw = (json.dumps(archive, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    archive_path.write_bytes(archive_raw)

    receipt = _synthetic_adaptive_receipt(tmp_path, candidate_id)
    receipt["evidence_root"] = str(tmp_path / "evidence")
    receipt["archive"] = {
        "path": str(archive_path),
        "sha256": hashlib.sha256(archive_raw).hexdigest(),
        "source_case_id": candidate["seed_case"],
        "source_mesh_sha256": candidate["prepared_mesh"]["sha256"],
        "source_manifest_sha256": receipt["source_manifest_sha256"],
        "source_attempt_id": "SYNTHETIC-SEED-ATTEMPT-01",
    }
    receipt_path = tmp_path / "synthetic-adaptive-runner-receipt.json"
    receipt_raw = (json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode()
    receipt_path.write_bytes(receipt_raw)
    return ({
        "QF_DEV_VV3D_ADAPTIVE_CANDIDATE_ID": candidate_id,
        "QF_DEV_TARGET_NODEID": candidate["nodeid"],
        "QF_DEV_VV3D_ADAPTIVE_RECEIPT_PATH": str(receipt_path),
        "QF_DEV_VV3D_ADAPTIVE_RECEIPT_SHA256": hashlib.sha256(receipt_raw).hexdigest(),
    }, archive_path)


def _mock_qpost_quadrature(monkeypatch) -> None:
    from experiments.wp12_vv3d_adaptive import field_error_draft

    monkeypatch.setattr(field_error_draft, "integrated_errors", lambda prepared, displacement, *, order: {
        "displacement_relative_l2": 0.20 if order == 8 else 0.21,
        "energy_error_relative": 0.30 if order == 8 else 0.32,
        "stress_error_relative": 0.40 if order == 8 else 0.44,
    })
    monkeypatch.setattr(case_harness, "_archived_scalar_energy", lambda prepared, displacement, order:
                        0.8 if order == 8 else 0.9)


def _set_synthetic_qpost_env(monkeypatch, context: dict[str, str]) -> None:
    for name, value in context.items():
        monkeypatch.setenv(name, value)


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


def test_synthetic_adaptive_eligibility_uses_closed_transition_conditions() -> None:
    seed_cases = {}
    for level, (u, energy) in enumerate(((0.9, 0.8), (0.5, 0.7), (0.1, 0.6)), 1):
        case_id = f"VV3D-TET4-L{level}"
        seed_cases[case_id] = {
            "observables": {"displacement_l2_m_5_2": {"status": "AVAILABLE", "relative_error": u},
                            "energy_error_norm_sqrt_j": {"status": "AVAILABLE", "relative_error": energy}},
            "criteria": {name: {"status": "PASS"} for name in (
                "finite", "det_j_positive", "free_residual", "energy_identity", "force_closure",
                "moment_closure", "load_quadrature", "post_quadrature")},
        }
    h1 = case_harness.evaluate_adaptive_eligibility("VV3D-ADAPT-TET4-H1", {"seed_cases": seed_cases})
    assert h1["status"] == "ELIGIBLE"

    qload = case_harness.evaluate_adaptive_eligibility("VV3D-ADAPT-TET4-QLOAD", {
        "load_quadrature_8_12": {
            "order_8": {"force_closure_n": [0, 0, 1.1], "moment_closure_nm": [0.5, 0, 0]},
            "order_12": {"force_closure_n": [0, 0, 1.0], "moment_closure_nm": [0.4, 0, 0]},
        },
    })
    assert qload["status"] == "ELIGIBLE"
    missing = case_harness.evaluate_adaptive_eligibility("VV3D-ADAPT-TET4-QPOST", {})
    assert missing["status"] == "NOT_ASSESSABLE"


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
    })
    monkeypatch.setattr(case_harness, "_archived_scalar_energy", lambda prepared, displacement, order:
                        0.8 if order == 8 else 0.9)
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

    with pytest.raises(PermissionError, match="archive contents differ"):
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
