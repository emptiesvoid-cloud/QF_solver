"""WP08B invariant-geometry mixed-modal campaign guards."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_wp08b_mixed_modal import _chain_model, _mesh_metrics


ROOT = Path(__file__).resolve().parents[2]
ROOT_CAUSE = ROOT / "qualification/0_2_8/wp08b_root_cause_audit.json"
CONTRACT = ROOT / "qualification/0_2_8/wp08b_mixed_modal_contract.json"
EVIDENCE = ROOT / "qualification/0_2_8/wp08b_mixed_modal_vnv.json"
MATRIX = ROOT / "qualification/0_2_8/wp08b_mixed_modal_matrix.json"
WP08 = ROOT / "qualification/0_2_8/wp08_mixed_modal_vnv.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp08b_preserves_wp08_and_freezes_a_separate_follow_up_contract() -> None:
    audit = _load(ROOT_CAUSE)
    contract = _load(CONTRACT)
    evidence = _load(EVIDENCE)
    matrix = _load(MATRIX)

    assert audit["classification"]["primary"] == "MESH_TO_MESH_MAPPING_PROBLEM"
    assert audit["wp08_refinement_construction"]["mechanical_geometry_preserved"] is False
    assert contract["status"] == "PREDECLARED_FOLLOW_UP_CONTRACT"
    assert contract["tolerance_policy"]["fixed_before_execution"] is True
    assert contract["tolerance_policy"]["post_observation_retuning"] is False
    assert evidence["technical_decision"] == "QUALIFIED_BOUNDED_CANDIDATE"
    assert matrix["summary"]["wp08_initial_decision_preserved"] == "SUPPORTED_WITH_LIMITATIONS"
    assert matrix["summary"]["element_analysis_registry_total"] == 46
    assert matrix["summary"]["element_analysis_registry_changed"] is False
    assert _load(WP08)["technical_decision"] == "SUPPORTED_WITH_LIMITATIONS"


def test_wp08b_full_chain_preserves_the_domain_and_refinement_gates_pass() -> None:
    models = {level: _chain_model(level) for level in (1, 2, 4, 8)}
    mesh = _mesh_metrics(models)
    evidence = _load(EVIDENCE)

    assert mesh["status"] == "PASS"
    assert [mesh["levels"][str(level)]["element_count"] for level in (1, 2, 4, 8)] == [3, 5, 9, 17]
    assert evidence["mesh_refinement"]["status"] == "PASS"
    assert all(row["assignment_is_identity"] for row in evidence["mesh_refinement"]["transitions"])
    assert min(row["minimum_assigned_mac"] for row in evidence["mesh_refinement"]["transitions"]) >= 0.85
    assert all(row["maximum_frequency_relative_change"] <= 0.1 for row in evidence["mesh_refinement"]["transitions"])


def test_wp08b_bounded_candidate_gates_and_integrity_pass() -> None:
    evidence = _load(EVIDENCE)
    matrix = _load(MATRIX)

    assert evidence["mixed_mass_assembly"]["status"] == "PASS"
    assert all(row["status"] == "PASS" for row in evidence["pairwise_modal"].values())
    assert evidence["reference_oracle"]["status"] == "PASS"
    assert evidence["interface_robustness"]["status"] == "PASS"
    assert evidence["failure_contract"]["status"] == "PASS"
    assert evidence["replay_determinism"]["status"] == "PASS"
    assert evidence["post_processing_output"]["status"] == "PASS"
    assert evidence["historical_0_2_7_evidence_changed"] is False
    assert evidence["wp08_evidence_changed"] is False
    assert evidence["numerical_source_changed"] is False
    assert matrix["registry_integrity"]["not_added_to_element_analysis_registry"] is True
