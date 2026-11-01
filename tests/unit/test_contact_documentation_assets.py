"""Generated documentation assets for the controlled contact studies."""

from pathlib import Path
from scripts import docs_contact


def test_contact_publisher_copies_campaign_assets_without_running_fem(tmp_path, monkeypatch) -> None:
    generated = tmp_path / "generated"
    assets = tmp_path / "assets"
    generated.mkdir()
    assets.mkdir()
    fixture_image = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "assets"
        / "reviews"
        / "contact_additional_models.png"
    )
    campaign_calls = []

    def fake_campaign_run(name, output_names):
        def run(campaign):
            campaign_calls.append(name)
            campaign.output_dir.mkdir(parents=True, exist_ok=True)
            for output_name in output_names:
                (campaign.output_dir / output_name).write_bytes(fixture_image.read_bytes())
            return {
                "status": "PASS_INTERNAL",
                "checks": [{"name": f"{name}-fixture", "value": 1.0, "limit": 1.0, "status": "PASS"}],
            }

        return run

    # Keep this publisher-wiring test separate from the controlled campaign solvers.
    monkeypatch.setattr(
        docs_contact.FrictionalContactVerificationCampaign,
        "run",
        fake_campaign_run("friction", ("friction_block_comparison.png",)),
    )
    monkeypatch.setattr(
        docs_contact.FrictionalStructuralContactCampaign,
        "run",
        fake_campaign_run("frictional-structural", ("friction_structural_convergence.png",)),
    )
    monkeypatch.setattr(
        docs_contact.FrictionlessStructuralContactCampaign,
        "run",
        fake_campaign_run(
            "frictionless-structural",
            ("contact_structural_convergence.png", "contact_structural_deformation.png"),
        ),
    )

    docs_contact.publish_contact_verification(generated, assets)

    assert campaign_calls == ["friction", "frictional-structural", "frictionless-structural"]
    assert (generated / "contact_friction_checks.md").is_file()
    assert (generated / "contact_friction_structural_checks.md").is_file()
    assert (generated / "contact_structural_checks.md").is_file()
    assert (generated / "contact_friction_code_aster_checks.md").is_file()
    assert (assets / "contact_friction_block_comparison.png").stat().st_size > 10_000
    assert (assets / "contact_friction_block_comparison.png").read_bytes() == fixture_image.read_bytes()
    assert (assets / "contact_friction_structural_convergence.png").stat().st_size > 10_000
    assert (assets / "contact_friction_structural_convergence.png").read_bytes() == fixture_image.read_bytes()
    assert (assets / "contact_friction_code_aster_comparison.png").stat().st_size > 10_000
