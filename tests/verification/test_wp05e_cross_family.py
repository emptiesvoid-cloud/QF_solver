"""Evidence-only verification of the WP05-E TET10/HEX20 comparison."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, cast

from scripts.wp05_cd_structural_harness import check_replay, evaluate_mesh_delta


ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION = ROOT / "qualification" / "0_2_9"
AUDIT_PATH = QUALIFICATION / "wp05e" / "wp05e_cross_family_audit.json"


def _load(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _relative_delta(first: float, second: float) -> float:
    return abs(first - second) / max(abs(first), abs(second), 1.0e-12)


def _vector_norm(value: list[float]) -> float:
    return math.sqrt(sum(float(component) ** 2 for component in value))


def _mesh_observables(result: dict[str, Any]) -> dict[str, Any]:
    observed = cast(dict[str, Any], result["observables"])
    return {
        "mean_end_displacement_y": observed["tip_displacement"],
        "clamp_reaction_resultant": observed["reaction_resultant"],
        "clamp_reaction_moment": observed["reaction_moment"],
        "strain_energy": observed["strain_energy"],
        "representative_sigma_xx": observed["representative_sigma_xx"],
    }


def _replay_observables(result: dict[str, Any]) -> dict[str, Any]:
    observed = cast(dict[str, Any], result["observables"])
    return {
        "mean_end_displacement_y": observed["tip_displacement"],
        "strain_energy": observed["strain_energy"],
        "representative_sigma_xx": observed["representative_sigma_xx"],
        "minimum_det_F": observed["minimum_detF"],
        "principal_stretch_min": observed["minimum_principal_stretch"],
        "principal_stretch_max": observed["maximum_principal_stretch"],
        "maximum_green_lagrange_strain_norm": observed["maximum_green_lagrange_norm"],
        "clamp_reaction_resultant": observed["reaction_resultant"],
        "clamp_reaction_moment": observed["reaction_moment"],
        "accepted_load_factor_history": result["accepted_load_factors"],
        "newton_iteration_count": result["newton_iterations"],
    }


def _c_result(level: str) -> dict[str, Any]:
    return _load(QUALIFICATION / "wp05c_formal_requalification" / "TET10" / level / "result.json")


def test_wp05e_is_evidence_only_and_requires_owner_review() -> None:
    audit = _load(AUDIT_PATH)
    governance = cast(dict[str, Any], audit["governance"])
    outcome = cast(dict[str, Any], audit["terminal_evaluation"])

    assert audit["status"] == "PASS_CANDIDATE_OWNER_REVIEW_REQUIRED"
    assert audit["phase"] == "CROSS_FAMILY_EVIDENCE_ONLY"
    assert governance["structural_solves_run_for_wp05e"] is False
    assert governance["production_mechanics_changed_in_wp05e"] is False
    assert governance["thresholds_changed"] is False
    assert governance["official_ledger_updated"] is False
    assert governance["official_total_before_owner_review"] == 58
    assert governance["full_repository_suite_run"] is False
    assert outcome["wp05e_candidate_points"] == "1/1"
    assert outcome["wp05e_official_points"] == "0/1_PENDING_OWNER_REVIEW"
    assert outcome["owner_review_required"] is True


def test_wp05c_h1_h2_h3_and_replay_prerequisites_pass() -> None:
    audit = _load(AUDIT_PATH)
    c_cases = {level: _c_result(level) for level in ("H1", "H2", "H3")}

    for level, result in c_cases.items():
        observed = cast(dict[str, Any], result["observables"])
        assert result["status"] == "PASS"
        assert result["family"] == "TET10"
        assert result["mesh_level"] == level
        assert len(result["accepted_load_factors"]) == 12
        assert result["accepted_load_factors"][-1] == 1.0
        assert result["fallback_count"] == 0
        assert result["load_check"]["status"] == "PASS"
        assert observed["envelope_status"] is True
        assert observed["force_equilibrium_relative"] <= 1.0e-8
        assert observed["moment_equilibrium_relative"] <= 1.0e-8

    mesh_delta = evaluate_mesh_delta(_mesh_observables(c_cases["H2"]), _mesh_observables(c_cases["H3"]))
    expected_mesh_delta = audit["prerequisites"]["wp05c"]["h2_to_h3_mesh_delta"]
    assert mesh_delta["status"] == expected_mesh_delta["status"] == "PASS"
    for metric, comparison in cast(dict[str, Any], expected_mesh_delta).items():
        if metric == "status":
            continue
        evaluated = cast(dict[str, Any], mesh_delta["results"])[metric]
        assert evaluated["status"] == "PASS"
        assert math.isclose(evaluated["relative_change"], comparison["delta"], rel_tol=1.0e-12, abs_tol=1.0e-18)
        assert evaluated["threshold"] == comparison["limit"]

    primary = c_cases["H1"]
    replay = _load(
        QUALIFICATION / "wp05c_formal_requalification_replay" / "TET10" / "H1" / "result.json"
    )
    replay_result = check_replay(_replay_observables(primary), _replay_observables(replay))
    assert replay["status"] == "PASS"
    assert replay_result["status"] == "PASS"
    assert replay_result["newton_iteration_count"]["first"] == replay_result["newton_iteration_count"]["second"]
    assert primary["raw_sha256"] == replay["raw_sha256"]


def test_wp05e_deltas_recompute_from_h3_raw_results() -> None:
    audit = _load(AUDIT_PATH)
    tet = _c_result("H3")
    hex20 = _load(
        QUALIFICATION / "wp05d_formal_requalification" / "production" / "HEX20" / "H3" / "result.json"
    )
    tet_observed = cast(dict[str, Any], tet["observables"])
    hex_observed = cast(dict[str, Any], hex20["observables"])
    comparisons = cast(dict[str, Any], audit["comparisons"])

    values = {
        "displacement": (float(tet_observed["tip_displacement"]), float(hex_observed["tip_displacement"])),
        "reaction_resultant": (
            _vector_norm(cast(list[float], tet_observed["reaction_resultant"])),
            _vector_norm(cast(list[float], hex_observed["reaction_resultant"])),
        ),
        "reaction_moment": (
            _vector_norm(cast(list[float], tet_observed["reaction_moment"])),
            _vector_norm(cast(list[float], hex_observed["reaction_moment"])),
        ),
        "strain_energy": (float(tet_observed["strain_energy"]), float(hex_observed["strain_energy"])),
        "representative_sigma_xx": (
            float(tet_observed["representative_sigma_xx"]),
            float(hex_observed["representative_sigma_xx"]),
        ),
    }
    for name, (tet_value, hex_value) in values.items():
        comparison = cast(dict[str, Any], comparisons[name])
        assert math.isclose(comparison.get("tet10", comparison.get("tet10_norm", comparison.get("tet10_common_historical"))), tet_value, rel_tol=0.0, abs_tol=1.0e-12)
        assert math.isclose(comparison.get("hex20", comparison.get("hex20_norm", comparison.get("hex20_common_historical"))), hex_value, rel_tol=0.0, abs_tol=1.0e-12)
        assert math.isclose(comparison["delta"], _relative_delta(tet_value, hex_value), rel_tol=1.0e-12, abs_tol=1.0e-18)
        assert comparison["delta"] <= comparison["threshold"]
        assert comparison["status"] == "PASS"
    assert comparisons["all_pass"] is True

    # The HEX20-only clipped-window observable is deliberately not the E stress comparator.
    assert hex20["candidate_observables"]["representative_sigma_xx"] == comparisons[
        "representative_sigma_xx"
    ]["hex20_candidate_window_sigma_xx_excluded"]
    assert hex20["candidate_observable_contract"]["formal_requalification"] is True
    assert hex20["candidate_observable_contract"]["claim_scope"].endswith("straight-sided affine HEX20")


def test_wp05e_provenance_physical_comparability_and_source_hashes_pass() -> None:
    audit = _load(AUDIT_PATH)
    sources = cast(dict[str, Any], audit["sources"])
    base_path = ROOT / sources["base_contract"]["path"]
    candidate_path = ROOT / sources["wp05d_candidate_contract"]["path"]
    base_contract = _load(base_path)
    candidate_contract = _load(candidate_path)
    tet = _c_result("H3")
    hex20 = _load(
        QUALIFICATION / "wp05d_formal_requalification" / "production" / "HEX20" / "H3" / "result.json"
    )
    comparison = cast(dict[str, Any], audit["physical_definition_comparison"])

    assert _sha256(base_path) == sources["base_contract"]["sha256"] == tet["contract_sha256"]
    assert _sha256(base_path) == hex20["historical_contract_sha256"]
    assert _sha256(candidate_path) == sources["wp05d_candidate_contract"]["sha256"]
    assert _sha256(candidate_path) == hex20["candidate_contract_sha256"]
    assert tet["source_sha"] == hex20["execution_sha"] == audit["provenance"]["execution_sha"]
    assert tet["governing_policy_digest"] == hex20["runtime_policy_binding_digest"]

    benchmark = cast(dict[str, Any], base_contract["benchmark"])
    physical_inputs = cast(dict[str, Any], candidate_contract["physical_inputs"])
    assert benchmark["geometry"] == physical_inputs["geometry"]
    assert {key: benchmark["material"][key] for key in ("E", "nu")} == physical_inputs["material"]
    assert benchmark["boundary"] == physical_inputs["boundary"]
    assert benchmark["levels"] == physical_inputs["mesh_levels"]

    load_equivalence = base_contract["conservation"]["cross_family_physical_load_equivalence"]
    assert load_equivalence["status"] == "PASS"
    assert load_equivalence["levels"]["H3"]["resultant_difference"] == comparison["load_resultant"][
        "contract_h3_difference"
    ]
    assert load_equivalence["levels"]["H3"]["moment_difference"] == comparison["load_reference_moment"][
        "contract_h3_difference"
    ]
    assert tet["load_check"]["status"] == hex20["load_check"]["status"] == "PASS"
    assert comparison["stress_region"]["match"] is True
    assert comparison["stress_weighting"]["match"] is True
    assert comparison["stress_weighting"]["different_discrete_population_disclosed"] is True
    assert comparison["all_required_matches"] is True

    for source in sources.values():
        path_fields = (("path", "sha256"), ("result_path", "result_sha256"), ("raw_path", "raw_sha256"))
        for path_key, hash_key in path_fields:
            if path_key in source:
                source_path = ROOT / source[path_key]
                assert source_path.is_file()
                assert _sha256(source_path) == source[hash_key].lower()

    owner_review = ROOT / sources["wp05d_owner_acceptance"]["path"]
    assert "ACCEPT 1/1 technique dans le périmètre établi" in owner_review.read_text(encoding="utf-8")
    d_summary = _load(ROOT / sources["wp05d_summary"]["path"])
    assert d_summary["production_status"] == "PASS_CANDIDATE"
    assert d_summary["independent_reference_status"] == "PASS"
    assert d_summary["replay_status"] == "PASS"
    assert d_summary["candidate_points"] == "1/1"
