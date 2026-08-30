"""Contracts for the controlled HEX20 CalculiX rescue evidence."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_hex20_rescue_evidence_is_bounded_and_does_not_close_g08() -> None:
    evidence = json.loads(
        (ROOT / "qualification" / "0_2_6" / "g08_hex20_calculix_rescue_evidence.json").read_text(
            encoding="utf-8"
        )
    )
    assert evidence["gate"] == "026-G08"
    assert evidence["status"] == "PASS_EXTERNAL_CORRELATION_BOUNDED"
    assert evidence["gate_status_unchanged"] == "PASS_WITH_LIMITATIONS"
    assert evidence["source_dirty"] is False
    assert evidence["root_cause"]["classification"] == "DECK_GENERATION"
    assert evidence["root_cause"]["functional_solver_code_changed"] is False
    assert evidence["policies"]["correlation_tolerance"] == 0.10
    assert evidence["scope"]["mesh_levels"] == [1, 2, 4]
    assert "4-cell" in (ROOT / "qualification" / "0_2_6" / "g08_hex20_calculix_rescue_evidence.md").read_text(
        encoding="utf-8"
    )
    for level in evidence["mesh_levels"]:
        assert level["first"]["status"] == "PASS"
        assert level["replay"]["status"] == "PASS"
        assert level["replay_within_tolerance"] is True
        assert level["first"]["relative_difference"] < 0.10
        mode = level["first"]["mode_comparison"]
        assert mode["status"] == "RECORDED_NO_OWNER_MAC_THRESHOLD"
        assert 0.0 <= mode["mac"] <= 1.0

    gates = json.loads((ROOT / "qualification" / "0_2_6" / "gates.json").read_text(encoding="utf-8"))
    g08 = next(item for item in gates["gates"] if item["id"] == "026-G08")
    assert g08["status"] == "PASS_WITH_LIMITATIONS"
    assert "g08_hex20_calculix_rescue_evidence.json" in g08["evidence_ids"]
    assert "g08_hex20_calculix_rescue_evidence.md" in g08["evidence_ids"]


def test_rescue_runner_forces_local_source_and_preserves_gate_status() -> None:
    source = (ROOT / "scripts" / "run_g08_hex20_calculix_rescue.py").read_text(encoding="utf-8")
    assert "sys.path.insert(0, str(ROOT / \"src\"))" in source
    assert "gate_status_unchanged" in source
    assert "no external MAC threshold" in source
