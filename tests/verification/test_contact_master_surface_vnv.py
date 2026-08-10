"""V&V evidence for bounded initial master-surface selection."""

import json

from solveur.verification.contact_master_surface import MasterSurfaceContactCampaign


def test_master_surface_selection_is_closed_form_and_reviewable(tmp_path) -> None:
    summary = MasterSurfaceContactCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["results"]["selected_face_index"] == 1
    assert summary["updated_switch"]["selected_face_index"] == 1
    assert summary["updated_switch"]["search_iteration_count"] >= 2
    assert summary["folded_updated_switch"]["selected_face_index"] == 1
    assert summary["folded_updated_switch"]["search_iteration_count"] >= 2
    assert summary["folded_slave_patch"]["selected_face_indices"] == [1, 1, 1]
    assert summary["folded_slave_patch"]["max_gap_m"] < 1.0e-12
    assert (tmp_path / "master_surface_selection.png").stat().st_size > 1_000
    assert (tmp_path / "master_surface_updated_switch.png").stat().st_size > 1_000
    assert (tmp_path / "master_surface_folded_updated_switch.png").stat().st_size > 1_000
    assert json.loads((tmp_path / "summary.json").read_text(encoding="utf-8")) == summary
