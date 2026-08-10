"""Publication helpers for the controlled node-to-triangle contact studies."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from scripts.docs_support import write_markdown_table
from solveur.io.manifest import sha256
from solveur.verification.frictional_contact import FrictionalContactVerificationCampaign
from solveur.verification.frictional_contact_structural import FrictionalStructuralContactCampaign
from solveur.verification.frictionless_contact_structural import FrictionlessStructuralContactCampaign


def publish_contact_verification(generated: str | Path, assets: str | Path) -> None:
    """Regenerate and publish the analytical and structural contact evidence."""
    generated_path, assets_path = Path(generated), Path(assets)
    friction_output = generated_path / "contact_friction"
    friction = FrictionalContactVerificationCampaign(friction_output).run()
    _require_pass(friction, "The internal frictional-contact analytical campaign did not pass.")
    shutil.copy2(friction_output / "friction_block_comparison.png", assets_path / "contact_friction_block_comparison.png")
    _write_checks(generated_path / "contact_friction_checks.md", friction)

    friction_structural_output = generated_path / "contact_friction_structural"
    friction_structural = FrictionalStructuralContactCampaign(friction_structural_output).run()
    _require_pass(friction_structural, "The structural frictional-contact refinement campaign did not pass.")
    shutil.copy2(
        friction_structural_output / "friction_structural_convergence.png",
        assets_path / "contact_friction_structural_convergence.png",
    )
    _write_checks(generated_path / "contact_friction_structural_checks.md", friction_structural)

    structural_output = generated_path / "contact_structural"
    structural = FrictionlessStructuralContactCampaign(structural_output).run()
    _require_pass(structural, "The structural TET4 contact-refinement campaign did not pass.")
    for name in ("contact_structural_convergence.png", "contact_structural_deformation.png"):
        shutil.copy2(structural_output / name, assets_path / name)
    _write_checks(generated_path / "contact_structural_checks.md", structural)
    _publish_external_friction_reference(generated_path, assets_path)


def _require_pass(summary: dict[str, Any], message: str) -> None:
    if summary.get("status") != "PASS_INTERNAL":
        raise RuntimeError(message)


def _write_checks(path: Path, summary: dict[str, Any]) -> None:
    write_markdown_table(
        path,
        ("Critere", "Valeur", "Limite", "Verdict"),
        [
            (check["name"], check["value"], check["limit"], check["status"] == "PASS")
            for check in summary["checks"]
        ],
    )


def _publish_external_friction_reference(generated: Path, assets: Path) -> None:
    """Publish only an integrity-checked, already executed Docker oracle result."""
    root = Path(__file__).resolve().parents[1]
    source = root / "qualification" / "external_reference_digests" / "code_aster_friction_contact.json"
    figure = root / "docs" / "assets" / "references" / "contact_friction_code_aster_comparison.png"
    if not source.is_file() or not figure.is_file():
        raise RuntimeError("Public Code_Aster friction digest is missing; run its explicit Docker script first.")
    summary = json.loads(source.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS_EXTERNAL_CORRELATION":
        raise RuntimeError("Controlled Code_Aster friction evidence is not accepted.")
    if sha256(figure) != str(summary.get("figure_sha256", "")):
        raise RuntimeError(f"Public Code_Aster friction figure failed SHA-256 verification: {figure}")
    shutil.copy2(figure, assets / "contact_friction_code_aster_comparison.png")
    write_markdown_table(
        generated / "contact_friction_code_aster_checks.md",
        ("Critere", "Valeur", "Limite", "Verdict"),
        [
            (check["id"], check["value"], check["limit"], check["status"] == "PASS")
            for check in summary["checks"]
        ],
    )
