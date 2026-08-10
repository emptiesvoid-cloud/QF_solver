"""Run and publish the bounded external Code_Aster sliding-contact correlation."""

from __future__ import annotations

import argparse
import shutil
from typing import Any
from pathlib import Path

from solveur.io.manifest import sha256, write_json_file
from solveur.verification.code_aster_friction_contact import CodeAsterFrictionContactCampaign


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    """Execute the pinned external oracle and copy its reviewable evidence."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = CodeAsterFrictionContactCampaign(args.output).run()
    _publish(args.output.resolve(), summary)
    print(f"{summary['study_id']}: {summary['status']}")
    return 0 if str(summary["status"]).startswith("PASS") else 1


def _publish(output: Path, summary: dict[str, Any]) -> None:
    """Archive internal evidence and a host-neutral public digest separately."""
    reference = ROOT / "qualification" / "vnv" / "external" / "code_aster_friction_contact" / "reference"
    # Preserve the normalized summary *and* the raw decks/logs named by the
    # manifest. A partial copy would make an apparently valid fingerprint
    # unverifiable during a later mechanical review.
    shutil.copytree(output, reference, dirs_exist_ok=True)
    public_dir = ROOT / "qualification" / "external_reference_digests"
    public_dir.mkdir(parents=True, exist_ok=True)
    public_figure = ROOT / "docs" / "assets" / "references" / "contact_friction_code_aster_comparison.png"
    public_figure.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(output / "code_aster_friction_comparison.png", public_figure)
    digest = {
        "schema_version": 1,
        "study_id": summary["study_id"],
        "status": summary["status"],
        "maturity": summary["maturity"],
        "scope": summary["scope"],
        "external_solver": summary["external_solver"],
        "model": summary["model"],
        "cases": summary["cases"],
        "checks": summary["checks"],
        "limitations": summary["limitations"],
        "figure_path": "docs/assets/references/contact_friction_code_aster_comparison.png",
        "figure_sha256": sha256(public_figure),
        "provenance": "Pinned Docker execution; raw decks and logs are retained in internal ignored evidence.",
    }
    write_json_file(public_dir / "code_aster_friction_contact.json", digest)


if __name__ == "__main__":
    raise SystemExit(main())
