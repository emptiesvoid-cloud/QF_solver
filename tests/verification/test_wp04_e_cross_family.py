"""Evidence-only checks for the frozen WP04-E G04-12 comparison."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, cast


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_9"


def _load(relative_path: str) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        json.loads((QUALIFICATION / relative_path).read_text(encoding="utf-8")),
    )


def _delta(first: float, second: float) -> float:
    return abs(first - second) / max(abs(first), abs(second), 1e-12)


def test_g04_12_is_evidence_only_and_preserves_governance_boundary() -> None:
    audit = _load("wp04e/g04_12_cross_family_audit.json")

    assert audit["audit_start_sha"] == "a4f8937919f5a008abbc15d0d404c47f09816459"
    assert audit["branch"] == "0.2.9-unified-nonlinear"
    assert audit["evidence_only"] is True
    assert audit["structural_solves_run"] is False
    assert audit["h4_run"] is False
    assert audit["petsc_run"] is False
    assert audit["full_test_suite_run"] is False
    assert audit["gate_decision"] == {
        "g04_10": "OWNER_APPROVED_PASS",
        "g04_11": "OWNER_APPROVED_PASS",
        "g04_12": "PASS_PENDING_OWNER_REVIEW",
        "wp04_points": "0/12",
        "validated_total": 29,
        "maturity_changed": False,
        "owner_review_required": True,
        "next_gate": "Independent WP04-F combined G04-01..G04-12 closure audit",
    }


def test_g04_12_recomputes_all_frozen_deltas_from_governing_source_records() -> None:
    audit = _load("wp04e/g04_12_cross_family_audit.json")
    tet_audit = _load("c2r6/frozen_threshold_audit.json")
    tet_campaign = _load("c2r6/campaign_result.json")
    hex_campaign = _load("wp04d/hex8_campaign_result.json")

    tet_audit_observables = cast(dict[str, Any], tet_audit["observables"])
    tet_campaign_cases = cast(dict[str, Any], tet_campaign["cases"])
    tet_source = cast(dict[str, Any], tet_campaign_cases["C2-M3"])["observables"]
    hex_cases = cast(dict[str, Any], hex_campaign["cases"])
    hex_source = cast(dict[str, Any], hex_cases["H3"])["observables"]

    # The frozen audit and its underlying C2R6 M3 result must agree exactly.
    tet_m3 = cast(dict[str, Any], tet_audit_observables["m3"])
    assert tet_m3["tip_displacement"] == tet_source["tip_displacement"]
    assert tet_m3["strain_energy"] == tet_source["strain_energy"]
    assert tet_m3["representative_sigma_xx"] == tet_source["representative_stress_sigma_xx"]

    source_values = {
        "displacement": (float(tet_source["tip_displacement"]), float(hex_source["tip_displacement"])),
        "reaction": (
            float(tet_source["equilibrium"]["reaction_resultant_norm"]),
            float(hex_source["equilibrium"]["reaction_resultant"][1]),
        ),
        "strain_energy": (float(tet_source["strain_energy"]), float(hex_source["strain_energy"])),
        "representative_sigma_xx": (
            float(tet_source["representative_stress_sigma_xx"]),
            float(hex_source["representative_stress_sigma_xx"]),
        ),
    }
    comparisons = cast(dict[str, Any], audit["comparisons"])

    for name, (tet4_value, hex8_value) in source_values.items():
        comparison = cast(dict[str, Any], comparisons[name])
        assert comparison["tet4"] == tet4_value
        assert comparison["hex8"] == hex8_value
        assert comparison["delta"] == _delta(tet4_value, hex8_value)
        assert comparison["status"] == "PASS"
        assert comparison["delta"] <= comparison["threshold"]

    assert comparisons["all_pass"] is True


def test_g04_12_physical_definition_and_provenance_checks_are_explicit() -> None:
    audit = _load("wp04e/g04_12_cross_family_audit.json")
    definitions = cast(dict[str, Any], audit["physical_definition_comparison"])

    for key in (
        "geometry",
        "material",
        "boundary_conditions",
        "load_resultant",
        "load_moment",
        "displacement_definition",
        "reaction_definition",
        "strain_energy_definition",
        "stress_region",
        "stress_weighting",
    ):
        assert definitions[key]["match"] is True
    assert definitions["all_required_matches"] is True

    load_disclosure = definitions["load_representation_disclosure"]
    assert load_disclosure["representation_difference_disclosed"] is True
    assert load_disclosure["physical_definition_mismatch"] is False

    provenance = cast(dict[str, Any], audit["provenance_checks"])
    assert all(
        value is True
        for key, value in provenance.items()
        if key.endswith("_approved")
        or key.startswith("same_")
        or key.startswith("no_")
        or key.endswith("_integrity_checked")
    )
    assert provenance["tet4_final_load_factor"] == 1.0
    assert provenance["hex8_final_load_factor"] == 1.0


def test_g04_12_source_file_hashes_and_carried_limitation_are_bound() -> None:
    audit = _load("wp04e/g04_12_cross_family_audit.json")
    sources = cast(dict[str, Any], audit["sources"])

    for family in ("tet4", "hex8"):
        source = cast(dict[str, Any], sources[family])
        for path_key, hash_key in (
            ("audit_path", "audit_sha256"),
            ("campaign_path", "campaign_sha256"),
            ("case_result_path", "case_result_sha256"),
        ):
            path = ROOT / source[path_key]
            assert path.is_file()
            assert hashlib.sha256(path.read_bytes()).hexdigest() == source[hash_key].lower()

    limitation = cast(list[dict[str, Any]], audit["carried_limitations"])[0]
    assert limitation["id"] == "HEX8_SMALL_LOAD_REACTION_SUPPORT"
    assert limitation["status"] == "LIMITATION_CARRIED_TO_WP04_F"
    assert limitation["reaction_relative_error"] > limitation["support_threshold"]
    assert limitation["g04_11_decision_changed"] is False
    assert limitation["g04_12_decision_changed"] is False


def test_g04_12_cross_family_observables_are_finite_and_within_envelope() -> None:
    audit = _load("wp04e/g04_12_cross_family_audit.json")
    for family in ("tet4", "hex8"):
        source = cast(dict[str, Any], audit["sources"])[family]
        observables = cast(dict[str, Any], source["raw_observables"])
        for key in (
            "tip_displacement",
            "reaction_resultant_norm",
            "strain_energy",
            "representative_sigma_xx",
            "minimum_det_f",
            "minimum_principal_stretch",
            "maximum_principal_stretch",
            "maximum_green_lagrange_norm",
        ):
            assert math.isfinite(float(observables[key]))
        assert observables["minimum_det_f"] >= 0.20
        assert observables["minimum_principal_stretch"] >= 0.75
        assert observables["maximum_principal_stretch"] <= 1.30
        assert observables["maximum_green_lagrange_norm"] <= 0.30
        assert source["final_load_factor"] == 1.0
