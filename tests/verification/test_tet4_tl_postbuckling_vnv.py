"""Optional execution of the full imperfect-column postbuckling benchmark."""

from __future__ import annotations

from pathlib import Path

import pytest

from solveur.verification.tet4_total_lagrangian_postbuckling import (
    TotalLagrangianPostbucklingCampaign,
)


@pytest.mark.benchmark
def test_tet4_total_lagrangian_postbuckling_campaign(tmp_path):
    buckling = Path("results/VNV-TET4-TL-BUCKLING-EULER-006/summary.json")
    if not buckling.is_file():
        pytest.skip("Run VNV-TET4-TL-BUCKLING-EULER-006 first.")
    summary = TotalLagrangianPostbucklingCampaign(tmp_path, buckling).run()
    assert summary["status"] == "PASS_POSTBUCKLING_RESEARCH"
