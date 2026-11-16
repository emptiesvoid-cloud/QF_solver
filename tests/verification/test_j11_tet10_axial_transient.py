"""J11 guided axial-bar transient against an independent continuum solution."""

from __future__ import annotations

import math

from research.j11_transient.tet10_axial_transient import (
    CHECKPOINT_STRIDE,
    MESH_LEVELS,
    TIME_STEPS_S,
    run_study,
)


def test_j11_tet10_axial_bar_time_mesh_and_animation() -> None:
    result = run_study()
    assert result["execution_status"] == "COMPLETED_EXPLORATORY"
    assert result["independent_reference"]["type"] == "continuum fixed-free axial-bar modal series"
    assert result["independent_reference"]["scope"].startswith("independent of QF M/K assembly")
    assert result["model"]["newmark"] == {
        "beta": 0.25,
        "gamma": 0.5,
        "rayleigh_alpha_s_inv": 0.0,
        "rayleigh_beta_s": 0.0,
    }
    assert [row["cells_x"] for row in result["mesh_study"]["mesh_levels"]] == list(MESH_LEVELS)
    assert [row["dt_s"] for row in result["time_study"]["results"]] == list(TIME_STEPS_S)
    for row in result["mesh_study"]["mesh_levels"]:
        assert row["newmark_status"] == "PASS"
        assert row["probe_position_m"] == [1.0, 0.2, 0.2]
        assert math.isclose(row["consistent_nodal_force_sum_n"], 1.0, rel_tol=0.0, abs_tol=1.0e-13)
        assert row["minimum_corner_volume_m3"] > 0.0
        assert math.isfinite(row["maximum_dynamic_residual_n"])
    animation = result["animation"]
    assert animation["status"] == "GENERATED_FROM_DURABLE_QF_CHECKPOINTS"
    assert animation["checkpoint_stride_steps"] == CHECKPOINT_STRIDE
    assert animation["frame_count_including_initial_zero_state"] == 41
    assert animation["displacement_amplification"] == 1.0e8
    assert "tet10_axial_bar_animation.gif" in result["artifacts"]
    assert "tet10_axial_bar_states.npz" in result["artifacts"]
