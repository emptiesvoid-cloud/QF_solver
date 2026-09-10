"""Executable gates for the 0.2.8 WEDGE6 static V&V campaign."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_wp05_wedge6 import (
    CONTRACT,
    HISTORICAL_EXTERNAL,
    _elemental_checks,
    _face_load_checks,
    _geometry_checks,
)


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qualification/0_2_8/wp05_wedge6_vnv.json"
MATRIX = ROOT / "qualification/0_2_8/wp05_maturity_matrix.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp05_contract_evidence_and_matrix_are_bounded() -> None:
    contract = _load(CONTRACT)
    evidence = _load(EVIDENCE)
    matrix = _load(MATRIX)

    assert contract["status"] == "PREDECLARED_CAMPAIGN_CONTRACT"
    assert contract["baseline_sha"] == "0ad191a41b45283cff53bb461996b08c8dc2739a"
    assert contract["tolerance_policy"]["fixed_before_execution"] is True
    assert contract["tolerance_policy"]["post_observation_retuning"] is False
    assert evidence["technical_decision"] == "QUALIFIED_BOUNDED"
    assert evidence["public_maturity"] == "QUALIFIED_BOUNDED"
    assert evidence["owner_gate_required"] is False
    assert evidence["historical_0_2_7_evidence_modified"] is False
    assert evidence["numerical_source_modified"] is False
    assert matrix["status"] == "OWNER_GATE_FINALIZED"
    assert matrix["summary"]["public_maturity_relabels_applied"] == 1
    assert matrix["decisions"][0]["source_record"] == "COMB-WEDGE6-linear_static"
    assert matrix["decisions"][0]["decision"] == "QUALIFIED_BOUNDED"
    assert matrix["decisions"][0]["promotion_applied"] is True


def test_wp05_replays_and_declared_verdicts_are_deterministic() -> None:
    evidence = _load(EVIDENCE)
    for key, expected_count in (("wp07", 8), ("wp08", 15), ("wp09", 22)):
        summary = evidence["current_replays"][key]
        assert summary["case_count"] == expected_count
        assert summary["deterministic"] is True
        assert summary["replay_digests"][0] == summary["replay_digests"][1]
        assert summary["all_declared_verdicts_pass"] is True


def test_wp05_current_elemental_face_and_geometry_gates_hold() -> None:
    evidence = _load(EVIDENCE)
    contract = _load(CONTRACT)
    tolerance = contract["tolerance_policy"]
    elemental = _elemental_checks()
    faces = _face_load_checks()
    geometry = _geometry_checks()

    assert evidence["checks"]["elemental"]["status"] == "PASS"
    assert elemental["stiffness_rank"] == tolerance["stiffness_rank"]
    assert elemental["stiffness_symmetry_relative"] <= tolerance["stiffness_symmetry_relative"]
    assert elemental["rigid_body_residual_relative"] <= tolerance["rigid_body_residual_relative"]
    assert elemental["production_reference_stiffness_relative"] <= tolerance["production_reference_stiffness_relative"]
    assert faces["triangular_faces_checked"] == 2
    assert faces["quadrilateral_faces_checked"] == 3
    assert faces["pressure_all_faces_max_relative_error"] <= tolerance["load_resultant_relative"]
    assert faces["traction_relative_error"] <= tolerance["load_resultant_relative"]
    assert geometry["nominal"] == "VALID"
    assert geometry["valid_skew"] == "VALID"
    assert geometry["near_degenerate"] == "VALID_WITH_WARNING"
    assert geometry["flat"] == "INVALID"
    assert geometry["inverted"] == "INVALID"
    assert geometry["direct_invalid_geometry_rejected"] is True


def test_wp05_external_artifact_is_independent_complete_and_not_rewritten() -> None:
    evidence = _load(EVIDENCE)
    external = evidence["checks"]["external_oracle"]["observed"]
    historical = _load(HISTORICAL_EXTERNAL)

    assert external["executed_in_wp05"] is False
    assert external["independent_comparable"] is True
    assert external["current_numeric_source_unchanged_since_external"] is True
    assert external["external_pass"] == 12
    assert external["external_fail"] == 0
    assert external["external_skipped"] == 0
    assert historical["calculix"]["verdict"] == "NOT_COMPARABLE"
    assert historical["legacy_internal_corpus"]["preserved"] is True
