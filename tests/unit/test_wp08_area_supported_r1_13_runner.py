"""Provenance and fail-closed checks for the R1.13 contact campaign."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from scripts import run_wp08_area_supported_m1_diagnostic_r1_10 as runner


def test_r1_13_freeze_fails_closed_without_preserved_r1_11_evidence(
    tmp_path: Path, monkeypatch: Any
) -> None:
    """Missing predecessor evidence blocks freeze rather than being fabricated."""
    monkeypatch.setattr(runner, "CAMPAIGN_REVISION", "R1.13")
    monkeypatch.setattr(
        runner, "ARTIFACT_ID", "QF-029-WP08-AREA-SUPPORTED-CONTACT-DIAGNOSTIC-R1.13"
    )
    monkeypatch.setattr(
        runner,
        "CONTRACT_DOCUMENT_REL",
        Path("docs/verification/0_2_9/wp08-area-supported-contact-r1-13-normalized-merit.md"),
    )

    with pytest.raises(FileNotFoundError, match="R1.13 requires the preserved R1.11 M1/M2/M3 evidence"):
        runner._contract(tmp_path, owner_authorized=True)
