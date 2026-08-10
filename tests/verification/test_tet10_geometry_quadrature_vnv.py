from __future__ import annotations

import json
from pathlib import Path

from solveur.verification.tet10_geometry_quadrature import Tet10GeometryQuadratureCampaign


def test_tet10_geometry_quadrature_campaign_passes(tmp_path: Path) -> None:
    summary = Tet10GeometryQuadratureCampaign(tmp_path).run()

    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert len(summary["cases"]) == 4
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["invalid_geometry_rejected"] is True
    assert (tmp_path / "tet10_quadrature_convergence.png").stat().st_size > 1000
    manifest = json.loads((tmp_path / "vnv_manifest.json").read_text(encoding="utf-8"))
    assert manifest["study_id"] == Tet10GeometryQuadratureCampaign.study_id
    assert manifest["source"]["repository"] == "."
