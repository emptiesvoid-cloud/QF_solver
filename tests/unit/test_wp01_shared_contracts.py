"""Declarative tests for the QF Solver 0.2.12 WP01 shared contracts.

These tests validate contract data only. They intentionally do not execute or
simulate any WP02-WP10 numerical implementation.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "qualification/0_2_12/wp01_shared_contracts.json"


def _contract() -> dict[str, object]:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_new_method_maturity_is_explicit_and_unknown_methods_fail_closed() -> None:
    contract = _contract()
    maturity = contract["method_aware_maturity"]
    assert maturity["unknown_or_unregistered_scope"] == "REJECT_UNREGISTERED_METHOD_SCOPE"
    assert maturity["numerical_pass_implies_qualification"] is False
    assert all(entry["maturity"] == "EXPERIMENTAL" for entry in maturity["new_0_2_12_methods"])
    assert maturity["no_implicit_inheritance_from"]


def test_direct_and_reduced_methods_have_distinct_qualification_scopes() -> None:
    contract = _contract()
    scopes = contract["qualification_scope"]["examples_that_must_remain_distinct"]
    assert ["harmonic_response", "direct_frequency"] in scopes
    assert ["harmonic_response", "modal_superposition"] in scopes
    assert ["transient_dynamic", "direct"] in scopes
    assert ["transient_dynamic", "modal_newmark"] in scopes
    assert contract["qualification_scope"]["missing_or_ambiguous_scope"] == "REJECT_FAIL_CLOSED"


def test_physical_operator_excitation_basis_and_execution_identities_are_separate() -> None:
    identities = _contract()["identities"]
    assert set(identities) == {
        "physical_identity",
        "operator_identity",
        "excitation_identity",
        "modal_basis_identity",
        "execution_identity",
    }
    assert identities["operator_identity"]["excludes"] == [
        "force values",
        "force phases",
        "time histories",
        "frequency sweep values",
    ]
    assert identities["excitation_identity"]["schema"] != identities["operator_identity"]["schema"]


def test_physical_identity_cannot_omit_concentrated_masses_or_springs() -> None:
    physical = _contract()["identities"]["physical_identity"]
    required = " ".join(physical["required_components"]).lower()
    assert "concentrated mass" in required
    assert "spring" in required
    assert physical["confirmed_legacy_finding"] == "NEW_MARK_PHYSICAL_IDENTITY_INCOMPLETE = CONFIRMED"
    assert "mass/spring-inclusive" in _contract()["checkpoint_and_migration"]["newmark_identity_requirement"]


def test_checkpoint_readability_does_not_imply_safe_resume() -> None:
    policy = _contract()["checkpoint_and_migration"]
    assert policy["principle"] == "READABLE != SAFE_TO_RESUME"
    assert policy["confirmed_legacy_finding"] == "NL_V1_TO_V2_MIGRATION_UNSAFE_CASE = CONFIRMED"
    assert policy["identity_missing_or_insufficient"] == {
        "safe_resume": "NO",
        "fail_closed": "YES",
        "action": "REFUSE_RESUME",
    }
    assert "Never rewrite historical checkpoint bytes" in policy["migration_policy"]


def test_rayleigh_and_prescribed_modal_damping_are_distinct() -> None:
    damping = _contract()["damping_semantics"]
    models = {model["id"]: model for model in damping["models"]}
    assert set(models) == {"rayleigh_physical_or_projected", "prescribed_modal_damping"}
    assert "C = alpha M + beta K" in models["rayleigh_physical_or_projected"]["definition"]
    modal = models["prescribed_modal_damping"]
    assert "diag(2*zeta_j*omega_j)" in modal["definition"]
    assert "Not a complete physical" in modal["physical_matrix_claim"]
    assert "basis rotation" in modal["degenerate_cluster_rule"]


def test_modal_basis_mutation_and_cluster_cut_are_fail_closed() -> None:
    basis = _contract()["identities"]["modal_basis_identity"]
    assert "invalidates" in basis["invalidation"]
    assert "REJECT_EXPLICITLY" in basis["clusters"]
    assert "no default" not in basis["cluster_threshold_policy"]
    assert "missing policy or threshold is a fail-closed precondition" in basis["cluster_threshold_policy"]


def test_excitation_contract_separates_real_space_and_complex_time_content() -> None:
    excitation = _contract()["excitation_contract"]
    assert excitation["spatial_temporal_separation"]["SPATIAL_LOAD_DISTRIBUTION"] == "REAL"
    assert excitation["harmonic"]["phasor_representation"] == {"real": "finite scalar", "imag": "finite scalar"}
    assert excitation["harmonic"]["response_convention"] == "response(t) = Re(U * exp(+i*omega*t))"
    assert excitation["harmonic"]["input_frequency"] == "Hz"
    assert excitation["harmonic"]["internal_frequency"] == "rad/s"
    assert "exactly once" in excitation["harmonic"]["conversion"]
    assert "reject" in excitation["legacy_compatibility"]
    assert "applied once" in excitation["factor_application"]


def test_base_motion_frames_use_full_mass_and_explicit_absolute_reconstruction() -> None:
    frames = _contract()["response_frames_and_base_motion"]
    assert frames["definitions"]["absolute_displacement"] == "u_abs = P q_rel + r_full*x_g"
    assert frames["definitions"]["base_force_reduced"] == "f_base,red = -P.T*M_full*r_full*a_g"
    assert "complete supported M_full" in frames["mass_ordering"]
    assert "rotational entries are zero" in frames["influence_vector"]
    assert "require x_g/v_g history" in frames["input_availability"]["base_acceleration_given"] or "require x_g/v_g history" in frames["input_availability"]["base_displacement_or_velocity"]


def test_reaction_availability_does_not_fabricate_physical_damping() -> None:
    reactions = _contract()["reaction_availability"]
    assert reactions["availability_enum"] == ["AVAILABLE", "UNAVAILABLE", "NOT_COMPUTED", "NOT_APPLICABLE"]
    assert any("prescribed modal damping" in condition for condition in reactions["unavailable_when"])
    assert "Never synthesize a physical C" in reactions["forbidden"]


def test_result_availability_is_explicit_and_nonexportable_data_is_not_blank() -> None:
    results = _contract()["result_availability"]
    assert results["availability_enum"] == ["AVAILABLE", "UNAVAILABLE", "NOT_COMPUTED", "NOT_APPLICABLE"]
    assert {"computed", "retained", "reconstructible", "exportable"}.issubset(
        set(results["per_quantity_fields"])
    )
    assert "explicit typed error/status" in results["export_rule"]


def test_serialization_preserves_legacy_semantics_and_versions_new_stress_data() -> None:
    serialization = _contract()["serialization_and_semantic_versioning"]
    assert serialization["new_result_envelope"] == {"schema_id": "qf-solver-result", "schema_version": 1}
    assert serialization["stress_metadata_fields"] == ["stress_measure", "stress_frame", "semantic_version"]
    assert "not proof" in serialization["legacy_second_piola_rule"]
    assert "never silently relabel" in serialization["legacy_second_piola_rule"]
    assert "never edit historical evidence in place" in serialization["old_result_migration"]


def test_nonlinear_findings_and_rescope_guard_remain_contractual_only() -> None:
    nonlinear = _contract()["nonlinear_contract_boundaries"]
    assert nonlinear["confirmed_findings"]["COROTATIONAL_SECOND_PIOLA_LABEL_INCORRECT"] == "CONFIRMED"
    assert nonlinear["confirmed_findings"]["COROTATIONAL_TANGENT_CENTRAL_DIFFERENCE"] == "CONFIRMED"
    assert nonlinear["confirmed_findings"]["COROTATIONAL_TANGENT_SYMMETRIZED"] == "CONFIRMED"
    assert nonlinear["confirmed_findings"]["COROTATIONAL_FD_STEP_ORIGIN_DEPENDENT"] == "CONFIRMED"
    assert nonlinear["confirmed_findings"]["HEX8_FORCE_EVAL_COUNT"] == 49
    assert nonlinear["confirmed_findings"]["HEX20_FORCE_EVAL_COUNT"] == 121
    assert "STOP, RECORD_LIMITATION, RESCOPE_REQUIRED" in nonlinear["wp08_wp09_rescope_rule"]
    assert "no constitutive, tangent or result-producing behavior changes" in nonlinear["wp01_effect"]


def test_new_api_is_additive_and_runtime_objects_are_not_model_json() -> None:
    compatibility = _contract()["api_and_backward_compatibility"]
    assert compatibility["new_methods_additive"] is True
    assert compatibility["legacy_defaults_changed"] is False
    assert compatibility["legacy_methods_require_new_fields"] is False
    assert "not embedded directly in JSON" in compatibility["model_serialization"]


def test_wp01_gate_status_does_not_close_future_formulation_or_numerical_gates() -> None:
    gates = _contract()["gate_status"]
    assert gates["QF0212_G01"] == "PASS"
    assert gates["QF0212_G02"] == "PASS"
    assert gates["QF0212_G03_DYN"] == "NOT_YET_APPLICABLE"
    assert gates["QF0212_G03_NL"] == "NOT_YET_APPLICABLE"
    assert gates["QF0212_G04_DYN"] == "NOT_YET_APPLICABLE"
    assert gates["QF0212_G04_NL"] == "NOT_YET_APPLICABLE"
    assert gates["QF0212_G05_RUNTIME_NON_REGRESSION"] == "NOT_YET_APPLICABLE"
    assert gates["QF0212_G06"] == "NOT_YET_APPLICABLE"
    assert gates["QF0212_G07"] == "NOT_YET_APPLICABLE"


def test_historical_statuses_and_wp_scope_are_preserved() -> None:
    contract = _contract()
    assert contract["historical_preservation"]["HISTORICAL_G03"] == "FAIL_PRESERVED"
    assert contract["historical_preservation"]["HISTORICAL_WP14"] == "HOLD_NOT_PROMOTED"
    assert contract["historical_preservation"]["WHOLE_REPOSITORY_ARCHIVE_CLEARED"] == "NO"
    assert contract["implementation_scope"]["runtime_solver_code_changed"] is False
    assert contract["implementation_scope"]["wp02_through_wp10_implemented"] is False
    assert contract["readiness"]["wp02_plus_started"] is False
