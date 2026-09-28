from __future__ import annotations

import numpy as np
import pytest

from scripts import run_wp08_area_supported_m4_diagnostic_r1_10 as runner
from scripts.prepare_wp08_area_supported_benchmark import generate_preflight


def test_r1_10_parent_evidence_fails_closed_when_raw_cases_are_absent() -> None:
    with pytest.raises(FileNotFoundError, match="Incomplete R1.10 parent evidence"):
        runner._parent_evidence()


def test_m4_preflight_and_contract_are_diagnostic_only() -> None:
    preflight = generate_preflight(runner.M4_LEVEL)
    parent = {
        "cases_read_only": {"synthetic_unit_fixture": {"status": "NOT_QUALIFICATION_EVIDENCE"}},
        "source_bundle_sha256": "a" * 64,
    }
    contract = runner._contract_payload("0" * 64, parent)

    assert preflight["element_count"] == 6144
    assert preflight["body_node_count"] == 1377
    assert preflight["body_dofs"] == 4131
    assert preflight["node_count"] == 1381
    assert preflight["total_dofs_including_rigid_master_metadata"] == 4143
    assert preflight["contact_slave_node_count"] == 81
    assert preflight["contact_face_count"] == 128
    assert preflight["contact_support_affine_rank"] == 2
    assert preflight["all_slave_nodes_project_inside_master_patch"] is True
    assert preflight["contact_patch_area_m2"] == 0.5
    assert preflight["integrated_tangential_stiffness_N_per_m"] == 1_333_350.0
    assert contract["diagnostic_gates"]["mesh_refinement_threshold"] is None
    assert contract["limitations"]["formal_wp08_qualification"] is False
    assert contract["policy_context_only"]["governing_policy_enforced"] is False
    assert contract["parent_provenance"]["cases_read_only"]["synthetic_unit_fixture"]["status"] == (
        "NOT_QUALIFICATION_EVIDENCE"
    )


def test_m3_m4_comparison_is_descriptive_and_reproducible(tmp_path) -> None:
    coordinates = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    zeros = np.zeros((2, 3))
    active = np.asarray([True, False])
    areas = np.asarray([0.25, 0.25])
    paths = (tmp_path / "m3.npz", tmp_path / "m4.npz")
    for path in paths:
        np.savez_compressed(
            path,
            node_coordinates=coordinates,
            body_node_count=np.asarray([2]),
            displacement=zeros,
            contact_normal_force=zeros,
            contact_tangential_force_global=zeros,
            contact_active=active,
            contact_reference_area=areas,
        )

    comparison = runner._m3_m4_comparison(*paths)

    assert comparison["classification"] == "DESCRIPTIVE_ONLY_NO_FROZEN_MESH_THRESHOLD"
    assert comparison["common_node_displacement"]["relative_l2"] == 0.0
    assert comparison["active_area_fraction"] == {"M3": 0.5, "M4": 0.5}
