"""WP11B experimental-readiness and historical non-promotion guards."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qualification/0_2_8/wp11b_hex8_buckling_experimental_vnv.json"
MATRIX = ROOT / "qualification/0_2_8/wp11b_hex8_buckling_experimental_matrix.json"
WP06 = ROOT / "qualification/0_2_8/wp06_hex8_buckling_vnv.json"
WP06B = ROOT / "qualification/0_2_8/wp06b_hex8_buckling_vnv.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def test_wp11b_is_experimental_candidate_only() -> None:
    evidence = _load(EVIDENCE)
    assert evidence["decision"] == "EXPERIMENTAL_CANDIDATE"
    assert evidence["proposed_public_status"] == "EXPERIMENTAL"
    assert evidence["owner_gate_required"] is True
    assert evidence["gates"]["primary_internal_checks"] == "PASS"
    assert evidence["gates"]["physical_scaling"] == "PASS"
    assert evidence["gates"]["invalid_geometry"] is True
    assert evidence["gates"]["replay_determinism"] is True
    assert evidence["external_oracle"]["status"] == "NOT_AVAILABLE"
    assert evidence["benchmark"]["refinement_characterization"].startswith("CHARACTERIZED_ONLY")


def test_wp11b_preserves_wp06_failures_and_integrity() -> None:
    evidence = _load(EVIDENCE)
    matrix = _load(MATRIX)
    wp06 = _load(WP06)
    wp06b = _load(WP06B)
    assert wp06["technical_decision"] == "NOT_QUALIFIED"
    assert wp06b["technical_decision"] == "NOT_QUALIFIED"
    assert evidence["historical_preservation"]["wp06_euler_fail_preserved"] is True
    assert evidence["historical_preservation"]["wp06_convergence_fail_preserved"] is True
    assert evidence["integrity"] == {
        "numerical_source_changed": False,
        "bugs_found": False,
        "bugs_fixed": False,
        "predeclared_gates_changed": False,
    }
    assert matrix["owner_gate_required"] is False
    assert matrix["final_status"] == "EXPERIMENTAL"
    assert matrix["technical_decision"] == "EXPERIMENTAL_CANDIDATE"
