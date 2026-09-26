"""Provenance and fail-closed checks for the R1.13 contact campaign."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts import run_wp08_area_supported_m1_diagnostic_r1_10 as runner


def test_r1_13_freeze_binds_r1_11_pass_and_r1_12_failure_immutably(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """R1.13 must retain both the latest full campaign and intervening M4 failure."""
    monkeypatch.setattr(runner, "CAMPAIGN_REVISION", "R1.13")
    monkeypatch.setattr(
        runner, "ARTIFACT_ID", "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.13"
    )
    monkeypatch.setattr(
        runner,
        "CONTRACT_DOCUMENT_REL",
        Path("docs/verification/0_2_9/wp08-area-supported-contact-r1-13-normalized-merit.md"),
    )

    contract, inventory, source_bundle_sha = runner._contract(tmp_path, owner_authorized=True)

    assert contract["campaign_revision"] == "R1.13"
    assert contract["previous_revision"]["revision"] == "R1.11"
    assert contract["previous_revision"]["status"] == "M1_M2_M3_DIAGNOSTIC_CASES_PASS_REFINEMENT_UNCLASSIFIED"
    assert contract["intervening_m4_diagnostic"]["revision"] == "R1.12"
    assert contract["intervening_m4_diagnostic"]["status"] == "FAIL_CLOSED_NUMERICAL"
    assert contract["intervening_m4_diagnostic"]["preserved_without_rewrite"] is True
    assert contract["formal_wp08_qualification"] is False
    assert contract["points_awarded"] is False
    assert "tests/unit/test_wp08_area_supported_r1_13_runner.py" in inventory
    assert source_bundle_sha == runner._canonical_sha(inventory)
