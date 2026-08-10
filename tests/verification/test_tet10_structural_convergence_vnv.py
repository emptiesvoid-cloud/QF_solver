from __future__ import annotations

from pathlib import Path

import pytest

from solveur.verification.tet10_structural_convergence import Tet10StructuralConvergenceCampaign


@pytest.mark.benchmark
def test_tet10_structural_convergence_campaign_passes(tmp_path: Path) -> None:
    pytest.importorskip("gmsh")

    summary = Tet10StructuralConvergenceCampaign(tmp_path).run()

    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    for problem in ("traction", "bending", "torsion"):
        assert len(summary[problem]["families"]["TET4"]["levels"]) == 4
        assert len(summary[problem]["families"]["TET10"]["levels"]) == 4
    assert (tmp_path / "tet10_structural_convergence.png").stat().st_size > 1000
