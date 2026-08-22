"""Shared pytest policy for the optional controlled V&V evidence corpus."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "qualification" / "vnv"
GENERATED_DOCS_MANIFEST = ROOT / "docs" / "generated" / "docs_manifest.json"
OPTIONAL_MESH_TEST_MODULES = {
    "tests/unit/test_code_aster_tet10_dynamic.py",
    "tests/unit/test_code_aster_tet4_dynamic.py",
}

EVIDENCE_TESTS = {
    "tests/documentation/test_docs_generation.py::test_every_controlled_page_is_registered_with_consistent_review_fields",
    "tests/documentation/test_docs_generation.py::test_generated_manifest_hashes_and_images_are_valid",
    "tests/documentation/test_technical_content_closure.py::test_every_implemented_element_analysis_pair_has_an_explicit_oracle_decision",
    "tests/documentation/test_technical_content_closure.py::test_documented_gaps_are_never_relabelled_as_mechanical_passes",
    "tests/documentation/test_technical_content_closure.py::test_content_closure_publishes_tables_hashes_and_external_views",
    "tests/integration/test_demonstration_api.py::test_library_runs_documented_json_model_with_evidence",
    "tests/integration/test_p0_cli_contract.py::test_tet10_qualification_run_is_accepted_after_signed_review",
    "tests/integration/test_p0_cli_contract.py::test_tet10_engineering_run_is_accepted",
    "tests/integration/test_p0_cli_contract.py::test_evidence_propagates_tet10_qualification_acceptance",
    "tests/integration/test_p0_cli_contract.py::test_qualification_readiness_exit_codes_are_stable",
    "tests/integration/test_qualification_campaign.py::test_public_api_runs_official_qualification_campaign",
    "tests/integration/test_qualification_campaign.py::test_cli_runs_qualification_campaign",
    "tests/unit/test_calculix_curved_composite.py::test_controlled_curved_calculix_evidence_is_complete",
    "tests/unit/test_calculix_curved_orientation.py::test_controlled_curved_orientation_evidence_is_complete",
    "tests/unit/test_calculix_j2.py::test_controlled_calculix_input_requests_isotropic_hardening",
    "tests/unit/test_calculix_tet10_evidence.py::test_controlled_calculix_tet10_evidence_is_complete",
    "tests/unit/test_documentation_baseline.py::test_p0_documentation_baseline_declares_automatic_evidence_and_owner_review_blockers",
    "tests/unit/test_element_analysis_matrix.py::test_element_analysis_matrix_is_complete_and_references_existing_evidence",
    "tests/unit/test_element_analysis_matrix.py::test_linear_dynamic_closure_register_references_real_evidence",
    "tests/unit/test_external_correlation.py::test_official_abaqus_reference_is_controlled_and_monotone",
    "tests/unit/test_external_correlation.py::test_pinched_cylinder_external_comparison_passes",
    "tests/unit/test_external_correlation.py::test_nafems_13h_reference_has_exact_abaqus_model_contract",
    "tests/unit/test_external_correlation.py::test_nafems_13h_external_comparison_accepts_measured_qf_peak",
    "tests/unit/test_external_correlation.py::test_nafems_13h_external_comparison_rejects_nonfinite_metrics",
    "tests/unit/test_mitc4_modal_10k_runner.py::test_owner_review_figures_are_generated",
    "tests/unit/test_mitc4_modal_external.py::test_controlled_code_aster_modal_reference_passes",
    "tests/unit/test_mitc4_modal_review_record.py::test_mitc4_modal_scope_points_to_provisional_review",
    "tests/unit/test_mitc4_transient_review_record.py::test_mitc4_transient_scope_points_to_final_review",
    "tests/unit/test_orthotropic_external.py::test_controlled_external_evidence_is_complete",
    "tests/unit/test_tet10_mass_modal_evidence.py::test_controlled_tet10_mass_modal_load_evidence_passes",
    "tests/unit/test_tet10_near_incompressible.py::test_controlled_near_incompressible_characterization_passes",
    "tests/unit/test_tet10_review_record.py::test_tet10_scope_is_candidate_after_signed_self_review",
    "tests/unit/test_tet10_structural_evidence.py::test_controlled_tet10_structural_convergence_evidence_passes",
    "tests/unit/test_traceability.py::test_total_lagrangian_candidate_scope_has_complete_internal_evidence",
    "tests/unit/test_traceability.py::test_total_lagrangian_structural_v2_is_candidate_after_review",
    "tests/verification/test_j2_material_vnv.py::test_j2_material_campaign_passes_all_acceptance_checks",
    "tests/verification/test_j2_material_vnv.py::test_j2_material_campaign_writes_auditable_json_and_markdown",
    "tests/verification/test_j2_material_vnv.py::test_j2_cycle_contains_loading_unloading_and_reloading",
    "tests/verification/test_j2_material_vnv.py::test_j2_uniaxial_matches_bilinear_theory_and_published_abaqus_points",
    "tests/verification/test_mitc3_external_evidence.py::test_controlled_mitc3_code_aster_evidence_passes",
    "tests/verification/test_mitc3_external_evidence.py::test_controlled_mitc3_calculix_evidence_preserves_warning",
    "tests/verification/test_mitc3_external_evidence.py::test_controlled_mitc3_external_manifests_match_files",
    "tests/verification/test_mitc3_external_evidence.py::test_refined_curved_shell_evidence_is_controlled_and_converged",
    "tests/verification/test_mitc3_hemisphere_evidence.py::test_controlled_mitc3_hemisphere_correlation_passes_declared_limits",
    "tests/verification/test_mitc3_hemisphere_evidence.py::test_controlled_mitc3_hemisphere_code_aster_figures_are_readable",
    "tests/verification/test_mitc4_campaign.py::test_mitc4_quick_campaign_writes_reviewable_evidence",
    "tests/verification/test_mitc4_harmonic_broadband_vnv.py::test_mitc4_broadband_response_matches_complete_modal_oracle",
    "tests/verification/test_mitc4_harmonic_nafems_vnv.py::test_nafems_13h_external_harmonic_correlation_passes",
    "tests/verification/test_mitc4_harmonic_nafems_vnv.py::test_nafems_13h_evidence_contains_model_setup_figure",
    "tests/verification/test_mitc4_newmark_broadband_vnv.py::test_reduced_wideband_newmark_campaign_passes",
    "tests/verification/test_orthotropic_completion_vnv.py::test_controlled_orthotropic_convergence_evidence_is_complete",
    "tests/verification/test_orthotropic_completion_vnv.py::test_controlled_orthotropic_performance_evidence_is_complete",
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Skip only archive-backed checks when the optional evidence corpus is absent."""
    evidence_available = (
        os.environ.get("QF_SOLVER_RUN_EVIDENCE", "0") == "1"
        and EVIDENCE_ROOT.is_dir()
        and GENERATED_DOCS_MANIFEST.is_file()
    )
    mesh_available = _gmsh_available()
    evidence_marker = pytest.mark.skip(reason="optional controlled V&V evidence corpus is not installed")
    mesh_marker = pytest.mark.skip(reason="optional Gmsh dependency is not installed")
    for item in items:
        base_nodeid = item.nodeid.split("[", maxsplit=1)[0]
        module_path = base_nodeid.split("::", maxsplit=1)[0]
        if not evidence_available and base_nodeid in EVIDENCE_TESTS:
            item.add_marker(pytest.mark.evidence)
            item.add_marker(evidence_marker)
        if not mesh_available and module_path in OPTIONAL_MESH_TEST_MODULES:
            item.add_marker(mesh_marker)


def _gmsh_available() -> bool:
    try:
        import gmsh  # noqa: F401
    except (ImportError, OSError):
        return False
    return True
