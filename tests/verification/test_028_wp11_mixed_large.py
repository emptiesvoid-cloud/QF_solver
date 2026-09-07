"""Contract guards for the WP11 mixed large-scale evidence pack."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "qualification" / "0_2_8" / "wp11_mixed_large_vnv.json"
MATRIX = ROOT / "qualification" / "0_2_8" / "wp11_mixed_large_matrix.json"


def test_wp11_mandatory_pack_passes_without_expanding_scope() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    mandatory = evidence["mandatory_300k"]
    assert evidence["status"] == "PASS"
    assert mandatory["manifest"]["dof"] >= 300_000
    assert mandatory["manifest"]["elements_by_family"] == {"TET4": 9091, "WEDGE6": 9091, "HEX8": 9091}
    assert mandatory["replay_determinism"] is True
    assert all(replay["finite_solution"] for replay in mandatory["replays"])
    assert all(replay["physics_digest"] == mandatory["replays"][0]["physics_digest"] for replay in mandatory["replays"])
    assert all(evidence["gates"].values())
    assert evidence["desired_1m"]["status"] == "NOT_RUN_NON_BLOCKER"
    assert evidence["stretch_3m"]["status"] == "NOT_RUN_NON_BLOCKER"


def test_wp11_matrix_preserves_bounded_claim_and_integrity() -> None:
    matrix = json.loads(MATRIX.read_text(encoding="utf-8"))
    assert matrix["mandatory_status"] == "PASS"
    assert matrix["decision"] == "PASS_WITH_BOUNDED_EVIDENCE"
    assert matrix["integrity"] == {
        "numerical_source_changed": False,
        "historical_0_2_7_evidence_changed": False,
        "wp01_wp10_records_changed": False,
    }
    assert any("not an arbitrary connected industrial mesh" in item.lower() for item in matrix["limitations"])
