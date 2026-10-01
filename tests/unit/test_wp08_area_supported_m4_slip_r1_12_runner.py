from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts import run_wp08_area_supported_m4_diagnostic_r1_10 as m4
from scripts import run_wp08_area_supported_m4_slip_r1_12 as runner


@pytest.fixture
def isolated_contract_inputs(tmp_path: Path, monkeypatch) -> Path:
    """Provide synthetic contract inputs, never archived qualification evidence."""
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(runner, "_git", lambda *args: "fixture-branch" if args[0] == "branch" else "f" * 40)
    prior_path = tmp_path / m4.OUTPUT_REL / "contract.json"
    prior_path.parent.mkdir(parents=True)
    prior_bytes = json.dumps({
        "artifact_id": "FIXTURE_ONLY_NOT_EXECUTION_EVIDENCE",
        "mesh": {"fixture_only": True},
        "benchmark": {"case": "slip_target", "fixture_only": True},
        "diagnostic_gates": {"fixture_only": True},
    }).encode("utf-8")
    prior_path.write_bytes(prior_bytes)
    monkeypatch.setattr(runner, "OLD_M4_CONTRACT_SHA256", hashlib.sha256(prior_bytes).hexdigest())
    parent_path = tmp_path / runner.R1_11_ROOT_REL / "contract_r1_11_optimizer_contact_requalification.json"
    parent_path.parent.mkdir(parents=True)
    parent_path.write_text(json.dumps({
        "optimizer_stopping_policy": {"fixture_only": True},
    }), encoding="utf-8")
    document = tmp_path / runner.DOC_REL
    document.parent.mkdir(parents=True, exist_ok=True)
    document.write_text("Fixture contract document, not qualification evidence.\n", encoding="utf-8")
    return tmp_path


def test_r1_12_contract_freezes_one_m4_slip_attempt(isolated_contract_inputs: Path) -> None:
    parent = {"cases": {"M1/slip_target": {"status": "PASS_DIAGNOSTIC_GATES"}}}
    old_failure = {"classification": "FAIL_CLOSED"}
    inventory = {"src/solveur/contact/slip_root.py": "a" * 64}
    preflight = m4.generate_preflight(m4.M4_LEVEL)

    contract = runner._contract_payload(inventory, parent, old_failure, preflight)

    assert contract["execution"]["sequence"] == ["M4/slip_target"]
    assert contract["execution"]["attempts"] == 1
    assert contract["execution"]["overwrite_or_retry"] is False
    assert contract["execution"]["rerun_M1_M2_M3"] is False
    assert contract["execution"]["reference_or_replay"] is False
    assert contract["acceptance"]["physical_active_slip_root_tolerance"] == 1e-9
    assert contract["limitations"]["formal_wp08_qualification"] is False
    assert contract["frozen_physical_inputs"]["mesh"] == {"fixture_only": True}
    assert contract["frozen_physical_inputs"]["r1_11_optimizer_policy"] == {"fixture_only": True}


def test_r1_12_preflight_is_the_frozen_m4_mesh() -> None:
    preflight = m4.generate_preflight(m4.M4_LEVEL)

    assert preflight["element_count"] == 6144
    assert preflight["body_node_count"] == 1377
    assert preflight["body_dofs"] == 4131
    assert preflight["contact_slave_node_count"] == 81
    assert preflight["contact_support_affine_rank"] == 2
    assert preflight["all_slave_nodes_project_inside_master_patch"] is True


def test_real_contract_builder_still_refuses_missing_parent(isolated_contract_inputs: Path) -> None:
    path = isolated_contract_inputs / runner.R1_11_ROOT_REL / "contract_r1_11_optimizer_contact_requalification.json"
    path.unlink()
    with pytest.raises(FileNotFoundError):
        runner._contract_payload({}, {}, {}, {})


def test_real_contract_builder_still_refuses_wrong_parent_hash(isolated_contract_inputs: Path, monkeypatch) -> None:
    monkeypatch.setattr(runner, "OLD_M4_CONTRACT_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="physical-input contract hash mismatch"):
        runner._contract_payload({}, {}, {}, {})


def test_parent_json_validation_is_not_removed_with_unused_assignment(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    path = tmp_path / runner.R1_11_ROOT_REL / "contract.json"
    path.parent.mkdir(parents=True)
    path.write_text("not-json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        runner._r1_11_parent_evidence()
