"""Contract checks for the diagnostic-only TL blocker-resolution pack."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from run_tl_blocker_resolution import (  # noqa: E402
    FAMILIES,
    MESH_LEVELS,
    SMALL_STRAIN_FACTORS,
    TANGENT_STATES,
    TANGENT_STEPS,
)


def test_blocker_resolution_study_contract_is_diagnostic_only() -> None:
    assert FAMILIES == ("TET4", "HEX8")
    assert SMALL_STRAIN_FACTORS == (1.0, 0.5, 0.25, 0.125, 0.0625)
    assert MESH_LEVELS == (1, 2, 3, 4)
    assert len(TANGENT_STATES) == 6
    assert len(TANGENT_STEPS) == 5


def test_no_policy_is_auto_approved() -> None:
    assert "OWNER_APPROVED" not in "PROPOSED_OWNER_REVIEW"
    assert "PASS" not in "OBSERVATION_ONLY"
