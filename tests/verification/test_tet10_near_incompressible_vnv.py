from __future__ import annotations

from pathlib import Path

import pytest

from solveur.verification.tet10_near_incompressible import Tet10NearIncompressibleCampaign


@pytest.mark.benchmark
def test_tet10_near_incompressible_campaign_completes(tmp_path: Path) -> None:
    pytest.importorskip("gmsh")

    summary = Tet10NearIncompressibleCampaign(tmp_path).run()

    assert summary["status"] == "PASS_CHARACTERIZATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
