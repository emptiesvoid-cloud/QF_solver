"""One registered constant-domain HEX8-SRI distortion sweep for J9."""

from __future__ import annotations

from research.j9_hex8.controlled_distortion import run_controlled_distortion


def test_j9_hex8_constant_domain_distortion_sweep() -> None:
    result = run_controlled_distortion()
    assert result["execution_status"] == "COMPLETED_EXPLORATORY"
    assert all(result["structural_checks"].values())
    assert len(result["levels"]) == 4
    assert result["state_npz"]["sha256"]
    assert result["figure"]["sha256"]
