"""Reproducibility check for the independent J5B modal post-processing."""

from __future__ import annotations

from scripts.j5c_modal_postprocess import OUTPUT_DIR, run_campaign


def test_j5c_archive_postprocess_and_ritz_reference() -> None:
    result = run_campaign(OUTPUT_DIR)

    assert result["classification"] == "DEVELOPMENT_DIAGNOSTIC_ONLY"
    assert result["status"] == "DIAGNOSTIC_ONLY"
    assert result["archived_attempt"]["campaign_status"] == "INCONCLUSIVE"
    assert result["archived_attempt"]["status_preserved"] is True
    assert result["archived_attempt"]["j5b_modal_validation_statuses"] == [
        "INCONCLUSIVE",
        "INCONCLUSIVE",
        "INCONCLUSIVE",
        "INCONCLUSIVE",
        "INCONCLUSIVE",
    ]
    checks = result["independent_checks"]
    assert checks["all_input_hashes_match_contract"] is True
    assert checks["all_meshes_structured_positive_area_and_correct_domain"] is True
    assert checks["j5b_nodal_mac_reproduced_within_1e_10"] is True
    assert checks["ritz_nested_basis_frequency_monotonicity_within_1e_8"] is True
    assert checks["eigenpair_residual"].startswith("NOT_RECOMPUTED")
    assert checks["mass_orthogonality"].startswith("NOT_RECOMPUTED")
    assert result["model"]["ritz_highest_system_dimension"] <= 931
    assert len(result["mesh_results"]) == 5
    for mesh in result["mesh_results"]:
        assert mesh["modal_validation_status"] == "INCONCLUSIVE"
        assert mesh["mesh_geometry"]["structured_geometry_ok"] is True
    for artifact in (
        "independent_check.json",
        "modal_comparison.csv",
        "ritz_convergence.csv",
        "frequency_comparison.png",
        "mode_shape_comparison.png",
        "README.md",
        "artifact_manifest.json",
        "sanitized_run_record.json",
    ):
        assert (OUTPUT_DIR / artifact).is_file()
