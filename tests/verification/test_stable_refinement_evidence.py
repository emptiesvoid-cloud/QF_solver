"""Regression checks for the <=1% stable-refinement campaigns."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]


def test_orthotropic_convergence_cg_setup_is_explicitly_spd_and_compact() -> None:
    from solveur.verification.orthotropic_convergence import _setup

    setup = _setup("TET4", "cg")
    analysis = setup["analysis"]
    assert analysis["method"] == "cg"
    assert analysis["parameters"]["assume_spd"] is True
    assert analysis["parameters"]["spd_dense_check_max_dofs"] == 0
    assert analysis["parameters"]["preconditioner"] == "jacobi"


def test_tet10_stable_refinement_is_under_one_percent() -> None:
    summary = json.loads(
        (ROOT / "qualification/vnv/tet10_stable_refinement/reference/summary.json").read_text(
            encoding="utf-8"
        )
    )
    bending = summary["bending"]["families"]["TET10"]
    assert len(bending["levels"]) == 6
    assert bending["finest_response_error"] <= 0.01
    assert bending["maximum_free_relative_residual"] <= 1.0e-8


def test_tet4_petsc_refined_probe_records_progress_without_false_promotion() -> None:
    campaign = ROOT / "qualification/vnv/tet4_structured_petsc_refined_003"
    summary = json.loads((campaign / "summary.json").read_text(encoding="utf-8"))
    row = summary["rows"][0]
    assert summary["status"] == "WARNING"
    assert row["elements"] == 3_072_000
    assert row["dofs"] == 1_579_923
    assert row["relative_error"] == pytest.approx(0.012176443672321737)
    assert row["relative_residual"] <= 1.0e-8
    assert (campaign / "vnv_manifest.json").is_file()
    assert (campaign / "level_40/model.h5").is_file()


def test_tet4_corrected_same_mesh_tet10_probe_separates_element_error() -> None:
    path = ROOT / "qualification/vnv/tet4_tet10_corrected_reference_002/summary.json"
    summary = json.loads(path.read_text(encoding="utf-8"))
    fine = summary["rows"][-1]
    assert summary["study_id"] == "VNV-TET4-TET10-3D-REFERENCE-CORRECTED-002"
    assert summary["discretization"] == {
        "decomposition": "centered",
        "load_distribution": "surface_consistent",
        "same_mesh_tet4_tet10": True,
    }
    assert fine["tet10_reference_error"] <= 0.01
    assert fine["tet4_tet10_difference"] > 0.01
    assert fine["tet4_residual"] <= 1.0e-8
    assert (path.parent / "vnv_manifest.json").is_file()


def test_mitc4_code_aster_refinement_is_under_one_percent() -> None:
    summary = json.loads(
        (
            ROOT
            / "qualification/vnv/external/code_aster_mitc4_conical_cutout_refinement/reference/summary.json"
        ).read_text(encoding="utf-8")
    )
    fine = summary["rows"][-1]
    assert len(summary["rows"]) == 5
    assert fine["vector_difference"] <= 0.01
    assert fine["reaction_resultant_difference"] <= 0.01


def test_mitc4_modal_refinement_is_under_one_percent() -> None:
    summary = json.loads(
        (
            ROOT
            / "qualification/vnv/external/code_aster_modal_refinement_048/reference/summary.json"
        ).read_text(encoding="utf-8")
    )
    assert summary["model"]["mesh"] == [48, 48]
    assert summary["model"]["compared_mode_count"] == 10
    assert max(summary["metrics"]["qf_code_aster_frequency_differences"]) <= 0.01
    assert min(summary["metrics"]["qf_code_aster_mac"].values()) >= 0.99


def test_mitc4_harmonic_refinement_has_three_levels_and_final_one_percent() -> None:
    summary = json.loads(
        (
            ROOT
            / "qualification/vnv/external/mitc4_harmonic_refinement_005/reference/summary.json"
        ).read_text(encoding="utf-8")
    )
    assert len(summary["rows"]) == 3
    assert summary["rows"][-1]["mesh_size"] == 16
    assert summary["rows"][-1]["max_primary_error"] <= 0.01
    assert any(row["max_primary_error"] > 0.01 for row in summary["rows"][:-1])


def test_tet10_newmark_refinement_has_final_increment_under_one_percent() -> None:
    evidence = json.loads(
        (
            ROOT
            / "qualification/maturity_evidence_0_2_1/tet10_dynamic_refinement_001.json"
        ).read_text(encoding="utf-8")
    )
    assert evidence["time_level_count"] == 4
    assert evidence["final_relative_rms_error"] <= 0.01
    assert evidence["final_adjacent_time_refinement_error"] <= 0.01
    assert evidence["all_levels_time_refinement_error_max"] > 0.01


def test_orthotropic_dynamic_refinement_respects_one_percent_gate() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/orthotropic.json").read_text(encoding="utf-8")
    )
    modal = evidence["scopes"]["orthotropic-solid-modal"]
    transient = evidence["scopes"]["orthotropic-solid-transient-dynamic"]
    assert modal["internal"]["mesh_level_count"] >= 4
    assert modal["internal"]["fine_theory_error"] <= 1.0e-2
    assert transient["internal"]["time_level_count"] >= 8
    assert transient["internal"]["time_refinement_error"] <= 1.0e-2
    assert transient["external_code_aster"]["newmark_history_relative_difference"] <= 1.0e-2
    assert (ROOT / "qualification/reviews/orthotropic_modal_owner_review_pending.json").is_file()
    assert (ROOT / "qualification/reviews/orthotropic_transient_dynamic_owner_review_pending.json").is_file()


def test_orthotropic_static_refinement_improves_tet4_but_keeps_stable_gate_closed() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/orthotropic.json").read_text(
            encoding="utf-8"
        )
    )
    static = evidence["scopes"]["orthotropic-solid-tet4-tet10"]["static"]
    assert static["tet4_convergence_level_count"] == 9
    assert static["tet4_final_deflection_error"] == 0.02828292499337792
    assert static["tet4_final_energy_error"] <= 0.03
    assert static["tet4_final_tip_increment"] > 0.01
    refined = ROOT / static["tet4_refined_campaign"]
    summary = json.loads(refined.read_text(encoding="utf-8"))
    assert summary["study_id"] == "VNV-ORTHOTROPIC-SOLID-CONVERGENCE-004"
    assert summary["qualification_interpretation"]["stable_one_percent_gate"] == "BLOCKED"
    assert (refined.parent / "report.md").is_file()
    assert (refined.parent / "orthotropic_convergence.png").stat().st_size > 0
    assert (ROOT / "output/pdf/orthotropic_static_refined_owner_review.pdf").stat().st_size > 0


def test_orthotropic_extended_tet4_refinement_records_the_one_percent_block() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/orthotropic.json").read_text(encoding="utf-8")
    )
    static = evidence["scopes"]["orthotropic-solid-tet4-tet10"]["static"]
    assert static["tet4_extended_level_count"] == 10
    assert static["tet4_extended_finest_deflection_error"] == 0.0132925457926133
    assert static["tet4_extended_finest_energy_error"] == 0.014478918348640086
    assert static["tet4_extended_stable_gate"] == "BLOCKED_OVER_1_PERCENT"
    summary_path = ROOT / static["tet4_extended_campaign"]
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["families"]["TET4"][-1]["elements"] == 290689
    assert (summary_path.parent / "orthotropic_convergence.png").stat().st_size > 0
    assert (ROOT / "docs/verification/orthotropic_static_extended_owner_review.md").is_file()
    assert (ROOT / "output/pdf/orthotropic_static_extended_owner_review.pdf").stat().st_size > 0


def test_orthotropic_large_cg_tet4_refinement_closes_one_percent_gate() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/orthotropic.json").read_text(encoding="utf-8")
    )
    static = evidence["scopes"]["orthotropic-solid-tet4-tet10"]["static"]
    assert static["tet4_large_cg_level_count"] == 11
    assert static["tet4_large_cg_finest_deflection_error"] <= 0.01
    assert static["tet4_large_cg_finest_energy_error"] <= 0.01
    assert static["tet4_large_cg_maximum_free_residual"] <= 1.0e-8
    assert static["tet4_large_cg_stable_gate"] == "PASS_UNDER_ONE_PERCENT"
    summary_path = ROOT / static["tet4_large_cg_campaign"]
    assert summary_path.is_file()
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["families"]["TET4"][-1]["solver_backend"] == "large_vectorized_scipy_cg"
    assert (summary_path.parent / "vnv_manifest.json").is_file()


def test_refinement_review_artifacts_are_published() -> None:
    paths = (
        ROOT / "output/pdf/tet10_stable_refinement_owner_review.pdf",
        ROOT / "output/pdf/mitc4_static_code_aster_refinement_owner_review.pdf",
        ROOT / "output/pdf/mitc4_modal_refinement_owner_review.pdf",
        ROOT / "output/pdf/mitc4_harmonic_refinement_owner_review.pdf",
        ROOT / "qualification/vnv/tet10_stable_refinement/reference/vnv_manifest.json",
        ROOT
        / "qualification/vnv/external/code_aster_mitc4_conical_cutout_refinement/reference/vnv_manifest.json",
        ROOT
        / "qualification/vnv/external/code_aster_modal_refinement_048/reference/vnv_manifest.json",
        ROOT
        / "qualification/vnv/external/mitc4_harmonic_refinement_005/reference/vnv_manifest.json",
        ROOT
        / "qualification/vnv/external/tet10_dynamic_refinement_001/reference/evidence_manifest.json",
        ROOT / "output/pdf/tet10_dynamic_refinement_owner_review.pdf",
        ROOT / "output/pdf/orthotropic_modal_newmark_stable_owner_review.pdf",
    )
    assert all(path.is_file() and path.stat().st_size > 0 for path in paths)


def test_mitc4_laminate_over_one_percent_probe_remains_explicitly_blocked() -> None:
    evidence = json.loads(
        (
            ROOT
            / "qualification/maturity_evidence_0_2_1/mitc4_laminate_orientation_refinement_192.json"
        ).read_text(encoding="utf-8")
    )
    assert evidence["stable_gate_status"] == "BLOCKED_OVER_1_PERCENT"
    assert evidence["final_primary_relative_error"] > 0.01
    assert evidence["same_order_oracle_probe"]["status"] == "NOT_APPLICABLE_EXTERNAL_BACKEND"
    assert evidence["faceted_s8r_probe"]["final_vector_difference"] > 0.01
    report = (ROOT / "docs/verification/mitc4_same_order_oracle_probe.md").read_text(encoding="utf-8")
    assert "S4" in report
    assert "1 %" in report
    faceted_report = (ROOT / "docs/verification/mitc4_curved_faceted_s8r_probe.md").read_text(encoding="utf-8")
    assert "1,829575 %" in faceted_report
    assert (ROOT / "output/pdf/mitc4_laminate_orientation_refinement_owner_review.pdf").stat().st_size > 0


def test_mitc3_laminate_dynamic_strict_refinement_remains_blocked() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/mitc3_laminate.json").read_text(
            encoding="utf-8"
        )
    )
    strict = evidence["scopes"]["mitc3-laminate-dynamic"]["strict_refined_campaign"]
    assert strict["mesh_level_count"] == 4
    assert strict["fine_modal_frequency_error_max"] > 0.01
    assert strict["fine_newmark_history_error"] > 0.01
    assert strict["fine_harmonic_response_error"] > 0.01
    assert strict["stable_gate_status"] == "BLOCKED_OVER_1_PERCENT"
    summary_path = ROOT / strict["ledger"]
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["execution_status"] == "PASS_EXTERNAL_CORRELATION"
    assert (summary_path.parent / "report.md").is_file()
    assert (summary_path.parent / "mitc3_laminate_dynamic_refinement.png").stat().st_size > 0
    extended = evidence["scopes"]["mitc3-laminate-dynamic"]["strict_extended_campaign"]
    assert extended["mesh_level_count"] == 5
    assert extended["fine_modal_frequency_error_max"] > 0.01
    assert extended["fine_newmark_history_error"] > 0.01
    assert extended["fine_harmonic_response_error"] > 0.01
    extended_path = ROOT / extended["ledger"]
    extended_summary = json.loads(extended_path.read_text(encoding="utf-8"))
    assert extended_summary["mesh_levels"][-1]["nx"] == 32
    assert (extended_path.parent / "mitc3_laminate_dynamic_refinement.png").stat().st_size > 0
    assert (ROOT / "docs/verification/mitc3_laminate_dynamic_extended_owner_review.md").is_file()
    assert (ROOT / "output/pdf/mitc3_laminate_dynamic_extended_owner_review.pdf").stat().st_size > 0

    diagnostic = evidence["scopes"]["mitc3-laminate-dynamic"]["explicit_shear_correction_diagnostic"]
    assert diagnostic["same_transverse_shear_correction"] is True
    assert diagnostic["shear_correction_factor"] == pytest.approx(5.0 / 6.0)
    assert diagnostic["fine_modal_frequency_error_max"] > 0.01
    assert diagnostic["fine_newmark_history_error"] > 0.01
    assert diagnostic["fine_harmonic_response_error"] > 0.01
    diagnostic_path = ROOT / diagnostic["ledger"]
    assert diagnostic_path.is_file()


def test_mitc3_laminate_dynamic_dkt_thin_subscope_is_under_one_percent() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/mitc3_laminate.json").read_text(
            encoding="utf-8"
        )
    )
    scope = evidence["scopes"]["mitc3-laminate-dynamic"]
    dkt = scope["dkt_thin_limit_campaign"]
    assert dkt["status"] == "PASS_EXTERNAL_CORRELATION"
    assert dkt["external_modelisation"] == "DKT"
    assert dkt["fine_modal_error"] < 0.01
    assert dkt["fine_newmark_error"] < 0.01
    assert dkt["fine_harmonic_error"] < 0.01
    dkt_path = ROOT / dkt["ledger"]
    dkt_summary = json.loads(dkt_path.read_text(encoding="utf-8"))
    assert dkt_summary["mesh_level_count"] == 3
    assert dkt_summary["stable_gate_status"] == "PASS_FOR_THIN_PLANAR_SUBSCOPE"
    assert dkt_summary["mesh_levels"][-1]["external_solver"]["modelisation"] == "DKT"
    assert (dkt_path.parent / "report.md").is_file()
    assert (dkt_path.parent / "mitc3_laminate_dynamic_refinement.png").stat().st_size > 0


def test_mitc3_laminate_dynamic_mass_and_time_diagnostics_are_linked() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/mitc3_laminate.json").read_text(
            encoding="utf-8"
        )
    )
    scope = evidence["scopes"]["mitc3-laminate-dynamic"]
    assert scope["temporal_refinement_campaign"]["status"] == "PASS_INTERNAL"
    assert scope["external_temporal_diagnostic"]["status"] == "PASS_DIAGNOSTIC"
    assert scope["mass_quadrature_audit"]["status"] == "PASS_INDEPENDENT_QUADRATURE"


def test_mitc4_laminate_dynamic_extended_layups_keep_one_percent_gate_explicit() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/mitc4_laminate_dynamic.json").read_text(
            encoding="utf-8"
        )
    )
    extended = evidence["strict_extended_campaign"]
    assert extended["status"] == "BLOCKED_OVER_1_PERCENT"
    assert extended["layup_count"] == 3
    assert extended["maximum_primary_error_fraction"] > 0.01
    assert extended["layups"][0]["modal_error_fraction"] <= 0.01
    assert extended["layups"][1]["modal_error_fraction"] > 0.01
    assert extended["additional_attempt"]["status"] == "FAIL_NUMERICAL_RESIDUAL"
    refined = extended["refined_three_layup_campaign"]
    assert refined["status"] == "PASS_EXTERNAL_CORRELATION"
    assert refined["layup_count"] == 3
    assert refined["maximum_primary_error_fraction"] <= 0.01
    assert refined["maximum_modal_residual"] <= 1.0e-7
    series = extended["refined_mesh_series"]
    assert series["mesh_level_count"] == 3
    assert series["layup_count"] == 3
    assert series["final_level_maximum_primary_error_fraction"] <= 0.01
    assert (ROOT / "docs/verification/mitc4_laminate_dynamic_extended_owner_review.md").is_file()
    assert (ROOT / "output/pdf/mitc4_laminate_dynamic_extended_owner_review.pdf").stat().st_size > 0


def test_mitc4_laminate_planar_subscope_has_three_loadings_under_one_percent() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/mitc4_laminate_static_planar.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["promotion_target"] == "stable"
    assert evidence["domain"]["loading_count"] >= 3
    assert evidence["primary_observables"]["maximum_primary_error"] <= 0.01
    assert evidence["invariants"]["qf_code_aster_relative_difference"] <= 0.01
    assert evidence["excluded_probes"]["curved_oblique_orientation"]["status"] == "OUTSIDE_STABLE_SUBSCOPE"
    assert (ROOT / "docs/verification/mitc4_laminate_static_planar_stable_owner_review.md").is_file()
    assert (ROOT / "output/pdf/mitc4_laminate_static_planar_stable_owner_review.pdf").stat().st_size > 0


def test_mitc3_curved_laminate_extended_campaign_is_under_one_percent_before_owner_decision() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/mitc3_laminate.json").read_text(
            encoding="utf-8"
        )
    )
    campaign = evidence["scopes"]["mitc3-laminate-static-curved"]["strict_extended_campaign"]
    assert campaign["mesh_level_count"] == 7
    assert campaign["mixed_fine_vector_difference"] <= 0.01
    assert campaign["transverse_fine_vector_difference"] <= 0.01
    assert campaign["mixed_qf_final_mesh_increment"] <= 0.05
    assert campaign["transverse_external_final_mesh_increment"] <= 0.05
    assert campaign["stable_one_percent_gate"] == "PASS"
    assert campaign["convergence_gate"] == "PASS_AT_5_PERCENT_INCREMENT"
    assert (ROOT / "docs/verification/mitc3_laminate_curved_stable_owner_review.md").is_file()
    assert (ROOT / "output/pdf/mitc3_laminate_curved_stable_owner_review.pdf").stat().st_size > 0


def test_mitc3_curved_material_consistent_campaign_keeps_axial_gate_blocked() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/mitc3_laminate.json").read_text(encoding="utf-8")
    )
    campaign = evidence["scopes"]["mitc3-laminate-static-curved"]["material_consistent_campaign"]
    assert campaign["material_contract"]["constants_match"] is True
    assert campaign["load_family_count"] == 3
    assert campaign["stable_one_percent_gate"] == "PASS"
    assert campaign["convergence_gate"] == "BLOCKED_AXIAL_FINAL_INCREMENT"
    assert campaign["load_families"]["mixed"]["fine_vector_difference"] <= 0.01
    assert campaign["load_families"]["transverse"]["fine_vector_difference"] <= 0.01
    assert campaign["load_families"]["axial"]["fine_vector_difference"] <= 0.01
    axial = campaign["axial_refinement"]
    assert axial["fine_vector_difference"] > 0.01
    assert (ROOT / axial["campaign"]).is_file()


def test_tet4_total_lagrangian_independent_review_packet_is_ready_without_decision() -> None:
    review = json.loads(
        (
            ROOT
            / "qualification/reviews/tet4_total_lagrangian_independent_review_pending.json"
        ).read_text(encoding="utf-8")
    )
    assert review["promotion_target"] == "stable"
    assert review["decision"] is None
    assert review["technical_snapshot"]["refined_buckling_euler_error"] > 0.01
    assert review["technical_snapshot"]["refined_qf_calculix_difference"] <= 0.01
    packet = ROOT / "output/pdf/qf_solver_tet4_total_lagrangian_independent_review_0_2_1.pdf"
    assert packet.is_file() and packet.stat().st_size > 0


def test_tet10_j2_complex_refinement_passes_one_percent_gate_without_owner_promotion() -> None:
    evidence = json.loads(
        (ROOT / "qualification/maturity_evidence_0_2_1/tet10_j2.json").read_text(encoding="utf-8")
    )
    refined = evidence["campaigns"]["strict_refined_campaign"]
    assert refined["level_count"] == 3
    assert refined["fine_peeq_path_rms"] <= 0.01
    assert refined["fine_maximum_qf_residual"] <= 1.0e-7
    assert refined["stable_one_percent_gate"] == "PASS"
    ledger = ROOT / "qualification/vnv/external/code_aster_tet10_j2_complex_refinement_strict/reference/summary.json"
    summary = json.loads(ledger.read_text(encoding="utf-8"))
    assert summary["stable_gate"]["status"] == "PASS"
    assert (ledger.parent / "refinement_report.md").is_file()
    assert (ledger.parent / "refinement_convergence.png").stat().st_size > 0
    assert (ROOT / "docs/verification/tet10_j2_complex_refined_owner_review.md").is_file()
    assert (ROOT / "output/pdf/tet10_j2_complex_refined_owner_review.pdf").stat().st_size > 0
