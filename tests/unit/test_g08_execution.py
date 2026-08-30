"""Schema checks for the controlled G08 execution harness."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"


def test_g08_execution_harness_declares_owner_policies_before_execution() -> None:
    source = (ROOT / "scripts" / "run_g08_vnv.py").read_text(encoding="utf-8")
    assert "EULER_RELATIVE_TOLERANCE = 0.10" in source
    assert "CALCULIX_RELATIVE_TOLERANCE = 0.10" in source
    assert "RESIDUAL_PASS = 1.0e-7" in source
    assert "RESIDUAL_WARNING = 1.0e-5" in source


def test_g08_execution_contract_remains_open_before_numeric_campaign() -> None:
    contract = json.loads((DATA / "g08_requirements.json").read_text(encoding="utf-8"))
    assert contract["gate_boundary"]["current_gate_status"] == "NOT_STARTED"
    assert contract["scope"]["first_mode_only"] is True
    assert contract["scope"]["families_supported_by_route"] == ["TET4", "TET10", "HEX8", "HEX20"]


def test_g08_execution_harness_does_not_promote_external_unavailability() -> None:
    source = (ROOT / "scripts" / "run_g08_vnv.py").read_text(encoding="utf-8")
    assert "SKIPPED_EXTERNAL_UNAVAILABLE" in source
    assert "PASS_EXTERNAL_CORRELATION_BOUNDED" in source
    assert "no universal mesh claim" in source
