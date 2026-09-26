from __future__ import annotations

from scripts import run_wp08_area_supported_m4_diagnostic_r1_10 as m4
from scripts import run_wp08_area_supported_m4_slip_r1_12 as runner


def test_r1_12_contract_freezes_one_m4_slip_attempt() -> None:
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


def test_r1_12_preflight_is_the_frozen_m4_mesh() -> None:
    preflight = m4.generate_preflight(m4.M4_LEVEL)

    assert preflight["element_count"] == 6144
    assert preflight["body_node_count"] == 1377
    assert preflight["body_dofs"] == 4131
    assert preflight["contact_slave_node_count"] == 81
    assert preflight["contact_support_affine_rank"] == 2
    assert preflight["all_slave_nodes_project_inside_master_patch"] is True
