"""Contract checks for the independent high-order Euler screen."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_high_order_euler_harness_declares_scope_before_execution() -> None:
    source = (ROOT / "scripts" / "run_g08_high_order_analytical.py").read_text(encoding="utf-8")
    assert "EULER_RELATIVE_TOLERANCE = 0.10" in source
    assert "EIGENPAIR_RESIDUAL_PASS = 1.0e-7" in source
    assert "REFERENCE_LOAD = -1.0" in source
    assert "MESH_LEVELS = (1, 2, 3)" in source
    assert "TRANSVERSE_LEVELS = (1, 2, 3)" in source
    assert "pcr_qf_signed" in source
    assert "loaded_node_count" in source
    assert "gate_status_unchanged" in source
    assert "No family is promoted automatically" in source


def test_high_order_euler_evidence_if_present_is_bounded() -> None:
    path = ROOT / "qualification" / "0_2_6" / "g08_high_order_analytical_evidence.json"
    if not path.is_file():
        return
    evidence = json.loads(path.read_text(encoding="utf-8"))
    assert evidence["gate"] == "026-G08"
    assert evidence["gate_status_unchanged"] == "PASS_WITH_LIMITATIONS"
    assert evidence["source_dirty"] is False
    assert evidence["families"] == ["TET10", "HEX8", "HEX20"]
    assert evidence["mesh_levels"] == [1, 2, 3]
    assert evidence["promotion"]["automatic"] is False
