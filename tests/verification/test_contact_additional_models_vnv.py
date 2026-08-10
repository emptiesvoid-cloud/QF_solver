from __future__ import annotations

from solveur.verification.contact_additional_models import AdditionalContactModelsCampaign


def test_three_additional_contact_models_pass(tmp_path) -> None:
    summary = AdditionalContactModelsCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert {case["id"] for case in summary["cases"]} == {
        "dual_stop_corner",
        "faceted_ramp_patch",
        "deformable_tet4_two_slaves",
    }
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert (tmp_path / "additional_contact_models.png").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()
