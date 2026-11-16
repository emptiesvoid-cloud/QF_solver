"""J10 fixed-physical-excitation TET10/Newmark exploratory study."""

from __future__ import annotations

import math

from research.j10_transient.tet10_fixed_excitation import (
    MESH_LEVELS,
    TIME_STEPS_S,
    run_study,
)


def test_j10_tet10_same_physical_excitation_time_mesh_study() -> None:
    result = run_study()
    assert result["execution_status"] == "COMPLETED_EXPLORATORY"
    assert result["excitation"]["same_physical_load_all_meshes"] is True
    assert result["excitation"]["same_physical_observation_times_all_meshes"] is True
    assert result["excitation"]["time_steps_s"] == list(TIME_STEPS_S)
    assert [tuple(level["cells"]) for level in result["mesh_levels"]] == list(MESH_LEVELS)
    assert [level["free_dof_count"] for level in result["mesh_levels"]] == [108, 216, 360, 600]
    for level in result["mesh_levels"]:
        assert level["minimum_tet_corner_volume_m3"] > 0.0
        assert level["load_position_m"] == [2.0, 0.2, 0.2]
        assert level["measurement_position_m"] == [1.0, 0.2, 0.2]
        assert level["assembled_force_resultant_n"] == [0.0, 0.0, -1.0]
        assert [row["time_step_s"] for row in level["time_levels"]] == list(TIME_STEPS_S)
        assert all(row["direct_status"] == "PASS" for row in level["time_levels"])
        assert all(math.isfinite(row["rms_normalized_by_global_oracle_peak"]) for row in level["time_levels"])
    assert result["normalization"]["global_oracle_peak_m"] > 0.0
    assert result["animation"]["status"] == "NOT_AVAILABLE"
    assert set(result["figures"]) == {
        "tet10_fixed_excitation_meshes.png",
        "tet10_fixed_excitation_time_refinement.png",
        "tet10_fixed_excitation_mesh_sensitivity.png",
    }
