"""Acceptance checks for the TET4 structural friction-refinement campaign."""

from solveur.verification.frictional_contact_structural import FrictionalStructuralContactCampaign


def test_frictional_structural_contact_refinement_is_reviewable(tmp_path) -> None:
    summary = FrictionalStructuralContactCampaign(tmp_path).run()

    assert summary["status"] == "PASS_INTERNAL"
    assert len(summary["levels"]) == 4
    assert all(check["status"] == "PASS" for check in summary["checks"])
    assert (tmp_path / "friction_structural_convergence.png").stat().st_size > 10_000
    assert (tmp_path / "report.md").is_file()
    assert (tmp_path / "vnv_manifest.json").is_file()
