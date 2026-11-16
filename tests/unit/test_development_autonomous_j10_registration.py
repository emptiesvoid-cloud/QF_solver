"""Unit checks for the isolated J10 development-runner registration."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from scripts import development_autonomous as runner


def test_j10_scope_is_bound_to_exact_nodes_one_thread_and_private_namespace(tmp_path: Path) -> None:
    expected = (
        "tests/verification/test_j10_tet10_fixed_excitation.py::test_j10_tet10_same_physical_excitation_time_mesh_study",
        "tests/verification/test_j10_hex8_j7_geometry.py::test_j10_hex8_j7_domain_preserving_distortion",
        "tests/verification/test_j10_tet10_modal_smoke.py::test_j10_tet10_modal_route_smoke",
    )
    assert runner.J10_NODEIDS == expected
    assert runner.J10_ATTEMPT_LIMITS == {
        expected[0]: 1,
        expected[1]: 3,
        expected[2]: 2,
    }
    assert runner.J10_BUDGETS == {
        "timeout_seconds": 1800,
        "rss_soft_limit_mib": 2048,
        "process_tree_limit": 4,
        "output_total_limit_mib": 8,
        "output_stream_limit_mib": 4,
        "temporary_limit_mib": 512,
        "archive_size_limit_mib": 128,
    }
    assert all(value == "1" for value in runner.J10_THREAD_ENVIRONMENT.values())
    assert runner._series_root(tmp_path, "fem_exploratory", "j10") == tmp_path / "worktrees" / "j10"

    root = Path(__file__).resolve().parents[2]
    registration = json.loads((root / "research/j10/execution_scope_registration.json").read_text(encoding="utf-8"))
    assert registration["allowed_nodeids"] == list(expected)
    assert registration["attempt_limit_per_nodeid"] == 1
    assert registration["attempt_limits_per_nodeid"] == runner.J10_ATTEMPT_LIMITS
    assert set(registration["family_contracts"]) == {
        "research/j10_transient/contracts/tet10_fixed_excitation_contract.json",
        "research/j10_hex8/contracts/hex8_j7_distortion_contract.json",
        "research/j10_hex8/contracts/hex8_j7_distortion_corrective_contract.json",
        "research/j10_hex8/contracts/hex8_j7_distortion_corrective_contract_003.json",
        "research/j10_modal/contracts/tet10_modal_route_smoke_contract.json",
        "research/j10_modal/contracts/tet10_modal_route_smoke_corrective_contract.json",
    }
    for relative in registration["family_contracts"]:
        contract = json.loads((root / relative).read_text(encoding="utf-8"))
        assert contract["execution"]["attempts"] == 1
        assert contract["execution"]["budgets"]["timeout_seconds"] == runner.J10_BUDGETS["timeout_seconds"]


def test_j10_hex8_corrective_contract_binds_sources_and_archived_inputs() -> None:
    root = Path(__file__).resolve().parents[2]
    relative = "research/j10_hex8/contracts/hex8_j7_distortion_corrective_contract_003.json"
    contract = json.loads((root / relative).read_text(encoding="utf-8"))
    contract_source_commit = "2999fb980ccfd3b7fe97cb724b1be43330507879"
    assert contract["contract_id"] == "J10-HEX8-J7-DOMAIN-PRESERVING-DISTORTION-CORRECTIVE-003"
    assert contract["execution"]["attempt_id"] == "J10-HEX8-J7-DISTORTION-ATTEMPT-003"
    for item in contract["source_identity"]:
        source = subprocess.check_output(["git", "show", f"{contract_source_commit}:{item['path']}"], cwd=root)
        assert hashlib.sha256(source).hexdigest() == item["canonical_sha256"]

    inputs = contract["inputs"]
    state = (root / inputs["j7_state_path"]).read_bytes()
    case_spec = (root / inputs["j7_case_spec_path"]).read_bytes().replace(b"\r\n", b"\n")
    historical_result = (root / inputs["historical_result_path"]).read_bytes()
    geometry_preflight = (root / inputs["geometry_preflight_result_path"]).read_bytes()
    assert hashlib.sha256(state).hexdigest() == inputs["j7_state_sha256_raw"]
    assert hashlib.sha256(case_spec).hexdigest() == inputs["j7_case_spec_sha256_canonical"]
    assert hashlib.sha256(historical_result).hexdigest() == inputs["historical_result_sha256_raw"]
    assert hashlib.sha256(geometry_preflight).hexdigest() == inputs["geometry_preflight_result_sha256_raw"]
    result_payload = json.loads(historical_result.decode("utf-8"))
    assert result_payload["scientific_criteria_status"] == "FAIL"
    assert result_payload["source"]["repository_head"] == "7b60400eeb34239e1cf639dc7e92f94118ca57bc"


def test_j10_modal_corrective_contract_binds_the_fixed_result_interface() -> None:
    root = Path(__file__).resolve().parents[2]
    relative = "research/j10_modal/contracts/tet10_modal_route_smoke_corrective_contract.json"
    contract = json.loads((root / relative).read_text(encoding="utf-8"))
    assert contract["contract_id"] == "J10-TET10-MODAL-ROUTE-SMOKE-CORRECTIVE-002"
    assert contract["supersedes"]["attempt_id"] == "J10-TET10-MODAL-ROUTE-SMOKE-ATTEMPT-001"
    assert contract["supersedes"]["execution_status"] == "PYTEST_FAILED"
    assert contract["supersedes"]["failure"] == "ModalResult exposes status; the original harness read nonexistent numerical_status."
    assert contract["execution"]["attempt_id"] == "J10-TET10-MODAL-ROUTE-SMOKE-ATTEMPT-002"
    assert contract["execution"]["attempt_number"] == 2
    assert contract["status_rules"]["PASS"].find("(30, 4)") >= 0
    assert contract["status_rules"]["INCONCLUSIVE"].find("INCONCLUSIVE") >= 0
    assert contract["status_rules"]["FAIL"].find("FAIL") >= 0
    prior_contract = subprocess.check_output(
        ["git", "show", f"2999fb980ccfd3b7fe97cb724b1be43330507879:{contract['supersedes']['contract_path']}"],
        cwd=root,
    )
    assert hashlib.sha256(prior_contract.replace(b"\r\n", b"\n")).hexdigest() == contract["supersedes"]["contract_canonical_sha256"]
    for item in contract["source_identity"]:
        actual = hashlib.sha256((root / item["path"]).read_bytes().replace(b"\r\n", b"\n")).hexdigest()
        assert actual == item["canonical_sha256"]


def test_j10_preflight_dispatches_to_its_own_exact_node_handler(monkeypatch) -> None:
    expected = {"state": "PREFLIGHT_PASS", "worktree_id": "j10"}
    monkeypatch.setattr(runner, "_preflight_j10_pytest", lambda target, preflight_id: expected)
    result = runner.preflight_pytest(
        "j10",
        runner.J10_NODEIDS[0],
        "pf-0123456789ab",
    )
    assert result is expected


def test_j10_environment_uses_approved_one_thread_configuration(tmp_path: Path) -> None:
    environment = runner.build_child_environment(
        tmp_path,
        base={},
        thread_environment=runner.J10_THREAD_ENVIRONMENT,
    )
    assert all(environment[name] == "1" for name in runner.J10_THREAD_ENVIRONMENT)
    assert environment["QF_DEVELOPMENT_AUTONOMOUS"] == "1"
