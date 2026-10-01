from __future__ import annotations

import numpy as np

from scripts.prepare_wp08_area_supported_benchmark import MeshLevel, generate_preflight
from scripts.run_wp08_area_supported_m4_diagnostic_r1_5 import (
    ARTIFACT_ID,
    M4_LEVEL,
    _case_gates,
    _relative_delta,
)


def test_m4_preflight_is_the_natural_dyadic_extension() -> None:
    record = generate_preflight(MeshLevel("M4", 16, 8, 8))
    assert M4_LEVEL == MeshLevel("M4", 16, 8, 8)
    assert record["element_count"] == 6144
    assert record["body_node_count"] == 1377
    assert record["body_dofs"] == 4131
    assert record["contact_slave_node_count"] == 81
    assert record["contact_face_count"] == 128
    assert record["contact_support_affine_rank"] == 2
    assert record["contact_patch_area_m2"] == 0.5
    assert record["integrated_tangential_stiffness_N_per_m"] == 1_333_350.0
    assert np.isclose(record["total_volume_m3"], 1.0)


def test_m4_diagnostic_gate_requires_expected_stick_state_and_eight_steps() -> None:
    body = np.asarray([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.5]])
    payload = {
        "solver": {
            "converged": True,
            "contact": {
                "contacts": [
                    {"active": True, "slave_node": 0, "tangential_state": "stick"},
                    {"active": True, "slave_node": 1, "tangential_state": "stick"},
                    {"active": True, "slave_node": 2, "tangential_state": "stick"},
                ],
                "load_steps": [{} for _ in range(8)],
            },
        }
    }
    gates = _case_gates(payload, "stick_target", body, (0, 1, 2), {0: 1.0, 1: 1.0, 2: 1.0})
    assert gates["status"] == "PASS_DIAGNOSTIC_GATES"
    assert gates["active_support_affine_rank"] == 2


def test_m4_wrong_terminal_state_fails_closed() -> None:
    body = np.asarray([[0.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 0.5]])
    payload = {
        "solver": {
            "converged": True,
            "contact": {
                "contacts": [
                    {"active": True, "slave_node": 0, "tangential_state": "stick"},
                    {"active": True, "slave_node": 1, "tangential_state": "stick"},
                    {"active": True, "slave_node": 2, "tangential_state": "stick"},
                ],
                "load_steps": [{} for _ in range(8)],
            },
        }
    }
    gates = _case_gates(payload, "slip_target", body, (0, 1, 2), {0: 1.0, 1: 1.0, 2: 1.0})
    assert gates["status"] == "FAIL_CLOSED_DIAGNOSTIC_GATE"
    assert gates["gates"]["expected_terminal_tangential_state"] is False


def test_relative_delta_uses_symmetric_norm_denominator() -> None:
    delta = _relative_delta(np.asarray([3.0, 4.0]), np.asarray([0.0, 4.0]))
    assert delta["absolute_l2"] == 3.0
    assert delta["relative_l2"] == 0.6


def test_runner_is_explicitly_diagnostic_only() -> None:
    assert ARTIFACT_ID.endswith("R1.5-M4")
