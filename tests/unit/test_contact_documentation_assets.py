"""Generated documentation assets for the controlled contact studies."""

from scripts.docs_contact import publish_contact_verification


def test_contact_publisher_includes_the_structural_friction_evidence(tmp_path) -> None:
    generated = tmp_path / "generated"
    assets = tmp_path / "assets"
    generated.mkdir()
    assets.mkdir()

    publish_contact_verification(generated, assets)

    assert (generated / "contact_friction_checks.md").is_file()
    assert (generated / "contact_friction_structural_checks.md").is_file()
    assert (generated / "contact_friction_code_aster_checks.md").is_file()
    assert (assets / "contact_friction_block_comparison.png").stat().st_size > 10_000
    assert (assets / "contact_friction_structural_convergence.png").stat().st_size > 10_000
    assert (assets / "contact_friction_code_aster_comparison.png").stat().st_size > 10_000
