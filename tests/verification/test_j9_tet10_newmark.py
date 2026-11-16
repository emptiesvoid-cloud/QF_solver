"""One registered TET10 direct/modal Newmark transient study for J9."""

from __future__ import annotations

from research.j9_transient.tet10_newmark import run_transient_study


def test_j9_tet10_direct_and_modal_newmark_time_mesh_study() -> None:
    result = run_transient_study()
    assert result["execution_status"] == "COMPLETED_EXPLORATORY"
    assert len(result["mesh_levels"]) == 2
    assert all(level["element_count"] > 0 for level in result["mesh_levels"])
    assert all(level["minimum_tet_corner_volume_m3"] > 0.0 for level in result["mesh_levels"])
    assert all(level["assembled_load_resultant_n"] == [0.0, 0.0, -1.0] for level in result["mesh_levels"])
    assert all(len(level["time_levels"]) == 3 for level in result["mesh_levels"])
    assert result["modal_route_comparison"]["basis_is_full_order"]
    assert result["states_npz"]["sha256"]
    assert set(result["figures"]) == {"tet10_newmark_mesh.png", "tet10_newmark_history.png"}
