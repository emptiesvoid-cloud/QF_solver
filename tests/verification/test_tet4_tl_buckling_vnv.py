"""Optional execution of the full Euler buckling benchmark."""

from __future__ import annotations

import pytest

from solveur.verification.tet4_total_lagrangian_buckling import (
    TotalLagrangianBucklingCampaign,
)


@pytest.mark.benchmark
def test_tet4_total_lagrangian_buckling_campaign(tmp_path):
    summary = TotalLagrangianBucklingCampaign(tmp_path).run()
    assert summary["status"] == "PASS_BUCKLING_RESEARCH"
