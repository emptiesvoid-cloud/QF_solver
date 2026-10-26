"""Synthetic tests for prospective planning rows; these never invoke FEM."""

from __future__ import annotations

from experiments.hex8_sri_equilibrium.campaign_planning import (
    iter_mesh_convergence_rows,
    iter_supplemental_validation_rows,
    write_mesh_convergence_matrix,
)


def test_prepared_mesh_matrix_has_sixty_paired_proposal_rows() -> None:
    rows = iter_mesh_convergence_rows()

    assert len(rows) == 60
    assert {row["campaign_status"] for row in rows} == {"PREPARED_NOT_AUTHORIZED"}
    assert {row["entry_status"] for row in rows} == {"PLANNED_NOT_IMPLEMENTED_OR_REGISTERED"}
    assert len({row["test_nodeid_proposal"] for row in rows}) == 60
    assert {row["formulation"] for row in rows} == {"hex8_standard", "sri_historical", "sri_corrected"}
    assert {row["poisson_ratio"] for row in rows} == {0.3, 0.45, 0.49, 0.499, 0.4999}


def test_mesh_matrix_counts_and_dof_maps_match_structured_grid_formula() -> None:
    rows = iter_mesh_convergence_rows()
    expected = {
        "4x2x2": (16, 45, 135, 27, 108),
        "8x4x4": (128, 225, 675, 75, 600),
        "16x8x8": (1024, 1377, 4131, 243, 3888),
        "32x16x16": (8192, 9537, 28611, 867, 27744),
    }

    for row in rows:
        assert (
            row["element_count"],
            row["node_count"],
            row["dof_count"],
            row["fixed_dof_count"],
            row["free_dof_count"],
        ) == expected[row["mesh_elements_xyz"]]
        assert row["max_attempts"] == 1
        assert row["threshold_status"] == "PROPOSAL_REQUIRES_OWNER_FREEZE_BEFORE_EXECUTION"


def test_matrix_writer_creates_only_proposal_csv(tmp_path) -> None:
    path = tmp_path / "NEXT_CAMPAIGN_MATRIX.csv"

    count = write_mesh_convergence_matrix(path)

    assert count == 60
    text = path.read_text(encoding="utf-8")
    assert "PREPARED_NOT_AUTHORIZED" in text
    assert "execution_authorized" not in text
    assert len(text.splitlines()) == 61


def test_supplemental_matrix_prepares_patch_geometry_global_and_spectral_cases() -> None:
    rows = iter_supplemental_validation_rows()

    assert len(rows) == 115
    assert {row["campaign_status"] for row in rows} == {"PREPARED_NOT_AUTHORIZED"}
    assert {row["study_family"] for row in rows} == {
        "analytic_patch_energy",
        "geometry_quality_screen",
        "local_element_stability_spectrum",
        "global_distortion_response",
    }
    assert len({row["test_nodeid_proposal"] for row in rows}) == 115
    assert all(row["max_attempts"] == 1 for row in rows)
    assert all(row["threshold_status"] == "PROPOSAL_REQUIRES_OWNER_FREEZE_BEFORE_EXECUTION" for row in rows)
