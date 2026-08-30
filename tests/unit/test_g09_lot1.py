"""Controlled contract and evidence checks for 026-G09 Lot 1."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.run_g09_lot1 import _expected_penetration_failure


ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "qualification" / "0_2_6"


def test_g09_contract_is_bounded_and_does_not_close_the_gate() -> None:
    contract = json.loads((DATA / "g09_requirements.json").read_text(encoding="utf-8"))
    assert contract["gate"] == "026-G09"
    assert contract["status"] == "CONTRACT_READY_NOT_CLOSED"
    assert contract["scope"]["formulation"] == "frictionless_penalty"
    assert contract["scope"]["finite_sliding"] is False
    assert contract["penalty_policy"]["predeclared"] is True
    assert len(contract["requirements"]) == 8


def test_g09_case_registry_keeps_unsupported_scope_explicit() -> None:
    registry = json.loads((DATA / "g09_case_registry.json").read_text(encoding="utf-8"))
    assert registry["gate"] == "026-G09"
    assert sum(row["status"] == "READY" for row in registry["cases"]) == 5
    assert sum(row["status"] == "NOT_SUPPORTED" for row in registry["cases"]) == 1


def test_g09_excessive_penetration_fails_closed() -> None:
    result = _expected_penetration_failure()
    assert result["status"] == "EXPECTED_FAILURE"
    assert result["converged"] is False
    assert result["fail_closed"] is True
    assert result["reason"] == "CONTACT_PENETRATION_EXCESSIVE"
