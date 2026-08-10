"""Acceptance checks for the assembled TET4 unilateral-contact refinement study."""

import json

from PIL import Image

from solveur.verification.frictionless_contact_structural import FrictionlessStructuralContactCampaign


def test_structural_tet4_contact_refinement_is_closed_convergent_and_reviewable(tmp_path) -> None:
    summary = FrictionlessStructuralContactCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert len(summary["levels"]) == 4
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert summary["levels"][-1]["pressure_change_from_previous"] < 0.03
    assert (tmp_path / "contact_structural_convergence.png").stat().st_size > 10_000
    image_path = tmp_path / "contact_structural_deformation.png"
    assert image_path.stat().st_size > 10_000
    with Image.open(image_path).convert("RGB") as image:
        colored = sum(max(pixel) - min(pixel) > 20 for pixel in image.getdata())
    assert colored > 5000
    assert (tmp_path / "vnv_manifest.json").is_file()
    stored = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    report = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert stored == summary
    assert summary["campaign_id"] in report
    assert "surface-a-surface" in report
