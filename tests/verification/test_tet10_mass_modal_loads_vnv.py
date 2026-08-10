from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from solveur.verification.tet10_mass_modal_loads import Tet10MassModalLoadsCampaign


@pytest.mark.benchmark
def test_tet10_mass_modal_loads_campaign_passes(tmp_path: Path) -> None:
    pytest.importorskip("gmsh")

    summary = Tet10MassModalLoadsCampaign(tmp_path).run()

    assert summary["status"] == "PASS_TECHNICAL_VERIFICATION"
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert len(summary["modal"]["frequencies_hz"]) == 6
    image_path = tmp_path / "tet10_modal_mode1.png"
    assert image_path.stat().st_size > 1000
    with Image.open(image_path).convert("RGB") as image:
        colored = sum(max(pixel) - min(pixel) > 20 for pixel in image.getdata())
    assert colored > 5000
